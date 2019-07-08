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
    proposer = ProposerClient(
        "./test_config.json", 'aergo-local', 'eth-poa-local', 3,
        privkey_pwd='1234', auto_update=True
    )
    proposer.run()
