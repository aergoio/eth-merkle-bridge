import json
import time

import aergo.herapy as herapy

from web3 import (
    Web3,
)
from web3.middleware import (
    geth_poa_middleware,
)

from ethaergo_bridge_operator.op_utils import (
    query_aergo_tempo,
    query_aergo_validators,
    query_unfreeze_fee,
    query_eth_tempo,
    query_eth_validators,
    query_aergo_oracle,
)


def test_eth_tempo_update(bridge_wallet):
    ip = bridge_wallet.config_data('networks', 'eth-poa-local', 'ip')
    w3 = Web3(Web3.HTTPProvider(ip))
    eth_poa = bridge_wallet.config_data('networks', 'eth-poa-local', 'isPOA')
    if eth_poa:
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    assert w3.isConnected()

    with open("./contracts/solidity/bridge_abi.txt", "r") as f:
        bridge_abi = f.read()
    with open("./contracts/solidity/oracle_abi.txt", "r") as f:
        oracle_abi = f.read()

    t_anchor_before = bridge_wallet.config_data(
        'networks', 'eth-poa-local', 'bridges', 'aergo-local', 't_anchor'
    )
    t_final_before = bridge_wallet.config_data(
        'networks', 'eth-poa-local', 'bridges', 'aergo-local', 't_final'
    )
    eth_bridge_addr = bridge_wallet.config_data(
        'networks', 'eth-poa-local', 'bridges', 'aergo-local', 'addr')
    eth_oracle_addr = bridge_wallet.config_data(
        'networks', 'eth-poa-local', 'bridges', 'aergo-local', 'oracle')
    eth_oracle = w3.eth.contract(
        address=eth_oracle_addr,
        abi=oracle_abi
    )
    t_anchor, t_final = query_eth_tempo(w3, eth_bridge_addr, bridge_abi)
    assert t_anchor == t_anchor_before
    assert t_final == t_final_before

    # increase tempo
    nonce_before = eth_oracle.functions._nonce().call()
    bridge_wallet.config_data(
        'networks', 'eth-poa-local', 'bridges', 'aergo-local', 't_anchor',
        value=t_anchor_before + 1
    )
    bridge_wallet.config_data(
        'networks', 'eth-poa-local', 'bridges', 'aergo-local', 't_final',
        value=t_final_before + 1
    )
    bridge_wallet.save_config()

    nonce = nonce_before
    while nonce <= nonce_before + 2:
        time.sleep(t_anchor)
        nonce = eth_oracle.functions._nonce().call()

    t_anchor, t_final = query_eth_tempo(w3, eth_bridge_addr, bridge_abi)
    assert t_anchor == t_anchor_before + 1
    assert t_final == t_final_before + 1

    # decrease tempo
    nonce_before = eth_oracle.functions._nonce().call()
    bridge_wallet.config_data(
        'networks', 'eth-poa-local', 'bridges', 'aergo-local', 't_anchor',
        value=t_anchor_before
    )
    bridge_wallet.config_data(
        'networks', 'eth-poa-local', 'bridges', 'aergo-local', 't_final',
        value=t_final_before
    )
    bridge_wallet.save_config()
    nonce = nonce_before
    while nonce <= nonce_before + 2:
        time.sleep(t_anchor)
        nonce = eth_oracle.functions._nonce().call()
    t_anchor, t_final = query_eth_tempo(w3, eth_bridge_addr, bridge_abi)
    assert t_anchor == t_anchor_before
    assert t_final == t_final_before


