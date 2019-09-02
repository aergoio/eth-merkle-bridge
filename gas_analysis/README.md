# Gas analysis

## Anchoring on Ethereum

At regular intervals, the bridge operator anchors the state of the connected chain.
The anchoring cost increases with the number of validators that signed the anchor.

Gas cost of Aergo anchors on Ethereum:

- 3 validators : 65,000 gas
- 10 validators: 115,000 gas
- 20 validators: 185,000 gas

## User transactions on Ethereum
### Sending tokens from Ethereum to Aergo

Users first allow the bridge to pull tokens with 'increaseAllowance' or 'increaseApproval' (standard ERC20 operation). Then call the 'lock' function of the bridge contract to lock their assets for initiating a transfer.

Lock : 75,000 gas (Estimated value : depends on state size)

Tokens can then be minted on Aergo by calling the mint function

### Sending tokens from Aergo to Ethereum

Users first burn their tokens on Aergo and then call the Unlock function on Ethereum 

Unlock : 160,000 gas (Estimated value : depends on state size)

## Conclusion
Anchoring is reasonably cheap for it to happen regularly.
User transfers (Ethereum side) don't cost much more than a standard ERC20 token transfer.
