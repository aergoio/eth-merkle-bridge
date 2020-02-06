import time
from typing import (
    Tuple,
)
from web3 import (
    Web3,
)
from web3.exceptions import (
    BadFunctionCallOutput,
)
from web3.datastructures import (
    AttributeDict,
)
import aergo.herapy as herapy
from aergo.herapy.obj.transaction import (
    Transaction
)
from aergo_wallet.exceptions import (
    InvalidMerkleProofError,
    TxError,
    InvalidArgumentsError
)
from ethaergo_wallet.wallet_utils import (
    is_ethereum_address,
    is_aergo_address
)
import logging

logger = logging.getLogger(__name__)


def lock(
    aergo_from: herapy.Aergo,
    bridge_from: str,
    receiver: str,
    value: int,
    asset: str,
    gas_limit: int,
    gas_price: int,
) -> Tuple[int, str, Transaction]:
    """ Lock can be called to lock aer or tokens.
        it supports delegated transfers when tx broadcaster is not
        the same as the token owner
    """
    if not is_ethereum_address(receiver):
        raise InvalidArgumentsError(
            "receiver {} must be an Ethereum address".format(receiver)
        )
    if not is_aergo_address(asset):
        raise InvalidArgumentsError(
            "asset {} must be an Aergo address".format(asset)
        )
    args = (bridge_from, {"_bignum": str(value)}, receiver[2:].lower())
    tx, result = aergo_from.call_sc(
        asset, "transfer", args=args, amount=0, gas_limit=gas_limit,
        gas_price=gas_price
    )
    if result.status != herapy.CommitStatus.TX_OK:
        raise TxError("Lock asset Tx commit failed : {}".format(result))

    # Check lock success
    result = aergo_from.wait_tx_result(tx.tx_hash)
    if result.status != herapy.TxResultStatus.SUCCESS:
        raise TxError("Lock asset Tx execution failed : {}".format(result))
    logger.info("\u26fd Aergo gas used: %s", result.gas_used)
    # get precise lock height
    tx_detail = aergo_from.get_tx(tx.tx_hash)
    lock_height = tx_detail.block.height

    return lock_height, str(tx.tx_hash), tx_detail


def build_lock_proof(
    aergo_from: herapy.Aergo,
    w3: Web3,
    receiver: str,
    bridge_from: str,
    bridge_to: str,
    bridge_to_abi: str,
    lock_height: int,
    token_origin: str,
):
    """ Check the last anchored root includes the lock and build
    a lock proof for that root
    """
    if not is_ethereum_address(receiver):
        raise InvalidArgumentsError(
            "Receiver {} must be an ethereum address".format(receiver)
        )
    if not is_aergo_address(token_origin):
        raise InvalidArgumentsError(
            "token_origin {} must be an Aergo address".format(token_origin)
        )
    trie_key = "_sv__locks-".encode('utf-8') + bytes.fromhex(receiver[2:]) \
        + token_origin.encode('utf-8')
    return _build_deposit_proof(
        aergo_from, w3, bridge_from, bridge_to, bridge_to_abi, lock_height,
        trie_key
    )


def mint(
    w3: Web3,
    signer_acct,
    receiver: str,
    lock_proof: herapy.obj.sc_state.SCState,
    token_origin: str,
    bridge_to: str,
    bridge_to_abi: str,
    gas_limit: int,
    gas_price: int
) -> Tuple[str, str, AttributeDict]:
    """ Mint the receiver's deposit balance on aergo_to. """
    if not is_ethereum_address(receiver):
        raise InvalidArgumentsError(
            "Receiver {} must be an Ethereum address".format(receiver)
        )
    if not is_aergo_address(token_origin):
        raise InvalidArgumentsError(
            "token_origin {} must be an Aergo address".format(token_origin)
        )
    receiver = Web3.toChecksumAddress(receiver)
    balance = int(lock_proof.var_proofs[0].value.decode('utf-8')[1:-1])
    ap = lock_proof.var_proofs[0].auditPath
    bitmap = lock_proof.var_proofs[0].bitmap
    leaf_height = lock_proof.var_proofs[0].height
    # call mint on ethereum with the lock proof from aergo_from
    eth_bridge = w3.eth.contract(
        address=bridge_to,
        abi=bridge_to_abi
    )
    construct_txn = eth_bridge.functions.mint(
        receiver, balance, token_origin, ap, bitmap, leaf_height
    ).buildTransaction({
        'chainId': w3.eth.chainId,
        'from': signer_acct.address,
        'nonce': w3.eth.getTransactionCount(
            signer_acct.address
        ),
        'gas': gas_limit,
        'gasPrice': w3.toWei(gas_price, 'gwei')
    })
    signed = signer_acct.sign_transaction(construct_txn)
    tx_hash = w3.eth.sendRawTransaction(signed.rawTransaction)
    receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    if receipt.status != 1:
        raise TxError("Mint asset Tx execution failed: {}".format(receipt))
    logger.info("\u26fd Eth Gas used: %s", receipt.gasUsed)
    events = eth_bridge.events.mintEvent().processReceipt(receipt)
    token_pegged = events[0]['args']['tokenAddress']

    return token_pegged, tx_hash.hex(), receipt


