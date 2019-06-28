from getpass import getpass
import json
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
    bytecode: str,
    abi: str,
    abi_path,
    network_name: str,
    token_name: str,
    privkey_pwd: str = None
):
    """ Deploys an Aergo ERC20 token for testing purposes"""

    print("------ Connect Web3 -----------")
    ip = config_data['networks'][network_name]['ip']
    w3 = Web3(Web3.HTTPProvider("http://" + ip))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    assert w3.isConnected()

    print("------ Set Sender Account -----------")
    privkey_name = 'default'
    keystore = config_data["wallet-eth"][privkey_name]['keystore']
    with open("./keystore/" + keystore, "r") as f:
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
    with open("./config.json", "w") as f:
        json.dump(config_data, f, indent=4, sort_keys=True)


if __name__ == '__main__':
    with open("./config.json", "r") as f:
        config_data = json.load(f)
    with open("./contracts/solidity/aergo_erc20_bytecode.txt", "r") as f:
        bytecode = f.read()
    abi_path = "./contracts/solidity/aergo_erc20_abi.txt"
    with open(abi_path, "r") as f:
        abi = f.read()

    deploy_aergo_erc20(config_data, bytecode, abi, abi_path, 'eth-poa-local',
                       'aergo_erc20', '1234')
