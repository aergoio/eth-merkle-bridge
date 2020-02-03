import argparse
from getpass import getpass
import json
import requests
import time
import threading
import traceback
from typing import (
    Tuple,
    List,
)

import aergo.herapy as herapy
from aergo.herapy.errors.general_exception import (
    GeneralException as HeraException,
)

from ethaergo_bridge_operator.op_utils import (
    query_aergo_tempo,
    query_aergo_validators,
    query_unfreeze_fee,
    load_config_data,
    query_aergo_oracle,
)
from ethaergo_bridge_operator.proposer.exceptions import (
    ValidatorMajorityError,
)
from web3 import (
    Web3,
)
from web3.middleware import (
    geth_poa_middleware,
)
from ethaergo_bridge_operator.proposer.aergo.validator_connect import (
    AergoValConnect,
)
from ethaergo_bridge_operator.proposer.aergo.transact import (
    AergoTx,
)
import logging

logger = logging.getLogger(__name__)


class AergoProposerClient(threading.Thread):
    """The aergo bridge proposer periodically (every t_anchor) broadcasts
    the finalized trie state root (after lib)
    onto the aergo bridge contract after validation by the Validator servers.
    It first checks the last merged height and waits until
    now > lib + t_anchor is reached, then merges the current finalised
    block (lib). If bridge_anchoring is True(default), then the proposer will
    create a Merkle proof of the bridge storage root to anchor both roots in
    the same transaction. Start again after waiting t_anchor.

    Note on config_data:
        - config_data is used to store current validators and their ip when the
          proposer starts. (change validators after the proposer has started)
        - After starting, when users change the config.json, the proposer will
          attempt to gather signatures to reflect the changes.
        - t_anchor value is always taken from the bridge contract
        - validators are taken from the config_data because ip information is
          not stored on chain
        - when a validator set update succeeds, self.config_data is updated
        - if another proposer updates to a new set of validators and the
          proposer doesnt know about it, proposer must be restarted with the
          new current validator set to create new connections to them.

    """

    def __init__(
        self,
        config_file_path: str,
        aergo_net: str,
        eth_net: str,
        eth_block_time: int,
        privkey_name: str = None,
        privkey_pwd: str = None,
        anchoring_on: bool = False,
        auto_update: bool = False,
        oracle_update: bool = False,
        aergo_gas_price: int = None,
        bridge_anchoring: bool = True,
        root_path: str = './',
        eco: bool = False
    ) -> None:
        threading.Thread.__init__(self, name="AergoProposerClient")
        if aergo_gas_price is None:
            aergo_gas_price = 0
        self.aergo_gas_price = aergo_gas_price
        self.config_file_path = config_file_path
        config_data = load_config_data(self.config_file_path)
        self.eth_block_time = eth_block_time
        self.eth_net = eth_net
        self.aergo_net = aergo_net
        self.anchoring_on = anchoring_on
        self.auto_update = auto_update
        self.oracle_update = oracle_update
        self.bridge_anchoring = bridge_anchoring
        self.eco = eco

        logger.info("\"Connect Aergo and Ethereum providers\"")
        self.hera = herapy.Aergo()
        self.hera.connect(config_data['networks'][aergo_net]['ip'])

        ip = config_data['networks'][eth_net]['ip']
        self.web3 = Web3(Web3.HTTPProvider(ip))
        eth_poa = config_data['networks'][eth_net]['isPOA']
        if eth_poa:
            self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        assert self.web3.isConnected()

        eth_bridge_abi_path = (config_data['networks'][eth_net]['bridges']
                               [aergo_net]['bridge_abi'])
        with open(root_path + eth_bridge_abi_path, "r") as f:
            eth_bridge_abi = f.read()
        self.eth_bridge_addr = (config_data['networks'][eth_net]['bridges']
                                [aergo_net]['addr'])
        self.eth_bridge = self.web3.eth.contract(
            address=self.eth_bridge_addr,
            abi=eth_bridge_abi
        )

        self.aergo_bridge = (config_data['networks'][aergo_net]['bridges']
                             [eth_net]['addr'])
        self.aergo_oracle = (config_data['networks'][aergo_net]['bridges']
                             [eth_net]['oracle'])

        # get the current t_anchor and t_final for both sides of bridge
        self.t_anchor, self.t_final = query_aergo_tempo(
            self.hera, self.aergo_bridge
        )
        logger.info(
            "\"%s <- %s (t_final=%s) : t_anchor=%s\"", aergo_net, eth_net,
            self.t_final, self.t_anchor
        )

        if not anchoring_on and not auto_update:
            # if anchoring and auto update are off, use proposer as monitoring
            # system
            return

        if privkey_name is None:
            privkey_name = 'proposer'
        sender_priv_key = config_data['wallet'][privkey_name]['priv_key']
        if privkey_pwd is None:
            while True:
                try:
                    privkey_pwd = getpass(
                        "Decrypt Aergo exported private key '{}'\nPassword: "
                        .format(privkey_name)
                    )
                    self.aergo_tx = AergoTx(
                        self.hera, sender_priv_key, privkey_pwd,
                        self.aergo_oracle, aergo_gas_price, self.t_anchor,
                        eth_block_time
                    )
                    break
                except HeraException:
                    logger.info("\"Wrong password, try again\"")
        else:
            self.aergo_tx = AergoTx(
                self.hera, sender_priv_key, privkey_pwd, self.aergo_oracle,
                aergo_gas_price, self.t_anchor, eth_block_time
            )

        logger.info("\"Connect to AergoValidators\"")
        self.val_connect = AergoValConnect(
            config_data, self.hera, self.aergo_oracle)

    def wait_next_anchor(
        self,
        merged_height: int,
    ) -> int:
        """ Wait until t_anchor has passed after merged height.
        Return the next finalized block after t_anchor to be the next anchor
        """
        best_height = self.web3.eth.blockNumber
        lib = best_height - self.t_final
        # wait for merged_height + t_anchor > lib
        wait = (merged_height + self.t_anchor) - lib + 1
        while wait > 0:
            logger.info(
                "\"\u23F0 waiting new anchor time : %ss ...\"",
                wait * self.eth_block_time
            )
            self.monitor_settings_and_sleep(wait * self.eth_block_time)
            # Wait lib > last merged block height + t_anchor
            best_height = self.web3.eth.blockNumber
            lib = best_height - self.t_final
            wait = (merged_height + self.t_anchor) - lib + 1
        return lib

    def run(
        self,
    ) -> None:
        """ Gathers signatures from validators, verifies them, and if 2/3 majority
        is acquired, set the new anchored root in aergo_bridge.
        """
        logger.info("\"Run Aergo proposer\"")
        while True:  # anchor a new root
            try:
                # Get last merge information
                bridge_status = self.hera.query_sc_state(
                    self.aergo_oracle,
                    ["_sv__anchorHeight", "_sv__anchorRoot", "_sv__tAnchor",
                     "_sv__tFinal"]
                )
                height_from, root_from, t_anchor, t_final = \
                    [proof.value for proof in bridge_status.var_proofs]
                merged_height_from = int(height_from)
                self.t_anchor = int(t_anchor)
                self.t_final = int(t_final)
                nonce_to = int(
                    self.hera.query_sc_state(
                        self.aergo_oracle, ["_sv__nonce"]).var_proofs[0].value
                )

                logger.info(
                    "\"Current Eth -> Aergo \u2693 anchor: "
                    "height: %s, root: %s, nonce: %s\"",
                    merged_height_from, root_from.decode('utf-8')[1:-1],
                    nonce_to
                )

                # Wait for the next anchor time
                next_anchor_height = self.wait_next_anchor(merged_height_from)

                if self.eco:
                    # only anchor if a lock / burn event happened on ethereum
                    if self.skip_anchor(
                        merged_height_from, next_anchor_height):
                        logger.info(
                            "\"Anchor skipped (no lock/burn events occured)\"")
                        self.monitor_settings_and_sleep(
                            self.t_anchor * self.eth_block_time)
                        continue

                # Get root of next anchor to broadcast
                root = \
                    self.web3.eth.getBlock(next_anchor_height).stateRoot.hex()
                if len(root) == 0:
                    logger.info("\"waiting deployment finalization...\"")
                    time.sleep(5)
                    continue

                if not self.anchoring_on and not self.auto_update:
                    logger.info(
                        "\"Anchoring height reached waiting for anchor...\""
                    )
                    time.sleep(30)
                    continue

                if self.anchoring_on:
                    logger.info(
                        "\"\U0001f58b Gathering validator signatures for: "
                        "root: %s, height: %s'\"", root, next_anchor_height
                    )

                    nonce_to = int(
                        self.hera.query_sc_state(
                            self.aergo_oracle, ["_sv__nonce"]
                        ).var_proofs[0].value
                    )

                    try:
                        sigs, validator_indexes = \
                            self.val_connect.get_anchor_signatures(
                                root[2:], next_anchor_height, nonce_to)
                    except ValidatorMajorityError:
                        logger.warning(
                            "\"Failed to gather 2/3 validators signatures, "
                            "\u23F0 waiting for next anchor...\""
                        )
                        self.monitor_settings_and_sleep(
                            self.t_anchor * self.eth_block_time)
                        continue

                    # don't broadcast if somebody else already did
                    merged_height = int(
                        self.hera.query_sc_state(
                            self.aergo_bridge, ["_sv__anchorHeight"]
                        ).var_proofs[0].value
                    )
                    if merged_height + self.t_anchor >= next_anchor_height:
                        logger.warning(
                            "\"Not yet anchor time, maybe another proposer "
                            "already anchored\""
                        )
                        wait = \
                            merged_height + self.t_anchor - next_anchor_height
                        self.monitor_settings_and_sleep(
                            wait * self.eth_block_time)
                        continue

                    if self.bridge_anchoring:
                        # broadcast the general state root and relay the bridge
                        # root with a merkle proof
                        bridge_contract_state, merkle_proof = \
                            self.buildBridgeAnchorArgs(next_anchor_height)
                        self.aergo_tx.new_state_and_bridge_anchor(
                            root, next_anchor_height, validator_indexes, sigs,
                            bridge_contract_state, merkle_proof
                        )
                    else:
                        # only broadcast the general state root
                        self.aergo_tx.new_state_anchor(
                            root, next_anchor_height, validator_indexes, sigs)

                if self.auto_update:
                    self.monitor_settings_and_sleep(
                        self.t_anchor * self.eth_block_time)
                else:
                    time.sleep(self.t_anchor * self.eth_block_time)

            except requests.exceptions.ConnectionError:
                logger.warning(
                    "%s",
                    {"Web3 ConnectionError":
                        json.dumps(traceback.format_exc())}
                )
                time.sleep(self.t_anchor / 10)
            except herapy.errors.exception.CommunicationException:
                logger.warning(
                    "%s",
                    {
                        "Hera CommunicationException":
                            json.dumps(traceback.format_exc())
                    }
                )
                time.sleep(self.t_anchor / 10)
            except:
                logger.warning(
                    "%s",
                    {"UNKNOWN ERROR": json.dumps(traceback.format_exc())}
                )
                time.sleep(self.t_anchor / 10)

    def skip_anchor(self, last_anchor, next_anchor):
        lock_events = self.eth_bridge.events.lockEvent.createFilter(
            fromBlock=last_anchor, toBlock=next_anchor).get_all_entries()
        if len(lock_events) > 0:
            return False

        burn_events = self.eth_bridge.events.burnEvent.createFilter(
            fromBlock=last_anchor, toBlock=next_anchor).get_new_entries()
        if len(burn_events) > 0:
            return False
        return True

    def monitor_settings_and_sleep(self, sleeping_time):
        """While sleeping, periodicaly check changes to the config
        file and update settings if necessary. If another
        proposer updated settings it doesnt matter, validators will
        just not give signatures.

        """
        start = time.time()
        self.monitor_settings()
        while time.time()-start < sleeping_time-10:
            # check the config file every 10 seconds
            time.sleep(10)
            self.monitor_settings()
        remaining = sleeping_time - (time.time() - start)
        if remaining > 0:
            time.sleep(remaining)

    def monitor_settings(self):
        """Check if a modification of bridge settings is requested by seeing
        if the config file has been changed and try to update the bridge
        contract (gather 2/3 validators signatures).

        """
        config_data = load_config_data(self.config_file_path)
        t_anchor, t_final = query_aergo_tempo(self.hera, self.aergo_bridge)
        unfreeze_fee = query_unfreeze_fee(self.hera, self.aergo_bridge)
        config_t_anchor = (config_data['networks'][self.aergo_net]['bridges']
                           [self.eth_net]['t_anchor'])
        if t_anchor != config_t_anchor:
            logger.info(
                '\"Anchoring periode update requested: %s\"', config_t_anchor)
            self.update_t_anchor(config_t_anchor)
        config_t_final = (config_data['networks'][self.aergo_net]['bridges']
                          [self.eth_net]['t_final'])
        if t_final != config_t_final:
            logger.info('\"Finality update requested: %s\"', config_t_final)
            self.update_t_final(config_t_final)
        config_unfreeze_fee = (config_data['networks'][self.aergo_net]
                               ['bridges'][self.eth_net]['unfreeze_fee'])
        if unfreeze_fee != config_unfreeze_fee:
            logger.info(
                '\"Unfreeze fee update requested: %s\"', config_unfreeze_fee)
            self.update_unfreeze_fee(config_unfreeze_fee)
        if self.oracle_update:
            validators = query_aergo_validators(self.hera, self.aergo_oracle)
            config_validators = \
                [val['addr'] for val in config_data['validators']]
            if validators != config_validators:
                logger.info(
                    '\"Validator set update requested: %s\"',
                    config_validators
                )
                if self.update_validators(config_validators):
                    self.val_connect.use_new_validators(config_data)
            oracle = query_aergo_oracle(self.hera, self.aergo_bridge)
            config_oracle = (config_data['networks'][self.aergo_net]['bridges']
                             [self.eth_net]['oracle'])
            if oracle != config_oracle:
                logger.info('\"Oracle change requested: %s\"', config_oracle)
                self.update_oracle(config_oracle)

    def update_validators(self, new_validators):
        """Try to update the validator set with the one in the config file."""
        try:
            sigs, validator_indexes = \
                self.val_connect.get_new_validators_signatures(new_validators)
        except ValidatorMajorityError:
            logger.warning("\"Failed to gather 2/3 validators signatures\"")
            return False
        # broadcast transaction
        return self.aergo_tx.set_validators(
            new_validators, validator_indexes, sigs)

    def update_t_anchor(self, t_anchor):
        """Try to update the anchoring periode registered in the bridge
        contract.

        """
        try:
            sigs, validator_indexes = \
                self.val_connect.get_tempo_signatures(
                    t_anchor, "GetEthTAnchorSignature", "A")
        except ValidatorMajorityError:
            logger.warning("\"Failed to gather 2/3 validators signatures\"")
            return
        # broadcast transaction
        self.aergo_tx.set_single_param(
            t_anchor, validator_indexes, sigs, "tAnchorUpdate", "\u231B")

    def update_t_final(self, t_final):
        """Try to update the anchoring periode registered in the bridge
        contract.

        """
        try:
            sigs, validator_indexes = \
                self.val_connect.get_tempo_signatures(
                    t_final, "GetEthTFinalSignature", "F")
        except ValidatorMajorityError:
            logger.warning("\"Failed to gather 2/3 validators signatures\"")
            return
        # broadcast transaction
        self.aergo_tx.set_single_param(
            t_final, validator_indexes, sigs, "tFinalUpdate", "\u231B")

    def update_unfreeze_fee(self, fee):
        """Try to update the anchoring periode registered in the bridge
        contract.

        """
        try:
            sigs, validator_indexes = \
                self.val_connect.get_unfreeze_fee_signatures(fee)
        except ValidatorMajorityError:
            logger.warning("\"Failed to gather 2/3 validators signatures\"")
            return
        # broadcast transaction
        self.aergo_tx.set_single_param(
            {'_bignum': str(fee)}, validator_indexes, sigs,
            "unfreezeFeeUpdate", "\U0001f4a7"
        )

    def update_oracle(self, oracle):
        """Try to update the oracle periode registered in the bridge
        contract.

        """
        try:
            sigs, validator_indexes = \
                self.val_connect.get_new_oracle_signatures(oracle)
        except ValidatorMajorityError:
            logger.warning("\"Failed to gather 2/3 validators signatures\"")
            return
        # broadcast transaction
        self.aergo_tx.set_oracle(oracle, validator_indexes, sigs)

    def buildBridgeAnchorArgs(
        self,
        next_anchor_height
    ) -> Tuple[List[str], List[str]]:
        """Build arguments to derive bridge storage root from the anchored
        state root with a merkle proof
        """
        state = self.web3.eth.getProof(
            self.eth_bridge_addr, [], next_anchor_height)
        bridge_nonce = \
            "0x" if state.nonce == 0 else "0x{:02x}".format(state.nonce)
        bridge_balance = \
            "0x" if state.balance == 0 else "0x{:02x}".format(state.balance)
        bridge_root = state.storageHash.hex()
        bridge_code_hash = state.codeHash.hex()
        bridge_contract_state = \
            [bridge_nonce, bridge_balance, bridge_root, bridge_code_hash]
        merkle_proof = [node.hex() for node in state.accountProof]

        '''
        # test
        import rlp
        from rlp.sedes import (
            Binary,
            big_endian_int,
        )
        from eth_utils import (
            keccak,
        )
        from trie import (
            HexaryTrie,
        )
        def format_proof_nodes(proof):
            trie_proof = []
            for rlp_node in proof:
                trie_proof.append(rlp.decode(bytes(rlp_node)))
            return trie_proof

        trie_root = Binary.fixed_length(32, allow_empty=True)
        hash32 = Binary.fixed_length(32)

        class _Account(rlp.Serializable):
            fields = [
                        ('nonce', big_endian_int),
                        ('balance', big_endian_int),
                        ('storage', trie_root),
                        ('code_hash', hash32)
                    ]
        acc = _Account(
            state.nonce, state.balance, state.storageHash, state.codeHash
        )
        rlp_account = rlp.encode(acc)
        print("0x" + rlp_account.hex())
        print(bridge_contract_state)
        trie_key = keccak(bytes.fromhex(state.address[2:]))
        print("key:", self.eth_bridge_addr)
        root = keccak(state.accountProof[0])
        print("root1:", root.hex())
        print(merkle_proof)
        print(state.accountProof)

        assert rlp_account == HexaryTrie.get_from_proof(
            root, trie_key, format_proof_nodes(state.accountProof)
        ), "Failed to verify account proof {}".format(state.address)
        '''
        return bridge_contract_state, merkle_proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Start a proposer on Ethereum and Aergo.')
    # Add arguments
    parser.add_argument(
        '-c', '--config_file_path', type=str, help='Path to config.json',
        required=True
    )
    parser.add_argument(
        '-a', '--aergo', type=str, help='Name of Aergo network in config file',
        required=True
    )
    parser.add_argument(
        '-e', '--eth', help='Name of Ethereum network in config file',
        type=str, required=True
    )
    parser.add_argument(
        '--eth_block_time', type=int, help='Average Ethereum block time',
        required=True
    )
    parser.add_argument(
        '--privkey_name', type=str, help='Name of account in config file '
        'to sign anchors', required=False
    )
    parser.add_argument(
        '--anchoring_on', dest='anchoring_on', action='store_true',
        help='Enable anchoring (can be diseabled when wanting to only update '
             'settings)'
    )
    parser.add_argument(
        '--auto_update', dest='auto_update', action='store_true',
        help='Update bridge contract when settings change in config file'
    )
    parser.add_argument(
        '--oracle_update', dest='oracle_update', action='store_true',
        help='Update bridge contract when validators or oracle addr '
             'change in config file'
    )
    parser.add_argument(
        '--aergo_gas_price', type=int,
        help='Gas price to use in transactions', required=False
    )
    parser.add_argument(
        '--eco', dest='eco', action='store_true',
        help='In eco mode, anchoring will only be done when lock/burn '
        'events happen in the bridge contract'
    )

    parser.set_defaults(anchoring_on=False)
    parser.set_defaults(auto_update=False)
    parser.set_defaults(oracle_update=False)
    parser.set_defaults(aergo_gas_price=None)
    args = parser.parse_args()

    proposer = AergoProposerClient(
        args.config_file_path, args.aergo, args.eth, args.eth_block_time,
        privkey_name=args.privkey_name,
        anchoring_on=args.anchoring_on,
        auto_update=args.auto_update,
        oracle_update=args.oracle_update,
        aergo_gas_price=args.aergo_gas_price,
        eco=args.eco,
    )
    proposer.run()
