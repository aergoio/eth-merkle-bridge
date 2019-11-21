Unfreeze service
================

The unfreeze service provides the service to users that want to transfer Aergo erc20 to Aergo Mainnet
(Aergo Native) but don't already own Aergo Native to pay for the unfreeze transaction fee.

The bridge contract on Aergo check if the tx sender is the same as the Aergo Native receiver and if they
are different, if will transfer _unfreezeFee to the tx sender and send the rest to the receiver.

The RequestUnfreeze service will check the receiver address is valid and that the amount to unfreeze is higher
than the _unfreezeFee.

Starting the unfreeze grpc service
----------------------------------

.. code-block:: bash

    $ python3 -m unfreeze_service.server --help
        usage: server.py [-h] -ip IP_PORT -c CONFIG_FILE_PATH -a AERGO -e ETH
                    --privkey_name PRIVKEY_NAME [--local_test]

        Aergo native unfreeze service

        optional arguments:
        -h, --help            show this help message and exit
        -ip IP_PORT, --ip_port IP_PORT
                                ip and port to run unfreeze service
        -c CONFIG_FILE_PATH, --config_file_path CONFIG_FILE_PATH
                                Path to config.json
        -a AERGO, --aergo AERGO
                                Name of Aergo network in config file
        -e ETH, --eth ETH     Name of Ethereum network in config file
        --privkey_name PRIVKEY_NAME
                                Name of account in config file to sign anchors
        --local_test          Start service for running tests


    $ python3 -m unfreeze_service.server -ip 'localhost:7891' -c './test_config.json' -a 'aergo-local' -e 'eth-poa-local' --privkey_name "broadcaster"
        "Ethereum bridge contract: 0x89eD1D1C145F6bF3A7e62d2B8eB0e1Bf15Cb2374"
        "Aergo bridge contract: AmgQqVWX3JADRBEVkVCM4CyWdoeXuumeYGGJJxEeoAukRC26hxmw"
        "Aergo ERC20: 0xd898383A12CDE0eDF7642F7dD4D7006FdE5c433e"
        Decrypt exported private key 'broadcaster'
        Password: 
        "Unfreezer Address: AmPiFGxLvETrs13QYrHUiYoFqAqqWv7TKYXG21zC8TJfJTDHc7HJ"
        "Unfreeze fee for broadcaster: 1000aer"
        "Unfreeze server started"


Starting the Envoy proxy
------------------------

.. code-block:: bash

    $ docker run --rm --name=proxy -p 8081:8080 -v $(pwd)/unfreeze_service//envoy/envoy.yaml:/etc/envoy/envoy.yaml envoyproxy/envoy:latest