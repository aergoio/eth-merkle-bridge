from getpass import getpass
import json
import time

from typing import (
    Dict,
)

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

COMMIT_TIME = 3


def run(
    config_data: Dict,
    lua_bytecode: str,
    sol_bytecode: str,
    sol_abi: str,
    t_anchor_eth: int,
    t_anchor_aergo: int,
    t_final_eth: int,
    eth_net: str,
    aergo_net: str,
    aergo_erc20,
    path: str = "./config.json",
    privkey_name: str = None,
) -> None:
    if privkey_name is None:
        privkey_name = 'proposer'
    print("------ DEPLOY BRIDGE BETWEEN Aergo & Ethereum -----------")

    print("------ Connect AERGO -----------")
    aergo = herapy.Aergo()
    aergo.connect(config_data[aergo_net]['ip'])
    print("------ Connect Web3 -----------")
    ip = config_data[eth_net]['ip']
    w3 = Web3(Web3.HTTPProvider("http://" + ip))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    assert w3.isConnected()

    status = aergo.get_status()
    height = status.best_block_height
    lib = status.consensus_info.status['LibNo']
    # aergo finalization time
    t_final_aergo = height - lib
    print("aergo finality: ", t_final_aergo)
    print("ethereum finality: ", t_final_eth)

    print("------ Set Sender Account -----------")
    privkey_pwd = getpass("Decrypt Aergo private key '{}'\nPassword: "
                          .format(privkey_name))
    sender_priv_key = config_data['wallet'][privkey_name]['priv_key']
    aergo.import_account(sender_priv_key, privkey_pwd)
    print("  > Sender Address Aergo: {}".format(aergo.account.address))

    keystore = config_data["wallet-eth"][privkey_name]['keystore']
    with open("./keystore/" + keystore, "r") as f:
        encrypted_key = f.read()
    privkey_pwd = getpass("Decrypt Ethereum keystore '{}'\nPassword: "
                          .format(privkey_name))
    privkey = w3.eth.account.decrypt(encrypted_key, privkey_pwd)
    acct = w3.eth.account.privateKeyToAccount(privkey)
    sender = acct.address
    print("  > Sender Address Ethereum: {}".format(sender))

    # get validators from config file
    aergo_validators = []
    eth_validators = []
    for validator in config_data['validators']:
        eth_validators.append(Web3.toChecksumAddress(validator['eth-addr']))
        aergo_validators.append(validator['addr'])
    print('aergo validators : ', aergo_validators)
    print('ethereum validators : ', eth_validators)

    print("------ Deploy Aergo SC -----------")
    payload = herapy.utils.decode_address(lua_bytecode)
    aergo_erc20 = config_data[eth_net]['tokens'][aergo_erc20]
    tx, result = aergo.deploy_sc(amount=0,
                                 payload=payload,
                                 args=[aergo_erc20,
                                       aergo_validators,
                                       t_anchor_aergo,
                                       t_final_eth])
    if result.status != herapy.CommitStatus.TX_OK:
        print("    > ERROR[{0}]: {1}"
              .format(result.status, result.detail))
        aergo.disconnect()
        return
    print("    > result[{0}] : {1}"
          .format(result.tx_id, result.status.name))

    time.sleep(COMMIT_TIME)

    result = aergo.get_tx_result(tx.tx_hash)
    if result.status != herapy.TxResultStatus.CREATED:
        print("  > ERROR[{0}]:{1}: {2}"
              .format(result.contract_address, result.status,
                      result.detail))
        aergo.disconnect()
        return

    print("------ Deploy Ethereum SC -----------")
    receipt = deploy_contract(
        sol_bytecode, sol_abi, w3, 6700000, 20, privkey,
        eth_validators,
        t_anchor_eth, t_final_aergo
    )
    bridge_contract = w3.eth.contract(
        address=receipt.contractAddress,
        abi=sol_abi
    )
    eth_id = bridge_contract.functions.ContractID().call().hex()

    eth_address = receipt.contractAddress
    aergo_address = result.contract_address
    aergo_id = result.detail[1:-1]

    print("  > SC Address Ethereum: {}".format(eth_address))
    print("  > SC Address Aergo: {}".format(aergo_address))

    print("------ Store bridge addresses in config.json  -----------")
    config_data[eth_net]['bridges'][aergo_net] = {}
    config_data[aergo_net]['bridges'][eth_net] = {}
    config_data[eth_net]['bridges'][aergo_net]['addr'] = eth_address
    config_data[aergo_net]['bridges'][eth_net]['addr'] = aergo_address
    config_data[eth_net]['bridges'][aergo_net]['id'] = eth_id
    config_data[aergo_net]['bridges'][eth_net]['id'] = aergo_id
    config_data[eth_net]['bridges'][aergo_net]['t_anchor'] = t_anchor_eth
    config_data[eth_net]['bridges'][aergo_net]['t_final'] = t_final_aergo
    config_data[aergo_net]['bridges'][eth_net]['t_anchor'] = t_anchor_aergo
    config_data[aergo_net]['bridges'][eth_net]['t_final'] = t_final_eth
    try:
        config_data[eth_net]['tokens']['aergo']
    except KeyError:
        pass
    else:
        # this is a new bridge, so remove any old pegged aergo with same name
        # bridge
        config_data[eth_net]['tokens']['aergo']['pegs'] = {}

    with open(path, "w") as f:
        json.dump(config_data, f, indent=4, sort_keys=True)

    print("------ Disconnect AERGO -----------")
    aergo.disconnect()


if __name__ == '__main__':
    with open("./config.json", "r") as f:
        config_data = json.load(f)
    with open("./contracts/lua/bridge_bytecode.txt", "r") as f:
        lua_bytecode = f.read()[:-1]
    with open("./contracts/solidity/bridge_bytecode.txt", "r") as f:
        sol_bytecode = f.read()
    with open("./contracts/solidity/bridge_abi.txt", "r") as f:
        sol_abi = f.read()
    # NOTE t_final is the minimum time to get lib : only informative (not
    # actually used in code except for Eth bridge because Eth doesn't have LIB)
    t_anchor_eth = 25  # aergo anchoring periord on ethereum
    t_anchor_aergo = 10  # ethereum anchoring periord on aergo
    t_final_eth = 10  # time after which ethereum is considered finalized
    run(
        config_data, lua_bytecode, sol_bytecode, sol_abi, t_anchor_eth,
        t_anchor_aergo, t_final_eth, 'eth-poa-local', 'aergo-local',
        'test_erc20'
    )
