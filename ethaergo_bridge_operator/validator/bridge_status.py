import json
import aergo.herapy as herapy
from web3 import (
    Web3,
)
from web3.middleware import (
    geth_poa_middleware,
)

from ethaergo_bridge_operator.op_utils import (
    query_aergo_tempo,
    query_eth_tempo,
    query_aergo_validators,
    query_eth_validators,
    query_aergo_id,
    query_eth_id,
)
from ethaergo_bridge_operator.validator import (
    logger,
)


def check_bridge_status(config_data, aergo_net, eth_net, auto_update):
    logger.info("Connect Aergo and Ethereum")
    hera = herapy.Aergo()
    hera.connect(config_data['networks'][aergo_net]['ip'])

    ip = config_data['networks'][eth_net]['ip']
    web3 = Web3(Web3.HTTPProvider(ip))
    eth_poa = config_data['networks'][eth_net]['isPOA']
    if eth_poa:
        web3.middleware_onion.inject(geth_poa_middleware, layer=0)
    assert web3.isConnected()

    # remember bridge contracts
    bridge_abi_path = (config_data['networks'][eth_net]['bridges']
                       [aergo_net]['bridge_abi'])
    with open(bridge_abi_path, "r") as f:
        eth_abi = f.read()
    eth_bridge_addr = (config_data['networks'][eth_net]['bridges']
                       [aergo_net]['addr'])
    aergo_bridge = (config_data['networks'][aergo_net]['bridges']
                    [eth_net]['addr'])

    # check validators are correct and warn the validator will vote for
    # a new validator set
    aergo_vals = query_aergo_validators(hera, aergo_bridge)
    eth_vals = query_eth_validators(web3, eth_bridge_addr,
                                    eth_abi)
    logger.info("Current Aergo validators : %s", json.dumps(aergo_vals))
    logger.info("Current Ethereum validators : %s", json.dumps(eth_vals))
    # get the current t_anchor and t_final for both sides of bridge
    t_anchor_aergo, t_final_aergo = query_aergo_tempo(
        hera, aergo_bridge
    )
    t_anchor_eth, t_final_eth = query_eth_tempo(
        web3, eth_bridge_addr, eth_abi
    )
    logger.info(
        "%s <- %s (t_final=%s) : t_anchor=%s", aergo_net, eth_net,
        t_final_aergo, t_anchor_aergo
    )
    logger.info(
        "%s (t_final=%s) -> %s : t_anchor=%s", aergo_net, t_final_eth,
        eth_net, t_anchor_eth
    )

    if auto_update:
        logger.warning(
            "WARNING: This validator will vote for settings update in "
            "config.json"
        )
        if len(aergo_vals) != len(eth_vals):
            logger.warning(
                "WARNING: different number of validators on both sides of the "
                "bridge"
            )
        if len(config_data['validators']) != len(aergo_vals):
            logger.warning(
                "WARNING: This validator is voting for a new set of aergo "
                "validators"
            )
        if len(config_data['validators']) != len(eth_vals):
            logger.warning(
                "WARNING: This validator is voting for a new set of eth "
                "validators"
            )
        for i, validator in enumerate(config_data['validators']):
            try:
                if validator['addr'] != aergo_vals[i]:
                    logger.warning(
                        "WARNING: This validator is voting for a new set of "
                        "aergo validators\n")
            except IndexError:
                # new validators index larger than current validators
                pass
            try:
                if validator['eth-addr'] != eth_vals[i]:
                    logger.warning(
                        "WARNING: This validator is voting for a new set of "
                        "eth validators\n"
                    )
            except IndexError:
                # new validators index larger than current validators
                pass

        t_anchor_aergo_c = (config_data['networks'][aergo_net]
                            ['bridges'][eth_net]['t_anchor'])
        t_final_aergo_c = (config_data['networks'][aergo_net]
                           ['bridges'][eth_net]['t_final'])
        t_anchor_eth_c = (config_data['networks'][eth_net]['bridges']
                          [aergo_net]['t_anchor'])
        t_final_eth_c = (config_data['networks'][eth_net]['bridges']
                         [aergo_net]['t_final'])
        if t_anchor_aergo_c != t_anchor_aergo:
            logger.warning(
                "WARNING: This validator is voting to update anchoring periode"
                " on aergo"
            )
        if t_final_aergo_c != t_final_aergo:
            logger.warning(
                "WARNING: This validator is voting to update finality of eth"
                " on aergo"
            )
        if t_anchor_eth_c != t_anchor_eth:
            logger.warning(
                "WARNING: This validator is voting to update anchoring periode"
                " on eth"
            )
        if t_final_eth_c != t_final_eth:
            logger.warning(
                "WARNING: This validator is voting to update finality of aergo"
                " on eth"
            )

    aergo_id = query_aergo_id(hera, aergo_bridge)
    eth_id = query_eth_id(web3, eth_bridge_addr, eth_abi)

    return aergo_id, eth_id
