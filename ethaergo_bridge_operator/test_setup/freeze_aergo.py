from getpass import getpass
import json

import aergo.herapy as herapy


def freeze_aergo(
    config_file_path: str,
    aergo_net: str,
    eth_net: str,
    bridge_vault: str,
    amount: int,
    privkey_pwd: str = None,
):
    """ Send aergo from the vault account to the bridge (freeze).

    NOTE:
        This is mainly for deploying test bridge as other wallets like aergo
        connect can be used to transfer aer
    """

    if privkey_pwd is None:
        privkey_pwd = getpass("Decrypt Aergo private key '{}'\nPassword: "
                              .format(bridge_vault))
    with open(config_file_path, "r") as f:
        config_data = json.load(f)
    aergo_bridge = \
        config_data['networks'][aergo_net]['bridges'][eth_net]['addr']

    keystore_path = config_data["wallet"][bridge_vault]['keystore']
    with open(keystore_path, "r") as f:
        keystore = f.read()

    hera = herapy.Aergo()
    hera.connect(config_data['networks'][aergo_net]['ip'])
    hera.import_account_from_keystore(keystore, privkey_pwd)
    hera.send_payload(to_address=aergo_bridge, amount=amount, payload=None)


if __name__ == '__main__':
    freeze_aergo('./test_config.json', 'aergo-local', 'eth-poa-local',
                 'bridge-vault', 100000000000000000000000, '1234')
