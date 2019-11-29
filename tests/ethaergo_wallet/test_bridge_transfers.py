def test_standard_token_transfer(bridge_wallet):
    eth_user = bridge_wallet.config_data('wallet-eth', 'default', 'addr')
    aergo_user = bridge_wallet.config_data('wallet', 'default', 'addr')

    balance_origin_before, _ = bridge_wallet.get_balance_aergo(
        'token1', 'aergo-local', account_addr=aergo_user
    )
    # Aergo => Eth
    lock_height, _ = bridge_wallet.lock_to_eth(
        'aergo-local', 'eth-poa-local', 'token1', 5*10**18,
        eth_user, privkey_pwd='1234'
    )
    balance_origin_after, _ = bridge_wallet.get_balance_aergo(
        'token1', 'aergo-local', account_addr=aergo_user
    )
    assert balance_origin_after == balance_origin_before - 5*10**18
    bridge_wallet.mint_to_eth(
        'aergo-local', 'eth-poa-local', 'token1', eth_user,
        lock_height, privkey_pwd='1234'
    )
    balance_destination_after, _ = bridge_wallet.get_balance_eth(
        'token1', 'eth-poa-local', 'aergo-local', account_addr=eth_user
    )

    # Eth => Aergo
    burn_height, _ = bridge_wallet.burn_to_aergo(
        'eth-poa-local', 'aergo-local', 'token1',
        5*10**18, aergo_user, privkey_pwd='1234'
    )
    balance_origin_after2, _ = bridge_wallet.get_balance_eth(
        'token1', 'eth-poa-local', 'aergo-local', account_addr=eth_user
    )
    assert balance_origin_after2 == balance_destination_after - 5*10**18
    bridge_wallet.unlock_to_aergo(
        'eth-poa-local', 'aergo-local', 'token1', aergo_user, burn_height,
        privkey_pwd='1234'
    )
    balance_destination_after2, _ = bridge_wallet.get_balance_aergo(
        'token1', 'aergo-local', account_addr=aergo_user
    )
    assert balance_origin_after2 == balance_destination_after - 5*10**18
    assert balance_destination_after2 == balance_origin_before


def test_erc20_token_transfer(bridge_wallet):
    eth_user = bridge_wallet.config_data('wallet-eth', 'default', 'addr')
    aergo_user = bridge_wallet.config_data('wallet', 'default', 'addr')

    # Eth => Aergo
    balance_origin_before, _ = bridge_wallet.get_balance_eth(
        'test_erc20', 'eth-poa-local', account_addr=eth_user
    )
    lock_height, _ = bridge_wallet.lock_to_aergo(
        'eth-poa-local', 'aergo-local', 'test_erc20',
        5*10**18, aergo_user, privkey_pwd='1234'
    )
    balance_origin_after, _ = bridge_wallet.get_balance_eth(
        'test_erc20', 'eth-poa-local', account_addr=eth_user
    )
    assert balance_origin_after == balance_origin_before - 5*10**18

    bridge_wallet.mint_to_aergo(
        'eth-poa-local', 'aergo-local', 'test_erc20', aergo_user, lock_height,
        privkey_pwd='1234'
    )
    balance_destination_after, _ = bridge_wallet.get_balance_aergo(
        'test_erc20', 'aergo-local', 'eth-poa-local', account_addr=aergo_user
    )
    # Aergo => Eth
    burn_height, _ = bridge_wallet.burn_to_eth(
        'aergo-local', 'eth-poa-local', 'test_erc20', 5*10**18, eth_user,
        privkey_pwd='1234'
    )
    balance_origin_after2, _ = bridge_wallet.get_balance_aergo(
        'test_erc20', 'aergo-local', 'eth-poa-local', account_addr=aergo_user
    )
    assert balance_origin_after2 == balance_destination_after - 5*10**18
    bridge_wallet.unlock_to_eth(
        'aergo-local', 'eth-poa-local', 'test_erc20',
        eth_user, burn_height,
        privkey_pwd='1234'
    )
    balance_destination_after2, _ = bridge_wallet.get_balance_eth(
        'test_erc20', 'eth-poa-local', account_addr=eth_user
    )
    assert balance_origin_after2 == balance_destination_after - 5*10**18
    assert balance_destination_after2 == balance_origin_before


