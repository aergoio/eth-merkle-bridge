import argparse

from ethaergo_bridge_operator.proposer.eth.client import (
    EthProposerClient
)
from ethaergo_bridge_operator.proposer.aergo.client import (
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
        anchoring_on: bool = False,
        auto_update: bool = False,
        oracle_update: bool = False,
        bridge_anchoring: bool = True,
        root_path: str = './',
        eco: bool = False,
        eth_eco: bool = False,
    ) -> None:
        self.t_eth_client = EthProposerClient(
            config_file_path, aergo_net, eth_net, privkey_name,
            privkey_pwd, anchoring_on, auto_update, oracle_update,
            root_path, eth_gas_price, bridge_anchoring, eco or eth_eco
        )
        self.t_aergo_client = AergoProposerClient(
            config_file_path, aergo_net, eth_net, eth_block_time, privkey_name,
            privkey_pwd, anchoring_on, auto_update, oracle_update,
            aergo_gas_price, bridge_anchoring, root_path, eco
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
        required=True
    )
    parser.add_argument(
        '-a', '--aergo', type=str, help='Name of Aergo network in config file',
        required=True
    )
    parser.add_argument(
        '-e', '--eth', type=str,
        help='Name of Ethereum network in config file', required=True
    )
    parser.add_argument(
        '--eth_block_time', type=int, help='Average Ethereum block time',
        required=True
    )
    parser.add_argument(
        '--privkey_name', type=str, help='Name of account in config file '
        'to sign anchors', required=False
    )
    parser.add_argument(
        '--privkey_pwd', type=str, help='Password to decrypt privkey_name'
        '(Eth and Aergo Keys need the same password)', required=False
    )
    parser.add_argument(
        '--anchoring_on', dest='anchoring_on', action='store_true',
        help='Enable anchoring (can be diseabled when wanting to only update '
             'settings)'
    )
    parser.add_argument(
        '--auto_update', dest='auto_update', action='store_true',
        help='Update bridge contract when settings change in config file'
    )
    parser.add_argument(
        '--oracle_update', dest='oracle_update', action='store_true',
        help='Update bridge contract when validators or oracle addr '
             'change in config file'
    )
    parser.add_argument(
        '--eth_gas_price', type=int,
        help='Gas price (gWei) to use in transactions', required=False
    )
    parser.add_argument(
        '--aergo_gas_price', type=int,
        help='Gas price to use in transactions', required=False
    )
    parser.add_argument(
        '--eco', dest='eco', action='store_true',
        help="In eco mode, anchoring will be skipped when lock/burn/freeze "
        "events don't happen in the bridge contracts"
    )
    parser.add_argument(
        '--eth_eco', dest='eth_eco', action='store_true',
        help="In eco mode, anchoring on Ethereum will be skipped when "
        "lock/burn/freeze events don't happen in the bridge contracts on Aergo"
    )

    args = parser.parse_args()

    proposer = ProposerClient(
        args.config_file_path, args.aergo, args.eth, args.eth_block_time,
        args.aergo_gas_price, args.eth_gas_price,
        privkey_name=args.privkey_name,
        privkey_pwd=args.privkey_pwd,
        anchoring_on=args.anchoring_on,
        auto_update=args.auto_update,
        oracle_update=args.oracle_update,
        eco=args.eco,
        eth_eco=args.eth_eco
    )
    proposer.run()
