from typing import (
    Optional,
)

import aergo.herapy as herapy
from web3 import (
    Web3,
)
from web3.middleware import (
    geth_poa_middleware,
)

from ethaergo_bridge_operator.op_utils import (
    query_aergo_tempo,
    query_aergo_validators,
    query_unfreeze_fee,
    load_config_data,
)


class SingleDataSource():
    """ Verify oracle data so that it can be trusted by signer """

    def __init__(
        self,
        config_file_path: str,
        aergo_net: str,
        eth_net: str,
        aergo_ip: str,
        eth_ip: str,
    ) -> None:
        self.config_file_path = config_file_path
        config_data = load_config_data(config_file_path)
        self.aergo_net = aergo_net
        self.eth_net = eth_net

        self.hera = herapy.Aergo()
        self.hera.connect(aergo_ip)

        self.web3 = Web3(Web3.HTTPProvider(eth_ip))
        eth_poa = config_data['networks'][eth_net]['isPOA']
        if eth_poa:
            self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        assert self.web3.isConnected()

        # remember bridge contracts
        bridge_abi_path = (config_data['networks'][eth_net]['bridges']
                           [aergo_net]['bridge_abi'])
        with open(bridge_abi_path, "r") as f:
            eth_abi = f.read()
        self.eth_bridge_addr = (config_data['networks'][eth_net]['bridges']
                                [aergo_net]['addr'])
        self.eth_bridge = self.web3.eth.contract(
            address=self.eth_bridge_addr,
            abi=eth_abi
        )
        self.aergo_bridge = (config_data['networks'][aergo_net]['bridges']
                             [eth_net]['addr'])

    def is_valid_aergo_anchor(
        self,
        anchor,
    ) -> Optional[str]:
        """ An anchor is valid if :
            1- it's height is finalized
            2- it's root for that height is correct.
            3- it's nonce is correct
            4- it's height is higher than previous anchored height + t_anchor
        """
        # 1- get the last block height and check anchor height > LIB
        # lib = best_height - finalized_from
        lib = self.hera.get_status().consensus_info.status['LibNo']
        if anchor.height > lib:
            return ("anchor height not finalized, got: {}, expected: {}"
                    .format(anchor.height, lib))

        # 2- get contract state root at origin_height
        # and check equals anchor root
        block = self.hera.get_block(block_height=int(anchor.height))
        contract = self.hera.get_account(address=self.aergo_bridge, proof=True,
                                         root=block.blocks_root_hash)
        root = contract.state_proof.state.storageRoot
        if root != anchor.root:
            return ("root doesn't match height {}, got: {}, expected: {}"
                    .format(lib, anchor.root.hex(), root.hex()))

        last_nonce_to = self.eth_bridge.functions._nonce().call()
        last_merged_height_from = \
            self.eth_bridge.functions._anchorHeight().call()

        # 3- check merkle bridge nonces are correct
        if last_nonce_to != anchor.destination_nonce:
            return ("anchor nonce invalid, got: {}, expected: {}"
                    .format(anchor.destination_nonce, last_nonce_to))

        # 4- check anchored height comes after the previous one and t_anchor is
        # passed
        t_anchor = self.eth_bridge.functions._tAnchor().call()
        if last_merged_height_from + t_anchor > anchor.height:
            return ("anchor height too soon, got: {}, expected: {}"
                    .format(anchor.height, last_merged_height_from + t_anchor))
        return None

    def is_valid_eth_anchor(
        self,
        anchor
    ) -> Optional[str]:
        """ An anchor is valid if :
            1- it's height is finalized
            2- it's root for that height is correct.
            3- it's nonce is correct
            4- it's height is higher than previous anchored height + t_anchor
        """
        t_anchor, t_final = query_aergo_tempo(self.hera, self.aergo_bridge)
        # 1- get the last block height and check anchor height > LIB
        # lib = best_height - finalized_from
        best_height = self.web3.eth.blockNumber
        lib = best_height - t_final
        if anchor.height > lib:
            return ("anchor height not finalized, got: {}, expected: {}"
                    .format(anchor.height, lib))

        # 2- get contract state root at origin_height
        # and check equals anchor root
        root = bytes(
            self.web3.eth.getProof(self.eth_bridge_addr, [], anchor.height)
            .storageHash
        )
        if root != anchor.root:
            return ("root doesn't match height {}, got: {}, expected: {}"
                    .format(lib, anchor.root.hex(), root.hex()))

        merge_info = self.hera.query_sc_state(
            self.aergo_bridge, ["_sv__nonce", "_sv__anchorHeight"]
        )
        last_nonce_to, last_merged_height_from = \
            [int(proof.value) for proof in merge_info.var_proofs]

        # 3- check merkle bridge nonces are correct
        if last_nonce_to != anchor.destination_nonce:
            return ("anchor nonce invalid, got: {}, expected: {}"
                    .format(anchor.destination_nonce, last_nonce_to))

        # 4- check anchored height comes after the previous one and t_anchor is
        # passed
        if last_merged_height_from + t_anchor > anchor.height:
            return ("anchor height too soon, got: {}, expected: {}"
                    .format(anchor.height, last_merged_height_from + t_anchor))
        return None

    def is_valid_eth_t_anchor(
        self,
        config_tempo,
        tempo_msg,
    ) -> Optional[str]:
        """ Check if the anchoring periode update requested matches the local
        validator setting.

        """
        current_tempo = int(self.hera.query_sc_state(
            self.aergo_bridge, ["_sv__tAnchor"]
        ).var_proofs[0].value)
        return self.is_valid_eth_tempo(
            config_tempo, tempo_msg, "t_anchor", current_tempo)

    def is_valid_eth_t_final(
        self,
        config_tempo,
        tempo_msg,
    ) -> Optional[str]:
        """ Check if the chain finality update requested matches the local
        validator setting.

        """
        current_tempo = int(self.hera.query_sc_state(
            self.aergo_bridge, ["_sv__tFinal"]
        ).var_proofs[0].value)
        return self.is_valid_eth_tempo(
            config_tempo, tempo_msg, "t_final", current_tempo)

    def is_valid_eth_tempo(
        self,
        config_tempo,
        tempo_msg,
        tempo_str,
        current_tempo
    ):
        # check destination nonce is correct
        nonce = int(self.hera.query_sc_state(
            self.aergo_bridge, ["_sv__nonce"]
        ).var_proofs[0].value)
        if nonce != tempo_msg.destination_nonce:
            return ("Incorrect Nonce, got: {}, expected: {}"
                    .format(tempo_msg.destination_nonce, nonce))
        # check new tempo is different from current one to prevent
        # update spamming
        if current_tempo == config_tempo:
            return "Not voting for a new {}".format(tempo_str)
        # check tempo matches the one in config
        if config_tempo != tempo_msg.tempo:
            return ("Invalid {}, got: {}, expected: {}"
                    .format(tempo_str, tempo_msg.tempo, config_tempo))
        return None

    def is_valid_aergo_t_anchor(
        self,
        config_tempo,
        tempo_msg,
    ) -> Optional[str]:
        """ Check if the anchoring periode update requested matches the local
        validator setting.

        """
        current_tempo = self.eth_bridge.functions._tAnchor().call()
        return self.is_valid_aergo_tempo(
            config_tempo, tempo_msg, 't_anchor', current_tempo)

    def is_valid_aergo_t_final(
        self,
        config_tempo,
        tempo_msg,
    ) -> Optional[str]:
        """ Check if the chain finality update requested matches the local
        validator setting.

        """
        current_tempo = self.eth_bridge.functions._tFinal().call()
        return self.is_valid_aergo_tempo(
            config_tempo, tempo_msg, 't_final', current_tempo)

    def is_valid_aergo_tempo(
        self,
        config_tempo,
        tempo_msg,
        tempo_str,
        current_tempo
    ):
        # check destination nonce is correct
        nonce = self.eth_bridge.functions._nonce().call()
        if nonce != tempo_msg.destination_nonce:
            return ("Incorrect Nonce, got: {}, expected: {}"
                    .format(tempo_msg.destination_nonce, nonce))
        # check new tempo is different from current one to prevent
        # update spamming
        if current_tempo == config_tempo:
            return "Not voting for a new {}".format(tempo_str)
        # check tempo matches the one in config
        if config_tempo != tempo_msg.tempo:
            return ("Invalid {}, got: {}, expected: {}"
                    .format(tempo_str, tempo_msg.tempo, config_tempo))
        return None

    def is_valid_eth_validators(self, config_vals, val_msg):
        """ Check if the Ethereum validator set update requested matches the local
        validator setting.

        """
        # check destination nonce is correct
        nonce = int(
            self.hera.query_sc_state(
                self.aergo_bridge, ["_sv__nonce"]).var_proofs[0].value
        )
        if nonce != val_msg.destination_nonce:
            return ("Incorrect Nonce, got: {}, expected: {}"
                    .format(val_msg.destination_nonce, nonce))
        # check new validators are different from current ones to prevent
        # update spamming
        current_validators = query_aergo_validators(self.hera,
                                                    self.aergo_bridge)
        if current_validators == config_vals:
            return "Not voting for a new validator set"
        # check validators are same in config file
        if config_vals != val_msg.validators:
            return "Invalid validator set"
        return None

    def is_valid_aergo_validators(self, config_vals, val_msg):
        """ Check if the Aergo validator set update requested matches the local
        validator setting.

        """
        # check destination nonce is correct
        nonce = self.eth_bridge.functions._nonce().call()
        if nonce != val_msg.destination_nonce:
            return ("Incorrect Nonce, got: {}, expected: {}"
                    .format(val_msg.destination_nonce, nonce))
        # check new validators are different from current ones to prevent
        # update spamming
        current_validators = self.eth_bridge.functions.getValidators().call()
        if current_validators == config_vals:
            return "Not voting for a new validator set"
        # check validators are same in config file
        if config_vals != val_msg.validators:
            return "Invalid validator set"
        return None

    def is_valid_unfreeze_fee(self, config_fee, new_fee_msg):
        """ Check if the unfreeze fee update requested matches the local
        validator setting.

        """
        current_fee = query_unfreeze_fee(self.hera, self.aergo_bridge)
        # check destination nonce is correct
        nonce = int(self.hera.query_sc_state(
            self.aergo_bridge, ["_sv__nonce"]
        ).var_proofs[0].value)
        if nonce != new_fee_msg.destination_nonce:
            return ("Incorrect Nonce, got: {}, expected: {}"
                    .format(new_fee_msg.destination_nonce, nonce))
        # check new tempo is different from current one to prevent
        # update spamming
        if current_fee == config_fee:
            return "Not voting for a new unfreeze fee"
        # check tempo matches the one in config
        if config_fee != new_fee_msg.fee:
            return ("Invalid unfreeze fee, got: {}, expected: {}"
                    .format(new_fee_msg.fee, config_fee))
