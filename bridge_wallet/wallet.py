from typing import (
    Dict
)

from bridge_wallet.wallet_config import (
    WalletConfig,
)


class BridgeWallet(WalletConfig):
    """EthAergoWallet transfers tokens on the Eth<->Aergo Bridge """

    def __init__(
        self,
        config_file_path: str,
        config_data: Dict = None,
    ) -> None:
        WalletConfig.__init__(self, config_file_path, config_data)
        self.gas_price = 0
        self.fee_price = 20  # gWei

    def eth_to_aergo_sidechain(
        self,
        from_chain: str,
        to_chain: str,
        asset_name: str,
        amount: int,
        aergo_receiver: str,
        aergo_privkey_name: str = 'default',
        aergo_privkey_pwd: str = None,
        eth_privkey_name: str = 'default',
        eth_privkey_pwd: str = None,
    ) -> None:
        """ Transfer a native ERC20 or ether to Aergo"""
        pass

    def aergo_to_eth_sidechain(
        self,
        from_chain: str,
        to_chain: str,
        asset_name: str,
        amount: int,
        aergo_receiver: str,
        aergo_privkey_name: str = 'default',
        aergo_privkey_pwd: str = None,
        eth_privkey_name: str = 'default',
        eth_privkey_pwd: str = None,
    ) -> None:
        """ Transfer a native Aergo Standard Token or Aer to Ethereum"""
        pass

    ###########################################################################
    # eth_to_aergo_sidechain
    # AergoERC20  -> lock_to_aergo -> | ->    unfreeze     -> Aer
    # MintedERC20 -> burn_to_aergo -> | -> unlock_to_aergo -> StandardToken
    # Eth/ERC20   -> lock_to_aergo -> | ->  mint_to_aergo  -> MintedStdToken
    ###########################################################################

    def lock_to_aergo(self):
        """ Initiate ERC20 token or Ether transfer to Aergo sidechain """
        pass

    def burn_to_aergo(self):
        """ Initiate minted Standard token transfer back to aergo origin"""
        pass

    def mint_to_aergo(self):
        """ Finalize ERC20 token or Ether transfer to Aergo sidechain """
        pass

    def unfreeze(self):
        """ Finalize ERC20Aergo transfer to Aergo Mainnet by unfreezing
            (aers are already minted and freezed in the bridge contract)
        """
        pass

    def unlock_to_aergo(self):
        """ Finalize Aergo Standard token transfer back to Aergo Origin"""
        pass

    ###########################################################################
    # aergo_to_eth_sidechain
    # Aer            ->    freeze   -> | -> unlock_to_eth -> Aer
    # MintedStdToken -> burn_to_eth -> | -> unlock_to_eth -> Eth/ERC20
    # StandardToken  -> lock_to_eth -> | ->  mint_to_eth  -> MintedERC20
    ###########################################################################

    def freeze(self):
        """ Initiate Aer transfer back to Ethereum AergoERC20 sidechain"""
        pass

    def burn_to_eth(self):
        """ Initiate minted token transfer back to ethereum origin"""
        pass

    def lock_to_eth(self):
        """ Initiate Aergo Standard Token transfer to Ethereum sidechain"""
        pass

    def mint_to_eth(self):
        """ Finalize Aergo Standard Token transfer to Ethereum sidechain """
        pass

    def unlock_to_eth(self):
        """ Finalize ERC20 or Eth transfer back to Ethereum origin """
        pass
