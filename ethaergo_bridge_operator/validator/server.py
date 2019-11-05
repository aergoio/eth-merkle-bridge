import argparse
from concurrent import (
    futures,
)
from functools import (
    partial,
)
import grpc
import json
from multiprocessing.dummy import (
    Pool,
)
import time


from ethaergo_bridge_operator.bridge_operator_pb2_grpc import (
    add_BridgeOperatorServicer_to_server,
)
from ethaergo_bridge_operator.validator.validator_service import (
    ValidatorService,
)
import logging

logger = logging.getLogger(__name__)

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


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
        oracle_update: bool = False,
        root_path: str = './'
    ) -> None:
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        add_BridgeOperatorServicer_to_server(
            ValidatorService(
                config_file_path, aergo_net, eth_net, privkey_name,
                privkey_pwd, validator_index, auto_update, oracle_update,
                root_path
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
        logger.info("\"server %s started\"", self.validator_index)
        try:
            while True:
                time.sleep(_ONE_DAY_IN_SECONDS)
        except KeyboardInterrupt:
            logger.info("Shutting down validator")
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
                               privkey_name, privkey_pwd, index, True, True)
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
