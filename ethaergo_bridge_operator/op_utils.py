import json
from typing import (
    List,
    Dict,
)
from web3 import (
    Web3,
)

import aergo.herapy as herapy


def query_aergo_tempo(
    aergo: herapy.Aergo,
    bridge: str,
) -> List[int]:
    result_q = aergo.query_sc_state(bridge, ["_sv__tAnchor", "_sv__tFinal"])
    result = [int(res.value) for res in result_q.var_proofs]
    return result


def query_aergo_validators(aergo: herapy.Aergo, bridge: str) -> List[str]:
    nb_validators_q = aergo.query_sc_state(bridge,
                                           ["_sv__validatorsCount"])
    nb_validators = int(nb_validators_q.var_proofs[0].value)
    args = ["_sv__validators-" + str(i+1) for i in range(nb_validators)]
    validators_q = aergo.query_sc_state(bridge, args)
    validators = [val.value.decode('utf-8')[1:-1]
                  for val in validators_q.var_proofs]
    return validators


def query_aergo_id(aergo: herapy.Aergo, bridge: str) -> str:
    id_q = aergo.query_sc_state(bridge, ["_sv__contractId"])
    id = id_q.var_proofs[0].value.decode('utf-8')[1:-1]
    return id


def query_unfreeze_fee(aergo: herapy.Aergo, bridge: str) -> int:
    unfreeze_fee_q = aergo.query_sc_state(bridge, ["_sv__unfreezeFee"])
    return int(json.loads(unfreeze_fee_q.var_proofs[0].value)['_bignum'])


def query_aergo_oracle(aergo: herapy.Aergo, bridge: str) -> str:
    oracle_q = aergo.query_sc_state(bridge, ["_sv__oracle"])
    oracle = oracle_q.var_proofs[0].value.decode('utf-8')[1:-1]
    return oracle


def query_eth_validators(w3: Web3, address: str, abi: str):
    bridge_contract = w3.eth.contract(
        address=address,
        abi=abi
    )
    return bridge_contract.functions.getValidators().call()


def query_eth_tempo(w3: Web3, address: str, abi: str):
    bridge_contract = w3.eth.contract(
        address=address,
        abi=abi
    )
    return (bridge_contract.functions._tAnchor().call(),
            bridge_contract.functions._tFinal().call(),
            )


def query_eth_id(w3: Web3, address: str, abi: str):
    bridge_contract = w3.eth.contract(
        address=address,
        abi=abi
    )
    return bridge_contract.functions._contractId().call()


def load_config_data(config_file_path: str) -> Dict:
    with open(config_file_path, "r") as f:
        config_data = json.load(f)
    return config_data