def burn(
    aergo_from: herapy.Aergo,
    bridge_from: str,
    receiver: str,
    value: int,
    token_pegged: str,
    gas_limit: int,
    gas_price: int,
) -> Tuple[int, str, Transaction]:
    """ Burn a minted token on a sidechain. """
    if not is_ethereum_address(receiver):
        raise InvalidArgumentsError(
            "Receiver {} must be an Ethereum address".format(receiver)
        )
    if not is_aergo_address(token_pegged):
        raise InvalidArgumentsError(
            "token_pegged {} must be an Aergo address".format(token_pegged)
        )
    args = (receiver[2:].lower(), {"_bignum": str(value)}, token_pegged)
    tx, result = aergo_from.call_sc(
        bridge_from, "burn", args=args, gas_limit=gas_limit,
        gas_price=gas_price
    )

    if result.status != herapy.CommitStatus.TX_OK:
        raise TxError("Burn asset Tx commit failed : {}".format(result))

    # Check burn success
    result = aergo_from.wait_tx_result(tx.tx_hash)
    if result.status != herapy.TxResultStatus.SUCCESS:
        raise TxError("Burn asset Tx execution failed : {}".format(result))
    logger.info("\u26fd Aergo gas used: %s", result.gas_used)
    # get precise burn height
    tx_detail = aergo_from.get_tx(tx.tx_hash)
    burn_height = tx_detail.block.height
    return burn_height, str(tx.tx_hash), tx_detail


def build_burn_proof(
    aergo_from: herapy.Aergo,
    w3: Web3,
    receiver: str,
    bridge_from: str,
    bridge_to: str,
    bridge_to_abi: str,
    burn_height: int,
    token_origin: str,
):
    """ Check the last anchored root includes the burn and build
    a burn proof for that root
    """
    if not is_ethereum_address(receiver):
        raise InvalidArgumentsError(
            "Receiver {} must be an Ethereum address".format(receiver)
        )
    if not is_ethereum_address(token_origin):
        raise InvalidArgumentsError(
            "token_origin {} must be an Ethereum address".format(token_origin)
        )
    trie_key = "_sv__burns-".encode('utf-8') + bytes.fromhex(receiver[2:]) \
        + bytes.fromhex(token_origin[2:])
    return _build_deposit_proof(
        aergo_from, w3, bridge_from, bridge_to, bridge_to_abi, burn_height,
        trie_key
    )


def unlock(
    w3: Web3,
    signer_acct,
    receiver: str,
    burn_proof: herapy.obj.sc_state.SCState,
    token_origin: str,
    bridge_to: str,
    bridge_to_abi: str,
    gas_limit: int,
    gas_price: int
) -> Tuple[str, AttributeDict]:
    """ Unlock the receiver's burnt balance on aergo_to. """
    if not is_ethereum_address(receiver):
        raise InvalidArgumentsError(
            "Receiver {} must be an Ethereum address".format(receiver)
        )
    if not is_ethereum_address(token_origin):
        raise InvalidArgumentsError(
            "token_origin {} must be an Ethereum address".format(token_origin)
        )
    receiver = Web3.toChecksumAddress(receiver)
    balance = int(burn_proof.var_proofs[0].value.decode('utf-8')[1:-1])
    ap = burn_proof.var_proofs[0].auditPath
    bitmap = burn_proof.var_proofs[0].bitmap
    leaf_height = burn_proof.var_proofs[0].height
    # call mint on ethereum with the lock proof from aergo_from
    eth_bridge = w3.eth.contract(
        address=bridge_to,
        abi=bridge_to_abi
    )
    construct_txn = eth_bridge.functions.unlock(
        receiver, balance, token_origin, ap, bitmap, leaf_height
    ).buildTransaction({
        'chainId': w3.eth.chainId,
        'from': signer_acct.address,
        'nonce': w3.eth.getTransactionCount(
            signer_acct.address
        ),
        'gas': gas_limit,
        'gasPrice': w3.toWei(gas_price, 'gwei')
    })
    signed = signer_acct.sign_transaction(construct_txn)
    tx_hash = w3.eth.sendRawTransaction(signed.rawTransaction)
    receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    if receipt.status != 1:
        raise TxError("Unlock asset Tx execution failed: {}".format(receipt))
    logger.info("\u26fd Eth Gas used: %s", receipt.gasUsed)
    return tx_hash.hex(), receipt


