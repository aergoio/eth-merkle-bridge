Configuration file
==================

The config file is used by the bridge operators, the wallet and the cli to store information about
node connections, validator connections, bridge parameters, assets and private keys.

It can be created and updated manually of with the help of the cli.

.. code-block:: js

    {
        "networks": { // list of registered networks
            "aergo-local": { // name of the network
                "bridges": { // list of bridges between 'aergo-local' and other blockchains
                    "eth-poa-local": { // name of bridged network
                        "addr": "AmhXrQ7KdNA4naBi2sTwHj13aBzVBohRhxy262nXsPbV2YbULXUR", // address of bridge contract
                        "oracle": "AmgQdbUqDuoX5krsmvSEHc9X3apBuXyJTQ4mimfWzejEsYScTo3f", // address of oracle controlling 'addr' bridge contract
                        "t_anchor": 6, // anchoring periode in bridge contract
                        "t_final": 4 // finality of chain anchored on bridge contract
                    }
                },
                "ip": "localhost:7845", // node connection ip
                "providers": [
                    "localhost:7845",
                    "localhost:7845"
                ], // redundant providers for validators to query different data sources
                "tokens": { // list of tokens originating from 'aergo-local'
                    "aergo": { // aer native asset
                        "addr": "aergo", // 'aergo' is the reserved name and address
                        "pegs": {}
                    },
                    "token1": { // asset name
                        "addr": "AmghHtk2gpcpMa6bj1v59qCBfNmKZTi8qDGeuMNg5meJuXGTa2Y1", // asset addresss
                        "pegs": { // list of networks where this asset has a peg
                            "eth-poa-local": "0xB7633077842e3fb1877e43C0cCa0972dB8bb6Fb0" // address of pegged asset
                        }
                    }
                },
                "type": "aergo" // type of network to differenciate between Aergo and Ethereum
            },
            "eth-poa-local": {
                "bridges": {
                    "aergo-local": {
                        "addr": "0xbC5385259C2Dfdd99996CFb9B6C2f92767FcB32b",
                        "bridge_abi": "contracts/solidity/bridge_abi.txt", // path to bridge abi
                        "minted_abi": "contracts/solidity/minted_erc20_abi.txt", // path to minted token abi
                        "oracle": "0x5b9fd5f3e14F0F886AD11aCc24Ff53823Bf9bdb5",
                        "oracle_abi": "contracts/solidity/oracle_abi.txt", // path to oracle abi
                        "t_anchor": 7,
                        "t_final": 5
                    }
                },
                "ip": "localhost:8545",
                "providers": [
                    "http://localhost:8545",
                    "http://localhost:8545"
                ], // redundant providers for validators to query different data sources
                "isPOA": true, // web3py needs middleware to connect to POA chains
                "tokens": {
                    "aergo_erc20": { // reserved name of aergo erc20 issued at ico
                        "abi": "contracts/solidity/aergo_erc20_abi.txt",
                        "addr": "0xd898383A12CDE0eDF7642F7dD4D7006FdE5c433e",
                        "pegs": {
                            "aergo-local": "aergo"
                        }
                    },
                    "test_erc20": {
                        "abi": "contracts/solidity/aergo_erc20_abi.txt",
                        "addr": "0xeeEF65f288b39d1514A54852566415b973927142",
                        "pegs": {
                            "aergo-local": "AmhiUx2hZ9phVDMZoBShEWD2sCFXPJ5BZpagNC8WfssPuZg7wzZS"
                        }
                    }
                },
                "type": "ethereum"
            }
        },
        "validators": [ // list of validators, only needed for bridge operator
            {
                "addr": "AmNLjcxUDmxeGZL7F8bqyaGt3zqog5HAoJmFBEZAx1RvfTKLSBsQ", // validator address in Aergo bridge contract
                "eth-addr": "0x210467b3849a408c3a3bEE14b4627aa57F342134", // validator address in Ethereum bridge contract
                "ip": "localhost:9841" // ip of validator API
            },
            {
                "addr": "AmNyNPEqeXPfdHeECMNhsH1QcnZsqCtDAudjgFyG5qpasN6tyLPE",
                "eth-addr": "0x7acb4a265bf759ec772510c2465fb7c8f4eaf54e",
                "ip": "localhost:9842"
            },
            {
                "addr": "AmPf349iHWd6kQGU45BxFzFCzEDu75Y3FqFPd4WBMteFq4mtDuZd",
                "eth-addr": "0xf1bf3497d98ead7f6a1bb9ee6dfbde9d448d7062",
                "ip": "localhost:9843"
            }
        ],
        "wallet": { // list of Aergo wallets
            "default": { // name of wallet
                "addr": "AmNPWDJMjU4g98Scm4AikW8JwQMGwWMztM7Qy8ggxNTkhgZMJHFp", // address matching private key
                "keystore": "keystore/AmNPWDJMjU4g98Scm4AikW8JwQMGwWMztM7Qy8ggxNTkhgZMJHFp__2020-01-20T04:13:06__keystore.json" // path to json keystore
            }
        },
        "wallet-eth": { // list of Ethereum wallets
            "default": { // name of wallet
                "addr": "0xfec3c905bcd3d9a5471452e53f82106844cb1e76", // address matching private key
                "keystore": "keystore/UTC--2019-05-13T09-23-35.377701000Z--fec3c905bcd3d9a5471452e53f82106844cb1e76" // path to json keystore
            }
        }
    }