import hashlib
import inquirer
import json
from pyfiglet import Figlet

from ethaergo_wallet.wallet import (
    EthAergoWallet,
)
from ethaergo_wallet.exceptions import (
    InvalidArgumentsError,
    TxError,
    InsufficientBalanceError,
)

from cli.utils import (
    confirm_transfer,
    get_amount,
    get_asset_abi,
    get_deposit_height,
    get_bridge,
    get_network,
    get_eth_privkey,
    get_aergo_privkey,
    get_new_asset,
    get_validators,
)


class EthMerkleBridgeCli():
    def __init__(self):
        with open("./contracts/solidity/bridge_abi.txt", "r") as f:
            self.bridge_abi = f.read()
        with open("./contracts/solidity/minted_erc20_abi.txt", "r") as f:
            self.minted_erc20_abi = f.read()
        with open('cli/pending_transfers.json', 'r') as file:
            self.pending_transfers = json.load(file)

    def start(self):
        f = Figlet(font='speed')
        print(f.renderText('Eth Merkel Bridge Cli'))
        print("Welcome to the Eth Merkle Bridge Interactive CLI.\n"
              "This is a tool to transfer assets across the "
              "Ethereum <=> Aergo Merke bridge and manage wallet "
              "settings (config.json)\n")
        while 1:
            questions = [
                inquirer.List('YesNo',
                              message="Do you have a config.json? ",
                              choices=[('Yes, find it with the path', 'Y'),
                                       ('No, create one from scratch', 'N'),
                                       'Quit'])
            ]
            answers = inquirer.prompt(questions)
            if answers['YesNo'] == 'Y':
                self.load_config()
            elif answers['YesNo'] == 'N':
                self.create_config()
            else:
                return

    def load_config(self):
        while 1:
            questions = [
                inquirer.Text(
                    'config_file_path',
                    message="Path to config.json (path/to/config.json)"),
            ]
            config_file_path = inquirer.prompt(questions)['config_file_path']
            try:
                self.wallet = EthAergoWallet(config_file_path)
                return self.root()
            except (IsADirectoryError, FileNotFoundError):
                print("Invalid path/to/config.json")
                return

    def root(self):
        while 1:
            questions = [
                inquirer.List(
                    'action',
                    message="What would you like to do ? ",
                    choices=[
                        ('Check pending transfer', 'P'),
                        ('Initiate transfer (Lock/Burn)', 'I'),
                        ('Finalize transfer (Mint/Unlock)', 'F'),
                        ('Settings (Register Assets and Networks)', 'S'),
                        'Back',
                        ])
            ]
            answers = inquirer.prompt(questions)
            try:
                if answers['action'] == 'Back':
                    return
                elif answers['action'] == 'P':
                    self.check_withdrawable_balance()
                elif answers['action'] == 'I':
                    self.initiate_transfer()
                elif answers['action'] == 'F':
                    self.finalize_transfer()
                elif answers['action'] == 'S':
                    self.edit_settings()
            except (TypeError, KeyboardInterrupt, InvalidArgumentsError,
                    TxError, InsufficientBalanceError) as e:
                print('Someting went wrong, check the status of your pending '
                      'transfers\nError msg: {}'.format(e))

    def edit_settings(self):
        while 1:
            questions = [
                inquirer.List(
                    'action',
                    message="What would you like to do ? ",
                    choices=[
                        ('Register new asset', 'A'),
                        ('Register new network', 'N'),
                        ('Register new bridge', 'B'),
                        ('Register new set of validators', 'V'),
                        'Back',
                        ])
            ]
            answers = inquirer.prompt(questions)
            try:
                if answers['action'] == 'Back':
                    return
                elif answers['action'] == 'A':
                    self.register_asset()
                elif answers['action'] == 'N':
                    self.register_network()
                elif answers['action'] == 'V':
                    self.register_new_validators()
                elif answers['action'] == 'B':
                    self.register_bridge()
            except (TypeError, KeyboardInterrupt, InvalidArgumentsError) as e:
                print('Someting went wrong, check the status of you pending '
                      'transfers\nError msg: {}'.format(e))

    def create_config(self):
        new_config = {}
        print("Let's register 2 networks, "
              "validators(optional) and a private key for interacting with "
              "each network.")
        # Register 2 networks
        answers = get_network()
        net1 = answers['name']
        net1_type = answers['type']
        new_config['networks'] = {net1: {'ip': answers['ip'],
                                         'type': net1_type,
                                         'tokens': {}
                                         }
                                  }
        if net1_type == 'ethereum':
            new_config['networks'][net1]['isPOA'] = answers['isPOA']
        answers = get_network()
        net2 = answers['name']
        net2_type = answers['type']
        new_config['networks'][net2] = {'ip': answers['ip'],
                                        'type': net2_type,
                                        'tokens': {}
                                        }
        if net2_type == 'ethereum':
            new_config['networks'][net2]['isPOA'] = answers['isPOA']
        # Register bridge contracts on each network
        answers = get_bridge(net1, net2)
        new_config['networks'][net1]['bridges'] = {
            net2: {'addr': answers['bridge1'],
                   't_anchor': int(answers['t_anchor1']),
                   't_final': int(answers['t_final1'])
                   }
        }
        new_config['networks'][net2]['bridges'] = {
            net1: {'addr': answers['bridge2'],
                   't_anchor': int(answers['t_anchor2']),
                   't_final': int(answers['t_final2'])
                   }
        }
        # Register a new private key (ethereum + aergo)
        print("Register a private key for {}".format(net1))
        new_config['wallet-eth'] = {}
        new_config['wallet'] = {}
        if net1_type == 'ethereum':
            name, addr, privkey = get_eth_privkey()
            new_config['wallet-eth'][name] = {"addr": addr,
                                              "keystore": privkey}
        else:
            name, addr, privkey = get_aergo_privkey()
            new_config['wallet'][name] = {"addr": addr,
                                          "priv_key": privkey}
        print("Register a private key for {}".format(net2))
        if net2_type == 'ethereum':
            name, addr, privkey = get_eth_privkey()
            new_config['wallet-eth'][name] = {"addr": addr,
                                              "keystore": privkey}
        else:
            name, addr, privkey = get_aergo_privkey()
            new_config['wallet'][name] = {"addr": addr,
                                          "priv_key": privkey}

        # Register bridge validators
        questions = [
            inquirer.List(
                'YN',
                message='Would you like to register validators ? '
                        '(not needed for bridge users)',
                choices=['Yes', 'No']
            )
        ]
        if inquirer.prompt(questions)['YN'] == 'Yes':
            validators = get_validators()
            new_config['validators'] = validators
        else:
            new_config['validators'] = {}

        questions = [
            inquirer.Text(
                'path',
                message="Path to save new config file"
            )
        ]
        path = inquirer.prompt(questions)['path']

        with open(path, "w") as f:
            json.dump(new_config, f, indent=4, sort_keys=True)

    def register_bridge(self):
        net1, net2 = self.get_directions()
        answers = get_bridge(net1, net2)
        self.wallet.config_data(
            'networks', net1, 'bridges', net2,
            value={'addr': answers['bridge1'],
                   't_anchor': int(answers['t_anchor1']),
                   't_final': int(answers['t_final1'])
                   }
        )
        self.wallet.config_data(
            'networks', net2, 'bridges', net1,
            value={'addr': answers['bridge2'],
                   't_anchor': int(answers['t_anchor2']),
                   't_final': int(answers['t_final2'])
                   }
        )
        self.wallet.save_config()

    def register_asset(self):
        networks = self.get_networks()
        name, origin, origin_addr, pegs, peg_addrs = get_new_asset(networks)
        try:
            self.wallet.config_data('networks', origin, 'tokens', name)
            questions = [
                inquirer.List(
                    'YN',
                    message="Warning : override existing asset with same name",
                    choices=['Yes', 'No']
                )
            ]
            if inquirer.prompt(questions)['YN'] == 'No':
                return
            self.wallet.config_data('networks', origin, 'tokens', name,
                                    value={'pegs': {}})
        except KeyError:
            self.wallet.config_data('networks', origin, 'tokens', name,
                                    value={'pegs': {}})
        self.wallet.config_data(
            'networks', origin, 'tokens', name, 'addr', value=origin_addr)
        for i, peg_net in enumerate(pegs):
            self.wallet.config_data(
                'networks', origin, 'tokens', name, 'pegs', peg_net,
                value=peg_addrs[i])
        self.wallet.save_config()

    def register_network(self):
        answers = get_network()
        net = answers['name']
        net_type = answers['type']
        ip = answers['ip']
        if net_type == 'ethereum':
            self.wallet.config_data(
                'networks', net, value={'ip': ip,
                                        'type': net_type,
                                        'tokens': {},
                                        'isPOA': answers['isPOA'],
                                        'bridges': {}}
            )
        else:
            self.wallet.config_data(
                'networks', net, value={'ip': ip, 'type': net_type,
                                        'tokens': {}, 'bridges': {}}
            )
        self.wallet.save_config()

    def register_new_validators(self):
        print("WARNING: current validators will be overridden in the config "
              "file")
        validators = get_validators()
        self.wallet.config_data('validators', value=validators)
        self.wallet.save_config()

    def initiate_transfer(self):
        from_chain, to_chain, from_assets, to_assets, asset_name, \
            receiver = self.commun_transfer_params()
        amount = get_amount()
        print("Initialize transfer summary:\n"
              "Departure chain: {}\n"
              "Destination chain: {}\n"
              "Asset name: {}\n"
              "Receiver at destination: {}\n"
              "Amount: {}\n"
              .format(from_chain, to_chain, asset_name, receiver, amount))
        if not confirm_transfer():
            print('Finalize transfer canceled')
            return
        deposit_height, tx_hash = 0, ""
        if self.wallet.config_data('networks',
                                   from_chain, 'type') == 'ethereum':
            privkey_name = self.get_privkey_name('wallet-eth')
            eth_poa = self.wallet.config_data('networks', from_chain, 'isPOA')
            if asset_name in from_assets:
                # if transfering a native asset Lock
                asset_abi = get_asset_abi(
                    self.wallet.config_data(
                        'networks', from_chain, 'tokens', asset_name, 'abi')
                )
                deposit_height, tx_hash = self.wallet.lock_to_aergo(
                    from_chain, to_chain, self.bridge_abi, asset_name,
                    asset_abi, amount, receiver, privkey_name, eth_poa=eth_poa
                )
            elif (asset_name in to_assets and
                  from_chain in self.wallet.config_data(
                      'networks', to_chain, 'tokens', asset_name, 'pegs')):
                # if transfering a pegged asset Burn
                deposit_height, tx_hash = self.wallet.burn_to_aergo(
                    from_chain, to_chain, self.bridge_abi, asset_name,
                    self.minted_erc20_abi, amount, receiver, privkey_name,
                    eth_poa=eth_poa
                )
            else:
                print('asset not properly registered in config.json')
                return
        elif self.wallet.config_data('networks',
                                     from_chain, 'type') == 'aergo':
            privkey_name = self.get_privkey_name('wallet')
            if asset_name in from_assets:
                # if transfering a native asset Lock
                if asset_name == 'aergo':
                    deposit_height, tx_hash = self.wallet.freeze(
                        from_chain, to_chain, amount, receiver, privkey_name
                    )
                else:
                    deposit_height, tx_hash = self.wallet.lock_to_eth(
                        from_chain, to_chain, asset_name, amount, receiver,
                        privkey_name
                    )
            elif (asset_name in to_assets and
                  from_chain in self.wallet.config_data(
                      'networks', to_chain, 'tokens', asset_name, 'pegs')):
                # if transfering a pegged asset Burn
                if asset_name == 'aergo_erc20':
                    deposit_height, tx_hash = self.wallet.freeze(
                        from_chain, to_chain, asset_name, amount, receiver,
                        privkey_name
                    )
                else:
                    deposit_height, tx_hash = self.wallet.burn_to_eth(
                        from_chain, to_chain, asset_name, amount, receiver,
                        privkey_name
                    )
            else:
                print('asset not properly registered in config.json')
                return
        print("Transaction Hash : {}\nBlock Height : {}\n"
              .format(tx_hash, deposit_height))
        pending_id = hashlib.sha256(
            (from_chain + to_chain + asset_name + receiver).encode('utf-8')
        ).digest().hex()
        self.pending_transfers[pending_id] = \
            [from_chain, to_chain, asset_name, receiver, deposit_height]
        self.store_pending_transfers()

    def finalize_transfer_arguments(self):
        choices = [val for _, val in self.pending_transfers.items()]
        choices.extend(["Custom transfer", "Back"])
        questions = [
            inquirer.List(
                'transfer',
                message="Choose a pending transfer",
                choices=choices
                )
        ]
        answers = inquirer.prompt(questions)
        if answers['transfer'] == 'Custom transfer':
            from_chain, to_chain, from_assets, to_assets, asset_name, \
                receiver = self.commun_transfer_params()
            deposit_height = get_deposit_height()
            print("Finalize transfer summary:\n"
                  "Departure chain: {}\n"
                  "Arrival chain: {}\n"
                  "Asset name: {}\n"
                  "Receiver at destination: {}\n"
                  "Block height of lock/burn/freeze: {}\n"
                  .format(from_chain, to_chain, asset_name, receiver,
                          deposit_height))
            if not confirm_transfer():
                print('Finalize transfer canceled')
                return
        elif answers['transfer'] == 'Back':
            return
        else:
            from_chain, to_chain, asset_name, receiver, deposit_height = \
                answers['transfer']
            from_assets, to_assets = self.get_assets(from_chain, to_chain)

        return (from_chain, to_chain, from_assets, to_assets, asset_name,
                receiver, deposit_height)

    def finalize_transfer(self):
        from_chain, to_chain, from_assets, to_assets, asset_name, receiver, \
            deposit_height = self.finalize_transfer_arguments()
        if self.wallet.config_data('networks',
                                   from_chain, 'type') == 'ethereum':
            privkey_name = self.get_privkey_name('wallet')
            eth_poa = self.wallet.config_data('networks', from_chain, 'isPOA')
            if asset_name in from_assets:
                # if transfering a native asset mint
                if asset_name == 'aergo_erc20':
                    self.wallet.unfreeze(
                        from_chain, to_chain, receiver, deposit_height,
                        privkey_name, eth_poa=eth_poa
                    )
                else:
                    self.wallet.mint_to_aergo(
                        from_chain, to_chain, asset_name, receiver,
                        deposit_height, privkey_name, eth_poa=eth_poa
                    )
            elif (asset_name in to_assets and
                  from_chain in self.wallet.config_data(
                      'networks', to_chain, 'tokens', asset_name, 'pegs')):
                # if transfering a pegged asset unlock
                self.wallet.unlock_to_aergo(
                    from_chain, to_chain, asset_name, receiver, deposit_height,
                    privkey_name, eth_poa=eth_poa
                )
            else:
                print('asset not properly registered in config.json')
                return
        elif self.wallet.config_data('networks',
                                     from_chain, 'type') == 'aergo':
            privkey_name = self.get_privkey_name('wallet')
            eth_poa = self.wallet.config_data('networks', to_chain, 'isPOA')
            if asset_name == 'aergo':
                asset_abi = get_asset_abi(
                    self.wallet.config_data(
                        'networks', to_chain, 'tokens', 'aergo_erc20', 'abi')
                )
                self.wallet.unlock_to_eth(
                    from_chain, to_chain, self.bridge_abi, 'aergo_erc20',
                    asset_abi, receiver, deposit_height, privkey_name,
                    eth_poa=eth_poa
                )
            elif asset_name in from_assets:
                # if transfering a native asset mint
                self.wallet.mint_to_eth(
                    from_chain, to_chain, self.bridge_abi, asset_name,
                    self.minted_erc20_abi, receiver, deposit_height,
                    privkey_name, eth_poa=eth_poa
                )
            elif (asset_name in to_assets and
                  from_chain in self.wallet.config_data(
                      'networks', to_chain, 'tokens', asset_name, 'pegs')
                  ):
                # if transfering a pegged asset unlock
                asset_abi = get_asset_abi(
                    self.wallet.config_data(
                        'networks', to_chain, 'tokens', asset_name, 'abi')
                )
                self.wallet.unlock_to_eth(
                    from_chain, to_chain, self.bridge_abi, asset_name,
                    asset_abi, receiver, deposit_height, privkey_name,
                    eth_poa=eth_poa
                )
            else:
                print('asset not properly registered in config.json')
                return
        # remove pending id from pending transfers
        pending_id = hashlib.sha256(
            (from_chain + to_chain + asset_name + receiver).encode('utf-8')
        ).digest().hex()
        self.pending_transfers.pop(pending_id, None)
        self.store_pending_transfers()

    def check_withdrawable_balance(self):
        choices = [val for _, val in self.pending_transfers.items()]
        choices.extend([("Check another custom transfer", "custom"), "Back"])
        questions = [
            inquirer.List(
                'transfer',
                message="Choose a pending transfer to finalize",
                choices=choices
                )
        ]
        answers = inquirer.prompt(questions)
        if answers['transfer'] == 'custom':
            from_chain, to_chain, from_assets, to_assets, asset_name, \
                receiver = self.commun_transfer_params()
        elif answers['transfer'] == 'Back':
            return
        else:
            from_chain, to_chain, asset_name, receiver, _ = \
                answers['transfer']
            from_assets, to_assets = self.get_assets(from_chain, to_chain)
        if self.wallet.config_data('networks',
                                   from_chain, 'type') == 'ethereum':
            eth_poa = self.wallet.config_data('networks', from_chain, 'isPOA')
            if asset_name in from_assets:
                # if native asset check minteable
                if asset_name == 'aergo_erc20':
                    withdrawable, pending = self.wallet.unfreezeable(
                        from_chain, to_chain, receiver, eth_poa=eth_poa)
                else:
                    withdrawable, pending = self.wallet.minteable_to_aergo(
                        from_chain, to_chain, asset_name, receiver,
                        eth_poa=eth_poa
                    )
            elif (asset_name in to_assets and
                  from_chain in self.wallet.config_data(
                      'networks', to_chain, 'tokens', asset_name, 'pegs')):
                # if pegged asset check unlockeable
                withdrawable, pending = self.wallet.unlockeable_to_aergo(
                    from_chain, to_chain, asset_name, receiver, eth_poa=eth_poa
                )
            else:
                print('asset not properly registered in config.json')
                return
        elif self.wallet.config_data('networks',
                                     from_chain, 'type') == 'aergo':
            eth_poa = self.wallet.config_data('networks', to_chain, 'isPOA')
            if asset_name == 'aergo':
                withdrawable, pending = self.wallet.unlockeable_to_eth(
                    from_chain, to_chain, 'aergo_erc20', receiver,
                    eth_poa=eth_poa
                )
            elif asset_name in from_assets:
                # if native asset check minteable
                withdrawable, pending = self.wallet.minteable_to_eth(
                    from_chain, to_chain, asset_name, receiver, eth_poa=eth_poa
                )
            elif (asset_name in to_assets and
                  from_chain in self.wallet.config_data(
                      'networks', to_chain, 'tokens', asset_name, 'pegs')
                  ):
                # if pegged asset check unlockeable
                withdrawable, pending = self.wallet.unlockeable_to_eth(
                    from_chain, to_chain, asset_name, receiver, eth_poa=eth_poa
                )
            else:
                print('asset not properly registered in config.json')
                return
        print("Withdrawable: {}  Pending: {}"
              .format(withdrawable/10**18, pending/10**18))

    def commun_transfer_params(self):
        from_chain, to_chain = self.get_directions()
        from_assets, to_assets = self.get_assets(from_chain, to_chain)
        questions = [
            inquirer.List(
                'asset_name',
                message="Name of asset to transfer : ",
                choices=from_assets + to_assets
            ),
            inquirer.Text(
                'receiver',
                message='Receiver of assets on other side of bridge'
            )
        ]
        answers = inquirer.prompt(questions)
        receiver = answers['receiver']
        asset_name = answers['asset_name']
        return from_chain, to_chain, from_assets, to_assets, asset_name, \
            receiver

    def get_privkey_name(self, wallet_name):
        accounts = self.wallet.config_data(wallet_name)
        questions = [
            inquirer.List(
                'privkey_name',
                message="Choose account to sign transaction : ",
                choices=[name for name in accounts]
                )
        ]
        answers = inquirer.prompt(questions)
        return answers['privkey_name']

    def get_directions(self):
        networks = self.get_networks()
        questions = [
            inquirer.List(
                'from_chain',
                message="Departure network",
                choices=networks)
        ]
        answers = inquirer.prompt(questions)
        from_chain = answers['from_chain']
        networks.remove(from_chain)
        questions = [
            inquirer.List(
                'to_chain',
                message="Destination network",
                choices=networks)
        ]
        answers = inquirer.prompt(questions)
        to_chain = answers['to_chain']
        return from_chain, to_chain

    def get_networks(self):
        networks = []
        for net in self.wallet.config_data('networks'):
            networks.append(net)
        return networks

    def get_assets(self, from_chain, to_chain):
        from_assets = []
        for asset in self.wallet.config_data('networks',
                                             from_chain, 'tokens'):
            from_assets.append(asset)
        to_assets = []
        for asset in self.wallet.config_data('networks', to_chain, 'tokens'):
            to_assets.append(asset)
        return from_assets, to_assets

    def store_pending_transfers(self):
        with open('cli/pending_transfers.json', 'w') as file:
            json.dump(self.pending_transfers, file, indent=4)


