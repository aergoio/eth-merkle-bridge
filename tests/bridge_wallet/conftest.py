from wallet.wallet import Wallet
from ethaergo_wallet.wallet import EthAergoWallet

import pytest


@pytest.fixture(scope="session")
def aergo_wallet():
    wallet = Wallet("./config.json")
    total_supply = 500*10**6*10**18
    with open("./contracts/lua/std_token_bytecode.txt", "r") as f:
        payload_str = f.read()[:-1]
    wallet.deploy_token(
        payload_str, "token1", total_supply, "aergo-local", privkey_pwd='1234'
    )
    balance, _ = wallet.get_balance('token1', 'aergo-local')
    return wallet


@pytest.fixture(scope="session")
def bridge_wallet(aergo_wallet):
    wallet = EthAergoWallet("./config.json")
    return wallet
