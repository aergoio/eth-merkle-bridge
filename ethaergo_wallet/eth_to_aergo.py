import time
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
from ethaergo_wallet.exceptions import (
    InvalidMerkleProofError,
    TxError
)
from ethaergo_wallet.eth_utils.merkle_proof import (
    verify_eth_getProof,
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
    fee_price: int
):
    """ Burn a token that was minted on ethereum. """
    bridge_from = Web3.toChecksumAddress(bridge_from)
    eth_bridge = w3.eth.contract(
        address=bridge_from,
        abi=bridge_from_abi
    )
    print(receiver, amount, erc20_address)
    construct_txn = eth_bridge.functions.lock(
        receiver, amount, erc20_address
    ).buildTransaction({
        'chainId': w3.eth.chainId,
        'from': signer_acct.address,
        'nonce': w3.eth.getTransactionCount(
            signer_acct.address
        ),
        'gas': 4108036,
        'gasPrice': w3.toWei(9, 'gwei')
    })
    signed = signer_acct.signTransaction(construct_txn)
    tx_hash = w3.eth.sendRawTransaction(signed.rawTransaction)
    receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    print(receipt)
    if receipt.status != 1:
        print(receipt)
        raise TxError("Lock asset Tx execution failed")
    events = eth_bridge.events.lockEvent().processReceipt(receipt)
    print("\nevents: ", events)
    return receipt.blockNumber, tx_hash


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
    bridge_from = Web3.toChecksumAddress(bridge_from)
    eth_bridge = w3.eth.contract(
        address=bridge_from,
        abi=bridge_from_abi
    )
    print(receiver, amount, token_pegged)
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
    signed = signer_acct.signTransaction(construct_txn)
    tx_hash = w3.eth.sendRawTransaction(signed.rawTransaction)
    receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    print(receipt)
    if receipt.status != 1:
        print(receipt)
        raise TxError("Burn asset Tx execution failed")
    events = eth_bridge.events.burnEvent().processReceipt(receipt)
    print("\nevents: ", events)
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
    bridge_from = Web3.toChecksumAddress(bridge_from)
    # check last merged height
    anchor_info = aergo_to.query_sc_state(bridge_to, ["_sv_Height",
                                                      "_sv_T_anchor"])
    last_merged_height_to = int(anchor_info.var_proofs[0].value)
    t_anchor = int(anchor_info.var_proofs[1].value)
    _, current_height = aergo_to.get_blockchain_status()
    # waite for anchor containing our transfer
    if last_merged_height_to < burn_height:
        print("waiting new anchor event...")
        stream = aergo_to.receive_event_stream(bridge_to, "set_root",
                                               start_block_no=current_height)
        while last_merged_height_to < burn_height:
            wait = last_merged_height_to + t_anchor - burn_height
            print("(estimated waiting time : {}s...)".format(wait))
            set_root_event = next(stream)
            last_merged_height_to = set_root_event.arguments[0]
        stream.stop()
    # get inclusion proof of lock in last merged block
    block = w3.eth.getBlock(last_merged_height_to)
    account_ref = (receiver + token_origin).encode('utf-8')
    # 'Burns is the 6th state var defined in solitity contract
    position = b'\x05'
    print(account_ref.rjust(32, b'\0') + position.rjust(32, b'\0'))
    trie_key = keccak(account_ref + position.rjust(32, b'\0'))
    eth_proof = w3.eth.getProof(bridge_from, [trie_key], last_merged_height_to)
    if not verify_eth_getProof(eth_proof, block.stateRoot):
        raise InvalidMerkleProofError("Unable to verify Lock proof")
    if trie_key != eth_proof.storageProof[0].key:
        raise InvalidMerkleProofError("Proof doesnt match requested key")
    if len(eth_proof.storageProof[0].value) == 0:
        raise InvalidMerkleProofError("User never deposited tokens")
    return eth_proof


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
    ap = format_proof_for_lua(burn_proof.storageProof[0].proof)
    balance = int.from_bytes(burn_proof.storageProof[0].value, "big")
    print(balance, burn_proof.storageProof[0].value, ap)
    # call unlock on aergo_to with the burn proof from aergo_from
    tx, result = aergo_to.call_sc(bridge_to, "unlock",
                                  args=[receiver, balance,
                                        token_origin, ap])
    if result.status != herapy.CommitStatus.TX_OK:
        raise TxError("Unlock asset Tx commit failed : {}".format(result))
    time.sleep(3)

    result = aergo_to.get_tx_result(tx.tx_hash)
    if result.status != herapy.TxResultStatus.SUCCESS:
        raise TxError("Unlock asset Tx execution failed : {}".format(result))
    return str(tx.tx_hash)
