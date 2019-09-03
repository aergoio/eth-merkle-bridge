from getpass import getpass
import json
import os
from typing import (
    Dict,
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


def deploy_aergo_erc20(
    config_data: Dict,
    config_path: str,
    bytecode: str,
    abi: str,
    abi_path,
    network_name: str,
    token_name: str,
    privkey_name: str = 'default',
    privkey_pwd: str = None
):
    """ Deploys an Aergo ERC20 token for testing purposes"""

    print("------ Connect Web3 -----------")
    ip = config_data['networks'][network_name]['ip']
    w3 = Web3(Web3.HTTPProvider(ip))
    eth_poa = config_data['networks'][network_name]['isPOA']
    if eth_poa:
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    assert w3.isConnected()

    print("------ Set Sender Account -----------")
    keystore = config_data["wallet-eth"][privkey_name]['keystore']
    file_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    root_path = os.path.dirname(file_path) + '/'
    with open(root_path + keystore, "r") as f:
        encrypted_key = f.read()
    if privkey_pwd is None:
        privkey_pwd = getpass("Decrypt Ethereum keystore '{}'\nPassword: "
                              .format(privkey_name))
    privkey = w3.eth.account.decrypt(encrypted_key, privkey_pwd)
    acct = w3.eth.account.from_key(privkey)
    sender = acct.address
    print("  > Sender Address: {}".format(sender))

    receipt = deploy_contract(bytecode, abi, w3, 1821490, 20, privkey)
    sc_address = receipt.contractAddress
    print("Deployed token address: ", sc_address)

    print("------ Store address in config.json -----------")
    config_data['networks'][network_name]['tokens'][token_name] = {}
    (config_data['networks'][network_name]['tokens'][token_name]
        ['addr']) = sc_address
    (config_data['networks'][network_name]['tokens'][token_name]
        ['pegs']) = {}
    (config_data['networks'][network_name]['tokens'][token_name]['pegs']
        ['aergo-local']) = 'aergo'
    (config_data['networks'][network_name]['tokens'][token_name]
        ['abi']) = abi_path
    with open(config_path, "w") as f:
        json.dump(config_data, f, indent=4, sort_keys=True)


if __name__ == '__main__':
    with open("./test_config.json", "r") as f:
        config_data = json.load(f)
    with open("./contracts/solidity/test_aergo_erc20_bytecode.txt", "r") as f:
        bytecode = f.read()
    abi_path = "contracts/solidity/aergo_erc20_abi.txt"
    with open(abi_path, "r") as f:
        abi = f.read()

    deploy_aergo_erc20(config_data, "./test_config.json", bytecode, abi,
                       abi_path, 'eth-poa-local', 'aergo_erc20', 'default',
                       '1234')
