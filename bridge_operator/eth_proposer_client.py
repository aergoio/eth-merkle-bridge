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
from eth_utils import (
    keccak,
)

from bridge_operator.bridge_operator_pb2_grpc import (
    BridgeOperatorStub,
)
from bridge_operator.bridge_operator_pb2 import (
    AergoAnchor,
)
from bridge_operator.op_utils import (
    query_eth_tempo,
    query_eth_validators,
)


class ValidatorMajorityError(Exception):
    pass


class EthProposerClient(threading.Thread):
    """The ethereum bridge proposer periodically (every t_anchor) broadcasts
    the finalized Aergo trie state root (after lib) of the bridge contract
    onto the ethereum bridge contract after validation by the Validators.
    It first checks the last merged height and waits until
    now > lib + t_anchor is reached, then merges the current finalised
    block (lib). Start again after waiting t_anchor.
    EthProposerClient anchors an Aergo state root onto Ethereum.
    """

    def __init__(
        self,
        config_data: Dict,
        aergo_net: str,
        eth_net: str,
        privkey_name: str = None,
        privkey_pwd: str = None,
        tab: str = ""
    ) -> None:
        threading.Thread.__init__(self)
        self.config_data = config_data
        self.tab = tab
        print("------ Connect Aergo and Ethereum -----------")
        self.hera = herapy.Aergo()
        self.hera.connect(self.config_data['networks'][aergo_net]['ip'])

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
        self.aergo_id = (config_data['networks'][aergo_net]['bridges'][eth_net]
                         ['id'])
        self.eth_id = (config_data['networks'][eth_net]['bridges'][aergo_net]
                       ['id'])

        print("------ Connect to Validators -----------")
        validators = query_eth_validators(self.web3, eth_bridge_address,
                                          eth_abi)
        print("Validators: ", validators)
        # create all channels with validators
        self.channels: List[grpc._channel.Channel] = []
        self.stubs: List[BridgeOperatorStub] = []
        for i, validator in enumerate(self.config_data['validators']):
            assert validators[i] == validator['eth-addr'], \
                "Validators in config file do not match bridge validators"\
                "Expected validators: {}".format(validators)
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
        keystore = self.config_data["wallet-eth"][privkey_name]['keystore']
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

    def get_validators_signatures(
        self,
        root: bytes,
        merge_height: int,
        nonce: int,
    ) -> Tuple[List[str], List[int]]:
        """ Query all validators and gather 2/3 of their signatures. """
        # messages to get signed
        msg_bytes = root + merge_height.to_bytes(32, byteorder='big') \
            + nonce.to_bytes(32, byteorder='big') \
            + bytes.fromhex(self.eth_id) \
            + bytes("R", 'utf-8')
        h = keccak(msg_bytes)

        anchor = AergoAnchor(
            root=root, height=merge_height, destination_nonce=nonce
        )

        # get validator signatures and verify sig in worker
        validator_indexes = [i for i in range(len(self.stubs))]
        worker = partial(self.get_signature_worker, anchor, h)
        approvals = self.pool.map(worker, validator_indexes)

        sigs, validator_indexes = self.extract_signatures(approvals)

        return sigs, validator_indexes

    def get_signature_worker(
        self,
        anchor,
        h: bytes,
        idx: int
    ):
        """ Get a validator's (index) signature and verify it"""
        try:
            approval = self.stubs[idx].GetAergoAnchorSignature(anchor)
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
            print(self.tab, "waiting new anchor time :", wait, "s ...")
            time.sleep(wait)
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
            print("{0}Anchor success,\n{0}wait until next anchor "
                  "time: {1}s...".format(self.tab, self.t_anchor))
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

            print("{0} __\n"
                  "{0}| last merged height: {1}\n"
                  "{0}| last merged contract trie root: {2}...\n"
                  "{0}| current update nonce: {3}\n"
                  .format(self.tab, merged_height_from,
                          merged_root_from.hex()[0:20], nonce_to))

            while True:  # try to gather 2/3 validators
                # Wait for the next anchor time
                next_anchor_height = self.wait_next_anchor(merged_height_from)
                # Get root of next anchor to broadcast
                block = self.hera.get_block(block_height=next_anchor_height)
                contract = self.hera.get_account(address=self.aergo_bridge,
                                                 proof=True,
                                                 root=block.blocks_root_hash)
                root = contract.state_proof.state.storageRoot
                if len(root) == 0:
                    print("{}waiting deployment finalization..."
                          .format(self.tab))
                    time.sleep(5)
                    continue

                print("{}anchoring new root :'0x{}...'"
                      .format(self.tab, root[:8].hex()))
                print("{}Gathering signatures from validators ..."
                      .format(self.tab))

                try:
                    sigs, validator_indexes = self.get_validators_signatures(
                            root, next_anchor_height, nonce_to
                        )
                except ValidatorMajorityError:
                    print("{0}Failed to gather 2/3 validators signatures,\n"
                          "{0}waiting for next anchor..."
                          .format(self.tab))
                    time.sleep(self.t_anchor)
                    continue
                break

            # don't broadcast if somebody else already did
            merged_height = self.eth_bridge.functions.Height().call()
            if merged_height + self.t_anchor >= next_anchor_height:
                print("{}Not yet anchor time, maybe another proposer"
                      " already anchored".format(self.tab))
                time.sleep(merged_height + self.t_anchor - next_anchor_height)
                continue

            # Broadcast finalised AergoAnchor on Ethereum
            self.set_root(root, next_anchor_height, validator_indexes, sigs)

            # Wait t_anchor
            time.sleep(self.t_anchor)

    def shutdown(self):
        print("\nDisconnecting AERGO")
        self.hera.disconnect()
        print("Closing channels")
        for channel in self.channels:
            channel.close()


if __name__ == '__main__':
    with open("./test_config.json", "r") as f:
        config_data = json.load(f)

    proposer = EthProposerClient(
        config_data, 'aergo-local', 'eth-poa-local', privkey_pwd='1234')
    proposer.run()
