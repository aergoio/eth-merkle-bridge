# eth-merkle-bridge

[![Build Status](https://travis-ci.org/aergoio/eth-merkle-bridge.svg?branch=master)](https://travis-ci.org/aergoio/eth-merkle-bridge)

Eth&lt;-->Aergo Merkle Bridge 

https://eth-merkle-bridge.readthedocs.io/

The Eth-Aergo Merkle bridge follows a similar design to the Aergo-Aergo Merkle bridge with some key differences : the total aer supply is already minted on Aergo mainnet (freezed in the Lua bridge contract so Aer is unfreezed/freezed instead of minted/burnt) and the Lua bridge contract needs to verify Ethereum Patricia Lock tree merkle proofs.


## Install
```sh
$ cd eth-merkle-bridge/
$ virtualenv -p python3 venv
$ source venv/bin/activate
$ pip install -r requirements.txt
```

Optional dev dependencies (lint, testing...)
```sh
$ pip install -r dev-dependencies.txt
```

## CLI
The CLI can generate new config.json files, perform cross chain asset transfers and query balances and pending transfer amounts. 
```sh
$ python3 -m ethaergo_cli.main
```

## Bridge Operator
### Proposer
Start a proposer between an Aergo and an Ethereum network
```sh
$ python3 -m ethaergo_bridge_operator.proposer.client -c './test_config.json' -a 'aergo-local' -e 'eth-poa-local' --eth_block_time 3 --privkey_name "proposer" --anchoring_on
```

### Validator
Start a validator between an Aergo and an Ethereum network
```sh
$ python3 -m ethaergo_bridge_operator.validator.server -c './test_config.json' -a 'aergo-local' -e 'eth-poa-local' --validator_index 1 --privkey_name "validator" --anchoring_on
```

### Running tests
Start 2 test networks locally in separate terminals
```sh
$ make docker-eth
$ make docker-aergo
```

Deploy a test bridge between aergo and ethereum test networks
```sh
$ make deploy_test_bridge
```
In a new terminal : start proposer
```sh
$ make proposer
```
In a new terminal : start validator
```sh
$ make validator
```
In a new terminal : start unfreeze service
```sh
$ make unfreeze_service
```

In a new terminal : test wallet transfers, bridge transfers and the bridge multisig
```sh
$ make tests
```
Remove test networks data
```sh
$ make clean
```