def test_aergo_tempo_update(bridge_wallet):
    eth_block_time = 1
    hera = herapy.Aergo()
    hera.connect(bridge_wallet.config_data('networks', 'aergo-local', 'ip'))
    aergo_bridge = bridge_wallet.config_data(
        'networks', 'aergo-local', 'bridges', 'eth-poa-local', 'addr')
    aergo_oracle = bridge_wallet.config_data(
        'networks', 'aergo-local', 'bridges', 'eth-poa-local', 'oracle')
    t_anchor_before = bridge_wallet.config_data(
        'networks', 'aergo-local', 'bridges', 'eth-poa-local', 't_anchor'
    )
    t_final_before = bridge_wallet.config_data(
        'networks', 'aergo-local', 'bridges', 'eth-poa-local', 't_final'
    )
    t_anchor, t_final = query_aergo_tempo(hera, aergo_bridge)
    assert t_anchor == t_anchor_before
    assert t_final == t_final_before

    # increase tempo
    nonce_before = int(
        hera.query_sc_state(aergo_oracle, ["_sv__nonce"]).var_proofs[0].value
    )
    bridge_wallet.config_data(
        'networks', 'aergo-local', 'bridges', 'eth-poa-local', 't_anchor',
        value=t_anchor_before + 1
    )
    bridge_wallet.config_data(
        'networks', 'aergo-local', 'bridges', 'eth-poa-local', 't_final',
        value=t_final_before + 1
    )
    bridge_wallet.save_config()
    nonce = nonce_before
    while nonce <= nonce_before + 2:
        time.sleep(t_anchor_before*eth_block_time)
        nonce = int(
            hera.query_sc_state(aergo_oracle, ["_sv__nonce"])
            .var_proofs[0].value
        )

    t_anchor, t_final = query_aergo_tempo(hera, aergo_bridge)
    assert t_anchor == t_anchor_before + 1
    assert t_final == t_final_before + 1

    # decrease tempo
    nonce_before = int(
        hera.query_sc_state(aergo_oracle, ["_sv__nonce"]).var_proofs[0].value
    )
    bridge_wallet.config_data(
        'networks', 'aergo-local', 'bridges', 'eth-poa-local', 't_anchor',
        value=t_anchor_before
    )
    bridge_wallet.config_data(
        'networks', 'aergo-local', 'bridges', 'eth-poa-local', 't_final',
        value=t_final_before
    )
    bridge_wallet.save_config()
    nonce = nonce_before
    while nonce <= nonce_before + 2:
        time.sleep(t_anchor_before*eth_block_time)
        nonce = int(
            hera.query_sc_state(aergo_oracle, ["_sv__nonce"])
            .var_proofs[0].value
        )
    t_anchor, t_final = query_aergo_tempo(hera, aergo_bridge)
    assert t_anchor == t_anchor_before
    assert t_final == t_final_before


