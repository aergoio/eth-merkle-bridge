from typing import (
    List,
    Dict,
    Tuple,
)

from bridge_wallet.wallet_config import (
    WalletConfig,
)


class EthWallet(WalletConfig):
    """EthWallet contains standard Ethereum wallet functionality
    (eth transfer, contract call/queries, balance queries)
    """

    def __init__(
        self,
        config_file_path: str,
        config_data: Dict = None,
    ) -> None:
        WalletConfig.__init__(self, config_file_path, config_data)
        self.gas_price = 0

    def get_web3(
        self,
        network_name: str,
        privkey_name: str = 'default',
        privkey_pwd: str = None,
    ):
        """ Get a web3 provider to connect to Ethereum network """
        pass

    def get_balance(
        self,
        asset_name: str,
        network_name: str,
        asset_origin_chain: str = None,
        account_name: str = 'default',
        account_addr: str = None
    ) -> Tuple[int, str]:
        """ Get account name balance of asset_name on network_name,
        and specify asset_origin_chain for a pegged asset query,
        """
        pass

    def transfer(
        self,
        value: int,
        to: str,
        asset_name: str,
        network_name: str,
        gas_limit: int,
        asset_origin_chain: str = None,
        privkey_name: str = 'default',
        privkey_pwd: str = None,
    ) -> str:
        """ Transfer aer or tokens on network_name and specify
        asset_origin_chain for transfers of pegged assets.
        """
        pass

    def write_contract(
        self,
        value: int,
        function: str,
        address: str,
        abi: str,
        arguments: List[str],
        gas_limit: int,
        privkey_name: str = 'default',
        privkey_pwd: str = None,
    ) -> str:
        """ Send a transaction calling a contract function"""
        pass

    def deploy_contract(
        self,
        bytecode: str,
        abi: str,
        gas_limit: int,
        privkey_name: str = 'default',
        privkey_pwd: str = None,
    ) -> str:
        """ Deploy a new contract """
        pass
