import argparse
from concurrent import (
    futures,
)
from getpass import getpass
import grpc
import json
import logging
import os
import time

from typing import (
    Dict,
)

import aergo.herapy as herapy
from ethaergo_wallet.wallet_utils import (
    is_aergo_address,
)
from ethaergo_wallet.eth_utils.merkle_proof import (
    format_proof_for_lua
)
from web3 import (
    Web3,
)
from web3.middleware import (
    geth_poa_middleware,
)
from eth_utils import (
    keccak,
)

from unfreeze_service.unfreeze_service_pb2_grpc import (
    UnfreezeServiceServicer,
    add_UnfreezeServiceServicer_to_server,
)
from unfreeze_service.unfreeze_service_pb2 import (
    Status,
)
from ethaergo_wallet.eth_to_aergo import (
    _build_deposit_proof,
    withdrawable,
)

_ONE_DAY_IN_SECONDS = 60 * 60 * 24

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

file_formatter = logging.Formatter(
    '{"level": "%(levelname)s", "time": "%(asctime)s", '
    '"service": "%(funcName)s", "message": %(message)s'
)
stream_formatter = logging.Formatter('%(message)s')


log_file_path = 'logs/unfreeze.log'
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
file_handler = logging.FileHandler(log_file_path)
file_handler.setFormatter(file_formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(stream_formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)


class UnfreezeService(UnfreezeServiceServicer):
    """Unfreezes freezed native aergo for users"""

    def __init__(
        self,
        ip_port: str,
        config_file_path: str,
        aergo_net: str,
        eth_net: str,
        privkey_name: str,
        privkey_pwd: str = None,
        root_path: str = './'
    ) -> None:
        """
            UnfreezeService unfreezes native aergo for users that have
            initiated a transfer by locking aergo erc20 but don't already have
            aergo native to pay for the fee.
        """
        self.config_file_path = config_file_path
        self.aergo_net = aergo_net
        self.eth_net = eth_net
        config_data = self.load_config_data()
        self.bridge_eth = \
            config_data['networks'][eth_net]['bridges'][aergo_net]['addr']
        self.bridge_aergo = \
            config_data['networks'][aergo_net]['bridges'][eth_net]['addr']
        aergo_erc20 = \
            config_data['networks'][eth_net]['tokens']['aergo_erc20']['addr']
        self.aergo_erc20_bytes = bytes.fromhex(aergo_erc20[2:])
        logger.info("\"Ethereum bridge contract: %s\"", self.bridge_eth)
        logger.info("\"Aergo bridge contract: %s\"", self.bridge_aergo)
        logger.info("\"Aergo ERC20: %s\"", aergo_erc20)

        # connect aergo provider
        self.hera = herapy.Aergo()
        aergo_ip = config_data['networks'][aergo_net]['ip']
        self.hera.connect(aergo_ip)

        # connect eth provider
        eth_ip = config_data['networks'][eth_net]['ip']
        self.web3 = Web3(Web3.HTTPProvider(eth_ip))
        eth_poa = config_data['networks'][eth_net]['isPOA']
        if eth_poa:
            self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        assert self.web3.isConnected()

        # load signer
        if privkey_pwd is None:
            privkey_pwd = getpass("Decrypt exported private key '{}'\n"
                                  "Password: ".format(privkey_name))
        keystore_path = \
            config_data['wallet'][privkey_name]['keystore']
        with open(root_path + keystore_path, "r") as f:
            keystore = f.read()
        self.hera.import_account_from_keystore(keystore, privkey_pwd)
        self.address = str(self.hera.account.address)
        logger.info("\"Unfreezer Address: %s\"", self.address)

        # query unfreeze fee
        unfreeze_fee_q = self.hera.query_sc_state(
            self.bridge_aergo, ["_sv__unfreezeFee"])
        self.unfreeze_fee = int(
            json.loads(unfreeze_fee_q.var_proofs[0].value)['_bignum'])
        logger.info(
            "\"Unfreeze fee for broadcaster: %saer\"", self.unfreeze_fee)

    def RequestUnfreeze(self, account_ref, context):
        """
            Create and broadcast unfreeze transactions if conditions are met:
            - the receiver is a valid aergo address
            - the unfreezable amount covers the unfreeze fee
        """
        if not is_aergo_address(account_ref.receiver):
            logger.warning(
                "\"Invalid receiver address %s\"", account_ref.receiver)
            return Status(error="Receiver must be an Aergo address")

        # format account references for Locks and Unfreezes
        account_ref_eth = \
            account_ref.receiver.encode('utf-8') + self.aergo_erc20_bytes
        position = b'\x05'  # Locks
        eth_trie_key = keccak(account_ref_eth + position.rjust(32, b'\0'))
        aergo_storage_key = \
            ('_sv__unfreezes-' + account_ref.receiver).encode('utf-8') \
            + self.aergo_erc20_bytes
        # check unfreezeable is larger that the fee
        unfreezeable, _ = withdrawable(
            self.bridge_eth, self.bridge_aergo, self.web3, self.hera,
            eth_trie_key, aergo_storage_key
        )
        if unfreezeable <= self.unfreeze_fee:
            logger.warning(
                "\"Unfreezable (%s aer) doesn't cover fee for: %s\"",
                unfreezeable, account_ref.receiver
            )
            return Status(
                error="Aergo native to unfreeze doesnt cover the fee")

        # build lock proof and arguments for unfreeze
        lock_proof = _build_deposit_proof(
            self.web3, self.hera, self.bridge_eth, self.bridge_aergo,
            0, eth_trie_key
        )
        ap = format_proof_for_lua(lock_proof.storageProof[0].proof)
        balance = int.from_bytes(lock_proof.storageProof[0].value, "big")
        ubig_balance = {'_bignum': str(balance)}

        # call unfreeze tx
        tx, result = self.hera.call_sc(
            self.bridge_aergo, "unfreeze",
            args=[account_ref.receiver, ubig_balance, ap]
        )
        if result.status != herapy.CommitStatus.TX_OK:
            logger.warning("\"Error: tx failed: %s\"", result.json())
            return Status(
                error="Unfreeze service error: tx failed")

        # all went well
        logger.info("\"Unfreeze success for: %s\"", account_ref.receiver)

        # Test unfreeze fee used
        # result = self.hera.wait_tx_result(tx.tx_hash)
        # logger.info("\"\u26fd Unfreeze tx fee paid: %s\"", result.fee_used)

        return Status(txHash=str(tx.tx_hash))

    def load_config_data(self) -> Dict:
        with open(self.config_file_path, "r") as f:
            config_data = json.load(f)
        return config_data


class UnfreezeServer:
    def __init__(
        self,
        ip_port: str,
        config_file_path: str,
        aergo_net: str,
        eth_net: str,
        privkey_name: str,
        privkey_pwd: str = None,
        root_path: str = './'
    ) -> None:
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        add_UnfreezeServiceServicer_to_server(
            UnfreezeService(
                ip_port, config_file_path, aergo_net, eth_net, privkey_name,
                privkey_pwd, root_path
            ),
            self.server
        )
        self.server.add_insecure_port(ip_port)

    def run(self):
        self.server.start()
        logger.info("\"Unfreeze server started\"")
        try:
            while True:
                time.sleep(_ONE_DAY_IN_SECONDS)
        except KeyboardInterrupt:
            logger.info("\"Shutting down unfreeze server\"")
            self.shutdown()

    def shutdown(self):
        self.server.stop(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Aergo native unfreeze service')
    # Add arguments
    parser.add_argument(
        '-ip', '--ip_port', type=str, required=True,
        help='ip and port to run unfreeze service')
    parser.add_argument(
        '-c', '--config_file_path', type=str, help='Path to config.json',
        required=True)
    parser.add_argument(
        '-a', '--aergo', type=str, help='Name of Aergo network in config file',
        required=True)
    parser.add_argument(
        '-e', '--eth', type=str, required=True,
        help='Name of Ethereum network in config file',
    )
    parser.add_argument(
        '--privkey_name', type=str, help='Name of account in config file '
        'to sign anchors', required=True)
    parser.add_argument(
        '--local_test', dest='local_test', action='store_true',
        help='Start service for running tests')
    parser.set_defaults(local_test=False)
    args = parser.parse_args()

    if args.local_test:
        validator = UnfreezeServer(
            args.ip_port, args.config_file_path, args.aergo, args.eth,
            privkey_name=args.privkey_name, privkey_pwd='1234'
        )
        validator.run()
    else:
        validator = UnfreezeServer(
            args.ip_port, args.config_file_path, args.aergo, args.eth,
            privkey_name=args.privkey_name,
        )
        validator.run()