def test_validators_update(bridge_wallet):
    eth_block_time = 1
    hera = herapy.Aergo()
    hera.connect(bridge_wallet.config_data('networks', 'aergo-local', 'ip'))

    ip = bridge_wallet.config_data('networks', 'eth-poa-local', 'ip')
    w3 = Web3(Web3.HTTPProvider(ip))
    eth_poa = bridge_wallet.config_data('networks', 'eth-poa-local', 'isPOA')
    if eth_poa:
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    assert w3.isConnected()

    with open("./contracts/solidity/oracle_abi.txt", "r") as f:
        oracle_abi = f.read()

    t_anchor_eth = bridge_wallet.config_data(
        'networks', 'eth-poa-local', 'bridges', 'aergo-local', 't_anchor'
    )
    t_anchor_aergo = bridge_wallet.config_data(
        'networks', 'aergo-local', 'bridges', 'eth-poa-local', 't_anchor'
    )
    aergo_oracle_addr = bridge_wallet.config_data(
        'networks', 'aergo-local', 'bridges', 'eth-poa-local', 'oracle'
    )

    eth_oracle_addr = bridge_wallet.config_data(
        'networks', 'eth-poa-local', 'bridges', 'aergo-local', 'oracle')
    eth_oracle = w3.eth.contract(
        address=eth_oracle_addr,
        abi=oracle_abi
    )
    validators_before = bridge_wallet.config_data('validators')
    aergo_validators_before = [val['addr'] for val in validators_before]
    eth_validators_before = [val['eth-addr'] for val in validators_before]
    aergo_validators = query_aergo_validators(hera, aergo_oracle_addr)
    eth_validators = query_eth_validators(w3, eth_oracle_addr, oracle_abi)
    assert aergo_validators == aergo_validators_before
    assert eth_validators == eth_validators_before

    # add a validator
    aergo_nonce_before = int(
        hera.query_sc_state(
            aergo_oracle_addr, ["_sv__nonce"]
        ).var_proofs[0].value
    )
    new_validators = validators_before + [validators_before[0]]
    bridge_wallet.config_data('validators', value=new_validators)

    bridge_wallet.save_config()
    # wait for changes to be reflected
    eth_nonce_before = eth_oracle.functions._nonce().call()
    nonce = aergo_nonce_before
    while nonce <= aergo_nonce_before + 2:
        time.sleep(t_anchor_aergo * eth_block_time)
        nonce = int(
            hera.query_sc_state(aergo_oracle_addr, ["_sv__nonce"])
            .var_proofs[0].value
        )
    nonce = eth_nonce_before
    while nonce <= eth_nonce_before + 2:
        time.sleep(t_anchor_eth)
        nonce = eth_oracle.functions._nonce().call()
    aergo_validators = query_aergo_validators(hera, aergo_oracle_addr)
    eth_validators = query_eth_validators(w3, eth_oracle_addr, oracle_abi)

    assert aergo_validators == \
        aergo_validators_before + [aergo_validators_before[0]]
    assert eth_validators == \
        eth_validators_before + [eth_validators_before[0]]

    # remove added validator
    aergo_nonce_before = int(
        hera.query_sc_state(
            aergo_oracle_addr, ["_sv__nonce"]
        ).var_proofs[0].value
    )
    bridge_wallet.config_data('validators', value=new_validators[:-1])
    bridge_wallet.save_config()
    # wait for changes to be reflected
    eth_nonce_before = eth_oracle.functions._nonce().call()
    nonce = aergo_nonce_before
    while nonce <= aergo_nonce_before + 2:
        time.sleep(t_anchor_aergo * eth_block_time)
        nonce = int(
            hera.query_sc_state(aergo_oracle_addr, ["_sv__nonce"])
            .var_proofs[0].value
        )
    nonce = eth_nonce_before
    while nonce <= eth_nonce_before + 2:
        time.sleep(t_anchor_eth)
        nonce = eth_oracle.functions._nonce().call()
    aergo_validators = query_aergo_validators(hera, aergo_oracle_addr)
    eth_validators = query_eth_validators(w3, eth_oracle_addr, oracle_abi)

    assert aergo_validators == aergo_validators_before
    assert eth_validators == eth_validators_before


def test_getters(bridge_wallet):
    hera = bridge_wallet.get_aergo('aergo-local', 'default', '1234')
    aergo_oracle_addr = bridge_wallet.config_data(
        'networks', 'aergo-local', 'bridges', 'eth-poa-local', 'oracle'
    )
    # query validators
    aergo_validators = query_aergo_validators(hera, aergo_oracle_addr)
    tx, _ = hera.call_sc(aergo_oracle_addr, "getValidators")
    result = hera.wait_tx_result(tx.tx_hash)
    getter_validators = json.loads(result.detail)
    assert getter_validators == aergo_validators

    # query anchored state
    tx, _ = hera.call_sc(aergo_oracle_addr, "getForeignBlockchainState")
    result = hera.wait_tx_result(tx.tx_hash)
    root, height = json.loads(result.detail)
    assert len(root) == 66
    assert type(height) == int


