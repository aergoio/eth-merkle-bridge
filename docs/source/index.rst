Welcome to the EthAergo Merkle bridge documentation!
====================================================

The EthAergo bridge is an efficient and descentralized way of connecting blockchains.
The repository is the POC implementation of Aergo's bridge design between Aergo and Ethereum networks.

Merkle bridge design.
----------------------

In order to transfer an asset from one blockchain to another blockchain, it should be locked on it’s origin chain and minted on the destination chain. 
At all times the minted assets should be pegged to the locked assets. 

The EthAergo Merkle Bridge enables decentralized custody and efficient minting of assets. 

At regular intervals, a proposer publishes the state root of the bridge contract on the bridged chain. 
The state root is recorded only if it has been signed by 2/3 of validators. 
Users can then independently mint assets on the destination bridge contract by verifying a merkle proof of their locked assets with the anchored state root.

The proposers do not need to watch and validate user transfers: the benefit of the merkle bridge design comes from the fact that
validators simply make sure that the state roots they sign are correct. Since onchain signature verification is only done once per root anchor,
it is possible use a large number of validators for best safety and sensorship resistance. 


.. toctree::
   :maxdepth: 3
   :caption: Contents:

   getting_started
   cli_operation
   proposer
   validator
   contracts
   config
   

.. toctree::
   :maxdepth: 2
   :caption: References:

   ethaergo_operator
   ethaergo_wallet
   ethaergo_cli



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
