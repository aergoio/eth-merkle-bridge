import json
from wallet.wallet import Wallet
from ethaergo_wallet.wallet import EthAergoWallet
from ethaergo_wallet.eth_utils.contract_deployer import (
    deploy_contract,
)
from web3 import (
    Web3,
)
from web3.middleware import (
    geth_poa_middleware,
)

import pytest


@pytest.fixture(scope="session")
def aergo_wallet():
    wallet = Wallet("./config.json")
    # deploy test token
    total_supply = 500*10**6*10**18
    with open("./contracts/lua/std_token_bytecode.txt", "r") as f:
        payload_str = f.read()[:-1]
    wallet.deploy_token(
        payload_str, "token1", total_supply, "aergo-local", privkey_pwd='1234'
    )
    balance, _ = wallet.get_balance('token1', 'aergo-local')
    return wallet


@pytest.fixture(scope="session")
def bridge_wallet(aergo_wallet):
    # deploy test token
    with open("./config.json", "r") as f:
        config_data = json.load(f)
    with open("./contracts/solidity/aergo_erc20_bytecode.txt", "r") as f:
        bytecode = f.read()
    with open("./contracts/solidity/aergo_erc20_abi.txt", "r") as f:
        abi = f.read()
    ip = config_data['networks']['eth-poa-local']['ip']
    w3 = Web3(Web3.HTTPProvider("http://" + ip))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    assert w3.isConnected()
    privkey_name = 'default'
    keystore = config_data["wallet-eth"][privkey_name]['keystore']
    with open("./keystore/" + keystore, "r") as f:
        encrypted_key = f.read()
    privkey = w3.eth.account.decrypt(encrypted_key, '1234')
    receipt = deploy_contract(bytecode, abi, w3, 1821490, 20, privkey)
    sc_address = receipt.contractAddress
    config_data['networks']['eth-poa-local']['tokens']['test_erc20'] = {}
    config_data['networks']['eth-poa-local']['tokens']['test_erc20']['addr'] = sc_address
    config_data['networks']['eth-poa-local']['tokens']['test_erc20']['pegs'] = {}
    with open("./config.json", "w") as f:
        json.dump(config_data, f, indent=4, sort_keys=True)
    wallet = EthAergoWallet("./config.json")
    return wallet
