from getpass import getpass
from typing import (
    Dict,
    Tuple
)
from wallet.exceptions import (
    InsufficientBalanceError,
    InvalidArgumentsError,
)
from wallet.wallet_utils import (
    get_balance as get_aergo_balance,
    get_signed_transfer,
)
from wallet.transfer_to_sidechain import (
    lock,
)

from ethaergo_wallet.wallet_config import (
    WalletConfig,
)
from ethaergo_wallet.eth_utils.wallet_utils import (
    get_balance as get_eth_balance
)
from ethaergo_wallet.aergo_to_eth import (
    build_lock_proof,
    mint
)
import aergo.herapy as herapy
from aergo.herapy.errors.general_exception import (
    GeneralException,
)
from web3 import (
    Web3,
)
from web3.middleware import (
    geth_poa_middleware,
)


class EthAergoWallet(WalletConfig):
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

    def lock_to_eth(
        self,
        from_chain: str,
        to_chain: str,
        asset_name: str,
        amount: int,
        receiver: str,
        privkey_name: str = 'default',
        privkey_pwd: str = None
    ) -> Tuple[int, str]:
        """ Initiate Aergo Standard Token transfer to Ethereum sidechain"""
        aergo_from = self.get_aergo(from_chain, privkey_name, privkey_pwd)
        sender = str(aergo_from.account.address)
        bridge_from = self.config_data(from_chain, 'bridges', to_chain, 'addr')
        asset_address = self.config_data(from_chain, 'tokens',
                                         asset_name, 'addr')
        # sign transfer so bridge can pull tokens to lock.
        fee_limit = 0
        signed_transfer, balance = \
            get_signed_transfer(amount, bridge_from, asset_address,
                                aergo_from)
        signed_transfer = signed_transfer[:2]  # only nonce, sig are needed
        if balance < amount:
            raise InsufficientBalanceError("not enough token balance")
        aer_balance = get_aergo_balance(sender, 'aergo', aergo_from)
        if aer_balance < fee_limit*self.fee_price:
            err = "not enough aer balance to pay tx fee"
            raise InsufficientBalanceError(err)

        print("{} balance on origin before transfer: {}"
              .format(asset_name, balance/10**18))

        print("\n\n------ Lock {} -----------".format(asset_name))
        lock_height, tx_hash = lock(aergo_from, bridge_from,
                                    receiver[2:], amount, asset_address, fee_limit,
                                    self.fee_price, signed_transfer)

        # remaining balance on origin : aer or asset
        balance = get_aergo_balance(sender, asset_address, aergo_from)
        print("remaining {} balance on origin after transfer: {}"
              .format(asset_name, balance/10**18))

        aergo_from.disconnect()
        return lock_height, tx_hash

    def mint_to_eth(
        self,
        from_chain: str,
        to_chain: str,
        bridge_to_abi: str,
        asset_name: str,
        minted_erc20_abi: str,
        receiver: str = None,
        lock_height: int = 0,
        privkey_name: str = 'default',
        privkey_pwd: str = None,
        eth_poa: bool = False
    ) -> Tuple[str, str]:
        """ Finalize Aergo Standard Token transfer to Ethereum sidechain
        NOTE anybody can mint so sender is not necessary.
        The amount to mint is the difference between total deposit and
        already minted amount.
        Bridge tempo is taken from config_data
        """
        aergo_from = self._connect_aergo(from_chain)
        # get ethereum tx signer
        w3 = self.get_web3(to_chain, eth_poa)
        sender_keystore = self.config_data('wallet-eth', privkey_name,
                                           'keystore')
        with open("./keystore/" + sender_keystore, "r") as f:
            encrypted_key = f.read()
        if privkey_pwd is None:
            privkey_pwd = getpass("Decrypt Ethereum keystore '{}'\nPassword: "
                                  .format(privkey_name))
        privkey = w3.eth.account.decrypt(encrypted_key, privkey_pwd)
        signer_acct = w3.eth.account.privateKeyToAccount(privkey)
        tx_sender = signer_acct.address

        if receiver is None:
            receiver = tx_sender

        bridge_from = self.config_data(from_chain, 'bridges', to_chain, 'addr')
        bridge_to = self.config_data(to_chain, 'bridges', from_chain, 'addr')
        asset_address = self.config_data(from_chain, 'tokens',
                                         asset_name, 'addr')
        save_pegged_token_address = False
        try:
            token_pegged = self.config_data(from_chain, 'tokens', asset_name,
                                            'pegs', to_chain)
            balance = get_eth_balance(receiver, token_pegged, w3,
                                      minted_erc20_abi)
            print("{} balance on destination before transfer : {}"
                  .format(asset_name, balance/10**18))
        except KeyError:
            print("Pegged token unknow by wallet")
            save_pegged_token_address = True

        fee_limit = 0
        eth_balance = get_eth_balance(tx_sender, 'ether', w3)
        if eth_balance < fee_limit*self.fee_price:
            err = "not enough aer balance to pay tx fee"
            raise InsufficientBalanceError(err)

        print("\n------ Get lock proof -----------")
        lock_proof = build_lock_proof(aergo_from, w3, receiver,
                                      bridge_from, bridge_to, bridge_to_abi,
                                      lock_height, asset_address)
        print("\n\n------ Mint {} on destination blockchain -----------"
              .format(asset_name))
        token_pegged, tx_hash = mint(
            w3, signer_acct, receiver, lock_proof, asset_address, bridge_to,
            bridge_to_abi, fee_limit, self.fee_price
        )

        # new balance on sidechain
        balance = get_eth_balance(receiver, token_pegged, w3, minted_erc20_abi)
        print("{} balance on destination after transfer : {}"
              .format(asset_name, balance/10**18))

        aergo_from.disconnect()

        # record mint address in file
        if save_pegged_token_address:
            print("\n------ Store mint address in config.json -----------")
            self.config_data(from_chain, 'tokens', asset_name, 'pegs',
                             to_chain, value=token_pegged)
            self.save_config()
        return token_pegged, tx_hash

    def unlock_to_eth(self):
        """ Finalize ERC20 or Eth transfer back to Ethereum origin """
        pass

    def _connect_aergo(self, network_name: str) -> herapy.Aergo:
        aergo = herapy.Aergo()
        aergo.connect(self.config_data(network_name, 'ip'))
        return aergo

    def get_aergo(
        self,
        network_name: str,
        privkey_name: str = 'default',
        privkey_pwd: str = None,
        skip_state: bool = False
    ) -> herapy.Aergo:
        """ Return aergo provider with new account created with
        priv_key
        """
        exported_privkey = self.config_data('wallet', privkey_name, 'priv_key')
        aergo = self._connect_aergo(network_name)
        if privkey_pwd is None:
            print("Decrypt exported private key '{}'".format(privkey_name))
            while True:
                try:
                    privkey_pwd = getpass("Password: ")
                    aergo.import_account(exported_privkey, privkey_pwd,
                                         skip_state=skip_state)
                except GeneralException:
                    print("Wrong password, try again")
                    continue
                break
        else:
            aergo.import_account(exported_privkey, privkey_pwd,
                                 skip_state=skip_state)
        return aergo

    def get_web3(
        self,
        network_name: str,
        eth_poa: bool = False
    ) -> Web3:
        ip = self.config_data(network_name, 'ip')
        w3 = Web3(Web3.HTTPProvider("http://" + ip))
        if eth_poa:
            w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        assert w3.isConnected()
        return w3
