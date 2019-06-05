
from functools import (
    partial,
)
from getpass import getpass
import grpc
import hashlib
import json
from multiprocessing.dummy import (
    Pool,
)
import time

from typing import (
    Tuple,
    Optional,
    List,
    Any,
    Dict
)

import aergo.herapy as herapy
from aergo.herapy.utils.signature import (
    verify_sig,
)

from bridge_operator.bridge_operator_pb2_grpc import (
    BridgeOperatorStub,
)
from bridge_operator.bridge_operator_pb2 import (
    EthAnchor,
)
from bridge_operator.op_utils import (
    query_aergo_tempo,
    query_aergo_validators,
)
from web3 import (
    Web3,
)
from web3.middleware import (
    geth_poa_middleware,
)


COMMIT_TIME = 3
_ONE_DAY_IN_SECONDS = 60 * 60 * 24


class ValidatorMajorityError(Exception):
    pass


class AergoProposerClient:
    """The bridge proposer periodically (every t_anchor) broadcasts
    the finalized trie state root (after lib) of the bridge contract
    on both sides of the bridge after validation by the Validator servers.
    It first checks the last merged height and waits until
    now > lib + t_anchor is reached, then merges the current finalised
    block (lib). Start again after waiting t_anchor.
    """

    def __init__(
        self,
        config_data: Dict,
        aergo_net: str,
        eth_net: str,
        eth_block_time: int,
        privkey_name: str = None,
        privkey_pwd: str = None,
        eth_poa: bool = False
    ) -> None:
        self.config_data = config_data
        self.eth_block_time = eth_block_time
        print("------ Connect Aergo and Ethereum -----------")
        self.hera = herapy.Aergo()
        self.hera.connect(self.config_data[aergo_net]['ip'])

        ip = config_data[eth_net]['ip']
        self.web3 = Web3(Web3.HTTPProvider("http://" + ip))
        if eth_poa:
            self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        assert self.web3.isConnected()

        self.eth_bridge = config_data[eth_net]['bridges'][aergo_net]['addr']
        self.aergo_bridge = config_data[aergo_net]['bridges'][eth_net]['addr']
        self.aergo_id = config_data[aergo_net]['bridges'][eth_net]['id']
        self.eth_id = config_data[eth_net]['bridges'][aergo_net]['id']

        print("------ Connect to Validators -----------")
        validators = query_aergo_validators(self.hera, self.aergo_bridge)
        print("Validators: ", validators)
        # create all channels with validators
        self.channels: List[grpc._channel.Channel] = []
        self.stubs: List[BridgeOperatorStub] = []
        for i, validator in enumerate(self.config_data['validators']):
            assert validators[i] == validator['addr'], \
                "Validators in config file do not match bridge validators"\
                "Expected validators: {}".format(validators)
            ip = validator['ip']
            channel = grpc.insecure_channel(ip)
            stub = BridgeOperatorStub(channel)
            self.channels.append(channel)
            self.stubs.append(stub)

        self.pool = Pool(len(self.stubs))

        # get the current t_anchor and t_final for both sides of bridge
        self.t_anchor, self.t_final = query_aergo_tempo(
            self.hera, self.aergo_bridge
        )
        print("{}              <- {} (t_final={}) : t_anchor={}"
              .format(aergo_net, eth_net, self.t_final, self.t_anchor))

        print("------ Set Sender Account -----------")
        if privkey_name is None:
            privkey_name = 'proposer'
        if privkey_pwd is None:
            privkey_pwd = getpass("Decrypt exported private key '{}'\n"
                                  "Password: ".format(privkey_name))
        sender_priv_key = self.config_data['wallet'][privkey_name]['priv_key']
        self.hera.import_account(sender_priv_key, privkey_pwd)
        print("  > Proposer Address: {}".format(self.hera.account.address))

    def get_validators_signatures(
        self,
        root: str,
        merge_height: int,
        nonce: int,
        tab: str
    ) -> Tuple[List[str], List[int]]:
        """ Query all validators and gather 2/3 of their signatures. """

        # messages to get signed
        msg_str = root + ',' + str(merge_height) + ',' + str(nonce) + ',' \
            + self.aergo_id + "R"
        msg = bytes(msg_str, 'utf-8')
        h = hashlib.sha256(msg).digest()

        anchor = EthAnchor(
            root=root, height=str(merge_height), destination_nonce=str(nonce)
        )

        # get validator signatures and verify sig in worker
        validator_indexes = [i for i in range(len(self.stubs))]
        worker = partial(self.get_signature_worker, tab, anchor, h)
        approvals = self.pool.map(worker, validator_indexes)

        sigs, validator_indexes = self.extract_signatures(approvals)

        return sigs, validator_indexes

    def get_signature_worker(
        self,
        tab: str,
        anchor,
        h: bytes,
        index: int
    ) -> Optional[Any]:
        """ Get a validator's (index) signature and verify it"""
        try:
            approval = self.stubs[index].GetEthAnchorSignature(anchor)
        except grpc.RpcError as e:
            print(e)
            return None
        if approval.error:
            print("{}{}".format(tab, approval.error))
            return None
        if approval.address != self.config_data['validators'][index]['addr']:
            # check nothing is wrong with validator address
            print("{}Unexpected validato {} address : {}"
                  .format(tab, index, approval.address))
            return None
        # validate signature
        if not verify_sig(h, approval.sig, approval.address):
            print("{}Invalid signature from validator {}"
                  .format(tab, index))
            return None
        return approval

    def extract_signatures(
        self,
        approvals: List[Any]
    ) -> Tuple[List[str], List[int]]:
        """ Convert signatures to hex string and keep 2/3 of them."""
        sigs, validator_indexes = [], []
        for i, approval in enumerate(approvals):
            if approval is not None:
                # convert to hex string for lua
                sigs.append('0x' + approval.sig.hex())
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
        tab: str = ""
    ) -> int:
        """ Wait until t_anchor has passed after merged height.
        Return the next finalized block after t_anchor to be the next anchor
        """
        best_height = self.web3.eth.blockNumber
        lib = best_height - self.t_final
        # wait for merged_height + t_anchor > lib
        wait = (merged_height + self.t_anchor) - lib + 1
        while wait > 0:
            print("waiting new anchor time :", wait * self.eth_block_time,
                  "s ...")
            time.sleep(wait * self.eth_block_time)
            # Wait lib > last merged block height + t_anchor
            best_height = self.web3.eth.blockNumber
            lib = best_height - self.t_final
            wait = (merged_height + self.t_anchor) - lib + 1
        return lib

    def set_root(
        self,
        root: str,
        next_anchor_height: int,
        validator_indexes: List[int],
        sigs: List[str],
        tab: str
    ) -> None:
        """Anchor a new root on chain"""
        tx, result = self.hera.call_sc(
            self.aergo_bridge, "set_root",
            args=[root, next_anchor_height, validator_indexes, sigs]
        )
        if result.status != herapy.CommitStatus.TX_OK:
            print("{}Anchor on aergo Tx commit failed : {}"
                  .format(tab, result))
            return

        time.sleep(COMMIT_TIME)
        result = self.hera.get_tx_result(tx.tx_hash)
        if result.status != herapy.TxResultStatus.SUCCESS:
            print("{}Anchor failed: already anchored, or invalid "
                  "signature: {}".format(tab, result))
        else:
            print("{0}Anchor success,\n{0}wait until next anchor "
                  "time: {1}s...".format(tab, self.t_anchor * self.eth_block_time))

    def run(
        self,
        tab: str = ""
    ) -> None:
        """ Gathers signatures from validators, verifies them, and if 2/3 majority
        is acquired, set the new anchored root in aergo_bridge.
        """
        while True:  # anchor a new root
            # Get last merge information
            merge_info_from = self.hera.query_sc_state(self.aergo_bridge,
                                                       ["_sv_Height",
                                                        "_sv_Root",
                                                        "_sv_Nonce"
                                                        ])
            merged_height_from, merged_root_from, nonce_to = \
                [proof.value for proof in merge_info_from.var_proofs]
            merged_height_from = int(merged_height_from)
            nonce_to = int(nonce_to)

            print("{0} __\n"
                  "{0}| last merged height: {1}\n"
                  "{0}| last merged contract trie root: {2}...\n"
                  "{0}| current update nonce: {3}\n"
                  .format(tab, merged_height_from,
                          merged_root_from.decode('utf-8')[1:20], nonce_to))

            while True:  # try to gather 2/3 validators
                # Wait for the next anchor time
                next_anchor_height = self.wait_next_anchor(merged_height_from,
                                                           tab)
                # Get root of next anchor to broadcast
                state = self.web3.eth.getProof(self.eth_bridge, [],
                                               next_anchor_height)
                root = state.storageHash.hex()[2:]
                if len(root) == 0:
                    print("{}waiting deployment finalization...".format(tab))
                    time.sleep(5)
                    continue

                print("{}anchoring new root :'0x{}...'"
                      .format(tab, root[:17]))
                print("{}Gathering signatures from validators ..."
                      .format(tab))

                try:
                    sigs, validator_indexes = self.get_validators_signatures(
                            root, next_anchor_height, nonce_to, tab
                        )
                except ValidatorMajorityError:
                    print("{0}Failed to gather 2/3 validators signatures,\n"
                          "{0}waiting for next anchor..."
                          .format(tab))
                    time.sleep(self.t_anchor * self.eth_block_time)
                    continue
                break

            # don't broadcast if somebody else already did
            last_merge = self.hera.query_sc_state(self.aergo_bridge,
                                                  ["_sv_Height"])
            merged_height = int(last_merge.var_proofs[0].value)
            if merged_height + self.t_anchor >= next_anchor_height:
                print("{}Not yet anchor time "
                      "or another proposer already anchored".format(tab))
                print(merged_height, self.t_anchor, next_anchor_height)
                wait = merged_height + self.t_anchor - next_anchor_height
                time.sleep(wait * self.eth_block_time)
                continue

            # Broadcast finalised merge block
            self.set_root(root, next_anchor_height, validator_indexes, sigs,
                          tab)

            # Wait t_anchor
            # counting commit time in t_anchor often leads to 'Next anchor not
            # reached exception.
            time.sleep(self.t_anchor * self.eth_block_time)

    def shutdown(self):
        print("\nDisconnecting AERGO")
        self.hera.disconnect()
        print("Closing channels")
        for channel in self.channels:
            channel.close()


if __name__ == '__main__':
    with open("./config.json", "r") as f:
        config_data = json.load(f)
    proposer = AergoProposerClient(
        config_data, 'aergo-local', 'eth-poa-local', 3, privkey_pwd='1234',
        eth_poa=True
    )
    proposer.run()
