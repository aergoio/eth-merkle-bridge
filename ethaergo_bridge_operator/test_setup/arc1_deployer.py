import json

import aergo.herapy as herapy


if __name__ == '__main__':
    print("\n\nDEPLOY TEST ARC1 on Aergo")
    privkey_name = 'default'
    privkey_pwd = '1234'
    config_path = './test_config.json'
    network_name = 'aergo-local'
    asset_name = 'token1'

    # deploy test token
    total_supply = 500*10**6*10**18
    with open("./contracts/lua/std_token_bytecode.txt", "r") as f:
        payload_str = f.read()[:-1]
    with open(config_path, "r") as f:
        config_data = json.load(f)
    keystore_path = config_data["wallet"][privkey_name]['keystore']
    with open(keystore_path, "r") as f:
        keystore = f.read()

    hera = herapy.Aergo()
    hera.connect(config_data['networks'][network_name]['ip'])
    hera.import_account_from_keystore(keystore, privkey_pwd)
    receiver = str(hera.account.address)

    tx, result = hera.deploy_sc(
        amount=0, payload=payload_str,
        args=[{"_bignum": str(total_supply)}, receiver]
    )
    if result.status != herapy.CommitStatus.TX_OK:
        print("Token deployment Tx commit failed : {}".format(result))

    result = hera.wait_tx_result(tx.tx_hash)
    if result.status != herapy.TxResultStatus.CREATED:
        print("Token deployment Tx execution failed : {}".format(result))

    sc_address = result.contract_address
    print("ARC1 token address: " + sc_address)

    config_data['networks'][network_name]['tokens'][asset_name] = {}
    config_data['networks'][network_name]['tokens'][asset_name]['addr'] = sc_address
    config_data['networks'][network_name]['tokens'][asset_name]['pegs'] = {}

    with open(config_path, "w") as f:
        json.dump(config_data, f, indent=4, sort_keys=True)
