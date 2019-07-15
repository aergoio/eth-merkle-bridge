from getpass import getpass

from wallet.wallet import Wallet


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
    w = Wallet(config_file_path)
    aergo_bridge = w.config_data('networks', aergo_net, 'bridges', eth_net,
                                 'addr')
    tx_hash = w.transfer(amount, aergo_bridge, 'aergo', aergo_net,
                         privkey_name=bridge_vault, privkey_pwd=privkey_pwd)
    print('\u2744 Freeze success: ', tx_hash)


if __name__ == '__main__':
    freeze_aergo('./test_config.json', 'aergo-local', 'eth-poa-local',
                 'bridge-vault', 100000000000000000000000, '1234')
