from aergo_wallet.wallet import AergoWallet


if __name__ == '__main__':
    print("\n\nDEPLOY TEST ARC1 on Aergo")
    wallet = AergoWallet("./test_config.json")
    # deploy test token
    total_supply = 500*10**6*10**18
    with open("./contracts/lua/std_token_bytecode.txt", "r") as f:
        payload_str = f.read()[:-1]
    addr = wallet.deploy_token(
        payload_str, "token1", total_supply, "aergo-local", privkey_pwd='1234'
    )
    print("ARC1 token address: " + addr)
