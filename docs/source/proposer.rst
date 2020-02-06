Proposer
========

A proposer connects to all validators and requests them to sign a new anchor 
with the GetEthAnchorSignature and GetAergoAnchorSignature rpc requests.
To prevent downtime, anybody can become a proposer and request signatures to validators.
It is the validator's responsibility to only sign correct anchors.
The bridge contracts will not update the state root if the anchoring time is not reached (t_anchor).


Starting a Proposer
-------------------

.. code-block:: bash

    $ python3 -m ethaergo_bridge_operator.proposer.client --help

        usage: client.py [-h] -c CONFIG_FILE_PATH -a AERGO -e ETH --eth_block_time
                    ETH_BLOCK_TIME [--privkey_name PRIVKEY_NAME]
                    [--privkey_pwd PRIVKEY_PWD] [--anchoring_on] [--auto_update]
                    [--oracle_update] [--eth_gas_price ETH_GAS_PRICE]
                    [--aergo_gas_price AERGO_GAS_PRICE] [--eco] [--eth_eco]

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
        --privkey_pwd PRIVKEY_PWD
                                Password to decrypt privkey_name(Eth and Aergo Keys
                                need the same password)
        --anchoring_on        Enable anchoring (can be diseabled when wanting to
                                only update settings)
        --auto_update         Update bridge contract when settings change in config
                                file
        --oracle_update       Update bridge contract when validators or oracle addr
                                change in config file
        --eth_gas_price ETH_GAS_PRICE
                                Gas price (gWei) to use in transactions
        --aergo_gas_price AERGO_GAS_PRICE
                                Gas price to use in transactions
        --eco                 In eco mode, anchoring will be skipped when
                                lock/burn/freeze events don't happen in the bridge
                                contracts
        --eth_eco             In eco mode, anchoring on Ethereum will be skipped
                                when lock/burn/freeze events don't happen in the
                                bridge contracts on Aergo

    $ python3 -m ethaergo_bridge_operator.proposer.client -c './test_config.json' -a 'aergo-local' -e 'eth-poa-local' --eth_block_time 3 --privkey_name "proposer" --anchoring_on

        proposer.eth: "Connect Aergo and Ethereum providers"
        proposer.eth: "aergo-local (t_final=5 ) -> eth-poa-local : t_anchor=7"
        proposer.eth: "Proposer Address: 0xc19b69591141443676a3EE56fbf1d3EA869d53D8"
        proposer.eth: "Connect to EthValidators"
        proposer.eth: "Validators: ['0x210467b3849a408c3a3bEE14b4627aa57F342134', '0x210467b3849a408c3a3bEE14b4627aa57F342134', '0x210467b3849a408c3a3bEE14b4627aa57F342134']"
        proposer.aergo: "Connect Aergo and Ethereum providers"
        proposer.aergo: "aergo-local <- eth-poa-local (t_final=4) : t_anchor=6"
        proposer.aergo: "Proposer Address: AmPxVdu993eosN3UjnPDdN3wb7TNbHeiHDvn2dvZUcH8KXDK3RLU"
        proposer.aergo: "Connect to AergoValidators"
        proposer.aergo: "Validators: ['AmNLjcxUDmxeGZL7F8bqyaGt3zqog5HAoJmFBEZAx1RvfTKLSBsQ', 'AmNLjcxUDmxeGZL7F8bqyaGt3zqog5HAoJmFBEZAx1RvfTKLSBsQ', 'AmNLjcxUDmxeGZL7F8bqyaGt3zqog5HAoJmFBEZAx1RvfTKLSBsQ']"
        proposer.eth: "Start Eth proposer"
        proposer.aergo: "Current Eth -> Aergo ⚓ anchor: height: 0, root: 0xconstructor, nonce: 0"
        proposer.aergo: "🖋 Gathering validator signatures for: root: 0xd97d33cb90c9e58befdba86467907ba68258b49f0f85a22781db7c4eda3033e4, height: 8262'"
        proposer.eth: "Current Aergo -> Eth ⚓ anchor: height: 0, root: 0x0000000000000000000000000000000000000000000000000000000000000000, nonce: 0"
        proposer.eth: "🖋 Gathering validator signatures for: root: 0x5d471941372b64d66361c29fca4e13c899819afe212cce87143794d80b510613, height: 8280'"
        proposer.eth: "⚓ Anchor success, ⏰ wait until next anchor time: 7s..."
        proposer.eth: "⛽ Gas used: 109287"
        proposer.aergo: "⚓ Anchor success, ⏰ wait until next anchor time: 6s..."


Updating bridge settings
------------------------

Bridge settings are updated when the config file changes and the proposer is started with --auto_update
The proposer will then try to gather signatures from validators to make the update on chain.

.. image:: images/t_anchor_update.png

If the new anchoring periode reached validator consensus, 
it can then be automatically updated in the bridge contract by the proposer.


.. code-block:: bash

    proposer.aergo: "Anchoring periode update requested: 7"
    proposer.aergo: "⌛ tAnchorUpdate success"
