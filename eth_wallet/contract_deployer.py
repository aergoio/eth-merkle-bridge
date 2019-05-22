from getpass import getpass
import json

from web3 import (
    Web3,
)
from web3.middleware import (
    geth_poa_middleware,
)


def deploy_contract(
    bytecode: str,
    abi: str,
    w3: Web3,
    gas_limit: int,
    gas_price: int,
    privkey: bytes,
    *args,
):
    contract_ = w3.eth.contract(
        abi=abi,
        bytecode=bytecode)

    acct = w3.eth.account.privateKeyToAccount(privkey)

    construct_txn = contract_.constructor(*args).buildTransaction({
        'chainId': w3.eth.chainId,
        'from': acct.address,
        'nonce': w3.eth.getTransactionCount(acct.address),
        'gas': gas_limit,
        'gasPrice': w3.toWei(gas_price, 'gwei')})

    signed = acct.signTransaction(construct_txn)

    tx_hash = w3.eth.sendRawTransaction(signed.rawTransaction)
    receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    assert receipt.status == 1, "Deployment failed"
    return receipt


if __name__ == '__main__':
    with open("./config.json", "r") as f:
        config_data = json.load(f)
    with open("./contracts/aergo_token_bytecode.txt", "r") as f:
        bytecode = f.read()
    with open("./contracts/aergo_token_abi.txt", "r") as f:
        abi = f.read()

    print("------ Connect Web3 -----------")
    ip = config_data['eth-poa-local']['ip']
    w3 = Web3(Web3.HTTPProvider("http://" + ip))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    assert w3.isConnected()

    print("------ Set Sender Account -----------")
    privkey_name = 'default'
    keystore = config_data["wallet-eth"][privkey_name]['keystore']
    with open("./keystore/" + keystore, "r") as f:
        encrypted_key = f.read()
    privkey_pwd = getpass("Decrypt Ethereum keystore '{}'\nPassword: "
                          .format(privkey_name))
    privkey = w3.eth.account.decrypt(encrypted_key, privkey_pwd)
    acct = w3.eth.account.privateKeyToAccount(privkey)
    sender = acct.address
    print("  > Sender Address: {}".format(sender))

    receipt = deploy_contract(bytecode, abi, w3, 1821490, 20, privkey)
    sc_address = receipt.contractAddress
    print("Deployed token address: ", sc_address)

    print("------ Store address in config.json -----------")
    config_data['eth-poa-local']['tokens']['test_erc20'] = {}
    config_data['eth-poa-local']['tokens']['test_erc20']['addr'] = sc_address
    config_data['eth-poa-local']['tokens']['test_erc20']['pegs'] = {}
    with open("./config.json", "w") as f:
        json.dump(config_data, f, indent=4, sort_keys=True)
