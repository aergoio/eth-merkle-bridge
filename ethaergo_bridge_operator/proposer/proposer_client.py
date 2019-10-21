import argparse

from ethaergo_bridge_operator.proposer.eth_proposer_client import (
    EthProposerClient
)
from ethaergo_bridge_operator.proposer.aergo_proposer_client import (
    AergoProposerClient
)


class ProposerClient:
    """ The ProposerClient starts Aergo and Ethereum proposers
    """

    def __init__(
        self,
        config_file_path: str,
        aergo_net: str,
        eth_net: str,
        eth_block_time: int,
        aergo_gas_price: int,
        eth_gas_price: int,
        privkey_name: str = None,
        privkey_pwd: str = None,
        auto_update: bool = False,
        root_path: str = './'
    ) -> None:
        self.t_eth_client = EthProposerClient(
            config_file_path, aergo_net, eth_net, privkey_name,
            privkey_pwd, "", auto_update, root_path, eth_gas_price
        )
        self.t_aergo_client = AergoProposerClient(
            config_file_path, aergo_net, eth_net, eth_block_time, privkey_name,
            privkey_pwd, "\t"*5, auto_update, aergo_gas_price
        )

    def run(self):
        self.t_eth_client.start()
        self.t_aergo_client.start()


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
        '-e', '--eth', type=str, help='Name of Ethereum network in config file',
        required=True)
    parser.add_argument(
        '--eth_block_time', type=int, help='Average Ethereum block time',
        required=True)
    parser.add_argument(
        '--privkey_name', type=str, help='Name of account in config file '
        'to sign anchors', required=False)
    parser.add_argument(
        '--auto_update', dest='auto_update', action='store_true',
        help='Update bridge contract when settings change in config file')
    parser.add_argument(
        '--local_test', dest='local_test', action='store_true',
        help='Start proposer with password for testing')
    parser.add_argument(
        '--eth_gas_price', type=int,
        help='Gas price (gWei) to use in transactions', required=False)
    parser.add_argument(
        '--aergo_gas_price', type=int,
        help='Gas price to use in transactions', required=False)
    parser.set_defaults(auto_update=False)
    parser.set_defaults(local_test=False)
    parser.set_defaults(eth_gas_price=None)
    parser.set_defaults(aergo_gas_price=None)
    args = parser.parse_args()

    if args.local_test:
        proposer = ProposerClient(
            args.config_file_path, args.aergo, args.eth, args.eth_block_time,
            args.aergo_gas_price, args.eth_gas_price,
            privkey_name=args.privkey_name, privkey_pwd='1234',
            auto_update=args.auto_update
        )
        proposer.run()
    else:
        proposer = ProposerClient(
            args.config_file_path, args.aergo, args.eth, args.eth_block_time,
            args.aergo_gas_price, args.eth_gas_price,
            privkey_name=args.privkey_name, auto_update=args.auto_update
        )
        proposer.run()
