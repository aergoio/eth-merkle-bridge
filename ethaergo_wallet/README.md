# EthAergo wallet package

## Transfer AergoERC20 from Ethereum to Aergo and back again
``` py
from ethaergo_wallet.wallet import EthAergoWallet

# create a wallet
wallet = EthAergoWallet("./test_config.json")

amount = 1*10**18
asset = 'aergo_erc20'
receiver = "AmNMFbiVsqy6vg4njsTjgy7bKPFHFYhLV4rzQyrENUS9AM1e3tw5"
# initiate transfer to aergo network
lock_height, _ = wallet.lock_to_aergo('eth-poa-local', 'aergo-local', asset, amount, receiver, privkey_name='default')
# finalize transfer to aergo network
wallet.unfreeze('eth-poa-local', 'aergo-local', receiver, lock_height, privkey_name='default')

receiver = "0xfec3c905bcd3d9a5471452e53f82106844cb1e76"
# initiate transfer back to ethereum network
freeze_height, _ = wallet.freeze('aergo-local', 'eth-poa-local', amount, receiver, privkey_name='default')
# finalize transfer back to ethereum network
wallet.unlock_to_eth('aergo-local', 'eth-poa-local', asset, receiver, freeze_height, privkey_name='default')
```

## Query pending transfer

``` py
from ethaergo_wallet.wallet import EthAergoWallet

wallet = EthAergoWallet("./test_config.json")
receiver = "AmNMFbiVsqy6vg4njsTjgy7bKPFHFYhLV4rzQyrENUS9AM1e3tw5"
withdrawable_now, pending = wallet.unfreezeable('eth-poa-local', 'aergo-local', receiver)
```