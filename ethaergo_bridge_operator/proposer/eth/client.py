import argparse
from getpass import getpass
import json
import requests
import threading
import time
import traceback
from typing import (
    Tuple,
    List,
)


import aergo.herapy as herapy
import web3
from web3 import (
    Web3,
)
from web3.middleware import (
    geth_poa_middleware,
)

from ethaergo_bridge_operator.op_utils import (
    load_config_data,
)
from ethaergo_bridge_operator.proposer.exceptions import (
    ValidatorMajorityError,
)
from ethaergo_bridge_operator.proposer.eth.validator_connect import (
    EthValConnect,
)
from ethaergo_bridge_operator.proposer.eth.transact import (
    EthTx,
)
import logging

logger = logging.getLogger(__name__)


class EthProposerClient(threading.Thread):
    """The ethereum bridge proposer periodically (every t_anchor) broadcasts
    the finalized Aergo trie state root (after lib)
    onto the ethereum bridge contract after validation by the Validators.
    It first checks the last merged height and waits until
    now > lib + t_anchor is reached, then merges the current finalised
    block (lib). If bridge_anchoring is True(default), then the proposer will
    create a Merkle proof of the bridge storage root to anchor both roots in
    the same transaction. Start again after waiting t_anchor.
    EthProposerClient anchors an Aergo state root onto Ethereum.

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
        privkey_name: str = None,
        privkey_pwd: str = None,
        anchoring_on: bool = False,
        auto_update: bool = False,
        oracle_update: bool = False,
        root_path: str = './',
        eth_gas_price: int = None,
        bridge_anchoring: bool = True
    ) -> None:
        threading.Thread.__init__(self, name="EthProposerClient")
        if eth_gas_price is None:
            eth_gas_price = 10
        self.config_file_path = config_file_path
        config_data = load_config_data(config_file_path)
        self.eth_net = eth_net
        self.aergo_net = aergo_net
        self.anchoring_on = anchoring_on
        self.auto_update = auto_update
        self.oracle_update = oracle_update
        self.bridge_anchoring = bridge_anchoring
        logger.info("\"Connect Aergo and Ethereum providers\"")
        self.hera = herapy.Aergo()
        self.hera.connect(config_data['networks'][aergo_net]['ip'])

        # Web3 instance for reading blockchains state, shared with
        # EthValConnect.
        ip = config_data['networks'][eth_net]['ip']
        self.web3 = Web3(Web3.HTTPProvider(ip))
        eth_poa = config_data['networks'][eth_net]['isPOA']
        if eth_poa:
            self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        assert self.web3.isConnected()

        # bridge contract
        bridge_abi_path = (config_data['networks'][eth_net]['bridges']
                           [aergo_net]['bridge_abi'])
        with open(root_path + bridge_abi_path, "r") as f:
            bridge_abi = f.read()
        eth_bridge_address = (config_data['networks'][eth_net]
                              ['bridges'][aergo_net]['addr'])
        self.eth_bridge = self.web3.eth.contract(
            address=eth_bridge_address,
            abi=bridge_abi
        )
        # oracle contract
        oracle_abi_path = (config_data['networks'][eth_net]['bridges']
                           [aergo_net]['oracle_abi'])
        with open(root_path + oracle_abi_path, "r") as f:
            oracle_abi = f.read()
        eth_oracle_address = (config_data['networks'][eth_net]
                              ['bridges'][aergo_net]['oracle'])
        self.eth_oracle = self.web3.eth.contract(
            address=eth_oracle_address,
            abi=oracle_abi
        )
        self.aergo_bridge = (config_data['networks'][aergo_net]['bridges']
                             [eth_net]['addr'])

        # get the current t_anchor and t_final for anchoring on etherem
        self.t_anchor = self.eth_bridge.functions._tAnchor().call()
        self.t_final = self.eth_bridge.functions._tFinal().call()
        logger.info(
            "\"%s (t_final=%s ) -> %s : t_anchor=%s\"", aergo_net,
            self.t_final, eth_net, self.t_anchor
        )

        if privkey_name is None:
            privkey_name = 'proposer'
        keystore = config_data["wallet-eth"][privkey_name]['keystore']
        with open(root_path + keystore, "r") as f:
            encrypted_key = f.read()
        if privkey_pwd is None:
            privkey_pwd = getpass("Decrypt Ethereum keystore '{}'\n"
                                  "Password: ".format(privkey_name))
        self.eth_tx = EthTx(
            self.web3, encrypted_key, privkey_pwd, eth_oracle_address,
            oracle_abi, eth_gas_price, self.t_anchor)

        logger.info("\"Connect to EthValidators\"")
        self.val_connect = EthValConnect(
            config_data, self.web3, eth_oracle_address,
            oracle_abi
        )

    def wait_next_anchor(
        self,
        merged_height: int,
    ) -> int:
        """ Wait until t_anchor has passed after merged height.
        Return the next finalized block after t_anchor to be the next anchor
        """
        lib = self.hera.get_status().consensus_info.status['LibNo']
        wait = (merged_height + self.t_anchor) - lib + 1
        while wait > 0:
            logger.info("\"\u23F0 waiting new anchor time : %ss ...\"", wait)
            self.monitor_settings_and_sleep(wait)
            # Wait lib > last merged block height + t_anchor
            lib = self.hera.get_status().consensus_info.status['LibNo']
            wait = (merged_height + self.t_anchor) - lib + 1
        return lib

    def run(
        self,
    ) -> None:
        """ Gathers signatures from validators, verifies them, and if 2/3 majority
        is acquired, set the new anchored root in eth_bridge.
        """
        logger.info("\"Start Eth proposer\"")
        while True:  # anchor a new root
            try:
                # Get last merge information
                merged_height_from = \
                    self.eth_oracle.functions._anchorHeight().call()
                merged_root_from = \
                    self.eth_oracle.functions._anchorRoot().call()
                nonce_to = self.eth_oracle.functions._nonce().call()
                self.t_anchor = self.eth_oracle.functions._tAnchor().call()

                logger.info(
                    "\"Current Aergo -> Eth \u2693 anchor: "
                    "height: %s, root: 0x%s, nonce: %s\"",
                    merged_height_from, merged_root_from.hex(), nonce_to
                )

                # Wait for the next anchor time
                next_anchor_height = self.wait_next_anchor(merged_height_from)
                # Get root of next anchor to broadcast
                block = self.hera.get_block_headers(
                    block_height=next_anchor_height, list_size=1)
                root = block[0].blocks_root_hash
                if len(root) == 0:
                    logger.info("\"waiting deployment finalization...\"")
                    time.sleep(5)
                    continue

                if self.anchoring_on:
                    logger.info(
                        "\"\U0001f58b Gathering validator signatures for: "
                        "root: 0x%s, height: %s'\"", root.hex(),
                        next_anchor_height
                    )

                    try:
                        nonce_to = self.eth_oracle.functions._nonce().call()
                        sigs, validator_indexes = \
                            self.val_connect.get_anchor_signatures(
                                root, next_anchor_height, nonce_to)
                    except ValidatorMajorityError:
                        logger.warning(
                            "\"Failed to gather 2/3 validators signatures, "
                            "\u23F0 waiting for next anchor...\""
                        )
                        self.monitor_settings_and_sleep(self.t_anchor)
                        continue

                    # don't broadcast if somebody else already did
                    merged_height = \
                        self.eth_oracle.functions._anchorHeight().call()
                    if merged_height + self.t_anchor >= next_anchor_height:
                        logger.warning(
                            "\"Not yet anchor time, maybe another proposer "
                            "already anchored\""
                        )
                        self.monitor_settings_and_sleep(
                            merged_height + self.t_anchor - next_anchor_height)
                        continue

                    if self.bridge_anchoring:
                        # broadcast the general state root and relay the bridge
                        # root with a merkle proof
                        bridge_state_proto, merkle_proof, bitmap, \
                            leaf_height = self.buildBridgeAnchorArgs(root)
                        self.eth_tx.new_state_and_bridge_anchor(
                            root, next_anchor_height, validator_indexes, sigs,
                            bridge_state_proto, merkle_proof, bitmap,
                            leaf_height
                        )
                    else:
                        # only broadcast the general state root
                        self.eth_tx.new_state_anchor(
                            root, next_anchor_height, validator_indexes, sigs)
                    # lower gas price by 10% after every successful anchor
                    # until min_gas_price is reached
                    self.eth_tx.change_gas_price(0.9)

                self.monitor_settings_and_sleep(self.t_anchor)

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
                    {"Hera CommunicationException":
                        json.dumps(traceback.format_exc())}
                )
                time.sleep(self.t_anchor / 10)
            except web3.exceptions.TimeExhausted:
                logger.warning(
                    "%s",
                    {"Web3 receipt TimeExhausted":
                        json.dumps(traceback.format_exc())}
                )
                time.sleep(self.t_anchor)
            except ValueError as e:
                if str(e) == "{'code': -32000, 'message': 'replacement transaction underpriced'}":
                    logger.warning(
                        "%s",
                        {"Eth tx underpriced":
                            json.dumps(traceback.format_exc())}
                    )
                    self.eth_tx.change_gas_price(1.4)
                else:
                    logger.warning(
                        "%s",
                        {"UNKNOWN ValueError": json.dumps(traceback.format_exc())}
                    )
                # skip to the next anchor if tx not mined
                # users will also wait for lower gas fees to transfer assets
                time.sleep(self.t_anchor)
            except TypeError:
                # This TypeError can be raised when the aergo node is
                # restarting and lib is None
                logger.warning(
                    "%s",
                    {"LIB == None?": json.dumps(traceback.format_exc())}
                )
                time.sleep(self.t_anchor / 10)
            except:
                logger.warning(
                    "%s",
                    {"UNKNOWN ERROR": json.dumps(traceback.format_exc())}
                )
                time.sleep(self.t_anchor / 10)

    def monitor_settings_and_sleep(self, sleeping_time):
        """While sleeping, periodicaly check changes to the config
        file and update settings if necessary. If another
        proposer updated settings it doesnt matter, validators will
        just not give signatures.

        """
        if self.auto_update:
            start = time.time()
            self.monitor_settings()
            while time.time()-start < sleeping_time-10:
                # check the config file every 10 seconds
                time.sleep(10)
                self.monitor_settings()
            remaining = sleeping_time - (time.time() - start)
            if remaining > 0:
                time.sleep(remaining)
        else:
            time.sleep(sleeping_time)

    def monitor_settings(self):
        """Check if a modification of bridge settings is requested by seeing
        if the config file has been changed and try to update the bridge
        contract (gather 2/3 validators signatures).

        """
        config_data = load_config_data(self.config_file_path)
        t_anchor = self.eth_oracle.functions._tAnchor().call()
        config_t_anchor = (config_data['networks'][self.eth_net]['bridges']
                           [self.aergo_net]['t_anchor'])
        if t_anchor != config_t_anchor:
            logger.info(
                '\"Anchoring periode update requested: %s\"', config_t_anchor)
            self.update_t_anchor(config_t_anchor)
        t_final = self.eth_oracle.functions._tFinal().call()
        config_t_final = (config_data['networks'][self.eth_net]['bridges']
                          [self.aergo_net]['t_final'])
        if t_final != config_t_final:
            logger.info('\"Finality update requested: %s\"', config_t_final)
            self.update_t_final(config_t_final)
        if self.oracle_update:
            validators = self.eth_oracle.functions.getValidators().call()
            config_validators = \
                [val['eth-addr'] for val in config_data['validators']]
            if validators != config_validators:
                logger.info(
                    '\"Validator set update requested: %s\"',
                    config_validators
                )
                if self.update_validators(config_validators):
                    self.val_connect.use_new_validators(config_data)
            oracle = self.eth_bridge.functions._oracle().call()
            config_oracle = (config_data['networks'][self.eth_net]['bridges']
                             [self.aergo_net]['oracle'])
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
        return self.eth_tx.set_validators(
            new_validators, validator_indexes, sigs)

    def update_t_anchor(self, t_anchor):
        """Try to update the anchoring periode registered in the bridge
        contract.

        """
        try:
            sigs, validator_indexes = self.val_connect.get_tempo_signatures(
                t_anchor, "GetAergoTAnchorSignature", "A")
        except ValidatorMajorityError:
            logger.warning("\"Failed to gather 2/3 validators signatures\"")
            return
        # broadcast transaction
        self.eth_tx.set_t_anchor(t_anchor, validator_indexes, sigs)

    def update_t_final(self, t_final):
        """Try to update the anchoring periode registered in the bridge
        contract.

        """
        try:
            sigs, validator_indexes = self.val_connect.get_tempo_signatures(
                t_final, "GetAergoTFinalSignature", "F")
        except ValidatorMajorityError:
            logger.warning("\"Failed to gather 2/3 validators signatures\"")
            return
        # broadcast transaction
        self.eth_tx.set_t_final(t_final, validator_indexes, sigs)

    def update_oracle(self, oracle):
        """Try to update the oracle registered in the bridge
        contract.

        """
        try:
            sigs, validator_indexes = \
                self.val_connect.get_new_oracle_signatures(oracle)
        except ValidatorMajorityError:
            logger.warning("\"Failed to gather 2/3 validators signatures\"")
            return
        # broadcast transaction
        self.eth_tx.set_oracle(oracle, validator_indexes, sigs)

    def buildBridgeAnchorArgs(
        self,
        root: bytes
    ) -> Tuple[bytes, List[bytes], bytes, int]:
        """Build arguments to derive bridge storage root from the anchored
        state root with a merkle proof
        """
        state = self.hera.get_account(
            address=self.aergo_bridge, proof=True, root=root, compressed=True)
        ap = state.state_proof.auditPath
        bitmap = state.state_proof.bitmap
        leaf_height = state.state_proof.height
        proto = state.state_proof.state.SerializeToString()
        return proto, ap, bitmap, leaf_height


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Start a proposer on Ethereum and Aergo.')
    # Add arguments
    parser.add_argument(
        '-c', '--config_file_path', type=str, help='Path to config.json',
        required=True)
    parser.add_argument(
        '-a', '--aergo', type=str, help='Name of Aergo network in config file',
        required=True)
    parser.add_argument(
        '-e', '--eth', type=str, required=True,
        help='Name of Ethereum network in config file')
    parser.add_argument(
        '--eth_block_time', type=int, help='Average Ethereum block time',
        required=True)
    parser.add_argument(
        '--privkey_name', type=str, help='Name of account in config file '
        'to sign anchors', required=False)
    parser.add_argument(
        '--anchoring_on', dest='anchoring_on', action='store_true',
        help='Enable anchoring (can be diseabled when wanting to only update '
             'settings)'
    )
    parser.add_argument(
        '--auto_update', dest='auto_update', action='store_true',
        help='Update bridge contract when settings change in config file')
    parser.add_argument(
        '--oracle_update', dest='oracle_update', action='store_true',
        help='Update bridge contract when validators or oracle addr '
             'change in config file'
    )
    parser.add_argument(
        '--eth_gas_price', type=int,
        help='Gas price (gWei) to use in transactions', required=False)
    parser.set_defaults(anchoring_on=False)
    parser.set_defaults(auto_update=False)
    parser.set_defaults(oracle_update=False)
    parser.set_defaults(eth_gas_price=None)
    args = parser.parse_args()

    proposer = EthProposerClient(
        args.config_file_path, args.aergo, args.eth,
        privkey_name=args.privkey_name,
        anchoring_on=args.anchoring_on,
        auto_update=args.auto_update,
        oracle_update=args.oracle_update,
        eth_gas_price=args.eth_gas_price
    )
    proposer.run()
