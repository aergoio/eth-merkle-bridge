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
)


def test_eth_tempo_update(bridge_wallet):
    ip = bridge_wallet.config_data('networks', 'eth-poa-local', 'ip')
    w3 = Web3(Web3.HTTPProvider("http://" + ip))
    eth_poa = bridge_wallet.config_data('networks', 'eth-poa-local', 'isPOA')
    if eth_poa:
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    assert w3.isConnected()

    with open("./contracts/solidity/bridge_abi.txt", "r") as f:
        eth_abi = f.read()

    t_anchor_before = bridge_wallet.config_data(
        'networks', 'eth-poa-local', 'bridges', 'aergo-local', 't_anchor'
    )
    t_final_before = bridge_wallet.config_data(
        'networks', 'eth-poa-local', 'bridges', 'aergo-local', 't_final'
    )
    eth_bridge_addr = bridge_wallet.config_data(
        'networks', 'eth-poa-local', 'bridges', 'aergo-local', 'addr')
    eth_bridge = w3.eth.contract(
        address=eth_bridge_addr,
        abi=eth_abi
    )
    t_anchor, t_final = query_eth_tempo(w3, eth_bridge_addr, eth_abi)
    assert t_anchor == t_anchor_before
    assert t_final == t_final_before

    # increase tempo
    nonce_before = eth_bridge.functions._nonce().call()
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
        nonce = eth_bridge.functions._nonce().call()

    t_anchor, t_final = query_eth_tempo(w3, eth_bridge_addr, eth_abi)
    assert t_anchor == t_anchor_before + 1
    assert t_final == t_final_before + 1

    # decrease tempo
    nonce_before = eth_bridge.functions._nonce().call()
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
        nonce = eth_bridge.functions._nonce().call()
    t_anchor, t_final = query_eth_tempo(w3, eth_bridge_addr, eth_abi)
    assert t_anchor == t_anchor_before
    assert t_final == t_final_before


