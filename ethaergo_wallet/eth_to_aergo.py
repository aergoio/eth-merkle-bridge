import json
from typing import (
    Tuple,
)
from eth_utils import (
    keccak,
)
from web3.datastructures import (
    AttributeDict,
)

from web3 import (
    Web3,
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
    is_aergo_address,
    is_ethereum_address
)
from ethaergo_wallet.eth_utils.merkle_proof import (
    verify_eth_getProof_inclusion,
    format_proof_for_lua
)
import logging

logger = logging.getLogger(__name__)


def lock(
    w3: Web3,
    signer_acct,
    receiver: str,
    amount: int,
    bridge_from: str,
    bridge_from_abi: str,
    erc20_address: str,
    gas_limit: int,
    gas_price: int,
    next_nonce: int = None
) -> Tuple[int, str, AttributeDict]:
    """ Lock an Ethereum ERC20 token. """
    if not is_aergo_address(receiver):
        raise InvalidArgumentsError(
            "Receiver {} must be an Aergo address".format(receiver)
        )
    bridge_from = Web3.toChecksumAddress(bridge_from)
    eth_bridge = w3.eth.contract(
        address=bridge_from,
        abi=bridge_from_abi
    )
    if next_nonce is None:
        next_nonce = w3.eth.getTransactionCount(signer_acct.address)
    construct_txn = eth_bridge.functions.lock(
        erc20_address, amount, receiver
    ).buildTransaction({
        'chainId': w3.eth.chainId,
        'from': signer_acct.address,
        'nonce': next_nonce,
        'gas': gas_limit,
        'gasPrice': w3.toWei(gas_price, 'gwei')
    })
    signed = signer_acct.sign_transaction(construct_txn)
    tx_hash = w3.eth.sendRawTransaction(signed.rawTransaction)
    receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    if receipt.status != 1:
        raise TxError("Lock asset Tx execution failed: {}".format(receipt))
    logger.info("\u26fd Eth Gas used: %s", receipt.gasUsed)
    return receipt.blockNumber, tx_hash.hex(), receipt


def build_lock_proof(
    w3: Web3,
    aergo_to: herapy.Aergo,
    receiver: str,
    bridge_from: str,
    bridge_to: str,
    lock_height: int,
    token_origin: str,
):
    """ Check the last anchored root includes the lock and build
    a lock proof for that root
    """
    if not is_aergo_address(receiver):
        raise InvalidArgumentsError(
            "Receiver {} must be an Aergo address".format(receiver)
        )
    if not is_ethereum_address(token_origin):
        raise InvalidArgumentsError(
            "token_origin {} must be an Ethereum address".format(token_origin)
        )
    account_ref = receiver.encode('utf-8') + bytes.fromhex(token_origin[2:])
    # 'Locks is the 6th state var defined in solitity contract
    position = b'\x05'
    trie_key = keccak(account_ref + position.rjust(32, b'\0'))
    return _build_deposit_proof(
        w3, aergo_to, bridge_from, bridge_to, lock_height, trie_key
    )


def mint(
    aergo_to: herapy.Aergo,
    receiver: str,
    lock_proof: AttributeDict,
    token_origin: str,
    bridge_to: str,
    gas_limit: int,
    gas_price: int
) -> Tuple[str, str, Transaction]:
    """ Unlock the receiver's deposit balance on aergo_to. """
    if not is_aergo_address(receiver):
        raise InvalidArgumentsError(
            "Receiver {} must be an Aergo address".format(receiver)
        )
    if not is_ethereum_address(token_origin):
        raise InvalidArgumentsError(
            "token_origin {} must be an Ethereum address".format(token_origin)
        )
    ap = format_proof_for_lua(lock_proof.storageProof[0].proof)
    balance = int.from_bytes(lock_proof.storageProof[0].value, "big")
    ubig_balance = {'_bignum': str(balance)}
    # call unlock on aergo_to with the burn proof from aergo_from
    tx, result = aergo_to.call_sc(
        bridge_to, "mint",
        args=[receiver, ubig_balance, token_origin[2:].lower(), ap],
        gas_limit=gas_limit, gas_price=gas_price
    )
    if result.status != herapy.CommitStatus.TX_OK:
        raise TxError("Mint asset Tx commit failed : {}".format(result))

    result = aergo_to.wait_tx_result(tx.tx_hash)
    if result.status != herapy.TxResultStatus.SUCCESS:
        raise TxError("Mint asset Tx execution failed : {}".format(result))
    logger.info("\u26fd Aergo gas used: %s", result.gas_used)
    token_pegged = json.loads(result.detail)[0]
    return token_pegged, str(tx.tx_hash), result


