from typing import (
    Optional,
    List
)

from ethaergo_bridge_operator.op_utils import (
    load_config_data,
)
from ethaergo_bridge_operator.validator.single_data_source import (
    SingleDataSource
)


class DataSources():
    """ Queries validator apis for each pair of providers.
    This gives extra security in case a node is compromised.

    """
    def __init__(
        self,
        config_file_path: str,
        aergo_net: str,
        eth_net: str,
        root_path: str,
    ) -> None:
        self.config_file_path = config_file_path
        config_data = load_config_data(self.config_file_path)
        self.aergo_net = aergo_net
        self.eth_net = eth_net
        self.data_sources: List[SingleDataSource] = []
        aergo_providers = config_data['networks'][aergo_net]['providers']
        eth_providers = config_data['networks'][eth_net]['providers']
        for i, aergo_ip in enumerate(aergo_providers):
            eth_ip = eth_providers[i]
            self.data_sources.append(
                SingleDataSource(
                    config_file_path, aergo_net, eth_net, aergo_ip, eth_ip,
                    root_path
                )
            )

    def is_valid_aergo_anchor(
        self,
        anchor,
    ) -> Optional[str]:
        for ds in self.data_sources:
            err_msg = ds.is_valid_aergo_anchor(anchor)
            if err_msg is not None:
                return err_msg
        return None

    def is_valid_eth_anchor(
        self,
        anchor
    ) -> Optional[str]:
        for ds in self.data_sources:
            err_msg = ds.is_valid_eth_anchor(anchor)
            if err_msg is not None:
                return err_msg
        return None

    def is_valid_eth_t_anchor(
        self,
        tempo_msg,
    ) -> Optional[str]:
        config_data = load_config_data(self.config_file_path)
        config_tempo = (config_data['networks'][self.aergo_net]['bridges']
                        [self.eth_net]["t_anchor"])
        for ds in self.data_sources:
            err_msg = ds.is_valid_eth_t_anchor(config_tempo, tempo_msg)
            if err_msg is not None:
                return err_msg
        return None

    def is_valid_eth_t_final(
        self,
        tempo_msg,
    ) -> Optional[str]:
        config_data = load_config_data(self.config_file_path)
        config_tempo = (config_data['networks'][self.aergo_net]['bridges']
                        [self.eth_net]["t_final"])
        for ds in self.data_sources:
            err_msg = ds.is_valid_eth_t_final(config_tempo, tempo_msg)
            if err_msg is not None:
                return err_msg
        return None

    def is_valid_aergo_t_anchor(
        self,
        tempo_msg,
    ) -> Optional[str]:
        config_data = load_config_data(self.config_file_path)
        config_tempo = (config_data['networks'][self.eth_net]['bridges']
                        [self.aergo_net]["t_anchor"])
        for ds in self.data_sources:
            err_msg = ds.is_valid_aergo_t_anchor(config_tempo, tempo_msg)
            if err_msg is not None:
                return err_msg
        return None

    def is_valid_aergo_t_final(
        self,
        tempo_msg,
    ) -> Optional[str]:
        config_data = load_config_data(self.config_file_path)
        config_tempo = (config_data['networks'][self.eth_net]['bridges']
                        [self.aergo_net]["t_final"])
        for ds in self.data_sources:
            err_msg = ds.is_valid_aergo_t_final(config_tempo, tempo_msg)
            if err_msg is not None:
                return err_msg
        return None

    def is_valid_eth_validators(self, val_msg):
        config_data = load_config_data(self.config_file_path)
        config_vals = [val['addr'] for val in config_data['validators']]
        for ds in self.data_sources:
            err_msg = ds.is_valid_eth_validators(config_vals, val_msg)
            if err_msg is not None:
                return err_msg
        return None

    def is_valid_aergo_validators(self, val_msg):
        config_data = load_config_data(self.config_file_path)
        config_vals = [val['eth-addr'] for val in config_data['validators']]
        for ds in self.data_sources:
            err_msg = ds.is_valid_aergo_validators(config_vals, val_msg)
            if err_msg is not None:
                return err_msg
        return None

    def is_valid_unfreeze_fee(self, new_fee_msg):
        config_data = load_config_data(self.config_file_path)
        config_fee = (config_data['networks'][self.aergo_net]['bridges']
                      [self.eth_net]['unfreeze_fee'])
        for ds in self.data_sources:
            err_msg = ds.is_valid_unfreeze_fee(config_fee, new_fee_msg)
            if err_msg is not None:
                return err_msg
        return None

    def is_valid_aergo_oracle(self, oracle_msg):
        config_data = load_config_data(self.config_file_path)
        config_oracle = (config_data['networks'][self.eth_net]['bridges']
                         [self.aergo_net]['oracle'])
        for ds in self.data_sources:
            err_msg = ds.is_valid_aergo_oracle(config_oracle, oracle_msg)
            if err_msg is not None:
                return err_msg
        return None

    def is_valid_eth_oracle(self, oracle_msg):
        config_data = load_config_data(self.config_file_path)
        config_oracle = (config_data['networks'][self.aergo_net]['bridges']
                         [self.eth_net]['oracle'])
        for ds in self.data_sources:
            err_msg = ds.is_valid_eth_oracle(config_oracle, oracle_msg)
            if err_msg is not None:
                return err_msg
        return None
