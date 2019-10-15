from aergo_wallet.wallet import AergoWallet
from ethaergo_wallet.wallet import EthAergoWallet
import pytest


@pytest.fixture(scope="session")
def aergo_wallet():
    wallet = AergoWallet("./test_config.json")
    return wallet


@pytest.fixture(scope="session")
def bridge_wallet(aergo_wallet):
    wallet = EthAergoWallet("./test_config.json")
    return wallet
