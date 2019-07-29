import argparse

from ethaergo_bridge_operator.eth_proposer_client import (
    EthProposerClient
)
from ethaergo_bridge_operator.aergo_proposer_client import (
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
        privkey_name: str = None,
        privkey_pwd: str = None,
        auto_update: bool = False
    ) -> None:
        self.t_eth_client = EthProposerClient(
            config_file_path, aergo_net, eth_net, privkey_name,
            privkey_pwd, "", auto_update
        )
        self.t_aergo_client = AergoProposerClient(
            config_file_path, aergo_net, eth_net, eth_block_time, privkey_name,
            privkey_pwd, "\t"*5, auto_update
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
    parser.set_defaults(auto_update=False)
    args = parser.parse_args()

    proposer = ProposerClient(
        args.config_file_path, args.aergo, args.eth, args.eth_block_time,
        privkey_name=args.privkey_name, auto_update=args.auto_update
    )
    proposer.run()