def test_aergo_erc20_unfreeze(bridge_wallet):
    eth_user = bridge_wallet.config_data('wallet-eth', 'default', 'addr')
    aergo_user = bridge_wallet.config_data('wallet', 'default', 'addr')

    # Eth => Aergo
    balance_origin_before, _ = bridge_wallet.get_balance_eth(
        'aergo_erc20', 'eth-poa-local', account_addr=eth_user
    )
    lock_height, _ = bridge_wallet.lock_to_aergo(
        'eth-poa-local', 'aergo-local', 'aergo_erc20',
        5*10**18, aergo_user, privkey_pwd='1234'
    )
    balance_origin_after, _ = bridge_wallet.get_balance_eth(
        'aergo_erc20', 'eth-poa-local', account_addr=eth_user
    )
    assert balance_origin_after == balance_origin_before - 5*10**18

    bridge_wallet.unfreeze(
        'eth-poa-local', 'aergo-local', aergo_user, lock_height,
        privkey_pwd='1234'
    )
    balance_destination_after, _ = bridge_wallet.get_balance_aergo(
        'aergo_erc20', 'aergo-local', 'eth-poa-local', account_addr=aergo_user
    )
    # Aergo => Eth
    freeze_height, freeze_hash = bridge_wallet.freeze(
        'aergo-local', 'eth-poa-local', 5*10**18, eth_user,
        privkey_pwd='1234'
    )
    balance_origin_after2, _ = bridge_wallet.get_balance_aergo(
        'aergo_erc20', 'aergo-local', 'eth-poa-local', account_addr=aergo_user
    )

    hera = bridge_wallet.get_aergo('aergo-local', 'default', '1234')
    freeze_fee = int(hera.get_tx_result(freeze_hash).fee_used)
    assert balance_origin_after2 == \
        balance_destination_after - 5*10**18 - freeze_fee
    bridge_wallet.unlock_to_eth(
        'aergo-local', 'eth-poa-local', 'aergo_erc20',
        eth_user, freeze_height,
        privkey_pwd='1234'
    )
    balance_destination_after2, _ = bridge_wallet.get_balance_eth(
        'aergo_erc20', 'eth-poa-local', account_addr=eth_user
    )
    assert balance_origin_after2 == \
        balance_destination_after - 5*10**18 - freeze_fee
    assert balance_destination_after2 == balance_origin_before


def test_aergo_erc20_unfreeze_service(bridge_wallet):
    aergo_receiver = bridge_wallet.config_data('wallet', 'receiver', 'addr')
    aergo_service = bridge_wallet.config_data('wallet', 'default', 'addr')
    lock_height, _ = bridge_wallet.lock_to_aergo(
        'eth-poa-local', 'aergo-local', 'aergo_erc20',
        5*10**18, aergo_receiver, privkey_pwd='1234'
    )
    balance_destination_before_rec, _ = bridge_wallet.get_balance_aergo(
        'aergo_erc20', 'aergo-local', 'eth-poa-local',
        account_addr=aergo_receiver
    )
    balance_destination_before_ser, _ = bridge_wallet.get_balance_aergo(
        'aergo_erc20', 'aergo-local', 'eth-poa-local',
        account_addr=aergo_service
    )
    tx_hash = bridge_wallet.unfreeze(
        'eth-poa-local', 'aergo-local', aergo_receiver, lock_height,
        privkey_pwd='1234'
    )
    hera = bridge_wallet.get_aergo('aergo-local', 'default', '1234')
    tx_fee = int(hera.get_tx_result(tx_hash).fee_used)
    # Eth => Aergo
    balance_destination_after_rec, _ = bridge_wallet.get_balance_aergo(
        'aergo_erc20', 'aergo-local', 'eth-poa-local',
        account_addr=aergo_receiver
    )
    balance_destination_after_ser, _ = bridge_wallet.get_balance_aergo(
        'aergo_erc20', 'aergo-local', 'eth-poa-local',
        account_addr=aergo_service
    )
    # check the fee was taken by broadcaster service
    assert balance_destination_after_rec == \
        balance_destination_before_rec + 5*10**18 - 1000
    assert balance_destination_after_ser == \
        balance_destination_before_ser + 1000 - tx_fee