def test_unfreeze_fee_update(bridge_wallet):
    eth_block_time = 1
    hera = herapy.Aergo()
    hera.connect(bridge_wallet.config_data('networks', 'aergo-local', 'ip'))
    t_anchor_aergo = bridge_wallet.config_data(
        'networks', 'aergo-local', 'bridges', 'eth-poa-local', 't_anchor'
    )
    bridge = bridge_wallet.config_data(
        'networks', 'aergo-local', 'bridges', 'eth-poa-local', 'addr'
    )
    oracle = bridge_wallet.config_data(
        'networks', 'aergo-local', 'bridges', 'eth-poa-local', 'oracle'
    )

    unfreeze_fee_setting = bridge_wallet.config_data(
        'networks', 'aergo-local', 'bridges', 'eth-poa-local', 'unfreeze_fee'
    )
    unfreeze_fee_before = query_unfreeze_fee(hera, bridge)
    assert unfreeze_fee_setting == unfreeze_fee_before

    # update fee
    aergo_nonce_before = int(
        hera.query_sc_state(oracle, ["_sv__nonce"]).var_proofs[0].value
    )
    new_fee = unfreeze_fee_before + 1000
    bridge_wallet.config_data(
        'networks', 'aergo-local', 'bridges', 'eth-poa-local', 'unfreeze_fee',
        value=new_fee)

    bridge_wallet.save_config()
    # wait for changes to be reflected
    nonce = aergo_nonce_before
    while nonce <= aergo_nonce_before + 2:
        time.sleep(t_anchor_aergo * eth_block_time)
        nonce = int(
            hera.query_sc_state(oracle, ["_sv__nonce"])
            .var_proofs[0].value
        )
    unfreeze_fee_after = query_unfreeze_fee(hera, bridge)

    assert unfreeze_fee_after == new_fee

    # reset fee to starting value
    aergo_nonce_before = int(
        hera.query_sc_state(oracle, ["_sv__nonce"]).var_proofs[0].value
    )
    new_fee = unfreeze_fee_after - 1000
    bridge_wallet.config_data(
        'networks', 'aergo-local', 'bridges', 'eth-poa-local', 'unfreeze_fee',
        value=new_fee)

    bridge_wallet.save_config()
    # wait for changes to be reflected
    nonce = aergo_nonce_before
    while nonce <= aergo_nonce_before + 2:
        time.sleep(t_anchor_aergo * eth_block_time)
        nonce = int(
            hera.query_sc_state(oracle, ["_sv__nonce"])
            .var_proofs[0].value
        )
    unfreeze_fee_after = query_unfreeze_fee(hera, bridge)

    assert unfreeze_fee_after == new_fee