def test_aergo_tempo_update(bridge_wallet):
    eth_block_time = 1
    hera = herapy.Aergo()
    hera.connect(bridge_wallet.config_data('networks', 'aergo-local', 'ip'))
    aergo_bridge = bridge_wallet.config_data(
        'networks', 'aergo-local', 'bridges', 'eth-poa-local', 'addr'
    )
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
        hera.query_sc_state(aergo_bridge, ["_sv__nonce"]).var_proofs[0].value
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
            hera.query_sc_state(aergo_bridge, ["_sv__nonce"])
            .var_proofs[0].value
        )

    t_anchor, t_final = query_aergo_tempo(hera, aergo_bridge)
    assert t_anchor == t_anchor_before + 1
    assert t_final == t_final_before + 1

    # decrease tempo
    nonce_before = int(
        hera.query_sc_state(aergo_bridge, ["_sv__nonce"]).var_proofs[0].value
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
            hera.query_sc_state(aergo_bridge, ["_sv__nonce"])
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
    w3 = Web3(Web3.HTTPProvider("http://" + ip))
    eth_poa = bridge_wallet.config_data('networks', 'eth-poa-local', 'isPOA')
    if eth_poa:
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    assert w3.isConnected()

    with open("./contracts/solidity/bridge_abi.txt", "r") as f:
        eth_abi = f.read()

    t_anchor_eth = bridge_wallet.config_data(
        'networks', 'eth-poa-local', 'bridges', 'aergo-local', 't_anchor'
    )
    t_anchor_aergo = bridge_wallet.config_data(
        'networks', 'aergo-local', 'bridges', 'eth-poa-local', 't_anchor'
    )
    aergo_bridge = bridge_wallet.config_data(
        'networks', 'aergo-local', 'bridges', 'eth-poa-local', 'addr'
    )
    eth_bridge_addr = bridge_wallet.config_data(
        'networks', 'eth-poa-local', 'bridges', 'aergo-local', 'addr')
    eth_bridge = w3.eth.contract(
        address=eth_bridge_addr,
        abi=eth_abi
    )
    validators_before = bridge_wallet.config_data('validators')
    aergo_validators_before = [val['addr'] for val in validators_before]
    eth_validators_before = [val['eth-addr'] for val in validators_before]
    aergo_validators = query_aergo_validators(hera, aergo_bridge)
    eth_validators = query_eth_validators(w3, eth_bridge_addr, eth_abi)
    assert aergo_validators == aergo_validators_before
    assert eth_validators == eth_validators_before

    # add a validatos
    aergo_nonce_before = int(
        hera.query_sc_state(aergo_bridge, ["_sv__nonce"]).var_proofs[0].value
    )
    new_validators = validators_before + [validators_before[0]]
    bridge_wallet.config_data('validators', value=new_validators)

    bridge_wallet.save_config()
    # wait for changes to be reflected
    eth_nonce_before = eth_bridge.functions._nonce().call()
    nonce = aergo_nonce_before
    while nonce <= aergo_nonce_before + 2:
        time.sleep(t_anchor_aergo * eth_block_time)
        nonce = int(
            hera.query_sc_state(aergo_bridge, ["_sv__nonce"])
            .var_proofs[0].value
        )
    nonce = eth_nonce_before
    while nonce <= eth_nonce_before + 2:
        time.sleep(t_anchor_eth)
        nonce = eth_bridge.functions._nonce().call()
    aergo_validators = query_aergo_validators(hera, aergo_bridge)
    eth_validators = query_eth_validators(w3, eth_bridge_addr, eth_abi)

    assert aergo_validators == \
        aergo_validators_before + [aergo_validators_before[0]]
    assert eth_validators == \
        eth_validators_before + [eth_validators_before[0]]

    # remove added validator
    aergo_nonce_before = int(
        hera.query_sc_state(aergo_bridge, ["_sv__nonce"]).var_proofs[0].value
    )
    bridge_wallet.config_data('validators', value=new_validators[:-1])
    bridge_wallet.save_config()
    # wait for changes to be reflected
    eth_nonce_before = eth_bridge.functions._nonce().call()
    nonce = aergo_nonce_before
    while nonce <= aergo_nonce_before + 2:
        time.sleep(t_anchor_aergo * eth_block_time)
        nonce = int(
            hera.query_sc_state(aergo_bridge, ["_sv__nonce"])
            .var_proofs[0].value
        )
    nonce = eth_nonce_before
    while nonce <= eth_nonce_before + 2:
        time.sleep(t_anchor_eth)
        nonce = eth_bridge.functions._nonce().call()
    aergo_validators = query_aergo_validators(hera, aergo_bridge)
    eth_validators = query_eth_validators(w3, eth_bridge_addr, eth_abi)

    assert aergo_validators == aergo_validators_before
    assert eth_validators == eth_validators_before


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

    unfreeze_fee_setting = bridge_wallet.config_data(
        'networks', 'aergo-local', 'bridges', 'eth-poa-local', 'unfreeze_fee'
    )
    unfreeze_fee_before = query_unfreeze_fee(hera, bridge)
    assert unfreeze_fee_setting == unfreeze_fee_before

    # update fee
    aergo_nonce_before = int(
        hera.query_sc_state(bridge, ["_sv__nonce"]).var_proofs[0].value
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
            hera.query_sc_state(bridge, ["_sv__nonce"])
            .var_proofs[0].value
        )
    unfreeze_fee_after = query_unfreeze_fee(hera, bridge)

    assert unfreeze_fee_after == new_fee

    # reset fee to starting value
    aergo_nonce_before = int(
        hera.query_sc_state(bridge, ["_sv__nonce"]).var_proofs[0].value
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
            hera.query_sc_state(bridge, ["_sv__nonce"])
            .var_proofs[0].value
        )
    unfreeze_fee_after = query_unfreeze_fee(hera, bridge)

    assert unfreeze_fee_after == new_fee
