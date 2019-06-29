from concurrent import (
    futures,
)
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
import os
import time

from typing import (
    Optional,
    Dict,
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
    BridgeOperatorServicer,
    add_BridgeOperatorServicer_to_server,
)
from bridge_operator.bridge_operator_pb2 import (
    AergoApproval,
    EthApproval
)
from bridge_operator.op_utils import (
    query_aergo_tempo,
    query_eth_tempo,
    query_aergo_validators,
    query_eth_validators,
)

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


class ValidatorService(BridgeOperatorServicer):
    """Validates anchors for the bridge proposer"""

    def __init__(
        self,
        config_data: Dict,
        aergo_net: str,
        eth_net: str,
        eth_abi: str,
        privkey_name: str = None,
        privkey_pwd: str = None,
        validator_index: int = 0,
        eth_poa: bool = False
    ) -> None:
        """ Initialize parameters of the bridge validator"""
        self.validator_index = validator_index
        print("------ Connect Aergo and Ethereum -----------")
        self.hera = herapy.Aergo()
        self.hera.connect(config_data['networks'][aergo_net]['ip'])

        ip = config_data['networks'][eth_net]['ip']
        self.web3 = Web3(Web3.HTTPProvider("http://" + ip))
        if eth_poa:
            self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        assert self.web3.isConnected()

        self.eth_bridge_addr = config_data['networks'][eth_net]['bridges'][aergo_net]['addr']
        self.eth_bridge = self.web3.eth.contract(
            address=self.eth_bridge_addr,
            abi=eth_abi
        )
        self.aergo_bridge = config_data['networks'][aergo_net]['bridges'][eth_net]['addr']
        self.aergo_id = config_data['networks'][aergo_net]['bridges'][eth_net]['id']
        self.eth_id = config_data['networks'][eth_net]['bridges'][aergo_net]['id']

        # check validators are correct
        aergo_vals = query_aergo_validators(self.hera, self.aergo_bridge)
        eth_vals = query_eth_validators(self.web3, self.eth_bridge_addr,
                                        eth_abi)
        for i, validator in enumerate(config_data['validators']):
            assert validator['addr'] == aergo_vals[i], \
                "Validators in config file do not match bridge validators"\
                "Expected aergo validators: {}".format(aergo_vals)
            assert validator['eth-addr'] == eth_vals[i], \
                "Validators in config file do not match bridge validators"\
                "Expected eth validators: {}".format(eth_vals)

        print("Aergo validators : ", aergo_vals)
        print("Ethereum validators : ", eth_vals)

        # TODO check validators match the ones in config

        # get the current t_anchor and t_final for both sides of bridge
        self.t_anchor_aergo, self.t_final_aergo = query_aergo_tempo(
            self.hera, self.aergo_bridge
        )
        self.t_anchor_eth, self.t_final_eth = query_eth_tempo(
            self.web3, self.eth_bridge_addr, eth_abi
        )
        print("{}             <- {} (t_final={}) : t_anchor={}"
              .format(aergo_net, eth_net, self.t_final_aergo,
                      self.t_anchor_aergo))
        print("{} (t_final={}) -> {}              : t_anchor={}"
              .format(aergo_net, self.t_final_eth, eth_net, self.t_anchor_eth))

        print("------ Set Signer Account -----------")
        if privkey_name is None:
            privkey_name = 'validator'
        if privkey_pwd is None:
            privkey_pwd = getpass("Decrypt Aergo and Ethereum accounts '{}'\n"
                                  "Password: ".format(privkey_name))
        # record private key for signing EthAnchor
        aergo_privkey = \
            config_data['wallet'][privkey_name]['priv_key']
        self.hera.import_account(aergo_privkey, privkey_pwd)
        self.aergo_addr = str(self.hera.account.address)
        print("  > Aergo validator Address: {}".format(self.aergo_addr))

        keystore = config_data["wallet-eth"][privkey_name]['keystore']
        file_path = os.path.dirname(os.path.realpath(__file__))
        root_path = os.path.dirname(file_path) + '/'
        with open(root_path + keystore, "r") as f:
            encrypted_key = f.read()

        # record private key for signing AergoAnchor
        self.eth_privkey = self.web3.eth.account.decrypt(encrypted_key,
                                                         privkey_pwd)
        acct = self.web3.eth.account.from_key(self.eth_privkey)
        self.eth_address = acct.address
        print("  > Ethereum validator Address: {}".format(self.eth_address))

    def GetAergoAnchorSignature(self, anchor, context):
        """ Verifies an aergo anchor and signs it to be broadcasted on ethereum
            aergo and ethereum nodes must be trusted.
        """
        err_msg = self.is_valid_aergo_anchor(anchor)
        if err_msg is not None:
            return AergoApproval(error=err_msg)

        # sign anchor and return approval
        msg_bytes = anchor.root + anchor.height.to_bytes(32, byteorder='big') \
            + anchor.destination_nonce.to_bytes(32, byteorder='big') \
            + bytes.fromhex(self.eth_id)\
            + bytes("R", 'utf-8')
        h = keccak(msg_bytes)
        sig = self.web3.eth.account.signHash(h, private_key=self.eth_privkey)
        approval = AergoApproval(
            address=self.eth_address, sig=bytes(sig.signature))
        print("{0}Validator {1} signed a new anchor for {2},\n"
              "{0}with nonce {3}"
              .format("\t"*5, self.validator_index, "Ethereum",
                      anchor.destination_nonce))
        return approval

    def is_valid_aergo_anchor(
        self,
        anchor,
    ) -> Optional[str]:
        """ An anchor is valid if :
            1- it's height is finalized
            2- it's root for that height is correct.
            3- it's nonce is correct
            4- it's height is higher than previous anchored height + t_anchor
        """
        # 1- get the last block height and check anchor height > LIB
        # lib = best_height - finalized_from
        lib = self.hera.get_status().consensus_info.status['LibNo']
        if int(anchor.height) > lib:
            print("anchor not finalized\n", anchor)
            return "anchor not finalized"

        # 2- get contract state root at origin_height
        # and check equals anchor root
        block = self.hera.get_block(block_height=int(anchor.height))
        contract = self.hera.get_account(address=self.aergo_bridge, proof=True,
                                         root=block.blocks_root_hash)
        root = contract.state_proof.state.storageRoot
        if root != anchor.root:
            print("root to sign doesnt match expected root\n", anchor)
            return "root to sign doesnt match expected root"

        last_nonce_to = self.eth_bridge.functions.Nonce().call()
        last_merged_height_from = self.eth_bridge.functions.Height().call()

        # 3- check merkle bridge nonces are correct
        if last_nonce_to != int(anchor.destination_nonce):
            print("anchor nonce is invalid\n", anchor)
            return "anchor nonce is invalid"

        # 4- check anchored height comes after the previous one and t_anchor is
        # passed
        if last_merged_height_from + self.t_anchor_eth > int(anchor.height):
            print("root update height is invalid: "
                  "must be higher than previous merge + t_anchor\n", anchor)
            return "root update height is invalid"
        return None

    def GetEthAnchorSignature(self, anchor, context):
        """ Verifies an ethereum anchor and signs it to be broadcasted on aergo
            aergo and ethereum nodes must be trusted.
        """
        err_msg = self.is_valid_eth_anchor(anchor)
        if err_msg is not None:
            return EthApproval(error=err_msg)

        # sign anchor and return approval
        msg = bytes(
            anchor.root + ',' + anchor.height + ',' + anchor.destination_nonce
            + ',' + self.aergo_id + "R", 'utf-8')
        h = hashlib.sha256(msg).digest()
        sig = self.hera.account.private_key.sign_msg(h)
        approval = EthApproval(address=self.aergo_addr, sig=sig)
        print("{0}Validator {1} signed a new anchor for {2},\n"
              "{0}with nonce {3}"
              .format("\t"*5, self.validator_index, "Aergo",
                      anchor.destination_nonce))
        return approval

    def is_valid_eth_anchor(
        self,
        anchor
    ) -> Optional[str]:
        """ An anchor is valid if :
            1- it's height is finalized
            2- it's root for that height is correct.
            3- it's nonce is correct
            4- it's height is higher than previous anchored height + t_anchor
        """
        # 1- get the last block height and check anchor height > LIB
        # lib = best_height - finalized_from
        best_height = self.web3.eth.blockNumber
        lib = best_height - self.t_final_aergo
        if int(anchor.height) > lib:
            print("anchor not finalized\n", anchor)
            return "anchor not finalized"

        # 2- get contract state root at origin_height
        # and check equals anchor root
        state = self.web3.eth.getProof(self.eth_bridge_addr, [],
                                       int(anchor.height))
        root = state.storageHash.hex()[2:]
        if root != anchor.root:
            print("root to sign doesnt match expected root\n", anchor)
            return "root to sign doesnt match expected root"

        merge_info = self.hera.query_sc_state(
            self.aergo_bridge, ["_sv_Nonce", "_sv_Height"]
        )
        last_nonce_to, last_merged_height_from = \
            [int(proof.value) for proof in merge_info.var_proofs]

        # 3- check merkle bridge nonces are correct
        if last_nonce_to != int(anchor.destination_nonce):
            print("anchor nonce is invalid\n", anchor)
            return "anchor nonce is invalid"

        # 4- check anchored height comes after the previous one and t_anchor is
        # passed
        if last_merged_height_from + self.t_anchor_aergo > int(anchor.height):
            print("root update height is invalid: "
                  "must be higher than previous merge + t_anchor\n", anchor)
            return "root update height is invalid"
        return None