def test_oracle_update(bridge_wallet):
    eth_block_time = 1

    # connect providers
    hera = herapy.Aergo()
    hera.connect(bridge_wallet.config_data('networks', 'aergo-local', 'ip'))

    ip = bridge_wallet.config_data('networks', 'eth-poa-local', 'ip')
    w3 = Web3(Web3.HTTPProvider(ip))
    eth_poa = bridge_wallet.config_data('networks', 'eth-poa-local', 'isPOA')
    if eth_poa:
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    assert w3.isConnected()

    # set eth signer
    keystore = bridge_wallet.config_data("wallet-eth", 'default', 'keystore')
    with open(keystore, "r") as f:
        encrypted_key = f.read()

    eth_privkey = w3.eth.account.decrypt(encrypted_key, '1234')
    signer_acct = w3.eth.account.from_key(eth_privkey)

    # set aergo signer
    encrypted_key = bridge_wallet.config_data('wallet', 'default', 'priv_key')
    hera.import_account(encrypted_key, '1234')

    with open("./contracts/solidity/oracle_abi.txt", "r") as f:
        oracle_abi = f.read()
    with open("./contracts/solidity/bridge_abi.txt", "r") as f:
        bridge_abi = f.read()

    t_anchor_eth = bridge_wallet.config_data(
        'networks', 'eth-poa-local', 'bridges', 'aergo-local', 't_anchor'
    )
    t_anchor_aergo = bridge_wallet.config_data(
        'networks', 'aergo-local', 'bridges', 'eth-poa-local', 't_anchor'
    )
    aergo_oracle_addr = bridge_wallet.config_data(
        'networks', 'aergo-local', 'bridges', 'eth-poa-local', 'oracle'
    )
    eth_oracle_addr = bridge_wallet.config_data(
        'networks', 'eth-poa-local', 'bridges', 'aergo-local', 'oracle')
    eth_oracle = w3.eth.contract(
        address=eth_oracle_addr,
        abi=oracle_abi
    )
    aergo_bridge = bridge_wallet.config_data(
        'networks', 'aergo-local', 'bridges', 'eth-poa-local', 'addr')
    eth_bridge_addr = bridge_wallet.config_data(
        'networks', 'eth-poa-local', 'bridges', 'aergo-local', 'addr')
    eth_bridge = w3.eth.contract(
        address=eth_bridge_addr,
        abi=bridge_abi
    )

    # change oracle to 'default' account
    aergo_nonce_before = int(
        hera.query_sc_state(
            aergo_oracle_addr, ["_sv__nonce"]
        ).var_proofs[0].value
    )
    new_oracle_aergo = bridge_wallet.config_data('wallet', 'default', 'addr')
    new_oracle_eth = bridge_wallet.config_data('wallet-eth', 'default', 'addr')
    bridge_wallet.config_data(
        'networks', 'eth-poa-local', 'bridges', 'aergo-local', 'oracle',
        value=new_oracle_eth
    )
    bridge_wallet.config_data(
        'networks', 'aergo-local', 'bridges', 'eth-poa-local', 'oracle',
        value=new_oracle_aergo
    )
    bridge_wallet.save_config()

    # wait for changes to be reflected
    eth_nonce_before = eth_oracle.functions._nonce().call()
    nonce = aergo_nonce_before
    while nonce <= aergo_nonce_before + 1:
        time.sleep(t_anchor_aergo * eth_block_time)
        nonce = int(
            hera.query_sc_state(aergo_oracle_addr, ["_sv__nonce"])
            .var_proofs[0].value
        )
    nonce = eth_nonce_before
    while nonce <= eth_nonce_before + 1:
        time.sleep(t_anchor_eth)
        nonce = eth_oracle.functions._nonce().call()

    oracle_aergo = query_aergo_oracle(hera, aergo_bridge)
    oracle_eth = eth_bridge.functions._oracle().call()

    assert oracle_aergo == new_oracle_aergo
    assert oracle_eth == new_oracle_eth

    bridge_wallet.config_data(
        'networks', 'eth-poa-local', 'bridges', 'aergo-local', 'oracle',
        value=eth_oracle_addr
    )
    bridge_wallet.config_data(
        'networks', 'aergo-local', 'bridges', 'eth-poa-local', 'oracle',
        value=aergo_oracle_addr
    )
    bridge_wallet.save_config()

    # reset to original oracle by calling oracleUpdate from 'default'
    hera.call_sc(
        aergo_bridge, "oracleUpdate", args=[aergo_oracle_addr]
    )
    construct_txn = eth_bridge.functions.oracleUpdate(
        eth_oracle_addr
    ).buildTransaction({
        'chainId': w3.eth.chainId,
        'from': signer_acct.address,
        'nonce': w3.eth.getTransactionCount(
            signer_acct.address
        ),
        'gas': 500000,
        'gasPrice': w3.toWei(9, 'gwei')
    })
    signed = signer_acct.sign_transaction(construct_txn)
    w3.eth.sendRawTransaction(signed.rawTransaction)
    time.sleep(2)

    oracle_aergo = query_aergo_oracle(hera, aergo_bridge)
    oracle_eth = eth_bridge.functions._oracle().call()

    assert oracle_aergo == aergo_oracle_addr
    assert oracle_eth == eth_oracle_addr
