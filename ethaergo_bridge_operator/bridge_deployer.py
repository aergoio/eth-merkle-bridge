import argparse
from getpass import getpass
import json

import aergo.herapy as herapy

from web3 import (
    Web3,
)
from web3.middleware import (
    geth_poa_middleware,
)

from ethaergo_wallet.eth_utils.contract_deployer import (
    deploy_contract,
)


def deploy_bridge(
    config_path: str,
    lua_bytecode_path: str,
    sol_bytecode_path: str,
    eth_net: str,
    aergo_net: str,
    aergo_erc20: str = 'aergo_erc20',
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
    with open(bridge_abi_path, "r") as f:
        bridge_abi = f.read()
    if privkey_name is None:
        privkey_name = 'proposer'
    t_anchor_aergo = \
        config_data['networks'][aergo_net]['bridges'][eth_net]['t_anchor']
    t_final_aergo = \
        config_data['networks'][aergo_net]['bridges'][eth_net]['t_final']
    t_anchor_eth = \
        config_data['networks'][eth_net]['bridges'][aergo_net]['t_anchor']
    t_final_eth = \
        config_data['networks'][eth_net]['bridges'][aergo_net]['t_final']
    unfreeze_fee = \
        config_data['networks'][aergo_net]['bridges'][eth_net]['unfreeze_fee']
    aergo_erc20_addr = \
        config_data['networks'][eth_net]['tokens'][aergo_erc20]['addr']
    print("------ DEPLOY BRIDGE BETWEEN Aergo & Ethereum -----------")

    print("------ Connect Hera and Web3 providers -----------")
    aergo = herapy.Aergo()
    aergo.connect(config_data['networks'][aergo_net]['ip'])
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
    sender_priv_key = config_data['wallet'][privkey_name]['priv_key']
    aergo.import_account(sender_priv_key, privkey_pwd)
    print("  > Sender Address Aergo: {}".format(aergo.account.address))

    keystore = config_data["wallet-eth"][privkey_name]['keystore']
    with open(keystore, "r") as f:
        encrypted_key = f.read()
    if privkey_pwd is None:
        privkey_pwd = getpass("Decrypt Ethereum keystore '{}'\nPassword: "
                              .format(privkey_name))
    privkey = w3.eth.account.decrypt(encrypted_key, privkey_pwd)
    acct = w3.eth.account.from_key(privkey)
    sender = acct.address
    print("  > Sender Address Ethereum: {}".format(sender))

    print("------ Deploy Aergo SC -----------")
    payload = herapy.utils.decode_address(lua_bytecode)
    args = \
        [aergo_erc20_addr[2:].lower(), t_anchor_aergo, t_final_aergo,
         {"_bignum": str(unfreeze_fee)}]
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
    aergo_bridge = result.contract_address

    print("------ Deploy Ethereum SC -----------")
    receipt = deploy_contract(
        sol_bytecode, bridge_abi, w3, 8000000, 20, privkey,
        t_anchor_eth, t_final_eth
    )
    eth_bridge = receipt.contractAddress

    print("  > Bridge Address Ethereum: {}".format(eth_bridge))
    print("  > Bridge Address Aergo: {}".format(aergo_bridge))

    print("------ Store bridge addresses in test_config.json  -----------")
    (config_data['networks'][eth_net]['bridges'][aergo_net]
        ['addr']) = eth_bridge
    (config_data['networks'][aergo_net]['bridges'][eth_net]
        ['addr']) = aergo_bridge

    with open(config_path, "w") as f:
        json.dump(config_data, f, indent=4, sort_keys=True)

    print("------ Disconnect AERGO -----------")
    aergo.disconnect()


if __name__ == '__main__':
    print("\n\nDEPLOY MERKLE BRIDGE")
    parser = argparse.ArgumentParser(
        description='Deploy bridge contracts between Ethereum and Aergo.')
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

    lua_bytecode_path = "contracts/lua/bridge_bytecode.txt"
    sol_bytecode_path = "contracts/solidity/bridge_bytecode.txt"

    if args.local_test:
        deploy_bridge(
            args.config_file_path, lua_bytecode_path, sol_bytecode_path,
            args.eth, args.aergo, 'aergo_erc20',
            privkey_name=args.privkey_name, privkey_pwd='1234'
        )
    else:
        deploy_bridge(
            args.config_file_path, lua_bytecode_path, sol_bytecode_path,
            args.eth, args.aergo, 'aergo_erc20', privkey_name=args.privkey_name
        )
