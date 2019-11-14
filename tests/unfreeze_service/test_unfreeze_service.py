import grpc

from unfreeze_service.unfreeze_service_pb2_grpc import (
    UnfreezeServiceStub,
)
from unfreeze_service.unfreeze_service_pb2 import (
    AccountRef,
)


def test_aergo_erc20_unfreeze_service(bridge_wallet):
    aergo_receiver = bridge_wallet.config_data('wallet', 'receiver', 'addr')
    broadcaster = bridge_wallet.config_data('wallet', 'broadcaster', 'addr')
    # connect to unfreeze service
    channel = grpc.insecure_channel('localhost:7891')
    stub = UnfreezeServiceStub(channel)
    account_ref = AccountRef(receiver=aergo_receiver)

    # balances at destination before transfer init
    balance_destination_before_rec, _ = bridge_wallet.get_balance_aergo(
        'aergo_erc20', 'aergo-local', 'eth-poa-local',
        account_addr=aergo_receiver
    )
    balance_destination_before_ser, _ = bridge_wallet.get_balance_aergo(
        'aergo_erc20', 'aergo-local', 'eth-poa-local',
        account_addr=broadcaster
    )

    # Lock
    bridge_wallet.lock_to_aergo(
        'eth-poa-local', 'aergo-local', 'aergo_erc20',
        5*10**18, aergo_receiver, privkey_pwd='1234'
    )
    pending = 1
    while pending != 0:
        _, pending = bridge_wallet.unfreezable(
            'eth-poa-local', 'aergo-local', aergo_receiver)
    # request unfreeze
    status = stub.RequestUnfreeze(account_ref)
    assert not status.error

    # assert success and store tx_hash
    # request again
    # assert not enough to unfreeze
    hera = bridge_wallet.connect_aergo('aergo-local')
    tx_fee = int(hera.wait_tx_result(status.txHash).fee_used)

    # balances at destination after unfreeze service
    balance_destination_after_rec, _ = bridge_wallet.get_balance_aergo(
        'aergo_erc20', 'aergo-local', 'eth-poa-local',
        account_addr=aergo_receiver
    )
    balance_destination_after_ser, _ = bridge_wallet.get_balance_aergo(
        'aergo_erc20', 'aergo-local', 'eth-poa-local',
        account_addr=broadcaster
    )
    # check the fee was taken by broadcaster service
    assert balance_destination_after_rec == \
        balance_destination_before_rec + 5*10**18 - 1000
    assert balance_destination_after_ser == \
        balance_destination_before_ser + 1000 - tx_fee

    # check error returned if amount to unfreeze doesnt cover fee
    status = stub.RequestUnfreeze(account_ref)
    assert status.error == "Aergo native to unfreeze doesnt cover the fee"