if __name__ == '__main__':
    app = EthMerkleBridgeCli()
    app.start()

    # 'Register network',
    # 'Register asset',
    # 'Register account with private key'
    # 'Send AergoERC20 to Aergo (Lock)',
    # 'Receive Aer on Aergo (Unfreeze)',
    # 'Send Aer to Ethereum (Freeze)',
    # 'Receive AergoERC20 on Ethereum (Unlock)',

    # 'Initiate cross-chain transfer (Lock)',
    # 'Initiate cross-chain transfer (Burn)',
    # 'Finalize cross-chain transfer (Mint)',
    # 'Finalize cross-chain transfer (Unlock)',

    # 'Send ERC20 to Aergo Mainnet (Lock)',
    # 'Receive pegged token on Aergo Mainnet (Mint)',
    # 'Send pegged token to Ethereum (Burn)',
    # 'Receive ERC20 on Ethereum (Unlock)',

    # 'Send StdToken to Ethereum (Lock)',
    # 'Unfreeze AergoERC20 --> Mainnet',
    # 'Freeze AergoERC20 --> Ethereum',
    # 'Lock ERC20     Ethereum => Aergo                   ',
    # '               Ethereum => Aergo           Mint peg',
    # '               Ethereum <= Aergo           Burn peg',
    # 'Unlock ERC20   Ethereum <= Aergo                   ',
    # '               Ethereum <= Aergo    Lock AergoToken',
    # 'Mint peg       Ethereum <= Aergo                   ',
    # 'Burn peg       Ethereum => Aergo                   ',
    # '               Ethereum => Aergo  Unlock AergoToken',