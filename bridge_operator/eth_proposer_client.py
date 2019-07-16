import argparse
from functools import (
    partial,
)
from getpass import getpass
import grpc
import json
from multiprocessing.dummy import (
    Pool,
)
import os
import threading
import time

from typing import (
    Dict,
    Tuple,
    List,
    Any,
)

import aergo.herapy as herapy
from web3 import (
    Web3,
)
from web3.middleware import (
    geth_poa_middleware,
)
from web3._utils.encoding import (
    pad_bytes,
)
from eth_utils import (
    keccak,
)

from bridge_operator.bridge_operator_pb2_grpc import (
    BridgeOperatorStub,
)
from bridge_operator.bridge_operator_pb2 import (
    Anchor,
    NewValidators,
    NewTempo
)
from bridge_operator.op_utils import (
    query_eth_tempo,
    query_eth_validators,
    query_eth_id,
)
from bridge_operator.exceptions import (
    ValidatorMajorityError,
)


class EthProposerClient(threading.Thread):
    """The ethereum bridge proposer periodically (every t_anchor) broadcasts
    the finalized Aergo trie state root (after lib) of the bridge contract
    onto the ethereum bridge contract after validation by the Validators.
    It first checks the last merged height and waits until
    now > lib + t_anchor is reached, then merges the current finalised
    block (lib). Start again after waiting t_anchor.
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
        tab: str = "",
        auto_update: bool = False
    ) -> None:
        threading.Thread.__init__(self)
        self.config_file_path = config_file_path
        config_data = self.load_config_data()
        self.config_data = config_data
        self.tab = tab
        self.eth_net = eth_net
        self.aergo_net = aergo_net
        self.auto_update = auto_update
        print("------ Connect Aergo and Ethereum -----------")
        self.hera = herapy.Aergo()
        self.hera.connect(config_data['networks'][aergo_net]['ip'])

        ip = config_data['networks'][eth_net]['ip']
        self.web3 = Web3(Web3.HTTPProvider("http://" + ip))
        eth_poa = config_data['networks'][eth_net]['isPOA']
        if eth_poa:
            self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        assert self.web3.isConnected()

        bridge_abi_path = (config_data['networks'][eth_net]['bridges']
                           [aergo_net]['bridge_abi'])
        with open(bridge_abi_path, "r") as f:
            eth_abi = f.read()
        eth_bridge_address = (config_data['networks'][eth_net]['bridges']
                              [aergo_net]['addr'])
        self.eth_bridge = self.web3.eth.contract(
            address=eth_bridge_address,
            abi=eth_abi
        )
        self.aergo_bridge = (config_data['networks'][aergo_net]['bridges']
                             [eth_net]['addr'])
        self.eth_id = query_eth_id(self.web3, eth_bridge_address, eth_abi)

        print("------ Connect to Validators -----------")
        validators = query_eth_validators(self.web3, eth_bridge_address,
                                          eth_abi)
        print("Validators: ", validators)
        # create all channels with validators
        self.channels: List[grpc._channel.Channel] = []
        self.stubs: List[BridgeOperatorStub] = []
        assert len(validators) == len(config_data['validators']), \
            "Validators in config file must match bridge validators " \
            "when starting (current validators connection needed to make "\
            "updates).\nExpected validators: {}".format(validators)
        for i, validator in enumerate(config_data['validators']):
            assert validators[i] == validator['eth-addr'], \
                "Validators in config file must match bridge validators " \
                "when starting (current validators connection needed to make "\
                "updates).\nExpected validators: {}".format(validators)
            ip = validator['ip']
            channel = grpc.insecure_channel(ip)
            stub = BridgeOperatorStub(channel)
            self.channels.append(channel)
            self.stubs.append(stub)

        self.pool = Pool(len(self.stubs))

        # get the current t_anchor and t_final for anchoring on etherem
        self.t_anchor, self._t_final = query_eth_tempo(
            self.web3, eth_bridge_address, eth_abi)
        print("{} (t_final={}) -> {} : t_anchor={}"
              .format(aergo_net, self._t_final, eth_net, self.t_anchor))

        print("------ Set Sender Account -----------")
        if privkey_name is None:
            privkey_name = 'proposer'
        keystore = config_data["wallet-eth"][privkey_name]['keystore']
        file_path = os.path.dirname(os.path.realpath(__file__))
        root_path = os.path.dirname(file_path) + '/'
        with open(root_path + keystore, "r") as f:
            encrypted_key = f.read()
        if privkey_pwd is None:
            privkey_pwd = getpass("Decrypt Ethereum keystore '{}'\n"
                                  "Password: ".format(privkey_name))
        privkey = self.web3.eth.account.decrypt(encrypted_key, privkey_pwd)
        self.proposer_acct = self.web3.eth.account.from_key(privkey)

        print("  > Proposer Address: {}".format(self.proposer_acct.address))

    def get_anchor_signatures(
        self,
        root: bytes,
        merge_height: int,
        nonce: int,
    ) -> Tuple[List[str], List[int]]:
        """ Query all validators and gather 2/3 of their signatures. """
        # messages to get signed
        msg_bytes = root + merge_height.to_bytes(32, byteorder='big') \
            + nonce.to_bytes(32, byteorder='big') \
            + self.eth_id \
            + bytes("R", 'utf-8')
        h = keccak(msg_bytes)

        anchor = Anchor(
            root=root, height=merge_height, destination_nonce=nonce
        )

        # get validator signatures and verify sig in worker
        validator_indexes = [i for i in range(len(self.stubs))]
        worker = partial(
            self.get_signature_worker, "GetAergoAnchorSignature", anchor, h)
        approvals = self.pool.map(worker, validator_indexes)

        sigs, validator_indexes = self.extract_signatures(approvals)

        return sigs, validator_indexes

    def get_signature_worker(
        self,
        rpc_service: str,
        request,
        h: bytes,
        idx: int
    ):
        """ Get a validator's (index) signature and verify it"""
        try:
            approval = getattr(self.stubs[idx], rpc_service)(request)
        except grpc.RpcError as e:
            print(e)
            return None
        if approval.error:
            print("{}{}".format(self.tab, approval.error))
            return None
        if approval.address != self.config_data['validators'][idx]['eth-addr']:
            # check nothing is wrong with validator address
            print("{}Unexpected validator {} address : {}"
                  .format(self.tab, idx, approval.address))
            return None
        # validate signature
        if not approval.address == self.web3.eth.account.recoverHash(
            h, signature=approval.sig
        ):
            print("{}Invalid signature from validator {}"
                  .format(self.tab, idx))
            return None
        return approval

    def extract_signatures(
        self,
        approvals: List[Any]
    ) -> Tuple[List[str], List[int]]:
        """Keep 2/3 of validator signatures (minimum to anchor)"""
        sigs, validator_indexes = [], []
        for i, approval in enumerate(approvals):
            if approval is not None:
                sigs.append(approval.sig)
                validator_indexes.append(i+1)
        total_validators = len(self.config_data['validators'])
        if 3 * len(sigs) < 2 * total_validators:
            raise ValidatorMajorityError()
        # slice 2/3 of total validators
        two_thirds = ((total_validators * 2) // 3
                      + ((total_validators * 2) % 3 > 0))
        return sigs[:two_thirds], validator_indexes[:two_thirds]

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
            print("{}{} waiting new anchor time : {}s ..."
                  .format(self.tab, u'\u23F0', wait))
            self.monitor_settings_and_sleep(wait)
            # Wait lib > last merged block height + t_anchor
            lib = self.hera.get_status().consensus_info.status['LibNo']
            wait = (merged_height + self.t_anchor) - lib + 1
        return lib

    def prepare_rsv(
        self,
        sigs: List[str]
    ) -> Tuple[List[int], List[str], List[str]]:
        """ Format signature for solidity ecrecover """
        vs, rs, ss = [], [], []
        for sig in sigs:
            vs.append(self.web3.toInt(sig[-1]))
            rs.append(self.web3.toHex(sig[:32]))
            ss.append(self.web3.toHex(sig[32:64]))
        return vs, rs, ss

    def set_root(
        self,
        root: bytes,
        next_anchor_height: int,
        validator_indexes: List[int],
        sigs: List[str],
    ) -> None:
        """Anchor a new root on Ethereum"""
        vs, rs, ss = self.prepare_rsv(sigs)
        construct_txn = self.eth_bridge.functions.set_root(
            root, next_anchor_height, validator_indexes, vs, rs, ss
        ).buildTransaction({
            'chainId': self.web3.eth.chainId,
            'from': self.proposer_acct.address,
            'nonce': self.web3.eth.getTransactionCount(
                self.proposer_acct.address
            ),
            'gas': 108036,
            'gasPrice': self.web3.toWei(9, 'gwei')
        })
        signed = self.proposer_acct.sign_transaction(construct_txn)
        tx_hash = self.web3.eth.sendRawTransaction(signed.rawTransaction)
        receipt = self.web3.eth.waitForTransactionReceipt(tx_hash)

        if receipt.status == 1:
            print("{0}{1} Anchor success,\n{0}{2} wait until next anchor "
                  "time: {3}s...".format(self.tab, u'\u2693', u'\u23F0',
                                         self.t_anchor))
        else:
            print("{}Anchor failed: already anchored, or invalid "
                  "signature: {}".format(self.tab, receipt))

    def run(
        self,
    ) -> None:
        """ Gathers signatures from validators, verifies them, and if 2/3 majority
        is acquired, set the new anchored root in eth_bridge.
        """
        print("------ START BRIDGE OPERATOR -----------\n")
        while True:  # anchor a new root
            # Get last merge information
            merged_height_from = self.eth_bridge.functions.Height().call()
            merged_root_from = self.eth_bridge.functions.Root().call()
            nonce_to = self.eth_bridge.functions.Nonce().call()
            self.t_anchor = self.eth_bridge.functions.T_anchor().call()

            print("\n{0}| Last anchor from Aergo:\n"
                  "{0}| -----------------------\n"
                  "{0}| height: {1}\n"
                  "{0}| contract trie root: 0x{2}...\n"
                  "{0}| current update nonce: {3}\n"
                  .format(self.tab, merged_height_from,
                          merged_root_from.hex()[0:20], nonce_to))

            # Wait for the next anchor time
            next_anchor_height = self.wait_next_anchor(merged_height_from)
            # Get root of next anchor to broadcast
            block = self.hera.get_block(block_height=next_anchor_height)
            contract = self.hera.get_account(
                address=self.aergo_bridge, proof=True,
                root=block.blocks_root_hash
            )
            root = contract.state_proof.state.storageRoot
            if len(root) == 0:
                print("{}waiting deployment finalization..."
                      .format(self.tab))
                time.sleep(5)
                continue

            print("{}anchoring new Aergo root :'0x{}...'"
                  .format(self.tab, root[:8].hex()))
            print("{}{} Gathering signatures from validators ..."
                  .format(self.tab, u'\U0001f58b'))

            try:
                nonce_to = self.eth_bridge.functions.Nonce().call()
                sigs, validator_indexes = self.get_anchor_signatures(
                        root, next_anchor_height, nonce_to
                    )
            except ValidatorMajorityError:
                print("{0}Failed to gather 2/3 validators signatures,\n"
                      "{0}{1} waiting for next anchor..."
                      .format(self.tab, u'\u23F0'))
                self.monitor_settings_and_sleep(self.t_anchor)
                continue

            # don't broadcast if somebody else already did
            merged_height = self.eth_bridge.functions.Height().call()
            if merged_height + self.t_anchor >= next_anchor_height:
                print("{}Not yet anchor time, maybe another proposer"
                      " already anchored".format(self.tab))
                self.monitor_settings_and_sleep(
                    merged_height + self.t_anchor - next_anchor_height)
                continue

            # Broadcast finalised AergoAnchor on Ethereum
            self.set_root(root, next_anchor_height, validator_indexes, sigs)
            self.monitor_settings_and_sleep(self.t_anchor)

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
        config_data = self.load_config_data()
        validators = self.eth_bridge.functions.get_validators().call()
        config_validators = [val['eth-addr']
                             for val in config_data['validators']]
        if validators != config_validators:
            print('{}Validator set update requested'.format(self.tab))
            if self.update_validators(config_validators):
                self.config_data = config_data
                self.update_validator_connections()
        t_anchor = self.eth_bridge.functions.T_anchor().call()
        config_t_anchor = (config_data['networks'][self.eth_net]['bridges']
                           [self.aergo_net]['t_anchor'])
        if t_anchor != config_t_anchor:
            print('{}Anchoring periode update requested'.format(self.tab))
            self.update_t_anchor(config_t_anchor)
        t_final = self.eth_bridge.functions.T_final().call()
        config_t_final = (config_data['networks'][self.eth_net]['bridges']
                          [self.aergo_net]['t_final'])
        if t_final != config_t_final:
            print('{}Finality update requested'.format(self.tab))
            self.update_t_final(config_t_final)

    def update_validator_connections(self):
        """Update connections to validators after a successful update
        of bridge validators with the validators in the config file.

        """
        self.channels = []
        self.stubs = []
        for validator in self.config_data['validators']:
            ip = validator['ip']
            channel = grpc.insecure_channel(ip)
            stub = BridgeOperatorStub(channel)
            self.channels.append(channel)
            self.stubs.append(stub)

        self.pool = Pool(len(self.stubs))

    def update_validators(self, new_validators):
        """Try to update the validator set with the one in the config file."""
        try:
            sigs, validator_indexes = self.get_new_validators_signatures(
                new_validators)
        except ValidatorMajorityError:
            print("{0}Failed to gather 2/3 validators signatures"
                  .format(self.tab))
            return False
        # broadcast transaction
        return self.set_validators(new_validators, validator_indexes, sigs)

    def set_validators(self, new_validators, validator_indexes, sigs):
        """Update validators on chain"""
        vs, rs, ss = self.prepare_rsv(sigs)
        construct_txn = self.eth_bridge.functions.update_validators(
            new_validators, validator_indexes, vs, rs, ss
        ).buildTransaction({
            'chainId': self.web3.eth.chainId,
            'from': self.proposer_acct.address,
            'nonce': self.web3.eth.getTransactionCount(
                self.proposer_acct.address
            ),
            'gas': 108036,
            'gasPrice': self.web3.toWei(9, 'gwei')
        })
        signed = self.proposer_acct.sign_transaction(construct_txn)
        tx_hash = self.web3.eth.sendRawTransaction(signed.rawTransaction)
        receipt = self.web3.eth.waitForTransactionReceipt(tx_hash)

        if receipt.status == 1:
            print("{}{} Set new validators update success"
                  .format(self.tab, u'\U0001f58b'))
            return True
        else:
            print("{}Set new validators failed: nonce already used, or "
                  "invalid signature: {}".format(self.tab, receipt))
            return False

    def get_new_validators_signatures(self, validators):
        """Request approvals of validators for the new validator set."""
        nonce = self.eth_bridge.functions.Nonce().call()
        new_validators_msg = NewValidators(
            validators=validators, destination_nonce=nonce)
        concat_vals = b''
        for val in validators:
            concat_vals += pad_bytes(b'\x00', 32, bytes.fromhex(val[2:]))
        msg_bytes = concat_vals \
            + nonce.to_bytes(32, byteorder='big') \
            + bytes.fromhex(self.eth_id)\
            + bytes("V", 'utf-8')
        h = keccak(msg_bytes)
        # get validator signatures and verify sig in worker
        validator_indexes = [i for i in range(len(self.stubs))]
        worker = partial(
            self.get_signature_worker, "GetAergoValidatorsSignature",
            new_validators_msg, h
        )
        approvals = self.pool.map(worker, validator_indexes)
        sigs, validator_indexes = self.extract_signatures(approvals)
        return sigs, validator_indexes

    def update_t_anchor(self, t_anchor):
        """Try to update the anchoring periode registered in the bridge
        contract.

        """
        try:
            sigs, validator_indexes = self.get_tempo_signatures(
                t_anchor, "GetAergoTAnchorSignature", "A")
        except ValidatorMajorityError:
            print("{0}Failed to gather 2/3 validators signatures"
                  .format(self.tab))
            return
        # broadcast transaction
        self.set_t_anchor(t_anchor, validator_indexes, sigs)

    def set_t_anchor(self, t_anchor, validator_indexes, sigs):
        """Update t_anchor on chain"""
        vs, rs, ss = self.prepare_rsv(sigs)
        construct_txn = self.eth_bridge.functions.update_t_anchor(
            t_anchor, validator_indexes, vs, rs, ss
        ).buildTransaction({
            'chainId': self.web3.eth.chainId,
            'from': self.proposer_acct.address,
            'nonce': self.web3.eth.getTransactionCount(
                self.proposer_acct.address
            ),
            'gas': 108036,
            'gasPrice': self.web3.toWei(9, 'gwei')
        })
        signed = self.proposer_acct.sign_transaction(construct_txn)
        tx_hash = self.web3.eth.sendRawTransaction(signed.rawTransaction)
        receipt = self.web3.eth.waitForTransactionReceipt(tx_hash)

        if receipt.status == 1:
            print("{}{} update_t_anchor success".format(self.tab, u'\u231B'))
            return True
        else:
            print("{}update_t_anchor failed: nonce already used, or "
                  "invalid signature: {}".format(self.tab, receipt))
            return False

    def update_t_final(self, t_final):
        """Try to update the anchoring periode registered in the bridge
        contract.

        """
        try:
            sigs, validator_indexes = self.get_tempo_signatures(
                t_final, "GetAergoTFinalSignature", "F")
        except ValidatorMajorityError:
            print("{0}Failed to gather 2/3 validators signatures"
                  .format(self.tab))
            return
        # broadcast transaction
        self.set_t_final(t_final, validator_indexes, sigs)

    def set_t_final(self, t_final, validator_indexes, sigs):
        """Update t_final on chain"""
        vs, rs, ss = self.prepare_rsv(sigs)
        construct_txn = self.eth_bridge.functions.update_t_final(
            t_final, validator_indexes, vs, rs, ss
        ).buildTransaction({
            'chainId': self.web3.eth.chainId,
            'from': self.proposer_acct.address,
            'nonce': self.web3.eth.getTransactionCount(
                self.proposer_acct.address
            ),
            'gas': 108036,
            'gasPrice': self.web3.toWei(9, 'gwei')
        })
        signed = self.proposer_acct.sign_transaction(construct_txn)
        tx_hash = self.web3.eth.sendRawTransaction(signed.rawTransaction)
        receipt = self.web3.eth.waitForTransactionReceipt(tx_hash)

        if receipt.status == 1:
            print("{}{} update_t_final success".format(self.tab, u'\u231B'))
            return True
        else:
            print("{}update_t_final failed: nonce already used, or "
                  "invalid signature: {}".format(self.tab, receipt))
            return False

    def get_tempo_signatures(self, tempo, rpc_service, tempo_id):
        """Request approvals of validators for the new t_anchor or t_final."""
        nonce = self.eth_bridge.functions.Nonce().call()
        new_tempo_msg = NewTempo(
            tempo=tempo, destination_nonce=nonce)
        msg_bytes = tempo.to_bytes(32, byteorder='big') \
            + nonce.to_bytes(32, byteorder='big') \
            + bytes.fromhex(self.eth_id)\
            + bytes(tempo_id, 'utf-8')
        h = keccak(msg_bytes)
        validator_indexes = [i for i in range(len(self.stubs))]
        worker = partial(
            self.get_signature_worker, rpc_service,
            new_tempo_msg, h
        )
        approvals = self.pool.map(worker, validator_indexes)
        sigs, validator_indexes = self.extract_signatures(approvals)
        return sigs, validator_indexes

    def load_config_data(self) -> Dict:
        with open(self.config_file_path, "r") as f:
            config_data = json.load(f)
        return config_data

    def shutdown(self):
        print("\nDisconnecting AERGO")
        self.hera.disconnect()
        print("Closing channels")
        for channel in self.channels:
            channel.close()


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
        '--auto_update', dest='auto_update', action='store_true',
        help='Update bridge contract when settings change in config file')
    parser.set_defaults(auto_update=False)
    args = parser.parse_args()

    proposer = EthProposerClient(
        args.config_file_path, args.aergo, args.eth,
        privkey_name=args.privkey_name, auto_update=args.auto_update
    )
    proposer.run()
