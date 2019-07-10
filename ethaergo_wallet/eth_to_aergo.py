import json
import time
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
from wallet.exceptions import (
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


def lock(
    w3: Web3,
    signer_acct,
    receiver: str,
    amount: int,
    bridge_from: str,
    bridge_from_abi: str,
    erc20_address: str,
    fee_limit: int,
    fee_price: int,
    next_nonce: int = None
):
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
        receiver, amount, erc20_address
    ).buildTransaction({
        'chainId': w3.eth.chainId,
        'from': signer_acct.address,
        'nonce': next_nonce,
        'gas': 4108036,
        'gasPrice': w3.toWei(9, 'gwei')
    })
    signed = signer_acct.sign_transaction(construct_txn)
    tx_hash = w3.eth.sendRawTransaction(signed.rawTransaction)
    receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    if receipt.status != 1:
        print(receipt)
        raise TxError("Lock asset Tx execution failed")
    return receipt.blockNumber, tx_hash


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
    # 'Burns is the 4th state var defined in solitity contract
    position = b'\x03'
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
    fee_limit: int,
    fee_price: int
) -> Tuple[str, str]:
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
    # call unlock on aergo_to with the burn proof from aergo_from
    tx, result = aergo_to.call_sc(bridge_to, "mint",
                                  args=[receiver, balance,
                                        token_origin[2:].lower(), ap])
    if result.status != herapy.CommitStatus.TX_OK:
        raise TxError("Mint asset Tx commit failed : {}".format(result))
    time.sleep(3)

    result = aergo_to.get_tx_result(tx.tx_hash)
    if result.status != herapy.TxResultStatus.SUCCESS:
        print(lock_proof, result)
        raise TxError("Mint asset Tx execution failed : {}".format(result))
    token_pegged = json.loads(result.detail)[0]
    return token_pegged, str(tx.tx_hash)


def burn(
    w3: Web3,
    signer_acct,
    receiver: str,
    amount: int,
    bridge_from: str,
    bridge_from_abi: str,
    token_pegged: str,
    fee_limit: int,
    fee_price: int
):
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
        'gas': 4108036,
        'gasPrice': w3.toWei(9, 'gwei')
    })
    signed = signer_acct.sign_transaction(construct_txn)
    tx_hash = w3.eth.sendRawTransaction(signed.rawTransaction)
    receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    if receipt.status != 1:
        print(receipt)
        raise TxError("Burn asset Tx execution failed")
    return receipt.blockNumber, tx_hash


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
    # 'Burns is the 6th state var defined in solitity contract
    position = b'\x05'
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
    fee_limit: int,
    fee_price: int
) -> str:
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
    # call unlock on aergo_to with the burn proof from aergo_from
    tx, result = aergo_to.call_sc(bridge_to, "unlock",
                                  args=[receiver, balance,
                                        token_origin, ap])
    if result.status != herapy.CommitStatus.TX_OK:
        raise TxError("Unlock asset Tx commit failed : {}".format(result))
    time.sleep(3)

    result = aergo_to.get_tx_result(tx.tx_hash)
    if result.status != herapy.TxResultStatus.SUCCESS:
        print(burn_proof, result)
        raise TxError("Unlock asset Tx execution failed : {}".format(result))
    return str(tx.tx_hash)


def unfreeze(
    aergo_to: herapy.Aergo,
    receiver: str,
    lock_proof: AttributeDict,
    bridge_to: str,
    fee_limit: int,
    fee_price: int
) -> str:
    """ Unlock the receiver's deposit balance on aergo_to. """
    if not is_aergo_address(receiver):
        raise InvalidArgumentsError(
            "Receiver {} must be an Aergo address".format(receiver)
        )
    ap = format_proof_for_lua(lock_proof.storageProof[0].proof)
    balance = int.from_bytes(lock_proof.storageProof[0].value, "big")
    # call unlock on aergo_to with the burn proof from aergo_from
    tx, result = aergo_to.call_sc(bridge_to, "unfreeze",
                                  args=[receiver, balance, ap])
    if result.status != herapy.CommitStatus.TX_OK:
        raise TxError("Mint asset Tx commit failed : {}".format(result))
    time.sleep(3)

    result = aergo_to.get_tx_result(tx.tx_hash)
    if result.status != herapy.TxResultStatus.SUCCESS:
        raise TxError("Mint asset Tx execution failed : {}".format(result))
    return str(tx.tx_hash)


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
    anchor_info = aergo_to.query_sc_state(bridge_to, ["_sv_Height"])
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
        bridge_to, "set_root", start_block_no=aergo_current_height
    )
    while last_merged_height_to < deposit_height:
        print("\u23F0 deposit not recorded in current anchor, waiting new "
              "anchor event... / "
              "deposit height : {} / "
              "last anchor height : {} "
              .format(deposit_height, last_merged_height_to)
              )
        set_root_event = next(stream)
        last_merged_height_to = set_root_event.arguments[0]
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
    aergo_storage_key: str
) -> Tuple[int, int]:
    # total_deposit : total latest deposit including pending
    bridge_from = Web3.toChecksumAddress(bridge_from)
    storage_value = w3.eth.getStorageAt(bridge_from, eth_trie_key, 'latest')
    total_deposit = int.from_bytes(storage_value, "big")

    # get total withdrawn and last anchor height
    withdraw_proof = hera.query_sc_state(
        bridge_to, ["_sv_Height", aergo_storage_key],
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
