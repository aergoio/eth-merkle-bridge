from getpass import getpass
from aergo_wallet.wallet import AergoWallet


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

    w = AergoWallet(config_file_path)
    aergo_bridge = w.config_data('networks', aergo_net, 'bridges', eth_net,
                                 'addr')
    w.transfer(amount, aergo_bridge, 'aergo', aergo_net,
               privkey_name=bridge_vault, privkey_pwd=privkey_pwd)


if __name__ == '__main__':
    freeze_aergo('./test_config.json', 'aergo-local', 'eth-poa-local',
                 'bridge-vault', 100000000000000000000000, '1234')
