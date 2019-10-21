from web3 import (
    Web3,
)


class EthSigner():
    def __init__(self, root_path, config_data, privkey_name, privkey_pwd):
        keystore = config_data["wallet-eth"][privkey_name]['keystore']
        with open(root_path + keystore, "r") as f:
            encrypted_key = f.read()

        self.web3 = Web3()
        self.eth_privkey = self.web3.eth.account.decrypt(encrypted_key,
                                                         privkey_pwd)
        acct = self.web3.eth.account.from_key(self.eth_privkey)
        self.address = acct.address

    def sign(self, h: bytes):
        return self.web3.eth.account.signHash(h, private_key=self.eth_privkey)
