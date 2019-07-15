from getpass import getpass
import os
from typing import (
    Dict,
    Tuple
)
import wallet.wallet_utils as aergo_u
from eth_utils import (
    keccak,
)

from ethaergo_wallet.wallet_config import (
    WalletConfig,
)
import ethaergo_wallet.eth_utils.erc20 as eth_u
import ethaergo_wallet.aergo_to_eth as aergo_to_eth
import ethaergo_wallet.eth_to_aergo as eth_to_aergo
from ethaergo_wallet.wallet_utils import (
    is_aergo_address,
    is_ethereum_address
)
from wallet.exceptions import (
    InsufficientBalanceError,
    InvalidArgumentsError,
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
        # root_path is the path/to/eth-merkle-bridge from which files are
        # tracked
        file_path = os.path.dirname(os.path.realpath(__file__))
        self.root_path = os.path.dirname(file_path) + '/'

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

    def lock_to_aergo(
        self,
        from_chain: str,
        to_chain: str,
        asset_name: str,
        amount: int,
        receiver: str,
        privkey_name: str = 'default',
        privkey_pwd: str = None,
    ) -> Tuple[int, str]:
        """ Initiate ERC20 token or Ether transfer to Aergo sidechain """
        print('\n' + from_chain + ' -> ' + to_chain)
        if not is_aergo_address(receiver):
            raise InvalidArgumentsError(
                "Receiver {} must be an Aergo address".format(receiver)
            )
        bridge_from_abi = self.load_bridge_abi(from_chain, to_chain)
        erc20_abi = self.load_erc20_abi(from_chain, asset_name)
        w3 = self.get_web3(from_chain)
        signer_acct = self.get_signer(w3, privkey_name, privkey_pwd)
        token_owner = signer_acct.address
        bridge_from = self.get_bridge_contract_address(from_chain, to_chain)
        erc20_address = self.get_asset_address(asset_name, from_chain)

        balance = eth_u.get_balance(token_owner, erc20_address, w3,
                                    erc20_abi)
        print("{} balance on destination before transfer : {}"
              .format(asset_name, balance/10**18))
        if balance < amount:
            raise InsufficientBalanceError("not enough token balance")

        fee_limit = 0  # TODO also count the gas fee for approval
        eth_balance = eth_u.get_balance(token_owner, 'ether', w3)
        if eth_balance < fee_limit*self.fee_price:
            err = "not enough aer balance to pay tx fee"
            raise InsufficientBalanceError(err)

        next_nonce, tx_hash = eth_u.increase_approval(
            bridge_from, erc20_address, amount, w3, erc20_abi, signer_acct
        )
        print("\u2b06 Increase approval success: ", tx_hash)

        lock_height, tx_hash = eth_to_aergo.lock(
            w3, signer_acct, receiver, amount, bridge_from, bridge_from_abi,
            erc20_address, fee_limit, self.fee_price, next_nonce
        )
        print('\U0001f512 Lock success: ', tx_hash)

        balance = eth_u.get_balance(token_owner, erc20_address, w3,
                                    erc20_abi)
        print("remaining {} balance on origin after transfer: {}"
              .format(asset_name, balance/10**18))
        return lock_height, tx_hash

    def mint_to_aergo(
        self,
        from_chain: str,
        to_chain: str,
        asset_name: str,
        receiver: str = None,
        lock_height: int = 0,
        privkey_name: str = 'default',
        privkey_pwd: str = None,
    ) -> str:
        """ Finalize ERC20 token or Ether transfer to Aergo sidechain """
        print('\n' + from_chain + ' -> ' + to_chain)
        w3 = self.get_web3(from_chain)
        aergo_to = self.get_aergo(to_chain, privkey_name, privkey_pwd)
        tx_sender = str(aergo_to.account.address)
        bridge_to = self.get_bridge_contract_address(to_chain, from_chain)
        bridge_from = self.get_bridge_contract_address(from_chain, to_chain)
        asset_address = self.get_asset_address(asset_name, from_chain)
        if receiver is None:
            receiver = tx_sender
        if not is_aergo_address(receiver):
            raise InvalidArgumentsError(
                "Receiver {} must be an Aergo address".format(receiver)
            )

        save_pegged_token_address = False
        try:
            token_pegged = self.get_asset_address(
                asset_name, to_chain, asset_origin_chain=from_chain)
            balance = aergo_u.get_balance(receiver, token_pegged, aergo_to)
            print("{} balance on destination before transfer: {}"
                  .format(asset_name, balance/10**18))
        except KeyError:
            print("Pegged token unknow by wallet")
            save_pegged_token_address = True

        fee_limit = 0
        aer_balance = aergo_u.get_balance(tx_sender, 'aergo', aergo_to)
        if aer_balance < fee_limit*self.fee_price:
            err = "not enough aer balance to pay tx fee"
            raise InsufficientBalanceError(err)

        lock_proof = eth_to_aergo.build_lock_proof(
            w3, aergo_to, receiver, bridge_from, bridge_to, lock_height,
            asset_address
        )
        print("\u2699 Built lock proof")

        token_pegged, tx_hash = eth_to_aergo.mint(
            aergo_to, receiver, lock_proof, asset_address, bridge_to,
            fee_limit, self.fee_price
        )
        print('\u26cf Mint success: ', tx_hash)
        # new balance on destination
        balance = aergo_u.get_balance(receiver, token_pegged, aergo_to)
        print("{} balance on destination after transfer: {}"
              .format(asset_name, balance/10**18))
        aergo_to.disconnect()

        # record mint address in file
        if save_pegged_token_address:
            print("------ Store mint address in config.json -----------")
            self.config_data(
                'networks', from_chain, 'tokens', asset_name, 'pegs', to_chain,
                value=token_pegged)
            self.save_config()
        return tx_hash

    def burn_to_aergo(
        self,
        from_chain: str,
        to_chain: str,
        asset_name: str,
        amount: int,
        receiver: str,
        privkey_name: str = 'default',
        privkey_pwd: str = None,
    ) -> Tuple[int, str]:
        """ Initiate minted Standard token transfer back to aergo origin"""
        print('\n' + from_chain + ' -> ' + to_chain)
        if not is_aergo_address(receiver):
            raise InvalidArgumentsError(
                "Receiver {} must be an Aergo address".format(receiver)
            )
        bridge_from_abi = self.load_bridge_abi(from_chain, to_chain)
        minted_erc20_abi = self.load_minted_erc20_abi(from_chain, to_chain)
        w3 = self.get_web3(from_chain)
        signer_acct = self.get_signer(w3, privkey_name, privkey_pwd)
        token_owner = signer_acct.address
        bridge_from = self.get_bridge_contract_address(from_chain, to_chain)
        token_pegged = self.get_asset_address(asset_name, from_chain,
                                              asset_origin_chain=to_chain)

        balance = eth_u.get_balance(token_owner, token_pegged, w3,
                                    minted_erc20_abi)
        print("{} balance on destination before transfer : {}"
              .format(asset_name, balance/10**18))
        if balance < amount:
            raise InsufficientBalanceError("not enough token balance")

        fee_limit = 0
        eth_balance = eth_u.get_balance(token_owner, 'ether', w3)
        if eth_balance < fee_limit*self.fee_price:
            err = "not enough aer balance to pay tx fee"
            raise InsufficientBalanceError(err)

        burn_height, tx_hash = eth_to_aergo.burn(
            w3, signer_acct, receiver, amount, bridge_from, bridge_from_abi,
            token_pegged, fee_limit, self.fee_price
        )
        print('\U0001f525 Burn success: ', tx_hash)

        balance = eth_u.get_balance(token_owner, token_pegged, w3,
                                    minted_erc20_abi)
        print("remaining {} balance on origin after transfer: {}"
              .format(asset_name, balance/10**18))
        return burn_height, tx_hash

    def unfreeze(
        self,
        from_chain: str,
        to_chain: str,
        receiver: str = None,
        lock_height: int = 0,
        privkey_name: str = 'default',
        privkey_pwd: str = None,
    ) -> str:
        """ Finalize ERC20Aergo transfer to Aergo Mainnet by unfreezing
            (aers are already minted and freezed in the bridge contract)
        """
        print('\n' + from_chain + ' -> ' + to_chain)
        asset_name = 'aergo_erc20'
        w3 = self.get_web3(from_chain)
        aergo_to = self.get_aergo(to_chain, privkey_name, privkey_pwd)
        tx_sender = str(aergo_to.account.address)
        bridge_to = self.get_bridge_contract_address(to_chain, from_chain)
        bridge_from = self.get_bridge_contract_address(from_chain, to_chain)
        asset_address = self.get_asset_address(asset_name, from_chain)
        if receiver is None:
            receiver = tx_sender
        if not is_aergo_address(receiver):
            raise InvalidArgumentsError(
                "Receiver {} must be an Aergo address".format(receiver)
            )

        balance = aergo_u.get_balance(receiver, 'aergo', aergo_to)
        print("{} balance on destination before transfer: {}"
              .format(asset_name, balance/10**18))

        fee_limit = 0
        if receiver != tx_sender:
            aer_balance = aergo_u.get_balance(tx_sender, 'aergo', aergo_to)
            if aer_balance < fee_limit*self.fee_price:
                err = "not enough aer balance to pay tx fee"
                raise InsufficientBalanceError(err)

        lock_proof = eth_to_aergo.build_lock_proof(
            w3, aergo_to, receiver, bridge_from, bridge_to, lock_height,
            asset_address
        )
        print("\u2699 Built lock proof")

        tx_hash = eth_to_aergo.unfreeze(
            aergo_to, receiver, lock_proof, bridge_to, fee_limit,
            self.fee_price
        )
        print('\U0001f4a7 Unfreeze success: ', tx_hash)
        # new balance on destination
        balance = aergo_u.get_balance(receiver, 'aergo', aergo_to)
        print("{} balance on destination after transfer: {}"
              .format(asset_name, balance/10**18))
        aergo_to.disconnect()

        # record mint address in file
        return tx_hash

    def unlock_to_aergo(
        self,
        from_chain: str,
        to_chain: str,
        asset_name: str,
        receiver: str,
        burn_height: int = 0,
        privkey_name: str = 'default',
        privkey_pwd: str = None,
    ) -> str:
        """ Finalize Aergo Standard token transfer back to Aergo Origin"""
        print('\n' + from_chain + ' -> ' + to_chain)
        if not is_aergo_address(receiver):
            raise InvalidArgumentsError(
                "Receiver {} must be an Aergo address".format(receiver)
            )
        w3 = self.get_web3(from_chain)
        aergo_to = self.get_aergo(to_chain, privkey_name, privkey_pwd)
        tx_sender = str(aergo_to.account.address)
        bridge_to = self.get_bridge_contract_address(to_chain, from_chain)
        bridge_from = self.get_bridge_contract_address(from_chain, to_chain)
        asset_address = self.get_asset_address(asset_name, to_chain)

        burn_proof = eth_to_aergo.build_burn_proof(
            w3, aergo_to, receiver, bridge_from, bridge_to, burn_height,
            asset_address
        )
        print("\u2699 Built burn proof")

        balance = aergo_u.get_balance(receiver, asset_address, aergo_to)
        print("{} balance on destination before transfer: {}"
              .format(asset_name, balance/10**18))

        fee_limit = 0
        aer_balance = aergo_u.get_balance(tx_sender, 'aergo', aergo_to)
        if aer_balance < fee_limit*self.fee_price:
            err = "not enough aer balance to pay tx fee"
            raise InsufficientBalanceError(err)

        tx_hash = eth_to_aergo.unlock(
            aergo_to, receiver, burn_proof, asset_address, bridge_to,
            fee_limit, self.fee_price
        )
        print('\U0001f513 Unlock success: ', tx_hash)

        # new balance on origin
        balance = aergo_u.get_balance(receiver, asset_address, aergo_to)
        print("{} balance on destination after transfer: {}"
              .format(asset_name, balance/10**18))

        return tx_hash

    def minteable_to_aergo(
        self,
        from_chain: str,
        to_chain: str,
        asset_name: str,
        receiver: str,
    ) -> Tuple[int, int]:
        """Check minteable balance on Aergo."""
        token_origin = self.get_asset_address(asset_name, from_chain)
        bridge_from = self.get_bridge_contract_address(from_chain, to_chain)
        bridge_to = self.get_bridge_contract_address(to_chain, from_chain)
        if not is_ethereum_address(token_origin):
            raise InvalidArgumentsError(
                "token_origin {} must be an Ethereum address"
                .format(token_origin)
            )
        if not is_aergo_address(receiver):
            raise InvalidArgumentsError(
                "Receiver {} must be an Aergo address".format(receiver)
            )
        hera = self.connect_aergo(to_chain)
        w3 = self.get_web3(from_chain)
        account_ref_eth = \
            receiver.encode('utf-8') + bytes.fromhex(token_origin[2:])
        position = b'\x03'  # Locks
        eth_trie_key = keccak(account_ref_eth + position.rjust(32, b'\0'))
        aergo_storage_key = '_sv_Mints-' + receiver + token_origin[2:].lower()
        return eth_to_aergo.withdrawable(
            bridge_from, bridge_to, w3, hera, eth_trie_key, aergo_storage_key
        )

    def unlockeable_to_aergo(
        self,
        from_chain: str,
        to_chain: str,
        asset_name: str,
        receiver: str,
    ) -> Tuple[int, int]:
        """Check unlockeable balance on Aergo."""
        token_origin = self.get_asset_address(asset_name, to_chain)
        bridge_from = self.get_bridge_contract_address(from_chain, to_chain)
        bridge_to = self.get_bridge_contract_address(to_chain, from_chain)
        if not is_aergo_address(token_origin):
            raise InvalidArgumentsError(
                "token_origin {} must be an Aergo address"
                .format(token_origin)
            )
        if not is_aergo_address(receiver):
            raise InvalidArgumentsError(
                "Receiver {} must be an Aergo address".format(receiver)
            )
        hera = self.connect_aergo(to_chain)
        w3 = self.get_web3(from_chain)
        account_ref = receiver + token_origin
        position = b'\x05'  # Burns
        eth_trie_key = keccak(account_ref.encode('utf-8')
                              + position.rjust(32, b'\0'))
        aergo_storage_key = '_sv_Unlocks-' + account_ref
        return eth_to_aergo.withdrawable(
            bridge_from, bridge_to, w3, hera, eth_trie_key, aergo_storage_key
        )

    def unfreezeable(
        self,
        from_chain: str,
        to_chain: str,
        receiver: str,
    ) -> Tuple[int, int]:
        """Check unfreezeable balance on Aergo."""
        token_origin = self.get_asset_address('aergo_erc20', from_chain)
        bridge_from = self.get_bridge_contract_address(from_chain, to_chain)
        bridge_to = self.get_bridge_contract_address(to_chain, from_chain)
        if not is_ethereum_address(token_origin):
            raise InvalidArgumentsError(
                "token_origin {} must be an Ethereum address"
                .format(token_origin)
            )
        if not is_aergo_address(receiver):
            raise InvalidArgumentsError(
                "Receiver {} must be an Aergo address".format(receiver)
            )
        hera = self.connect_aergo(to_chain)
        w3 = self.get_web3(from_chain)
        account_ref_eth = \
            receiver.encode('utf-8') + bytes.fromhex(token_origin[2:])
        position = b'\x03'  # Locks
        eth_trie_key = keccak(account_ref_eth + position.rjust(32, b'\0'))
        aergo_storage_key = \
            '_sv_Unfreezes-' + receiver + token_origin[2:].lower()
        return eth_to_aergo.withdrawable(
            bridge_from, bridge_to, w3, hera, eth_trie_key, aergo_storage_key
        )

    ###########################################################################
    # aergo_to_eth_sidechain
    # Aer            ->    freeze   -> | -> unlock_to_eth -> Aer
    # MintedStdToken -> burn_to_eth -> | -> unlock_to_eth -> Eth/ERC20
    # StandardToken  -> lock_to_eth -> | ->  mint_to_eth  -> MintedERC20
    ###########################################################################

    def freeze(
        self,
        from_chain: str,
        to_chain: str,
        amount: int,
        receiver: str,
        privkey_name: str = 'default',
        privkey_pwd: str = None,
    ) -> Tuple[int, str]:
        """ Initiate Aer transfer back to Ethereum AergoERC20 sidechain"""
        print('\n' + from_chain + ' -> ' + to_chain)
        if not is_ethereum_address(receiver):
            raise InvalidArgumentsError(
                "receiver {} must be an Ethereum address".format(receiver)
            )
        asset_name = 'aergo_erc20'
        aergo_from = self.get_aergo(from_chain, privkey_name, privkey_pwd)
        sender = str(aergo_from.account.address)
        bridge_from = self.get_bridge_contract_address(from_chain, to_chain)

        fee_limit = 0
        balance = aergo_u.get_balance(sender, 'aergo', aergo_from)
        if balance < amount + fee_limit * self.fee_price:
            raise InsufficientBalanceError("not enough token balance")
        print("{} balance on sidechain before transfer: {}"
              .format(asset_name, balance/10**18))

        freeze_height, tx_hash = aergo_to_eth.freeze(
            aergo_from, bridge_from, receiver, amount, fee_limit,
            self.fee_price
        )
        print('\u2744 Freeze success: ', tx_hash)

        # remaining balance on origin : aer or asset
        balance = aergo_u.get_balance(sender, 'aergo', aergo_from)
        print("remaining {} balance on origin after transfer: {}"
              .format(asset_name, balance/10**18))

        aergo_from.disconnect()
        return freeze_height, tx_hash

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
        print('\n' + from_chain + ' -> ' + to_chain)
        if not is_ethereum_address(receiver):
            raise InvalidArgumentsError(
                "receiver {} must be an Ethereum address".format(receiver)
            )
        if asset_name == 'aergo':
            raise InvalidArgumentsError(
                'aer cannot be locked on Aergo, must be frozen'
            )
        aergo_from = self.get_aergo(from_chain, privkey_name, privkey_pwd)
        sender = str(aergo_from.account.address)
        bridge_from = self.get_bridge_contract_address(from_chain, to_chain)
        asset_address = self.get_asset_address(asset_name, from_chain)

        # sign transfer so bridge can pull tokens to lock.
        fee_limit = 0
        signed_transfer, balance = \
            aergo_u.get_signed_transfer(amount, bridge_from, asset_address,
                                        aergo_from)
        signed_transfer = signed_transfer[:2]  # only nonce, sig are needed
        if balance < amount:
            raise InsufficientBalanceError("not enough token balance")

        aer_balance = aergo_u.get_balance(sender, 'aergo', aergo_from)
        if aer_balance < fee_limit*self.fee_price:
            err = "not enough aer balance to pay tx fee"
            raise InsufficientBalanceError(err)

        print("{} balance on origin before transfer: {}"
              .format(asset_name, balance/10**18))

        lock_height, tx_hash = aergo_to_eth.lock(
            aergo_from, bridge_from, receiver, amount,
            asset_address, fee_limit, self.fee_price, signed_transfer
        )
        print('\U0001f512 Lock success: ', tx_hash)

        # remaining balance on origin : aer or asset
        balance = aergo_u.get_balance(sender, asset_address, aergo_from)
        print("remaining {} balance on origin after transfer: {}"
              .format(asset_name, balance/10**18))

        aergo_from.disconnect()
        return lock_height, tx_hash

    def mint_to_eth(
        self,
        from_chain: str,
        to_chain: str,
        asset_name: str,
        receiver: str = None,
        lock_height: int = 0,
        privkey_name: str = 'default',
        privkey_pwd: str = None,
    ) -> Tuple[str, str]:
        """ Finalize Aergo Standard Token transfer to Ethereum sidechain
        NOTE anybody can mint so sender is not necessary.
        The amount to mint is the difference between total deposit and
        already minted amount.
        Bridge tempo is taken from config_data
        """
        print('\n' + from_chain + ' -> ' + to_chain)
        bridge_to_abi = self.load_bridge_abi(to_chain, from_chain)
        minted_erc20_abi = self.load_minted_erc20_abi(to_chain, from_chain)
        aergo_from = self.connect_aergo(from_chain)
        w3 = self.get_web3(to_chain)
        signer_acct = self.get_signer(w3, privkey_name, privkey_pwd)
        tx_sender = signer_acct.address
        if receiver is None:
            receiver = tx_sender
        if not is_ethereum_address(receiver):
            raise InvalidArgumentsError(
                "receiver {} must be an Ethereum address".format(receiver)
            )
        bridge_from = self.get_bridge_contract_address(from_chain, to_chain)
        bridge_to = self.get_bridge_contract_address(to_chain, from_chain)
        asset_address = self.get_asset_address(asset_name, from_chain)

        save_pegged_token_address = False
        try:
            token_pegged = self.get_asset_address(
                asset_name, to_chain, asset_origin_chain=from_chain)
            balance = eth_u.get_balance(receiver, token_pegged, w3,
                                        minted_erc20_abi)
            print("{} balance on destination before transfer : {}"
                  .format(asset_name, balance/10**18))
        except KeyError:
            print("Pegged token unknow by wallet")
            save_pegged_token_address = True

        fee_limit = 0
        eth_balance = eth_u.get_balance(tx_sender, 'ether', w3)
        if eth_balance < fee_limit*self.fee_price:
            err = "not enough aer balance to pay tx fee"
            raise InsufficientBalanceError(err)

        lock_proof = aergo_to_eth.build_lock_proof(
            aergo_from, w3, receiver, bridge_from, bridge_to, bridge_to_abi,
            lock_height, asset_address
        )
        print("\u2699 Built lock proof")

        token_pegged, tx_hash = aergo_to_eth.mint(
            w3, signer_acct, receiver, lock_proof, asset_address, bridge_to,
            bridge_to_abi, fee_limit, self.fee_price
        )
        print('\u26cf Mint success: ', tx_hash)

        # new balance on sidechain
        balance = eth_u.get_balance(receiver, token_pegged, w3,
                                    minted_erc20_abi)
        print("{} balance on destination after transfer : {}"
              .format(asset_name, balance/10**18))

        aergo_from.disconnect()

        # record mint address in file
        if save_pegged_token_address:
            print("------ Store mint address in config.json -----------")
            self.config_data(
                'networks', from_chain, 'tokens', asset_name, 'pegs', to_chain,
                value=token_pegged)
            self.save_config()
        return token_pegged, tx_hash

    def burn_to_eth(
        self,
        from_chain: str,
        to_chain: str,
        asset_name: str,
        amount: int,
        receiver: str,
        privkey_name: str = 'default',
        privkey_pwd: str = None,
    ) -> Tuple[int, str]:
        """ Initiate minted token transfer back to ethereum origin"""
        print('\n' + from_chain + ' -> ' + to_chain)
        if not is_ethereum_address(receiver):
            raise InvalidArgumentsError(
                "receiver {} must be an Ethereum address".format(receiver)
            )
        aergo_from = self.get_aergo(from_chain, privkey_name, privkey_pwd)
        sender = str(aergo_from.account.address)
        bridge_from = self.get_bridge_contract_address(from_chain, to_chain)
        token_pegged = self.get_asset_address(asset_name, from_chain,
                                              asset_origin_chain=to_chain)

        fee_limit = 0
        balance = aergo_u.get_balance(sender, token_pegged, aergo_from)
        if balance < amount:
            raise InsufficientBalanceError("not enough token balance")
        print("{} balance on sidechain before transfer: {}"
              .format(asset_name, balance/10**18))

        aer_balance = aergo_u.get_balance(sender, 'aergo', aergo_from)
        if aer_balance < fee_limit*self.fee_price:
            err = "not enough aer balance to pay tx fee"
            raise InsufficientBalanceError(err)

        burn_height, tx_hash = aergo_to_eth.burn(
            aergo_from, bridge_from, receiver, amount, token_pegged,
            fee_limit, self.fee_price
        )
        print('\U0001f525 Burn success: ', tx_hash)

        # remaining balance on origin : aer or asset
        balance = aergo_u.get_balance(sender, token_pegged, aergo_from)
        print("remaining {} balance on origin after transfer: {}"
              .format(asset_name, balance/10**18))

        aergo_from.disconnect()
        return burn_height, tx_hash

    def unlock_to_eth(
        self,
        from_chain: str,
        to_chain: str,
        asset_name: str,
        receiver: str = None,
        burn_height: int = 0,
        privkey_name: str = 'default',
        privkey_pwd: str = None,
    ) -> Tuple[str, str]:
        """ Finalize ERC20 or Eth transfer back to Ethereum origin """
        print('\n' + from_chain + ' -> ' + to_chain)
        bridge_to_abi = self.load_bridge_abi(to_chain, from_chain)
        erc20_abi = self.load_erc20_abi(to_chain, asset_name)
        aergo_from = self.connect_aergo(from_chain)
        # get ethereum tx signer
        w3 = self.get_web3(to_chain)
        signer_acct = self.get_signer(w3, privkey_name, privkey_pwd)
        tx_sender = signer_acct.address

        if receiver is None:
            receiver = tx_sender
        if not is_ethereum_address(receiver):
            raise InvalidArgumentsError(
                "receiver {} must be an Ethereum address".format(receiver)
            )

        bridge_from = self.get_bridge_contract_address(from_chain, to_chain)
        bridge_to = self.get_bridge_contract_address(to_chain, from_chain)
        asset_address = self.get_asset_address(asset_name, to_chain)
        balance = eth_u.get_balance(receiver, asset_address, w3, erc20_abi)
        print("{} balance on destination before transfer : {}"
              .format(asset_name, balance/10**18))

        fee_limit = 0
        eth_balance = eth_u.get_balance(tx_sender, 'ether', w3)
        if eth_balance < fee_limit*self.fee_price:
            err = "not enough aer balance to pay tx fee"
            raise InsufficientBalanceError(err)

        lock_proof = aergo_to_eth.build_burn_proof(
            aergo_from, w3, receiver, bridge_from, bridge_to, bridge_to_abi,
            burn_height, asset_address
        )
        print("\u2699 Built burn proof")

        tx_hash = aergo_to_eth.unlock(
            w3, signer_acct, receiver, lock_proof, asset_address, bridge_to,
            bridge_to_abi, fee_limit, self.fee_price
        )
        print('\U0001f513 Unlock success: ', tx_hash)

        # new balance on origin
        balance = eth_u.get_balance(receiver, asset_address, w3,
                                    erc20_abi)
        print("{} balance on destination after transfer : {}"
              .format(asset_name, balance/10**18))

        aergo_from.disconnect()
        return tx_hash

    def minteable_to_eth(
        self,
        from_chain: str,
        to_chain: str,
        asset_name: str,
        receiver: str,
    ) -> Tuple[int, int]:
        """Check minteable balance on Ethereum."""
        token_origin = self.get_asset_address(asset_name, from_chain)
        bridge_from = self.get_bridge_contract_address(from_chain, to_chain)
        bridge_to = self.get_bridge_contract_address(to_chain, from_chain)
        if not is_aergo_address(token_origin):
            raise InvalidArgumentsError(
                "token_origin {} must be an Aergo address".format(token_origin)
            )
        if not is_ethereum_address(receiver):
            raise InvalidArgumentsError(
                "Receiver {} must be an Ethereum address".format(receiver)
            )
        hera = self.connect_aergo(from_chain)
        w3 = self.get_web3(to_chain)
        account_ref_eth = \
            bytes.fromhex(receiver[2:]) + token_origin.encode('utf-8')
        position = b'\x06'  # Mints
        eth_trie_key = keccak(account_ref_eth + position.rjust(32, b'\0'))
        aergo_storage_key = '_sv_Locks-'.encode('utf-8') \
            + bytes.fromhex(receiver[2:]) + token_origin.encode('utf-8')
        return aergo_to_eth.withdrawable(
            bridge_from, bridge_to, hera, w3, aergo_storage_key, eth_trie_key
        )

    def unlockeable_to_eth(
        self,
        from_chain: str,
        to_chain: str,
        asset_name: str,
        receiver: str,
    ) -> Tuple[int, int]:
        """Check unlockeable balance on Ethereum."""
        token_origin = self.get_asset_address(asset_name, to_chain)
        bridge_from = self.get_bridge_contract_address(from_chain, to_chain)
        bridge_to = self.get_bridge_contract_address(to_chain, from_chain)
        if not is_ethereum_address(token_origin):
            raise InvalidArgumentsError(
                "token_origin {} must be an Ethereum address"
                .format(token_origin)
            )
        if not is_ethereum_address(receiver):
            raise InvalidArgumentsError(
                "Receiver {} must be an Ethereum address".format(receiver)
            )
        hera = self.connect_aergo(from_chain)
        w3 = self.get_web3(to_chain)
        account_ref = receiver[2:] + token_origin[2:]
        position = b'\x04'  # Unlocks
        eth_trie_key = keccak(
            bytes.fromhex(account_ref) + position.rjust(32, b'\0'))
        aergo_storage_key = '_sv_Burns-'.encode('utf-8') \
            + bytes.fromhex(account_ref)
        return aergo_to_eth.withdrawable(
            bridge_from, bridge_to, hera, w3, aergo_storage_key, eth_trie_key
        )

    def connect_aergo(self, network_name: str) -> herapy.Aergo:
        aergo = herapy.Aergo()
        aergo.connect(self.config_data('networks', network_name, 'ip'))
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
        aergo = self.connect_aergo(network_name)
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
    ) -> Web3:
        ip = self.config_data('networks', network_name, 'ip')
        w3 = Web3(Web3.HTTPProvider("http://" + ip))
        eth_poa = self.config_data('networks', network_name, 'isPOA')
        if eth_poa:
            w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        assert w3.isConnected()
        return w3

    def get_balance_aergo(
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
        if account_addr is None:
            account_addr = self.config_data('wallet', account_name, 'addr')
        if not is_aergo_address(account_addr):
            raise InvalidArgumentsError(
                "Account {} must be an Aergo address".format(account_addr)
            )
        aergo = self.connect_aergo(network_name)
        asset_addr = self.get_asset_address(asset_name, network_name,
                                            asset_origin_chain)
        balance = aergo_u.get_balance(account_addr, asset_addr, aergo)
        aergo.disconnect()
        return balance, asset_addr

    def get_balance_eth(
        self,
        asset_name: str,
        network_name: str,
        asset_origin_chain: str = None,
        account_name: str = 'default',
        account_addr: str = None,
    ) -> Tuple[int, str]:
        """ Get account name balance of asset_name on network_name,
        and specify asset_origin_chain for a pegged asset query,
        """
        if account_addr is None:
            account_addr = self.get_eth_wallet_address(account_name)
        if not is_ethereum_address(account_addr):
            raise InvalidArgumentsError(
                "Account {} must be an Ethereum address".format(account_addr)
            )
        w3 = self.get_web3(network_name)
        asset_addr = self.get_asset_address(asset_name, network_name,
                                            asset_origin_chain)
        if asset_origin_chain is None:
            if asset_addr == 'ether':
                balance = eth_u.get_balance(account_addr, asset_addr, w3)
                return balance, asset_addr
            abi = self.load_erc20_abi(network_name, asset_name)
        else:
            abi = self.load_minted_erc20_abi(network_name, asset_origin_chain)

        balance = eth_u.get_balance(account_addr, asset_addr, w3, abi)
        return balance, asset_addr

    def load_bridge_abi(
        self,
        from_chain: str,
        to_chain: str,
    ) -> str:
        """Load Ethereum bridge contract abi from file location in config."""
        bridge_abi_path = self.config_data(
            'networks', from_chain, 'bridges', to_chain, 'bridge_abi')
        with open(self.root_path + bridge_abi_path, "r") as f:
            bridge_from_abi = f.read()
        return bridge_from_abi

    def load_minted_erc20_abi(
        self,
        from_chain: str,
        to_chain: str,
    ) -> str:
        """Load Ethereum bridge contract minted token abi from file location
        in config.

        """
        minted_erc20_abi_path = self.config_data(
            'networks', from_chain, 'bridges', to_chain, 'minted_abi')
        with open(self.root_path + minted_erc20_abi_path, "r") as f:
            minted_erc20_abi = f.read()
        return minted_erc20_abi

    def load_erc20_abi(
        self,
        origin_chain: str,
        asset_name: str,
    ) -> str:
        """Load erc20 contract abi from file location in config."""
        erc20_abi_path = self.config_data('networks', origin_chain, 'tokens',
                                          asset_name, 'abi')
        with open(self.root_path + erc20_abi_path, "r") as f:
            erc20_abi = f.read()
        return erc20_abi

    def load_keystore(
        self,
        privkey_name: str
    ) -> str:
        """Load encrypted private key from Ethereum json keystore."""
        sender_keystore = self.config_data(
            'wallet-eth', privkey_name, 'keystore')
        with open(self.root_path + sender_keystore, "r") as f:
            encrypted_key = f.read()
        return encrypted_key

    def get_signer(
        self,
        w3: Web3,
        privkey_name: str,
        privkey_pwd: str = None,
    ):
        """Get the web3 signer object from the ethereum private key."""
        encrypted_key = self.load_keystore(privkey_name)
        if privkey_pwd is None:
            while True:
                try:
                    privkey_pwd = getpass(
                        "Decrypt Ethereum keystore '{}'\nPassword: "
                        .format(privkey_name))
                except ValueError:
                    print("Wrong password, try again")
                    continue
                break

        privkey = w3.eth.account.decrypt(encrypted_key, privkey_pwd)
        signer_acct = w3.eth.account.from_key(privkey)
        return signer_acct
