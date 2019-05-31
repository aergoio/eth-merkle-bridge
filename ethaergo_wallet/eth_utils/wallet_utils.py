from web3 import (
    Web3,
)
from wallet.exceptions import (
    InvalidArgumentsError,
)


def get_balance(
    account_addr: str,
    asset_addr: str,
    w3: Web3,
    abi: str = None
) -> int:
    account_addr = Web3.toChecksumAddress(account_addr)
    balance = 0
    if asset_addr == "ether":
        balance = w3.eth.getBalance(account_addr)
    else:
        asset_addr = Web3.toChecksumAddress(asset_addr)
        if abi is None:
            raise InvalidArgumentsError("Provide token abi to query balance")
        token_contract = w3.eth.contract(
            address=asset_addr,
            abi=abi
        )
        balance = token_contract.functions.balanceOf(account_addr).call()
    return balance
