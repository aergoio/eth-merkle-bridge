import json

from typing import (
    Union,
    List,
    Dict,
)


class WalletConfig():
    def __init__(
        self,
        config_file_path: str,
        config_data: Dict = None,
    ) -> None:
        if config_data is None:
            with open(config_file_path, "r") as f:
                config_data = json.load(f)
        self._config_data = config_data
        self._config_path = config_file_path

    def config_data(
        self,
        *json_path: Union[str, int],
        value: Union[str, int, List, Dict] = None
    ):
        """ Get the value in nested dictionary at the end of
        json path if value is None, or set value at the end of
        the path.
        """
        config_dict = self._config_data
        for key in json_path[:-1]:
            config_dict = config_dict[key]
        if value is not None:
            config_dict[json_path[-1]] = value
        return config_dict[json_path[-1]]

    def save_config(self, path: str = None) -> None:
        if path is None:
            path = self._config_path
        with open(path, "w") as f:
            json.dump(self._config_data, f, indent=4, sort_keys=True)

    def get_wallet_address(
        self,
        wallet_name: str,
        account_name: str = 'default',
    ) -> str:
        addr = self.config_data('wallet-eth', account_name, 'addr')
        return addr

    def get_asset_address(
        self,
        asset_name: str,
        network_name: str,
        asset_origin_chain: str = None
    ) -> str:
        """ Get the address of a time in config_data given it's name"""
        if asset_origin_chain is None:
            # query a token issued on network_name
            asset_addr = self.config_data(network_name, 'tokens',
                                          asset_name, 'addr')
        else:
            # query a pegged token (from asset_origin_chain) balance
            # on network_name sidechain (token or aer)
            asset_addr = self.config_data(asset_origin_chain, 'tokens',
                                          asset_name, 'pegs',
                                          network_name)
        return asset_addr
