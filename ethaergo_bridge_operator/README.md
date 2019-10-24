# Bridge operator package

## Proposer

```sh
$ python3 -m ethaergo_bridge_operator.proposer.client --help

usage: client.py [-h] -c CONFIG_FILE_PATH -a AERGO -e ETH --eth_block_time
                 ETH_BLOCK_TIME [--privkey_name PRIVKEY_NAME] [--auto_update]
                 [--local_test] [--eth_gas_price ETH_GAS_PRICE]
                 [--aergo_gas_price AERGO_GAS_PRICE]

Start a proposer on Ethereum and Aergo.

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG_FILE_PATH, --config_file_path CONFIG_FILE_PATH
                        Path to config.json
  -a AERGO, --aergo AERGO
                        Name of Aergo network in config file
  -e ETH, --eth ETH     Name of Ethereum network in config file
  --eth_block_time ETH_BLOCK_TIME
                        Average Ethereum block time
  --privkey_name PRIVKEY_NAME
                        Name of account in config file to sign anchors
  --auto_update         Update bridge contract when settings change in config
                        file
  --local_test          Start proposer with password for testing
  --eth_gas_price ETH_GAS_PRICE
                        Gas price (gWei) to use in transactions
  --aergo_gas_price AERGO_GAS_PRICE
                        Gas price to use in transactions

$ python3 -m ethaergo_bridge_operator.proposer.client -c './test_config.json' -a 'aergo-local' -e 'eth-poa-local' --eth_block_time 3 --privkey_name "proposer" --auto_update
```

``` py
from ethaergo_bridge_operator.proposer.client import ProposerClient

proposer = ProposerClient('./test_config.json', 'aergo-local', 'eth-poa-local', 15, 'proposer')
proposer.run()
```

## Validator
```sh
$ python3 -m ethaergo_bridge_operator.validator.server --help

usage: server.py [-h] -c CONFIG_FILE_PATH -a AERGO -e ETH -i VALIDATOR_INDEX
                 [--privkey_name PRIVKEY_NAME] [--auto_update] [--local_test]

Start a validator on Ethereum and Aergo.

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG_FILE_PATH, --config_file_path CONFIG_FILE_PATH
                        Path to config.json
  -a AERGO, --aergo AERGO
                        Name of Aergo network in config file
  -e ETH, --eth ETH     Name of Ethereum network in config file
  -i VALIDATOR_INDEX, --validator_index VALIDATOR_INDEX
                        Index of the validator in the ordered list of
                        validators
  --privkey_name PRIVKEY_NAME
                        Name of account in config file to sign anchors
  --auto_update         Update bridge contract when settings change in config
                        file
  --local_test          Start all validators locally for convenient testing

$ python3 -m ethaergo_bridge_operator.validator.server -c './test_config.json' -a 'aergo-local' -e 'eth-poa-local' --validator_index 1 --privkey_name "validator" --auto_update
```

``` py
from ethaergo_bridge_operator.validator.server import ValidatorServer

validator = ValidatorServer("./test_config.json", 'aergo-local', 'eth-poa-local', privkey_name='validator', validator_index=1)
validator.run()
```