def test_aergo_unfreezable(bridge_wallet):
    eth_user = bridge_wallet.config_data('wallet-eth', 'default', 'addr')
    aergo_user = bridge_wallet.config_data('wallet', 'default', 'addr')

    withdrawable, pending = bridge_wallet.unfreezable(
        'eth-poa-local', 'aergo-local', aergo_user
    )
    before_transfer = withdrawable + pending
    lock_height, _ = bridge_wallet.lock_to_aergo(
        'eth-poa-local', 'aergo-local', 'aergo_erc20',
        5*10**18, aergo_user, privkey_pwd='1234'
    )
    withdrawable, pending = bridge_wallet.unfreezable(
        'eth-poa-local', 'aergo-local', aergo_user
    )
    assert withdrawable + pending - before_transfer == 5*10**18
    # send tokens back to origin
    bridge_wallet.unfreeze(
        'eth-poa-local', 'aergo-local', aergo_user, lock_height,
        privkey_pwd='1234'
    )
    freeze_height, _ = bridge_wallet.freeze(
        'aergo-local', 'eth-poa-local', 5*10**18, eth_user,
        privkey_pwd='1234'
    )
    bridge_wallet.unlock_to_eth(
        'aergo-local', 'eth-poa-local', 'aergo_erc20',
        eth_user, freeze_height,
        privkey_pwd='1234'
    )


def test_token_withdrawable(bridge_wallet):
    eth_user = bridge_wallet.config_data('wallet-eth', 'default', 'addr')
    aergo_user = bridge_wallet.config_data('wallet', 'default', 'addr')

    withdrawable, pending = bridge_wallet.mintable_to_eth(
        'aergo-local', 'eth-poa-local', 'token1', eth_user
    )
    before_transfer = withdrawable + pending
    lock_height, _ = bridge_wallet.lock_to_eth(
        'aergo-local', 'eth-poa-local', 'token1', 5*10**18,
        eth_user, privkey_pwd='1234'
    )
    withdrawable, pending = bridge_wallet.mintable_to_eth(
        'aergo-local', 'eth-poa-local', 'token1', eth_user
    )
    assert withdrawable + pending - before_transfer == 5*10**18
    bridge_wallet.mint_to_eth(
        'aergo-local', 'eth-poa-local', 'token1', eth_user,
        lock_height, privkey_pwd='1234'
    )
    withdrawable, pending = bridge_wallet.unlockable_to_aergo(
        'eth-poa-local', 'aergo-local', 'token1', aergo_user
    )
    before_transfer = withdrawable + pending
    burn_height, _ = bridge_wallet.burn_to_aergo(
        'eth-poa-local', 'aergo-local', 'token1',
        5*10**18, aergo_user, privkey_pwd='1234'
    )
    withdrawable, pending = bridge_wallet.unlockable_to_aergo(
        'eth-poa-local', 'aergo-local', 'token1', aergo_user
    )
    assert withdrawable + pending - before_transfer == 5*10**18
    bridge_wallet.unlock_to_aergo(
        'eth-poa-local', 'aergo-local', 'token1', aergo_user, burn_height,
        privkey_pwd='1234'
    )


def test_erc20_withdrawable(bridge_wallet):
    eth_user = bridge_wallet.config_data('wallet-eth', 'default', 'addr')
    aergo_user = bridge_wallet.config_data('wallet', 'default', 'addr')

    withdrawable, pending = bridge_wallet.mintable_to_aergo(
        'eth-poa-local', 'aergo-local', 'test_erc20', aergo_user
    )
    before_transfer = withdrawable + pending
    lock_height, _ = bridge_wallet.lock_to_aergo(
        'eth-poa-local', 'aergo-local', 'test_erc20',
        5*10**18, aergo_user, privkey_pwd='1234'
    )
    withdrawable, pending = bridge_wallet.mintable_to_aergo(
        'eth-poa-local', 'aergo-local', 'test_erc20', aergo_user
    )

    assert withdrawable + pending - before_transfer == 5*10**18

    bridge_wallet.mint_to_aergo(
        'eth-poa-local', 'aergo-local', 'test_erc20', aergo_user, lock_height,
        privkey_pwd='1234'
    )

    withdrawable, pending = bridge_wallet.unlockable_to_eth(
        'aergo-local', 'eth-poa-local', 'test_erc20', eth_user,
    )
    before_transfer = withdrawable + pending
    burn_height, _ = bridge_wallet.burn_to_eth(
        'aergo-local', 'eth-poa-local', 'test_erc20', 5*10**18, eth_user,
        privkey_pwd='1234'
    )
    withdrawable, pending = bridge_wallet.unlockable_to_eth(
        'aergo-local', 'eth-poa-local', 'test_erc20', eth_user,
    )
    assert withdrawable + pending - before_transfer == 5*10**18
    bridge_wallet.unlock_to_eth(
        'aergo-local', 'eth-poa-local', 'test_erc20',
        eth_user, burn_height,
        privkey_pwd='1234'
    )
