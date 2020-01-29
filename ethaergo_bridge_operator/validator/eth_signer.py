from web3 import (
    Web3,
)


class EthSigner():
    def __init__(
        self,
        keystore: str,
        privkey_name: str,
        privkey_pwd: str
    ) -> None:
        self.web3 = Web3()
        self.eth_privkey = self.web3.eth.account.decrypt(
            keystore, privkey_pwd)
        acct = self.web3.eth.account.from_key(self.eth_privkey)
        self.address = acct.address

    def sign(self, h: bytes):
        return self.web3.eth.account.signHash(h, private_key=self.eth_privkey)