class ValidatorServer:
    def __init__(
        self,
        config_file_path: str,
        aergo_net: str,
        eth_net: str,
        eth_abi: str,
        privkey_name: str = None,
        privkey_pwd: str = None,
        validator_index: int = 0,
        eth_poa: bool = False
    ) -> None:
        with open(config_file_path, "r") as f:
            config_data = json.load(f)
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        add_BridgeOperatorServicer_to_server(
            ValidatorService(
                config_data, aergo_net, eth_net, eth_abi, privkey_name,
                privkey_pwd, validator_index, eth_poa
            ),
            self.server
        )
        self.server.add_insecure_port(config_data['validators']
                                      [validator_index]['ip'])
        self.validator_index = validator_index

    def run(self):
        self.server.start()
        print("server", self.validator_index, " started")
        print("{}Aergo{}Ethereum".format("\t", "\t"*4))
        try:
            while True:
                time.sleep(_ONE_DAY_IN_SECONDS)
        except KeyboardInterrupt:
            print("\nShutting down validator")
            self.shutdown()

    def shutdown(self):
        self.server.stop(0)


def _serve_worker(servers, index):
    servers[index].run()


def _serve_all(config_file_path, aergo_net, eth_net, eth_abi,
               privkey_name=None, privkey_pwd=None):
    """ For testing, run all validators in different threads """
    with open(config_file_path, "r") as f:
        config_data = json.load(f)
    validator_indexes = [i for i in range(len(config_data['validators']))]
    servers = [ValidatorServer(config_file_path, aergo_net, eth_net, eth_abi,
                               privkey_name, privkey_pwd, index, True)
               for index in validator_indexes]
    worker = partial(_serve_worker, servers)
    pool = Pool(len(validator_indexes))
    pool.map(worker, validator_indexes)


if __name__ == '__main__':
    with open("./contracts/solidity/bridge_abi.txt", "r") as f:
        eth_abi = f.read()
    with open("./config.json", "r") as f:
        config_data = json.load(f)
    # validator = ValidatorServer(
    #   "./config.json", 'aergo-local', 'eth-poa-local', eth_abi,
    #   privkey_name='validator', privkey_pwd='1234', validator_index=1,
    #   eth_poa=True
    # )
    # validator.run()
    _serve_all("./config.json", 'aergo-local', 'eth-poa-local', eth_abi,
               privkey_name='validator', privkey_pwd='1234')
