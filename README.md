# eth-merkle-bridge
Eth&lt;-->Aergo Merkle Bridge 

The Eth-Aergo Merkle bridge follows a similar design to the Aergo-Aergo Merkle bridge with some key differences : the total aer supply is already minted on Aergo mainnet (locked in the Lua bridge contract so Aer is unfreezed/freezed instead of minted/burnt) and the Lua bridge contract needs to verify Ethereum Patricia Lock tree merkle proofs.

## TODO

### Lua bridge contract:
- Patricia tree proof verification
- RLP proof node decoder (Lua native: https://github.com/ethereum/wiki/wiki/RLP)
- Keccak hash function (Lua native: https://ethereum.stackexchange.com/questions/550/which-cryptographic-hash-function-does-ethereum-use)
- If ERC20Aergo transfered to mainnet, unfreeze locked aer instead of minting

### Solidity bridge contract:
- SMT merkle proof verification
- 2 step Lock with transfer_from() instead of signed transfer

### Proposer / Validator
- connect to Aergo Mainnet full node with herapy
- connect to Ethereum full node with web3py
- anchoring on ethereum : validator signatures to be verified by ecrecover

### Python command line wallet
- build lock merkle proofs with web3py
- build freeze merkle proofs with herapy
- support ethereum tx and aergo tx

### Tx broadcaster
- Cannot be supported because users need to pay eth fees anyway to call approve_transfer(), and delegated token transfers through bridge are only secure if sender == receiver (Eth addr != Aergo addr).

### Aergo Connect User UI
- Get Lock merkle proofs from Ethereum full node provided by Blocko/Aergo with web3js
- Add eth_GetProof to web3js (same as web3py : https://github.com/ethereum/web3.py/pull/1185)
- Get Burn/Freeze merkle proofs from Aergo full node (herajs)
- Support Ethereum and Aergo private keys for Lock() and Unlock() tx with merkle proof in argument
