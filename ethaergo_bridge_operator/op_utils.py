from typing import (
    List,
)
from web3 import (
    Web3,
)

import aergo.herapy as herapy


def query_aergo_tempo(
    aergo: herapy.Aergo,
    bridge: str,
) -> List[int]:
    result_q = aergo.query_sc_state(bridge, ["_sv_T_anchor", "_sv_T_final"])
    result = [int(res.value) for res in result_q.var_proofs]
    return result


def query_aergo_validators(aergo: herapy.Aergo, bridge: str) -> List[str]:
    nb_validators_q = aergo.query_sc_state(bridge,
                                           ["_sv_Nb_Validators"])
    nb_validators = int(nb_validators_q.var_proofs[0].value)
    args = ["_sv_Validators-" + str(i+1) for i in range(nb_validators)]
    validators_q = aergo.query_sc_state(bridge, args)
    validators = [val.value.decode('utf-8')[1:-1]
                  for val in validators_q.var_proofs]
    return validators


def query_aergo_id(aergo: herapy.Aergo, bridge: str) -> str:
    id_q = aergo.query_sc_state(bridge, ["_sv_ContractID"])
    id = id_q.var_proofs[0].value.decode('utf-8')[1:-1]
    return id


def query_eth_validators(w3: Web3, address: str, abi: str):
    bridge_contract = w3.eth.contract(
        address=address,
        abi=abi
    )
    return bridge_contract.functions.get_validators().call()


def query_eth_tempo(w3: Web3, address: str, abi: str):
    bridge_contract = w3.eth.contract(
        address=address,
        abi=abi
    )
    return (bridge_contract.functions.T_anchor().call(),
            bridge_contract.functions.T_final().call(),
            )


def query_eth_id(w3: Web3, address: str, abi: str):
    bridge_contract = w3.eth.contract(
        address=address,
        abi=abi
    )
    return bridge_contract.functions.ContractID().call()
