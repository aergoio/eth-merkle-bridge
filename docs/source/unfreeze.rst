Unfreeze service
================

The unfreeze service provides the service to users that want to transfer Aergo erc20 to Aergo Mainnet
(Aergo Native) but don't already own Aergo Native to pay for the unfreeze transaction fee.

The bridge contract on Aergo check if the tx sender is the same as the Aergo Native receiver and if they
are different, if will transfer _unfreezeFee to the tx sender and send the rest to the receiver.

The RequestUnfreeze service will check the receiver address is valid and that the amount to unfreeze is higher
than the _unfreezeFee.