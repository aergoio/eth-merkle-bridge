import aergo.herapy as herapy


class AergoSigner():
    def __init__(self, config_data, privkey_name, privkey_pwd):
        aergo_privkey = \
            config_data['wallet'][privkey_name]['priv_key']
        self.hera = herapy.Aergo()
        self.hera.import_account(aergo_privkey, privkey_pwd)
        self.address = str(self.hera.account.address)

    def sign(self, h: bytes):
        return self.hera.account.private_key.sign_msg(h)
