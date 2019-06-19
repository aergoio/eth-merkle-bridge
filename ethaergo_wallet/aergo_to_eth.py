import time
from typing import (
    Tuple,
)
from web3 import (
    Web3,
)
import aergo.herapy as herapy
from wallet.exceptions import (
    InvalidMerkleProofError,
    TxError
)
COMMIT_TIME = 3


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
    account_ref = receiver[2:].lower() + token_origin
    trie_key = "_sv_Locks-" + account_ref
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
    fee_limit: int,
    fee_price: int
) -> Tuple[str, str]:
    """ Mint the receiver's deposit balance on aergo_to. """
    receiver = Web3.toChecksumAddress(receiver)
    print("version:", w3.clientVersion)
    balance = int(lock_proof.var_proofs[0].value.decode('utf-8')[1:-1])
    ap = lock_proof.var_proofs[0].auditPath
    print("ap: ", [item.hex() for item in ap])
    bitmap = lock_proof.var_proofs[0].bitmap
    print("bitmap: ", bitmap.hex())
    leaf_height = lock_proof.var_proofs[0].height
    # call mint on ethereum with the lock proof from aergo_from
    eth_bridge = w3.eth.contract(
        address=bridge_to,
        abi=bridge_to_abi
    )
    print(eth_bridge)
    print(receiver, balance, token_origin, ap, bitmap, leaf_height)
    construct_txn = eth_bridge.functions.mint(
        receiver, balance, token_origin, ap, bitmap, leaf_height
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
    events = eth_bridge.events.mintEvent().processReceipt(receipt)
    print("\nevents: ", events)
    token_pegged = events[0]['args']['token_address']

    return token_pegged, tx_hash


def burn(
    aergo_from: herapy.Aergo,
    bridge_from: str,
    receiver: str,
    value: int,
    token_pegged: str,
    fee_limit: int,
    fee_price: int,
) -> Tuple[int, str]:
    """ Burn a minted token on a sidechain. """
    args = (receiver[2:].lower(), str(value), token_pegged)
    tx, result = aergo_from.call_sc(bridge_from, "burn", args=args)

    if result.status != herapy.CommitStatus.TX_OK:
        raise TxError("Burn asset Tx commit failed : {}".format(result))
    time.sleep(COMMIT_TIME)

    # Check burn success
    result = aergo_from.get_tx_result(tx.tx_hash)
    if result.status != herapy.TxResultStatus.SUCCESS:
        raise TxError("Burn asset Tx execution failed : {}".format(result))
    # get precise burn height
    tx_detail = aergo_from.get_tx(tx.tx_hash)
    burn_height = tx_detail.block.height
    return burn_height, str(tx.tx_hash)


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
    account_ref = receiver[2:].lower() + token_origin[2:].lower()
    trie_key = "_sv_Burns-" + account_ref
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
    fee_limit: int,
    fee_price: int
) -> Tuple[str, str]:
    """ Unlock the receiver's burnt balance on aergo_to. """
    receiver = Web3.toChecksumAddress(receiver)
    print("version:", w3.clientVersion)
    balance = int(burn_proof.var_proofs[0].value.decode('utf-8')[1:-1])
    ap = burn_proof.var_proofs[0].auditPath
    print("ap: ", [item.hex() for item in ap])
    bitmap = burn_proof.var_proofs[0].bitmap
    print("bitmap: ", bitmap.hex())
    leaf_height = burn_proof.var_proofs[0].height
    # call mint on ethereum with the lock proof from aergo_from
    eth_bridge = w3.eth.contract(
        address=bridge_to,
        abi=bridge_to_abi
    )
    print(eth_bridge)
    print(receiver, balance, token_origin, ap, bitmap, leaf_height)
    construct_txn = eth_bridge.functions.unlock(
        receiver, balance, token_origin, ap, bitmap, leaf_height
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
    events = eth_bridge.events.unlockEvent().processReceipt(receipt)
    print("\nevents: ", events)
    return tx_hash


def freeze(
    aergo_from: herapy.Aergo,
    bridge_from: str,
    receiver: str,
    value: int,
    fee_limit: int,
    fee_price: int,
) -> Tuple[int, str]:
    """ Freeze aergo native """
    print('receiver:', receiver)
    args = (receiver[2:].lower(), str(value))
    tx, result = aergo_from.call_sc(
        bridge_from, "freeze", amount=value, args=args
    )

    if result.status != herapy.CommitStatus.TX_OK:
        raise TxError("Burn asset Tx commit failed : {}".format(result))
    time.sleep(COMMIT_TIME)

    # Check freeze success
    result = aergo_from.get_tx_result(tx.tx_hash)
    if result.status != herapy.TxResultStatus.SUCCESS:
        raise TxError("Freeze Aer Tx execution failed : {}".format(result))
    # get precise burn height
    tx_detail = aergo_from.get_tx(tx.tx_hash)
    freeze_height = tx_detail.block.height
    return freeze_height, str(tx.tx_hash)


def _build_deposit_proof(
    aergo_from: herapy.Aergo,
    w3: Web3,
    bridge_from: str,
    bridge_to: str,
    bridge_to_abi: str,
    lock_height: int,
    trie_key: str,
):
    """ Check the last anchored root includes the deposit and build
    a deposit proof for that root
    """
    # check last merged height
    eth_bridge = w3.eth.contract(
        address=bridge_to,
        abi=bridge_to_abi
    )
    last_merged_height_to = eth_bridge.functions.Height().call()
    # waite for anchor containing our transfer
    if last_merged_height_to < lock_height:
        print("deposit not recorded in current anchor, waiting new anchor "
              "event... / "
              "deposit height : {} / "
              "last anchor height : {} / "
              .format(lock_height, last_merged_height_to)
              )
        while last_merged_height_to < lock_height:
            time.sleep(1)
            last_merged_height_to = eth_bridge.functions.Height().call()
    # get inclusion proof of lock in last merged block
    print("Root: ", eth_bridge.functions.Root().call().hex())
    merge_block_from = aergo_from.get_block(block_height=last_merged_height_to)
    # TODO store real bytes
    proof = aergo_from.query_sc_state(
        bridge_from, [trie_key],
        root=merge_block_from.blocks_root_hash, compressed=True
    )
    if not proof.verify_proof(merge_block_from.blocks_root_hash):
        raise InvalidMerkleProofError("Unable to verify deposit proof",
                                      proof)
    if not proof.var_proofs[0].inclusion:
        raise InvalidMerkleProofError("Trie key {} doesn't exist"
                                      .format(trie_key))
    return proof
