# Bridge operator package

## Proposer

```sh
$ python3 -m ethaergo_bridge_operator.proposer_client --help

usage: proposer_client.py [-h] -c CONFIG_FILE_PATH -a AERGO -e ETH
                          --eth_block_time ETH_BLOCK_TIME
                          [--privkey_name PRIVKEY_NAME] [--auto_update]

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

$ python3 -m ethaergo_bridge_operator.proposer_client -c './test_config.json' -a 'aergo-local' -e 'eth-poa-local' --eth_block_time 3 --privkey_name "proposer" --auto_update
```

``` py
from ethaergo_bridge_operator.proposer_client import ProposerClient

proposer = ProposerClient('./test_config.json', 'aergo-local', 'eth-poa-local', 15, 'proposer')
proposer.run()
```

## Validator
```sh
$ python3 -m ethaergo_bridge_operator.validator_server --help

usage: validator_server.py [-h] -c CONFIG_FILE_PATH -a AERGO -e ETH -i
                           VALIDATOR_INDEX [--privkey_name PRIVKEY_NAME]
                           [--auto_update] [--local_test]

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

$ python3 -m ethaergo_bridge_operator.validator_server -c './test_config.json' -a 'aergo-local' -e 'eth-poa-local' --validator_index 1 --privkey_name "validator" --auto_update
```

``` py
from ethaergo_bridge_operator.validator_server import ValidatorServer

validator = ValidatorServer("./test_config.json", 'aergo-local', 'eth-poa-local', privkey_name='validator', validator_index=1)
validator.run()
```