def freeze(
    aergo_from: herapy.Aergo,
    bridge_from: str,
    receiver: str,
    value: int,
    gas_limit: int,
    gas_price: int,
) -> Tuple[int, str, Transaction]:
    """ Freeze aergo native """
    if not is_ethereum_address(receiver):
        raise InvalidArgumentsError(
            "Receiver {} must be an Ethereum address".format(receiver)
        )
    args = (receiver[2:].lower(), {"_bignum": str(value)})
    tx, result = aergo_from.call_sc(
        bridge_from, "freeze", amount=value, args=args, gas_limit=gas_limit,
        gas_price=gas_price
    )

    if result.status != herapy.CommitStatus.TX_OK:
        raise TxError("Freeze asset Tx commit failed : {}".format(result))

    # Check freeze success
    result = aergo_from.wait_tx_result(tx.tx_hash)
    if result.status != herapy.TxResultStatus.SUCCESS:
        raise TxError("Freeze Aer Tx execution failed : {}".format(result))
    logger.info("\u26fd Aergo gas used: %s", result.gas_used)
    # get precise burn height
    tx_detail = aergo_from.get_tx(tx.tx_hash)
    freeze_height = tx_detail.block.height
    return freeze_height, str(tx.tx_hash), tx_detail


def _build_deposit_proof(
    aergo_from: herapy.Aergo,
    w3: Web3,
    bridge_from: str,
    bridge_to: str,
    bridge_to_abi: str,
    deposit_height: int,
    trie_key: bytes,
):
    """ Check the last anchored root includes the deposit and build
    a deposit proof for that root
    """
    # check last merged height
    eth_bridge = w3.eth.contract(
        address=bridge_to,
        abi=bridge_to_abi
    )
    try:
        last_merged_height_to = eth_bridge.functions._anchorHeight().call()
    except BadFunctionCallOutput as e:
        raise InvalidArgumentsError(e, bridge_to)
    # waite for anchor containing our transfer
    if last_merged_height_to < deposit_height:
        logger.info(
            "\u23F0 deposit not recorded in current anchor, waiting new "
            "anchor event... / deposit height : %s / last anchor height : %s ",
            deposit_height, last_merged_height_to
        )
        while last_merged_height_to < deposit_height:
            time.sleep(1)
            last_merged_height_to = eth_bridge.functions._anchorHeight().call()
    # get inclusion proof of lock in last merged block
    merge_block_from = aergo_from.get_block_headers(
        block_height=last_merged_height_to, list_size=1)
    root_from = merge_block_from[0].blocks_root_hash
    proof = aergo_from.query_sc_state(
        bridge_from, [trie_key],
        root=root_from, compressed=True
    )
    if not proof.verify_proof(root_from):
        raise InvalidMerkleProofError("Unable to verify deposit proof",
                                      proof)
    if not proof.account.state_proof.inclusion:
        raise InvalidMerkleProofError(
            "Contract doesnt exist in state, check contract deployed and "
            "chain synced {}".format(proof))
    if not proof.var_proofs[0].inclusion:
        raise InvalidMerkleProofError(
            "No tokens deposited for this account reference: {}"
            .format(proof))
    return proof


def withdrawable(
    bridge_from: str,
    bridge_to: str,
    hera: herapy.Aergo,
    w3: Web3,
    aergo_storage_key: bytes,
    eth_trie_key: bytes,
) -> Tuple[int, int]:
    # total_deposit : total latest deposit including pending
    _, block_height = hera.get_blockchain_status()
    block_from = hera.get_block_headers(
        block_height=block_height, list_size=1)
    root_from = block_from[0].blocks_root_hash
    deposit_proof = hera.query_sc_state(
        bridge_from, [aergo_storage_key],
        root=root_from, compressed=False
    )
    if not deposit_proof.account.state_proof.inclusion:
        raise InvalidArgumentsError(
            "Contract doesnt exist in state, check contract deployed and "
            "chain synced {}".format(deposit_proof))
    total_deposit = 0
    if deposit_proof.var_proofs[0].inclusion:
        total_deposit = int(deposit_proof.var_proofs[0].value
                            .decode('utf-8')[1:-1])

    # get total withdrawn and last anchor height
    bridge_to = Web3.toChecksumAddress(bridge_to)
    storage_value = w3.eth.getStorageAt(bridge_to, eth_trie_key, 'latest')
    total_withdrawn = int.from_bytes(storage_value, "big")
    # Height is at position 1 in solidity contract
    storage_value = w3.eth.getStorageAt(bridge_to, 1, 'latest')
    last_anchor_height = int.from_bytes(storage_value, "big")

    # get anchored deposit : total deposit before the last anchor
    block_from = hera.get_block_headers(
        block_height=last_anchor_height, list_size=1)
    root_from = block_from[0].blocks_root_hash
    deposit_proof = hera.query_sc_state(
        bridge_from, [aergo_storage_key],
        root=root_from, compressed=False
    )
    if not deposit_proof.account.state_proof.inclusion:
        raise InvalidArgumentsError(
            "Contract doesnt exist in state, check contract deployed and "
            "chain synced {}".format(deposit_proof))
    anchored_deposit = 0
    if deposit_proof.var_proofs[0].inclusion:
        anchored_deposit = int(deposit_proof.var_proofs[0].value
                               .decode('utf-8')[1:-1])

    withdrawable_balance = anchored_deposit - total_withdrawn
    pending = total_deposit - anchored_deposit
    return withdrawable_balance, pending
