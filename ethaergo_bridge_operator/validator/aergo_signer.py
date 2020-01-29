import aergo.herapy as herapy


class AergoSigner():
    def __init__(
        self,
        keystore: str,
        privkey_name: str,
        privkey_pwd: str
    ) -> None:
        self.hera = herapy.Aergo()
        self.hera.import_account_from_keystore(
            keystore, privkey_pwd, skip_state=True)
        self.address = str(self.hera.account.address)

    def sign(self, h: bytes):
        return self.hera.account.private_key.sign_msg(h)
