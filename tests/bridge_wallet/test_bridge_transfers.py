def test_aer_transfer():
    assert True


def test_bridge_token_transfer(bridge_wallet):
    with open("./contracts/solidity/bridge_abi.txt", "r") as f:
        bridge_abi = f.read()
    with open("./contracts/solidity/minted_erc20_abi.txt", "r") as f:
        minted_erc20_abi = f.read()

    eth_user = bridge_wallet.config_data('wallet-eth', 'default', 'addr')
    aergo_user = bridge_wallet.config_data('wallet', 'default', 'addr')
    
    # Aergo => Eth
    lock_height, _ = bridge_wallet.lock_to_eth(
        'aergo-local', 'eth-poa-local', 'token1', 5*10**18,
        eth_user, privkey_pwd='1234'
    )
    bridge_wallet.mint_to_eth(
        'aergo-local', 'eth-poa-local', bridge_abi, 'token1',
        minted_erc20_abi, '0xfec3c905bcd3d9a5471452e53f82106844cb1e76',
        lock_height, privkey_pwd='1234', eth_poa=True
    )
    # Eth => Aergo
    burn_height, _ = bridge_wallet.burn_to_aergo(
        'eth-poa-local', 'aergo-local', bridge_abi, 'token1',
        minted_erc20_abi, 5*10**18, aergo_user, privkey_pwd='1234',
        eth_poa=True
    )
    bridge_wallet.unlock_to_aergo(
        'eth-poa-local', 'aergo-local', 'token1', aergo_user, burn_height,
        privkey_pwd='1234', eth_poa=True
    )