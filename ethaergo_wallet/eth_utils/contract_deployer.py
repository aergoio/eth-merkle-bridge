from web3 import (
    Web3,
)
import logging

logger = logging.getLogger(__name__)


def deploy_contract(
    bytecode: str,
    abi: str,
    w3: Web3,
    gas_limit: int,
    gas_price: int,
    privkey: bytes,
    *args,
):
    """ Deploy a new contract to ethereum."""
    contract_ = w3.eth.contract(
        abi=abi,
        bytecode=bytecode)

    acct = w3.eth.account.from_key(privkey)

    construct_txn = contract_.constructor(*args).buildTransaction({
        'chainId': w3.eth.chainId,
        'from': acct.address,
        'nonce': w3.eth.getTransactionCount(acct.address),
        'gas': gas_limit,
        'gasPrice': w3.toWei(gas_price, 'gwei')})

    signed = acct.sign_transaction(construct_txn)

    tx_hash = w3.eth.sendRawTransaction(signed.rawTransaction)
    receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    if receipt.status != 1:
        logger.info("Deployment failed: %s", receipt)
    return receipt
