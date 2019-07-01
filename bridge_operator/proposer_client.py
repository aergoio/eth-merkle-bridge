import json
import time

from typing import (
    Dict
)

from bridge_operator.eth_proposer_client import (
    EthProposerClient
)
from bridge_operator.aergo_proposer_client import (
    AergoProposerClient
)


class ProposerClient:
    """ The ProposerClient starts Aergo and Ethereum proposers
    """

    def __init__(
        self,
        config_data: Dict,
        aergo_net: str,
        eth_net: str,
        eth_block_time: int,
        privkey_name: str = None,
        privkey_pwd: str = None,
    ) -> None:
        self.t_eth_client = EthProposerClient(
            config_data, aergo_net, eth_net, privkey_name,
            privkey_pwd
        )
        self.t_aergo_client = AergoProposerClient(
            config_data, aergo_net, eth_net, eth_block_time, privkey_name,
            privkey_pwd, "\t"*5
        )

    def run(self):
        self.t_eth_client.start()
        self.t_aergo_client.start()


if __name__ == '__main__':
    with open("./test_config.json", "r") as f:
        config_data = json.load(f)
    proposer = ProposerClient(
        config_data, 'aergo-local', 'eth-poa-local', 3,
        privkey_pwd='1234'
    )
    proposer.run()
