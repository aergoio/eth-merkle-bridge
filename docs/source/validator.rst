Validator
=========

A validator will sign any state root from any proposer via the GetAnchorSignature rpc request as long as it is valid.
Therefore a validator must run a full node.
Assets on the sidechain are secure as long as 2/3 of the validators validate both chains and are honnest.
Since signature verification only happens when anchoring (and not when transfering assets), 
the number of validators can be very high as the signature verification cost is necessary only once per anchor.

Starting a Validator
--------------------

.. code-block:: bash

    $ python3 -m ethaergo_bridge_operator.validator.server --help

        usage: server.py [-h] -c CONFIG_FILE_PATH -a AERGO -e ETH -i VALIDATOR_INDEX
                        [--privkey_name PRIVKEY_NAME] [--anchoring_on]
                        [--auto_update] [--oracle_update] [--local_test]

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
        --anchoring_on        Enable anchoring (can be diseabled when wanting to
                                only update settings)
        --auto_update         Update bridge contract when settings change in config
                                file
        --oracle_update       Update bridge contract when validators or oracle addr
                                change in config file
        --local_test          Start all validators locally for convenient testing

    $ python3 -m ethaergo_bridge_operator.validator.server -c './test_config.json' -a 'aergo-local' -e 'eth-poa-local' --validator_index 1 --privkey_name "validator" --auto_update

        "Connect Aergo and Ethereum"
        "Current Aergo validators : ['AmNLjcxUDmxeGZL7F8bqyaGt3zqog5HAoJmFBEZAx1RvfTKLSBsQ', 'AmNLjcxUDmxeGZL7F8bqyaGt3zqog5HAoJmFBEZAx1RvfTKLSBsQ', 'AmNLjcxUDmxeGZL7F8bqyaGt3zqog5HAoJmFBEZAx1RvfTKLSBsQ']"
        "Current Ethereum validators : ['0x210467b3849a408c3a3bEE14b4627aa57F342134', '0x210467b3849a408c3a3bEE14b4627aa57F342134', '0x210467b3849a408c3a3bEE14b4627aa57F342134']"
        "aergo-local <- eth-poa-local (t_final=4) : t_anchor=6"
        "aergo-local (t_final=5) -> eth-poa-local : t_anchor=7"
        "WARNING: This validator will vote for settings update in config.json"
        Decrypt Aergo and Ethereum accounts 'validator'
        Password: 
        "Aergo validator Address: AmNLjcxUDmxeGZL7F8bqyaGt3zqog5HAoJmFBEZAx1RvfTKLSBsQ"
        "Ethereum validator Address: 0x210467b3849a408c3a3bEE14b4627aa57F342134"
        "server 1 started"
        {"val_index": 1, "signed": true, "type": "⚓ anchor", "value": {"root": "0xd97d33cb90c9e58befdba86467907ba68258b49f0f85a22781db7c4eda3033e4", "height": 8102}, "destination": "aergo-local", "nonce": 0}
        {"val_index": 1, "signed": true, "type": "⚓ anchor", "value": {"root": "0x5d471941372b64d66361c29fca4e13c899819afe212cce87143794d80b510613", "height": 8119}, "destination": "eth-poa-local", "nonce": 0}


Updating bridge settings
------------------------

The information (validator set, anchoring periods, finality of blockchains) contained in the config file
will be used by the validator to vote on changes if --auto_update is enabled.
Be careful that the information in config file is correct as any proposer can request a signature of that information.
If the proposer gathers 2/3 signatures for the same information them the bridge settings can be updated.


.. image:: images/t_anchor_update.png