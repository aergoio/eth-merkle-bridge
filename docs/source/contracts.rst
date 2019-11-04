Deploying a new bridge
======================

Before using the bridge deployer, a config file should be created to register network node connections, 
bridge tempo (anchoring periode and finality of both chains), validators and the address of aergo_erc20 on ethereum.
The aergo bridge contract must record the aergo_erc20 so that aergo can be unfroozen.

Create a new config file
------------------------
A config file can be created with the cli tool or manually.

.. image:: images/scratch.png

.. image:: images/register_aergo_erc20.png


Deploy the bridge contracts
---------------------------
The sender of the deployment tx will be the bridge owner.

.. code-block:: bash

    $ python3 -m ethaergo_bridge_operator.bridge_deployer --help                                                                                                                                                                           18h17m ⚑ ◒  
        usage: bridge_deployer.py [-h] -c CONFIG_FILE_PATH -a AERGO -e ETH
                                [--privkey_name PRIVKEY_NAME] [--local_test]

        Deploy bridge contracts between Ethereum and Aergo.

        optional arguments:
        -h, --help            show this help message and exit
        -c CONFIG_FILE_PATH, --config_file_path CONFIG_FILE_PATH
                                Path to config.json
        -a AERGO, --aergo AERGO
                                Name of Aergo network in config file
        -e ETH, --eth ETH     Name of Ethereum network in config file
        --privkey_name PRIVKEY_NAME
                                Name of account in config file to sign anchors
        --local_test          Start proposer with password for testing 

    $ python3 -m ethaergo_bridge_operator.bridge_deployer -c './test_config.json' -a 'aergo-local' -e eth-poa-local --privkey_name "proposer"

        DEPLOY MERKLE BRIDGE
        ------ DEPLOY BRIDGE BETWEEN Aergo & Ethereum -----------
        ------ Connect Hera and Web3 providers -----------
        ------ Set Sender Account -----------
        > Sender Address Aergo: AmPxVdu993eosN3UjnPDdN3wb7TNbHeiHDvn2dvZUcH8KXDK3RLU
        > Sender Address Ethereum: 0xc19b69591141443676a3EE56fbf1d3EA869d53D8
        ------ Deploy Aergo SC -----------
            > result[CrbmTHjGLEdgtKF7zUicgPwTZMYuueiX76mu87w7U2YE] : TX_OK
        ------ Deploy Ethereum SC -----------
        > Bridge Address Ethereum: 0xa146911F6779301D131139353960216D179693D6
        > Bridge Address Aergo: AmhJjVxa7Yp8CiXpTXVhoDXiDa66SD6rsejbimPFNxzvPNbLzEg5
        ------ Store bridge addresses in test_config.json  -----------


Send native aer to the bridge contract
--------------------------------------

After deployment, the aer on the Aergo network should be sent (frozen) to the bridge contract so 
that it can be unfrozen when users send their erc20 from the ethereum network.

Transfer control of the bridge to the multisig oracle
-----------------------------------------------------

The oracle_deployer script will deploy the oracle contract (with validators previously registered in config.json),
and transfer ownership to the newly deployed contract.

.. code-block:: bash

    $ python3 -m ethaergo_bridge_operator.oracle_deployer --help                                                                                                                                                                           18h17m ⚑ ◒  

        DEPLOY ORACLE
        usage: oracle_deployer.py [-h] -c CONFIG_FILE_PATH -a AERGO -e ETH
                                [--privkey_name PRIVKEY_NAME] [--local_test]

        Deploy oracle contracts to controle the bridge between Ethereum and Aergo.

        optional arguments:
        -h, --help            show this help message and exit
        -c CONFIG_FILE_PATH, --config_file_path CONFIG_FILE_PATH
                                Path to config.json
        -a AERGO, --aergo AERGO
                                Name of Aergo network in config file
        -e ETH, --eth ETH     Name of Ethereum network in config file
        --privkey_name PRIVKEY_NAME
                                Name of account in config file to sign anchors
        --local_test          Start proposer with password for testing

    $ python3 -m ethaergo_bridge_operator.oracle_deployer -c './test_config.json' -a 'aergo-local' -e eth-poa-local --privkey_name "proposer"

        DEPLOY ORACLE
        aergo validators :  ['AmNLjcxUDmxeGZL7F8bqyaGt3zqog5HAoJmFBEZAx1RvfTKLSBsQ', 'AmNLjcxUDmxeGZL7F8bqyaGt3zqog5HAoJmFBEZAx1RvfTKLSBsQ', 'AmNLjcxUDmxeGZL7F8bqyaGt3zqog5HAoJmFBEZAx1RvfTKLSBsQ']
        ethereum validators :  ['0x210467b3849a408c3a3bEE14b4627aa57F342134', '0x210467b3849a408c3a3bEE14b4627aa57F342134', '0x210467b3849a408c3a3bEE14b4627aa57F342134']
        ------ DEPLOY BRIDGE BETWEEN Aergo & Ethereum -----------
        ------ Connect AERGO -----------
        ------ Connect Web3 -----------
        ------ Set Sender Account -----------
        > Sender Address Aergo: AmPxVdu993eosN3UjnPDdN3wb7TNbHeiHDvn2dvZUcH8KXDK3RLU
        > Sender Address Ethereum: 0xc19b69591141443676a3EE56fbf1d3EA869d53D8
        ------ Deploy Aergo SC -----------
            > result[7bATQt58yd64cYY7h8YUSvQoU6NLFB6SXDUnRD1x39Mx] : TX_OK
        ------ Deploy Ethereum SC -----------
        > Oracle Address Ethereum: 0xF05692cE866f21b5E108781055AdEDde00E50872
        > Oracle Address Aergo: AmgwgSFDwtdxzdfa4kUxuYXMWkHN1MLZMVANBcm85rpsDSaAymFU
        ------ Store bridge addresses in test_config.json  -----------
        ------ Transfer bridge control to oracles -----------