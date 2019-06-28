from web3 import (
    Web3,
)
from wallet.exceptions import (
    InvalidArgumentsError,
    TxError
)
from ethaergo_wallet.wallet_utils import (
    is_ethereum_address
)


def get_balance(
    account_addr: str,
    asset_addr: str,
    w3: Web3,
    erc20_abi: str = None
) -> int:
    if not is_ethereum_address(account_addr):
        raise InvalidArgumentsError(
            "Account {} must be an Ethereum address".format(account_addr)
        )
    account_addr = Web3.toChecksumAddress(account_addr)
    balance = 0
    if asset_addr == "ether":
        balance = w3.eth.getBalance(account_addr)
    else:
        asset_addr = Web3.toChecksumAddress(asset_addr)
        if erc20_abi is None:
            raise InvalidArgumentsError("Provide token abi to query balance")
        token_contract = w3.eth.contract(
            address=asset_addr,
            abi=erc20_abi
        )
        balance = token_contract.functions.balanceOf(account_addr).call()
    return balance


def increase_approval(
    spender: str,
    asset_addr: str,
    amount: int,
    w3: Web3,
    erc20_abi: str,
    signer_acct
):
    """ Increase approval increases the amount of tokens that spender
        can withdraw. For older tokens without the increaseApproval
        function in the abi, approval should be set to 0 and then to amount.
        Newer tokens with increaseAllowance should also be suported
    """
    asset_addr = Web3.toChecksumAddress(asset_addr)
    spender = Web3.toChecksumAddress(spender)
    token_contract = w3.eth.contract(
        address=asset_addr,
        abi=erc20_abi
    )
    construct_txn = token_contract.functions.increaseApproval(
        spender, amount
    ).buildTransaction({
        'chainId': w3.eth.chainId,
        'from': signer_acct.address,
        'nonce': w3.eth.getTransactionCount(
            signer_acct.address
        ),
        'gas': 4108036,
        'gasPrice': w3.toWei(9, 'gwei')
    })
    signed = signer_acct.sign_transaction(construct_txn)
    tx_hash = w3.eth.sendRawTransaction(signed.rawTransaction)
    receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    print(receipt)
    if receipt.status != 1:
        print(receipt)
        raise TxError("Mint asset Tx execution failed")
