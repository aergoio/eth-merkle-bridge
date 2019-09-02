import argparse
import hashlib

import aergo.herapy as herapy

from ethaergo_wallet.wallet import EthAergoWallet
import ethaergo_wallet.eth_utils.erc20 as eth_u
import ethaergo_wallet.eth_to_aergo as eth_to_aergo
import ethaergo_wallet.aergo_to_eth as aergo_to_eth
from aergo_wallet.exceptions import (
    TxError,
)


def get_aergo_address(privkey: bytes) -> str:
    hera = herapy.Aergo()
    hera.new_account(private_key=privkey, skip_state=True)
    return hera.account.address.__str__()


def get_random_eth_address(i: int) -> str:
    return '0x' + \
        hashlib.sha256(i.to_bytes(3, byteorder='big')).digest().hex()[:40]


def run(start_index: int, batch_count: int, service_key: str):
    config_path = './test_config.json'
    abi_path = "contracts/solidity/aergo_erc20_abi.txt"
    with open(abi_path, "r") as f:
        erc20_abi = f.read()
    bridge_abi_path = "contracts/solidity/bridge_abi.txt"
    with open(bridge_abi_path, "r") as f:
        bridge_abi = f.read()
    # EthAergoWallet is only used to access some util functions, transfers
    # are made using the lib functions.
    ethaergo_wallet = EthAergoWallet(config_path)
    w3 = ethaergo_wallet.get_web3('eth-poa-local')
    hera = ethaergo_wallet.get_aergo('aergo-local', service_key, '1234')
    eth_bridge = ethaergo_wallet.get_bridge_contract_address(
        'eth-poa-local', 'aergo-local')
    aergo_bridge = ethaergo_wallet.get_bridge_contract_address(
        'aergo-local', 'eth-poa-local')
    erc20_address = ethaergo_wallet.get_asset_address(
        'aergo_erc20', 'eth-poa-local')
    amount = 10*10**18

    aergo_addrs = []
    # create receiver addresses
    for i in range(start_index, start_index + batch_count):
        privkey = i.to_bytes(32, byteorder='big')
        receiver = get_aergo_address(privkey)
        aergo_addrs.append(receiver)

    print("Lock Batch")
    # The service_key privkey will send amount to batch_count nb of
    # different address across the bridge.
    # Locks mapping will contain batch_count nb of new entries.
    signer_acct = ethaergo_wallet.get_signer(w3, service_key, '1234')
    next_nonce, _ = eth_u.increase_approval(
        eth_bridge, erc20_address, amount*batch_count, w3, erc20_abi,
        signer_acct
    )
    for i, receiver in enumerate(aergo_addrs):
        lock_height, _ = eth_to_aergo.lock(
            w3, signer_acct, receiver, amount, eth_bridge, bridge_abi,
            erc20_address, 0, 0, next_nonce
        )
        next_nonce += 1
        print(i)

    print("Unfreeze Batch")
    # The service_key privkey will unfreeze balances of batch_count nb of
    # different addresses
    # Unfreezes mapping will contain batch_count nb of new entries.
    for i, receiver in enumerate(aergo_addrs):
        while True:
            # retry because unfreeze can fail if a new anchor came right after
            # the merkle proof was queried
            print(i)
            lock_proof = eth_to_aergo.build_lock_proof(
                w3, hera, receiver, eth_bridge, aergo_bridge, lock_height,
                erc20_address
            )
            try:
                eth_to_aergo.unfreeze(
                    hera, receiver, lock_proof, aergo_bridge, 0, 0
                )
            except TxError:
                continue
            except ValueError:
                break
            break

    print("Freeze Batch")
    # Each privkey that received unfreezed aergo will freeze amount/10
    # and send it to batch_count nb of different addresses
    # Burns mapping will contain batch_count nb of new entries.
    amount = 10**18
    eth_addrs = []
    for i in range(start_index, start_index + batch_count):
        privkey = i.to_bytes(32, byteorder='big')
        receiver = get_random_eth_address(start_index + i)
        eth_addrs.append(receiver)
        hera.new_account(private_key=privkey, skip_state=False)
        freeze_height, _ = aergo_to_eth.freeze(
            hera, aergo_bridge, receiver, amount, 0, 0
        )
        print(i)

    print("Unlock Batch")
    # The service_key privkey will unlock balances of batch_count nb of
    # different addresses
    # Unlocks mapping will contain batch_count nb of new entries.
    for i, receiver in enumerate(eth_addrs):
        while True:
            # retry because unlock can fail if a new anchor came right after
            # the merkle proof was queried
            print(i)
            burn_proof = aergo_to_eth.build_burn_proof(
                hera, w3, receiver, aergo_bridge, eth_bridge, bridge_abi,
                freeze_height, erc20_address
            )
            try:
                aergo_to_eth.unlock(
                    w3, signer_acct, receiver, burn_proof, erc20_address,
                    eth_bridge, bridge_abi, 0, 0
                )
            except TxError:
                continue
            except ValueError:
                break
            break


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Gas analysis with growing state storage')
    parser.add_argument(
        '--start_index', type=int, help='privkey start index',
        required=True)
    parser.add_argument(
        '--qty', type=int, help='nb of new users',
        required=True)
    parser.add_argument(
        '--service', type=str, help='privkey name of unfreezing service',
        required=True)
    args = parser.parse_args()
    run(args.start_index, args.qty, args.service)
