import argparse
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
import time

from typing import (
    Optional,
    Dict,
)

import aergo.herapy as herapy
from web3 import (
    Web3,
)
from web3._utils.encoding import (
    pad_bytes,
)
from web3.middleware import (
    geth_poa_middleware,
)
from eth_utils import (
    keccak,
)

from ethaergo_bridge_operator.bridge_operator_pb2_grpc import (
    BridgeOperatorServicer,
    add_BridgeOperatorServicer_to_server,
)
from ethaergo_bridge_operator.bridge_operator_pb2 import (
    Approval,
)
from ethaergo_bridge_operator.op_utils import (
    query_aergo_tempo,
    query_eth_tempo,
    query_aergo_validators,
    query_eth_validators,
    query_unfreeze_fee,
    query_aergo_id,
    query_eth_id,
)

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


class ValidatorService(BridgeOperatorServicer):
    """Validates anchors for the bridge proposer.

    The validatorService and onchain bridge contracts are designed
    so that validators don't need to care about which proposer is
    calling them, validators will sign anything that is correct and
    there can be multiple proposers.

    """

    def __init__(
        self,
        config_file_path: str,
        aergo_net: str,
        eth_net: str,
        privkey_name: str = None,
        privkey_pwd: str = None,
        validator_index: int = 0,
        auto_update: bool = False,
        root_path: str = './'
    ) -> None:
        """ Initialize parameters of the bridge validator"""
        self.config_file_path = config_file_path
        config_data = self.load_config_data()
        self.validator_index = validator_index
        self.aergo_net = aergo_net
        self.eth_net = eth_net
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

        # remember bridge contracts
        bridge_abi_path = (config_data['networks'][eth_net]['bridges']
                           [aergo_net]['bridge_abi'])
        with open(bridge_abi_path, "r") as f:
            eth_abi = f.read()
        self.eth_bridge_addr = (config_data['networks'][eth_net]['bridges']
                                [aergo_net]['addr'])
        self.eth_bridge = self.web3.eth.contract(
            address=self.eth_bridge_addr,
            abi=eth_abi
        )
        self.aergo_bridge = (config_data['networks'][aergo_net]['bridges']
                             [eth_net]['addr'])
        self.aergo_id = query_aergo_id(self.hera, self.aergo_bridge)
        self.eth_id = query_eth_id(self.web3, self.eth_bridge_addr, eth_abi)

        # check validators are correct and warn the validator will vote for
        # a new validator set
        aergo_vals = query_aergo_validators(self.hera, self.aergo_bridge)
        eth_vals = query_eth_validators(self.web3, self.eth_bridge_addr,
                                        eth_abi)
        print("Current Aergo validators : ", aergo_vals)
        print("Current Ethereum validators : ", eth_vals)
        # get the current t_anchor and t_final for both sides of bridge
        t_anchor_aergo, t_final_aergo = query_aergo_tempo(
            self.hera, self.aergo_bridge
        )
        t_anchor_eth, t_final_eth = query_eth_tempo(
            self.web3, self.eth_bridge_addr, eth_abi
        )
        print("{}             <- {} (t_final={}) : t_anchor={}"
              .format(aergo_net, eth_net, t_final_aergo,
                      t_anchor_aergo))
        print("{} (t_final={}) -> {}              : t_anchor={}"
              .format(aergo_net, t_final_eth, eth_net, t_anchor_eth))

        if auto_update:
            print("WARNING: This validator will vote for settings update in "
                  "config.json")
            if len(aergo_vals) != len(eth_vals):
                print("WARNING: different number of validators on both sides "
                      "of the bridge")
            if len(config_data['validators']) != len(aergo_vals):
                print("WARNING: This validator is voting for a new set of "
                      "aergo validators")
            if len(config_data['validators']) != len(eth_vals):
                print("WARNING: This validator is voting for a new set of eth "
                      "validators")
            try:
                for i, validator in enumerate(config_data['validators']):
                    if validator['addr'] != aergo_vals[i]:
                        print("WARNING: This validator is voting for a new "
                              "set of aergo validators\n")
                    if validator['eth-addr'] != eth_vals[i]:
                        print("WARNING: This validator is voting for a new "
                              "set of eth validators\n")
                    break
            except IndexError:
                pass

            t_anchor_aergo_c = (config_data['networks'][self.aergo_net]
                                ['bridges'][self.eth_net]['t_anchor'])
            t_final_aergo_c = (config_data['networks'][self.aergo_net]
                               ['bridges'][self.eth_net]['t_final'])
            t_anchor_eth_c = (config_data['networks'][self.eth_net]['bridges']
                              [self.aergo_net]['t_anchor'])
            t_final_eth_c = (config_data['networks'][self.eth_net]['bridges']
                             [self.aergo_net]['t_final'])
            if t_anchor_aergo_c != t_anchor_aergo:
                print("WARNING: This validator is voting to update anchoring "
                      "periode on aergo")
            if t_final_aergo_c != t_final_aergo:
                print("WARNING: This validator is voting to update finality "
                      "of eth on aergo")
            if t_anchor_eth_c != t_anchor_eth:
                print("WARNING: This validator is voting to update anchoring "
                      "periode on eth")
            if t_final_eth_c != t_final_eth:
                print("WARNING: This validator is voting to update finality "
                      "of aergo on eth")

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

        # record private key for signing AergoAnchor
        keystore = config_data["wallet-eth"][privkey_name]['keystore']
        with open(root_path + keystore, "r") as f:
            encrypted_key = f.read()

        self.eth_privkey = self.web3.eth.account.decrypt(encrypted_key,
                                                         privkey_pwd)
        acct = self.web3.eth.account.from_key(self.eth_privkey)
        self.eth_address = acct.address.lower()
        print("  > Ethereum validator Address: {}".format(self.eth_address))

    def load_config_data(self) -> Dict:
        with open(self.config_file_path, "r") as f:
            config_data = json.load(f)
        return config_data

    def GetAergoAnchorSignature(self, anchor, context):
        """ Verifies an aergo anchor and signs it to be broadcasted on ethereum
            aergo and ethereum nodes must be trusted.

        Note:
            Anchoring service has priority over settings update because it can
            take time to gather signatures for settings update or a validator
            may not be aware settings have changed.
            So the current onchain bridge settings are queried every time.

        """
        err_msg = self.is_valid_aergo_anchor(anchor)
        if err_msg is not None:
            return Approval(error=err_msg)

        # sign anchor and return approval
        msg_bytes = anchor.root + anchor.height.to_bytes(32, byteorder='big') \
            + anchor.destination_nonce.to_bytes(32, byteorder='big') \
            + self.eth_id \
            + bytes("R", 'utf-8')
        h = keccak(msg_bytes)
        sig = self.web3.eth.account.signHash(h, private_key=self.eth_privkey)
        approval = Approval(
            address=self.eth_address, sig=bytes(sig.signature))
        print("{0}{1} Validator {2} signed a new anchor for {3},\n"
              "{0}with nonce {4}"
              .format("\t"*5, u'\u2693', self.validator_index, "Ethereum",
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
        if anchor.height > lib:
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

        last_nonce_to = self.eth_bridge.functions._nonce().call()
        last_merged_height_from = self.eth_bridge.functions._anchorHeight().call()

        # 3- check merkle bridge nonces are correct
        if last_nonce_to != anchor.destination_nonce:
            print("anchor nonce is invalid\n", anchor)
            return "anchor nonce is invalid"

        # 4- check anchored height comes after the previous one and t_anchor is
        # passed
        t_anchor = self.eth_bridge.functions._tAnchor().call()
        if last_merged_height_from + t_anchor > anchor.height:
            print("root update height is invalid: "
                  "must be higher than previous merge + t_anchor\n", anchor)
            return "root update height is invalid"
        return None

    def GetEthAnchorSignature(self, anchor, context):
        """ Verifies an ethereum anchor and signs it to be broadcasted on aergo
            aergo and ethereum nodes must be trusted.

        Note:
            Anchoring service has priority over settings update because it can
            take time to gather signatures for settings update or a validator
            may not be aware settings have changed.
            So the current onchain bridge settings are queries every time.

        """
        err_msg = self.is_valid_eth_anchor(anchor)
        if err_msg is not None:
            return Approval(error=err_msg)

        # sign anchor and return approval
        msg = bytes(
            anchor.root.hex() + ',' + str(anchor.height)
            + str(anchor.destination_nonce) + self.aergo_id + "R",
            'utf-8')
        h = hashlib.sha256(msg).digest()
        sig = self.hera.account.private_key.sign_msg(h)
        approval = Approval(address=self.aergo_addr, sig=sig)
        print("{0}{1} Validator {2} signed a new anchor for {3},\n"
              "{0}with nonce {4}"
              .format("", u'\u2693', self.validator_index, "Aergo",
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
        t_anchor, t_final = query_aergo_tempo(self.hera, self.aergo_bridge)
        # 1- get the last block height and check anchor height > LIB
        # lib = best_height - finalized_from
        best_height = self.web3.eth.blockNumber
        lib = best_height - t_final
        if anchor.height > lib:
            print("anchor not finalized\n", anchor)
            return "anchor not finalized"

        # 2- get contract state root at origin_height
        # and check equals anchor root
        root = bytes(
            self.web3.eth.getProof(self.eth_bridge_addr, [], anchor.height)
            .storageHash
        )
        if root != anchor.root:
            print("root to sign doesnt match expected root\n", anchor)
            return "root to sign doesnt match expected root"

        merge_info = self.hera.query_sc_state(
            self.aergo_bridge, ["_sv__nonce", "_sv__anchorHeight"]
        )
        last_nonce_to, last_merged_height_from = \
            [int(proof.value) for proof in merge_info.var_proofs]

        # 3- check merkle bridge nonces are correct
        if last_nonce_to != anchor.destination_nonce:
            print("anchor nonce is invalid\n", anchor)
            return "anchor nonce is invalid"

        # 4- check anchored height comes after the previous one and t_anchor is
        # passed
        if last_merged_height_from + t_anchor > anchor.height:
            print("root update height is invalid: "
                  "must be higher than previous merge + t_anchor\n", anchor)
            return "root update height is invalid"
        return None

    def GetEthTAnchorSignature(self, tempo_msg, context):
        """Get a vote(signature) from the validator to update the t_anchor
        setting in the Aergo bridge contract bridging to Ethereum

        """
        current_tempo = int(self.hera.query_sc_state(
            self.aergo_bridge, ["_sv__tAnchor"]
        ).var_proofs[0].value)
        return self.get_eth_tempo(tempo_msg, 't_anchor', "A", current_tempo)

    def GetEthTFinalSignature(self, tempo_msg, context):
        """Get a vote(signature) from the validator to update the t_final
        setting in the Aergo bridge contract bridging to Ethereum

        """
        current_tempo = int(self.hera.query_sc_state(
            self.aergo_bridge, ["_sv__tFinal"]
        ).var_proofs[0].value)
        return self.get_eth_tempo(tempo_msg, 't_final', "F", current_tempo)

    def get_eth_tempo(self, tempo_msg, tempo_str, tempo_id, current_tempo):
        if not self.auto_update:
            return Approval(error="Voting not enabled")
        # check destination nonce is correct
        nonce = int(self.hera.query_sc_state(
            self.aergo_bridge, ["_sv__nonce"]
        ).var_proofs[0].value)
        if nonce != tempo_msg.destination_nonce:
            return Approval(error="Incorrect Nonce")
        config_data = self.load_config_data()
        tempo = (config_data['networks'][self.aergo_net]['bridges']
                 [self.eth_net][tempo_str])
        # check new tempo is different from current one to prevent
        # update spamming
        if current_tempo == tempo:
            return Approval(
                error="New {} is same as current one".format(tempo_str))
        # check tempo matches the one in config
        if tempo != tempo_msg.tempo:
            return Approval(error="Refused to vote for this anchor periode")
        # sign anchor and return approval
        msg = bytes(
            str(tempo) + str(nonce) + self.aergo_id + tempo_id,
            'utf-8'
        )
        h = hashlib.sha256(msg).digest()
        sig = self.hera.account.private_key.sign_msg(h)
        approval = Approval(address=self.aergo_addr, sig=sig)
        print("{0}{1} Validator {2} signed a new {3} for {4},\n"
              "{0}with nonce {5}"
              .format("", u'\u231B', self.validator_index, tempo_str, "Aergo",
                      tempo_msg.destination_nonce))
        return approval

    def GetAergoTAnchorSignature(self, tempo_msg, context):
        """Get a vote(signature) from the validator to update the t_anchor
        setting in the Ethereum bridge contract bridging to Aergo

        """
        current_tempo = self.eth_bridge.functions._tAnchor().call()
        return self.get_aergo_tempo(tempo_msg, 't_anchor', 'A', current_tempo)

    def GetAergoTFinalSignature(self, tempo_msg, context):
        """Get a vote(signature) from the validator to update the t_final
        setting in the Ethereum bridge contract bridging to Aergo

        """
        current_tempo = self.eth_bridge.functions._tFinal().call()
        return self.get_aergo_tempo(tempo_msg, 't_final', 'F', current_tempo)

    def get_aergo_tempo(self, tempo_msg, tempo_str, tempo_id, current_tempo):
        if not self.auto_update:
            return Approval(error="Voting not enabled")
        # check destination nonce is correct
        nonce = self.eth_bridge.functions._nonce().call()
        if nonce != tempo_msg.destination_nonce:
            return Approval(error="Incorrect Nonce")
        config_data = self.load_config_data()
        tempo = (config_data['networks'][self.eth_net]['bridges']
                 [self.aergo_net][tempo_str])
        # check new tempo is different from current one to prevent
        # update spamming
        if current_tempo == tempo:
            return Approval(
                error="New {} is same as current one".format(tempo_str))
        # check tempo matches the one in config
        if tempo != tempo_msg.tempo:
            return Approval(error="Refused to vote for this anchor "
                                  "periode")
        # sign anchor and return approval
        msg_bytes = tempo.to_bytes(32, byteorder='big') \
            + nonce.to_bytes(32, byteorder='big') \
            + self.eth_id \
            + bytes(tempo_id, 'utf-8')
        h = keccak(msg_bytes)
        sig = self.web3.eth.account.signHash(h, private_key=self.eth_privkey)
        approval = Approval(
            address=self.eth_address, sig=bytes(sig.signature))
        print("{0}{1} Validator {2} signed a new {3} for {4},\n"
              "{0}with nonce {5}"
              .format("\t"*5, u'\u231B', self.validator_index, tempo_str,
                      "Ethereum", tempo_msg.destination_nonce))
        return approval

    def GetEthValidatorsSignature(self, val_msg, context):
        if not self.auto_update:
            return Approval(error="Voting not enabled")
        # check destination nonce is correct
        nonce = int(
            self.hera.query_sc_state(
                self.aergo_bridge, ["_sv__nonce"]).var_proofs[0].value
        )
        if nonce != val_msg.destination_nonce:
            return Approval(error="Incorrect Nonce")
        config_data = self.load_config_data()
        config_vals = [val['addr'] for val in config_data['validators']]
        # check new validators are different from current ones to prevent
        # update spamming
        current_validators = query_aergo_validators(self.hera,
                                                    self.aergo_bridge)
        if current_validators == config_vals:
            return Approval(error="New validators are same as current ones")
        # check validators are same in config file
        if config_vals != val_msg.validators:
            return Approval(error="Refused to vote for this validator "
                                  "set")
        # sign validators
        data = ""
        for val in config_vals:
            data += val
        data += str(nonce) + self.aergo_id + "V"
        data_bytes = bytes(data, 'utf-8')
        h = hashlib.sha256(data_bytes).digest()
        sig = self.hera.account.private_key.sign_msg(h)
        approval = Approval(address=self.aergo_addr, sig=sig)
        print("{0}{1} Validator {2} signed a new validator set for {3},\n"
              "{0}with nonce {4}"
              .format("", u'\U0001f58b', self.validator_index, "Aergo",
                      val_msg.destination_nonce))
        return approval

    def GetAergoValidatorsSignature(self, val_msg, context):
        if not self.auto_update:
            return Approval(error="Voting not enabled")
        # check destination nonce is correct
        nonce = self.eth_bridge.functions._nonce().call()
        if nonce != val_msg.destination_nonce:
            return Approval(error="Incorrect Nonce")
        config_data = self.load_config_data()
        config_vals = [val['eth-addr'] for val in config_data['validators']]
        # check new validators are different from current ones to prevent
        # update spamming
        current_validators = self.eth_bridge.functions.getValidators().call()
        if current_validators == config_vals:
            return Approval(error="New validators are same as current ones")
        # check validators are same in config file
        if config_vals != val_msg.validators:
            return Approval(error="Refused to vote for this validator "
                                  "set")
        # sign validators
        concat_vals = b''
        for val in config_vals:
            concat_vals += pad_bytes(b'\x00', 32, bytes.fromhex(val[2:]))
        msg_bytes = concat_vals \
            + nonce.to_bytes(32, byteorder='big') \
            + self.eth_id \
            + bytes("V", 'utf-8')
        h = keccak(msg_bytes)
        sig = self.web3.eth.account.signHash(h, private_key=self.eth_privkey)
        approval = Approval(
            address=self.eth_address, sig=bytes(sig.signature))
        print("{0}{1} Validator {2} signed a new validator set for {3},\n"
              "{0}with nonce {4}"
              .format("\t"*5, u'\U0001f58b', self.validator_index, "Ethereum",
                      val_msg.destination_nonce))
        return approval

    def GetAergoUnfreezeFeeSignature(self, new_fee_msg, context):
        """Get a vote(signature) from the validator to update the unfreezeFee
        setting in the Aergo bridge contract bridging to Ethereum

        """
        current_fee = query_unfreeze_fee(self.hera, self.aergo_bridge)
        if not self.auto_update:
            return Approval(error="Voting not enabled")
        # check destination nonce is correct
        nonce = int(self.hera.query_sc_state(
            self.aergo_bridge, ["_sv__nonce"]
        ).var_proofs[0].value)
        if nonce != new_fee_msg.destination_nonce:
            return Approval(error="Incorrect Nonce")
        config_data = self.load_config_data()
        new_fee = (config_data['networks'][self.aergo_net]['bridges']
                   [self.eth_net]['unfreeze_fee'])
        # check new tempo is different from current one to prevent
        # update spamming
        if current_fee == new_fee:
            return Approval(
                error="New fee is same as current one")
        # check tempo matches the one in config
        if new_fee != new_fee_msg.fee:
            return Approval(error="Refused to vote for this fee")
        # sign anchor and return approval
        msg = bytes(
            str(new_fee) + str(nonce) + self.aergo_id + "UF",
            'utf-8'
        )
        h = hashlib.sha256(msg).digest()
        sig = self.hera.account.private_key.sign_msg(h)
        approval = Approval(address=self.aergo_addr, sig=sig)
        print("{0}{1} Validator {2} signed a new unfreeze fee for Aergo,\n"
              "{0}with nonce {3}"
              .format("", "\U0001f4a7", self.validator_index,
                      new_fee_msg.destination_nonce))
        return approval


class ValidatorServer:
    def __init__(
        self,
        config_file_path: str,
        aergo_net: str,
        eth_net: str,
        privkey_name: str = None,
        privkey_pwd: str = None,
        validator_index: int = 0,
        auto_update: bool = False,
        root_path: str = './'
    ) -> None:
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        add_BridgeOperatorServicer_to_server(
            ValidatorService(
                config_file_path, aergo_net, eth_net, privkey_name,
                privkey_pwd, validator_index, auto_update, root_path
            ),
            self.server
        )
        with open(config_file_path, "r") as f:
            config_data = json.load(f)
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


def _serve_all(config_file_path, aergo_net, eth_net,
               privkey_name=None, privkey_pwd=None):
    """ For testing, run all validators in different threads """
    with open(config_file_path, "r") as f:
        config_data = json.load(f)
    validator_indexes = [i for i in range(len(config_data['validators']))]
    servers = [ValidatorServer(config_file_path, aergo_net, eth_net,
                               privkey_name, privkey_pwd, index, True)
               for index in validator_indexes]
    worker = partial(_serve_worker, servers)
    pool = Pool(len(validator_indexes))
    pool.map(worker, validator_indexes)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Start a validator on Ethereum and Aergo.')
    # Add arguments
    parser.add_argument(
        '-c', '--config_file_path', type=str, help='Path to config.json',
        required=True)
    parser.add_argument(
        '-a', '--aergo', type=str, help='Name of Aergo network in config file',
        required=True)
    parser.add_argument(
        '-e', '--eth', type=str, help='Name of Ethereum network in config file',
        required=True)
    parser.add_argument(
        '-i', '--validator_index', type=int, required=True,
        help='Index of the validator in the ordered list of validators')
    parser.add_argument(
        '--privkey_name', type=str, help='Name of account in config file '
        'to sign anchors', required=False)
    parser.add_argument(
        '--auto_update', dest='auto_update', action='store_true',
        help='Update bridge contract when settings change in config file')
    parser.add_argument(
        '--local_test', dest='local_test', action='store_true',
        help='Start all validators locally for convenient testing')
    parser.set_defaults(auto_update=False)
    parser.set_defaults(local_test=False)
    args = parser.parse_args()

    if args.local_test:
        _serve_all(args.config_file_path, args.aergo, args.eth,
                   privkey_name=args.privkey_name, privkey_pwd='1234')
    else:
        validator = ValidatorServer(
            args.config_file_path, args.aergo, args.eth,
            privkey_name=args.privkey_name,
            validator_index=args.validator_index,
            auto_update=args.auto_update
        )
        validator.run()
