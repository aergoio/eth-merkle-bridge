# eth-merkle-bridge
Eth&lt;-->Aergo Merkle Bridge 

The Eth-Aergo Merkle bridge follows a similar design to the Aergo-Aergo Merkle bridge with some key differences : the total aer supply is already minted on Aergo mainnet (freezed in the Lua bridge contract so Aer is unfreezed/freezed instead of minted/burnt) and the Lua bridge contract needs to verify Ethereum Patricia Lock tree merkle proofs.


## Install
```sh
$ cd eth-merkle-bridge/
$ virtualenv -p python3 venv
$ source venv/bin/activate
$ make install
```

## CLI
The CLI can generate new config.json files, perform cross chain asset transfers and query balances and pending transfer amounts. 
```sh
$ python3 -m cli.main
```

## Bridge Operator
### Proposer
Start a proposer between an Aergo and an Ethereum network
```sh
$ python3 -m bridge_operator.proposer_client -c './test_config.json' -a 'aergo-local' -e 'eth-poa-local' --eth_block_time 3 --privkey_name "proposer" --auto_update
```

### Validator
Start a validator between an Aergo and an Ethereum network
```sh
$ python3 -m bridge_operator.validator_server -c './test_config.json' -a 'aergo-local' -e 'eth-poa-local' --validator_index 1 --privkey_name "validator" --auto_update
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

In a new terminal : test wallet transfers, bridge transfers and the bridge multisig
```sh
$ make tests
```
Remove test networks data
```sh
$ make clean
```

## TODO
delegated fee minting when Aergo v2