def burn(
    w3: Web3,
    signer_acct,
    receiver: str,
    amount: int,
    bridge_from: str,
    bridge_from_abi: str,
    token_pegged: str,
    gas_limit: int,
    gas_price: int
) -> Tuple[int, str, AttributeDict]:
    """ Burn a token that was minted on ethereum. """
    if not is_aergo_address(receiver):
        raise InvalidArgumentsError(
            "Receiver {} must be an Aergo address".format(receiver)
        )
    if not is_ethereum_address(token_pegged):
        raise InvalidArgumentsError(
            "token_pegged {} must be an Ethereum address".format(token_pegged)
        )
    bridge_from = Web3.toChecksumAddress(bridge_from)
    eth_bridge = w3.eth.contract(
        address=bridge_from,
        abi=bridge_from_abi
    )
    construct_txn = eth_bridge.functions.burn(
        receiver, amount, token_pegged
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
        raise TxError("Burn asset Tx execution failed: {}".format(receipt))
    logger.info("\u26fd Eth Gas used: %s", receipt.gasUsed)
    return receipt.blockNumber, tx_hash.hex(), receipt


def build_burn_proof(
    w3: Web3,
    aergo_to: herapy.Aergo,
    receiver: str,
    bridge_from: str,
    bridge_to: str,
    burn_height: int,
    token_origin: str,
):
    """ Check the last anchored root includes the lock and build
    a lock proof for that root
    """
    if not is_aergo_address(receiver):
        raise InvalidArgumentsError(
            "Receiver {} must be an Aergo address".format(receiver)
        )
    if not is_aergo_address(token_origin):
        raise InvalidArgumentsError(
            "token_origin {} must be an Aergo address".format(token_origin)
        )
    account_ref = (receiver + token_origin).encode('utf-8')
    # 'Burns is the 8th state var defined in solitity contract
    position = b'\x07'
    trie_key = keccak(account_ref + position.rjust(32, b'\0'))
    return _build_deposit_proof(
        w3, aergo_to, bridge_from, bridge_to, burn_height, trie_key
    )


def unlock(
    aergo_to: herapy.Aergo,
    receiver: str,
    burn_proof: AttributeDict,
    token_origin: str,
    bridge_to: str,
    gas_limit: int,
    gas_price: int
) -> Tuple[str, Transaction]:
    """ Unlock the receiver's deposit balance on aergo_to. """
    if not is_aergo_address(receiver):
        raise InvalidArgumentsError(
            "Receiver {} must be an Aergo address".format(receiver)
        )
    if not is_aergo_address(token_origin):
        raise InvalidArgumentsError(
            "token_origin {} must be an Aergo address".format(token_origin)
        )
    ap = format_proof_for_lua(burn_proof.storageProof[0].proof)
    balance = int.from_bytes(burn_proof.storageProof[0].value, "big")
    ubig_balance = {'_bignum': str(balance)}
    # call unlock on aergo_to with the burn proof from aergo_from
    tx, result = aergo_to.call_sc(
        bridge_to, "unlock",
        args=[receiver, ubig_balance, token_origin, ap],
        gas_limit=gas_limit, gas_price=gas_price
    )
    if result.status != herapy.CommitStatus.TX_OK:
        raise TxError("Unlock asset Tx commit failed : {}".format(result))

    result = aergo_to.wait_tx_result(tx.tx_hash)
    if result.status != herapy.TxResultStatus.SUCCESS:
        raise TxError("Unlock asset Tx execution failed : {}".format(result))
    logger.info("\u26fd Aergo gas used: %s", result.gas_used)
    return str(tx.tx_hash), result


def unfreeze(
    aergo_to: herapy.Aergo,
    receiver: str,
    lock_proof: AttributeDict,
    bridge_to: str,
    gas_limit: int,
    gas_price: int
) -> Tuple[str, Transaction]:
    """ Unlock the receiver's deposit balance on aergo_to. """
    if not is_aergo_address(receiver):
        raise InvalidArgumentsError(
            "Receiver {} must be an Aergo address".format(receiver)
        )
    ap = format_proof_for_lua(lock_proof.storageProof[0].proof)
    balance = int.from_bytes(lock_proof.storageProof[0].value, "big")
    ubig_balance = {'_bignum': str(balance)}
    # call unlock on aergo_to with the burn proof from aergo_from
    tx, result = aergo_to.call_sc(
        bridge_to, "unfreeze", args=[receiver, ubig_balance, ap],
        gas_limit=gas_limit, gas_price=gas_price
    )
    if result.status != herapy.CommitStatus.TX_OK:
        raise TxError("Unfreeze asset Tx commit failed : {}".format(result))

    result = aergo_to.wait_tx_result(tx.tx_hash)
    if result.status != herapy.TxResultStatus.SUCCESS:
        raise TxError("Unfreeze asset Tx execution failed : {}".format(result))
    logger.info("\u26fd Unfreeze tx fee paid: %s", result.fee_used)
    logger.info("\u26fd Aergo gas used: %s", result.gas_used)
    return str(tx.tx_hash), result


def _build_deposit_proof(
    w3: Web3,
    aergo_to: herapy.Aergo,
    bridge_from: str,
    bridge_to: str,
    deposit_height: int,
    trie_key: bytes
):
    """ Check the last anchored root includes the deposit and build
    a deposit (lock or burn) proof for that root
    """
    bridge_from = Web3.toChecksumAddress(bridge_from)
    # check last merged height
    _, aergo_current_height = aergo_to.get_blockchain_status()
    anchor_info = aergo_to.query_sc_state(bridge_to, ["_sv__anchorHeight"])
    if not anchor_info.account.state_proof.inclusion:
        raise InvalidArgumentsError(
            "Contract doesnt exist in state, check contract deployed and "
            "chain synced {}".format(anchor_info))
    if not anchor_info.var_proofs[0].inclusion:
        raise InvalidArgumentsError("Cannot query last anchored height",
                                    anchor_info)
    last_merged_height_to = int(anchor_info.var_proofs[0].value)
    # waite for anchor containing our transfer
    stream = aergo_to.receive_event_stream(
        bridge_to, "newAnchor", start_block_no=aergo_current_height
    )
    while last_merged_height_to < deposit_height:
        logger.info(
            "\u23F0 deposit not recorded in current anchor, waiting new "
            "anchor event... / deposit height : %s / last anchor height : %s ",
            deposit_height, last_merged_height_to
        )
        new_anchor_event = next(stream)
        last_merged_height_to = new_anchor_event.arguments[1]
    stream.stop()
    # get inclusion proof of lock in last merged block
    block = w3.eth.getBlock(last_merged_height_to)
    eth_proof = w3.eth.getProof(bridge_from, [trie_key], last_merged_height_to)
    try:
        verify_eth_getProof_inclusion(eth_proof, block.stateRoot)
    except AssertionError as e:
        raise InvalidMerkleProofError("Unable to verify deposit proof",
                                      eth_proof, e)
    if trie_key != eth_proof.storageProof[0].key:
        raise InvalidMerkleProofError("Proof doesnt match requested key",
                                      eth_proof, trie_key)
    if len(eth_proof.storageProof[0].value) == 0:
        raise InvalidMerkleProofError("Trie key {} doesn't exist"
                                      .format(trie_key.hex()))
    return eth_proof


def withdrawable(
    bridge_from: str,
    bridge_to: str,
    w3: Web3,
    hera: herapy.Aergo,
    eth_trie_key: bytes,
    aergo_storage_key: bytes
) -> Tuple[int, int]:
    # total_deposit : total latest deposit including pending
    bridge_from = Web3.toChecksumAddress(bridge_from)
    storage_value = w3.eth.getStorageAt(bridge_from, eth_trie_key, 'latest')
    total_deposit = int.from_bytes(storage_value, "big")

    # get total withdrawn and last anchor height
    withdraw_proof = hera.query_sc_state(
        bridge_to, ["_sv__anchorHeight", aergo_storage_key],
        compressed=False
    )
    if not withdraw_proof.account.state_proof.inclusion:
        raise InvalidArgumentsError(
            "Contract doesnt exist in state, check contract deployed and "
            "chain synced {}".format(withdraw_proof))
    if not withdraw_proof.var_proofs[0].inclusion:
        raise InvalidMerkleProofError("Cannot query last anchored height",
                                      withdraw_proof)
    total_withdrawn = 0
    if withdraw_proof.var_proofs[1].inclusion:
        total_withdrawn = int(withdraw_proof.var_proofs[1].value
                              .decode('utf-8')[1:-1])
    last_anchor_height = int(withdraw_proof.var_proofs[0].value)

    # get anchored deposit : total deposit before the last anchor
    storage_value = w3.eth.getStorageAt(bridge_from, eth_trie_key,
                                        last_anchor_height)
    anchored_deposit = int.from_bytes(storage_value, "big")

    withdrawable_balance = anchored_deposit - total_withdrawn
    pending = total_deposit - anchored_deposit
    return withdrawable_balance, pending
