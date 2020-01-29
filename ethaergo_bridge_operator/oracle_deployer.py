import argparse
from getpass import getpass
import hashlib
import json

import aergo.herapy as herapy

from aergo.herapy.utils.encoding import (
    decode_address,
)

from web3 import (
    Web3,
)
from web3.middleware import (
    geth_poa_middleware,
)

from ethaergo_wallet.eth_utils.contract_deployer import (
    deploy_contract,
)


def deploy_oracle(
    config_path: str,
    lua_bytecode_path: str,
    sol_bytecode_path: str,
    eth_net: str,
    aergo_net: str,
    privkey_name: str = None,
    privkey_pwd: str = None,
) -> None:
    """ Deploy brige contract on Aergo and Ethereum."""

    with open(config_path, "r") as f:
        config_data = json.load(f)
    with open(lua_bytecode_path, "r") as f:
        lua_bytecode = f.read()[:-1]
    with open(sol_bytecode_path, "r") as f:
        sol_bytecode = f.read()
    bridge_abi_path = \
        config_data['networks'][eth_net]['bridges'][aergo_net]['bridge_abi']
    oracle_abi_path = \
        config_data['networks'][eth_net]['bridges'][aergo_net]['oracle_abi']
    bridge_eth_addr = \
        config_data['networks'][eth_net]['bridges'][aergo_net]['addr']
    bridge_aergo_addr = \
        config_data['networks'][aergo_net]['bridges'][eth_net]['addr']
    t_anchor_aergo = \
        config_data['networks'][aergo_net]['bridges'][eth_net]['t_anchor']
    t_final_aergo = \
        config_data['networks'][aergo_net]['bridges'][eth_net]['t_final']
    t_anchor_eth = \
        config_data['networks'][eth_net]['bridges'][aergo_net]['t_anchor']
    t_final_eth = \
        config_data['networks'][eth_net]['bridges'][aergo_net]['t_final']
    bridge_aergo_trie_key = \
        hashlib.sha256(decode_address(bridge_aergo_addr)).digest()
    print("bridge key aergo: 0x{}".format(bridge_aergo_trie_key.hex()))
    # bridge_eth_address is used instead of bridge_eth_trie_key because
    # crypto.verifyProof() already hashes the key
    # bridge_eth_trie_key = \
    #    "0x" + keccak(bytes.fromhex(bridge_eth_addr[2:])).hex()
    # print("bridge key eth: ", bridge_eth_trie_key)
    with open(bridge_abi_path, "r") as f:
        bridge_abi = f.read()
    with open(oracle_abi_path, "r") as f:
        oracle_abi = f.read()
    if privkey_name is None:
        privkey_name = 'proposer'
    # get validators from config file
    aergo_validators = []
    eth_validators = []
    for validator in config_data['validators']:
        eth_validators.append(Web3.toChecksumAddress(validator['eth-addr']))
        aergo_validators.append(validator['addr'])
    print('aergo validators : ', aergo_validators)
    print('ethereum validators : ', eth_validators)

    print("------ DEPLOY ORACLE BETWEEN Aergo & Ethereum -----------")

    print("------ Connect AERGO -----------")
    aergo = herapy.Aergo()
    aergo.connect(config_data['networks'][aergo_net]['ip'])
    print("------ Connect Web3 -----------")
    ip = config_data['networks'][eth_net]['ip']
    w3 = Web3(Web3.HTTPProvider(ip))
    eth_poa = config_data['networks'][eth_net]['isPOA']
    if eth_poa:
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    assert w3.isConnected()

    print("------ Set Sender Account -----------")
    if privkey_pwd is None:
        privkey_pwd = getpass("Decrypt Aergo private key '{}'\nPassword: "
                              .format(privkey_name))

    keystore_path = config_data['wallet'][privkey_name]['keystore']
    with open(keystore_path, "r") as f:
        keystore = f.read()
    aergo.import_account_from_keystore(keystore, privkey_pwd)
    print("  > Sender Address Aergo: {}".format(aergo.account.address))

    keystore_path = config_data["wallet-eth"][privkey_name]['keystore']
    with open(keystore_path, "r") as f:
        keystore = f.read()
    if privkey_pwd is None:
        privkey_pwd = getpass("Decrypt Ethereum keystore '{}'\nPassword: "
                              .format(privkey_name))
    privkey = w3.eth.account.decrypt(keystore, privkey_pwd)
    acct = w3.eth.account.from_key(privkey)
    sender = acct.address
    print("  > Sender Address Ethereum: {}".format(sender))

    print("------ Deploy Aergo SC -----------")
    payload = herapy.utils.decode_address(lua_bytecode)
    args = [aergo_validators, bridge_aergo_addr, bridge_eth_addr,
            t_anchor_aergo, t_final_aergo]
    tx, result = aergo.deploy_sc(amount=0,
                                 payload=payload,
                                 args=args)
    if result.status != herapy.CommitStatus.TX_OK:
        print("    > ERROR[{0}]: {1}"
              .format(result.status, result.detail))
        aergo.disconnect()
        return
    print("    > result[{0}] : {1}"
          .format(result.tx_id, result.status.name))

    result = aergo.wait_tx_result(tx.tx_hash)
    if result.status != herapy.TxResultStatus.CREATED:
        print("  > ERROR[{0}]:{1}: {2}"
              .format(result.contract_address, result.status,
                      result.detail))
        aergo.disconnect()
        return
    aergo_oracle = result.contract_address

    print("------ Deploy Ethereum SC -----------")
    receipt = deploy_contract(
        sol_bytecode, oracle_abi, w3, 8000000, 20, privkey,
        eth_validators, bridge_eth_addr, bridge_aergo_trie_key, t_anchor_eth,
        t_final_eth
    )
    eth_oracle = receipt.contractAddress

    print("  > Oracle Address Ethereum: {}".format(eth_oracle))
    print("  > Oracle Address Aergo: {}".format(aergo_oracle))

    print("------ Store bridge addresses in test_config.json  -----------")
    (config_data['networks'][eth_net]['bridges'][aergo_net]
        ['oracle']) = eth_oracle
    (config_data['networks'][aergo_net]['bridges'][eth_net]
        ['oracle']) = aergo_oracle

    with open(config_path, "w") as f:
        json.dump(config_data, f, indent=4, sort_keys=True)

    print("------ Transfer bridge control to oracles -----------")
    tx, result = aergo.call_sc(
        bridge_aergo_addr, "oracleUpdate", args=[aergo_oracle], amount=0
    )
    if result.status != herapy.CommitStatus.TX_OK:
        print("oracleUpdate Tx commit failed : {}".format(result))

    # Check oracle transfer success
    result = aergo.wait_tx_result(tx.tx_hash)
    if result.status != herapy.TxResultStatus.SUCCESS:
        print("oracleUpdate Tx execution failed : {}".format(result))

    eth_bridge = w3.eth.contract(
        address=bridge_eth_addr,
        abi=bridge_abi
    )
    next_nonce = w3.eth.getTransactionCount(acct.address)
    construct_txn = eth_bridge.functions.oracleUpdate(
        eth_oracle
    ).buildTransaction({
        'chainId': w3.eth.chainId,
        'from': acct.address,
        'nonce': next_nonce,
        'gas': 50000,
        'gasPrice': w3.toWei(2, 'gwei')
    })
    signed = acct.sign_transaction(construct_txn)
    tx_hash = w3.eth.sendRawTransaction(signed.rawTransaction)
    receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    if receipt.status != 1:
        print("Oracle update execution failed: {}".format(receipt))

    print("------ Disconnect AERGO -----------")
    aergo.disconnect()


