def _test_transfer(wallet, asset, fee=0):
    """ Basic token/aer transfer on it's native chain."""
    to = wallet.get_wallet_address('receiver')
    amount = 2

    to_balance, _ = wallet.get_balance(asset, 'aergo-local',
                                       account_name='receiver')
    print('receiver balance before', to_balance)
    from_balance, _ = wallet.get_balance(asset, 'aergo-local')
    print('sender balance before', from_balance)

    wallet.transfer(amount, to, asset, 'aergo-local', privkey_pwd='1234')

    to_balance_after, _ = wallet.get_balance(asset, 'aergo-local',
                                             account_name='receiver')
    print('receiver balance after', to_balance_after)
    from_balance_after, _ = wallet.get_balance(asset, 'aergo-local')
    print('sender balance after', from_balance_after)

    assert to_balance_after == to_balance + amount
    assert from_balance_after == from_balance - amount - fee


def test_aer_transfer(aergo_wallet):
    return _test_transfer(aergo_wallet, 'aergo', fee=0)


def test_token_transfer(aergo_wallet):
    return _test_transfer(aergo_wallet, 'token1')