if __name__ == '__main__':
    print("\n\nDEPLOY ORACLE")
    parser = argparse.ArgumentParser(
        description='Deploy oracle contracts to controle the bridge between '
                    'Ethereum and Aergo.')
    # Add arguments
    parser.add_argument(
        '-c', '--config_file_path', type=str, help='Path to config.json',
        required=True)
    parser.add_argument(
        '-a', '--aergo', type=str, required=True,
        help='Name of Aergo network in config file')
    parser.add_argument(
        '-e', '--eth', type=str, required=True,
        help='Name of Ethereum network in config file')
    parser.add_argument(
        '--privkey_name', type=str, help='Name of account in config file '
        'to sign anchors', required=False)
    parser.add_argument(
        '--local_test', dest='local_test', action='store_true',
        help='Start proposer with password for testing')
    parser.set_defaults(local_test=False)

    args = parser.parse_args()

    lua_bytecode_path = "contracts/lua/oracle_bytecode.txt"
    sol_bytecode_path = "contracts/solidity/oracle_bytecode.txt"

    if args.local_test:
        deploy_oracle(
            args.config_file_path, lua_bytecode_path, sol_bytecode_path,
            args.eth, args.aergo, privkey_name=args.privkey_name,
            privkey_pwd='1234'
        )
    else:
        deploy_oracle(
            args.config_file_path, lua_bytecode_path, sol_bytecode_path,
            args.eth, args.aergo, privkey_name=args.privkey_name
        )
