import hashlib
import PyInquirer as inquirer
import json
import os
from pyfiglet import Figlet

from ethaergo_wallet.wallet import (
    EthAergoWallet,
)
from aergo_wallet.exceptions import (
    InvalidArgumentsError,
    TxError,
    InsufficientBalanceError,
)

from ethaergo_cli.utils import (
    confirm_transfer,
    prompt_amount,
    prompt_deposit_height,
    prompt_new_bridge,
    prompt_new_network,
    prompt_eth_privkey,
    prompt_aergo_privkey,
    prompt_new_asset,
    prompt_new_validators,
    prompt_file_path,
    prompt_bridge_abi_paths,
    prompt_number,
    aergo_style,
    promptYN,
    print_balance_table_header,
    print_balance_table_lines,
)


class EthMerkleBridgeCli():
    """CLI tool for interacting with the EthAergoWallet.

    First choose an existing config file or create one from scratch.
    Once a config file is chosen, the CLI provides an interface to the
    EthAergoWallet and has the following features:
    - edit config file settings
    - transfer assets between networks
    - check status of transfers
    - check balances for each asset on each network

    """

    def __init__(self, root_path: str = './'):
        """Load the pending transfers."""
        # root_path is the path from which files are tracked
        with open(root_path
                  + 'ethaergo_cli/pending_transfers.json', 'r') as file:
            self.pending_transfers = json.load(file)
        self.root_path = root_path

    def start(self):
        """Entry point of cli : load a wallet configuration file of create a
        new one

        """
        f = Figlet(font='speed')
        print(f.renderText('Eth Merkel Bridge Cli'))
        print("Welcome to the Eth Merkle Bridge Interactive CLI.\n"
              "This is a tool to transfer assets across the "
              "Ethereum <=> Aergo Merke bridge and manage wallet "
              "settings (config.json)\n")
        while 1:
            questions = [
                {
                    'type': 'list',
                    'name': 'YesNo',
                    'message': "Do you have a config.json? ",
                    'choices': [
                        {
                            'name': 'Yes, find it with the path',
                            'value': 'Y'
                        },
                        {
                            'name': 'No, create one from scratch',
                            'value': 'N'
                        },
                        'Quit']
                }
            ]
            answers = inquirer.prompt(questions, style=aergo_style)
            try:
                if answers['YesNo'] == 'Y':
                    self.load_config()
                    self.menu()
                elif answers['YesNo'] == 'N':
                    self.create_config()
                else:
                    return
            except KeyError:
                return

    def load_config(self):
        """Load the configuration file from path and create a wallet object."""
        while 1:
            questions = [
                {
                    'type': 'input',
                    'name': 'config_file_path',
                    'message': 'Path to config.json (path/to/config.json)'
                }
            ]
            config_file_path = inquirer.prompt(
                questions, style=aergo_style)['config_file_path']
            try:
                self.wallet = EthAergoWallet(config_file_path)
                break
            except (IsADirectoryError, FileNotFoundError):
                print("Invalid path/to/config.json")
            except KeyError:
                return

    def menu(self):
        """Menu for interacting with network.

        Users can change settings, query balances, check pending transfers,
        execute cross chain transactions

        """
        while 1:
            questions = [
                {
                    'type': 'list',
                    'name': 'action',
                    'message': "What would you like to do ? ",
                    'choices': [
                        {
                            'name': 'Check pending transfer',
                            'value': 'P'
                        },
                        {
                            'name': 'Check balances',
                            'value': 'B'
                        },
                        {
                            'name': 'Initiate transfer (Lock/Burn)',
                            'value': 'I'
                        },
                        {
                            'name': 'Finalize transfer (Mint/Unlock)',
                            'value': 'F'
                        },
                        {
                            'name': 'Settings (Register Assets and Networks)',
                            'value': 'S'
                        },
                        'Back'
                    ]
                }
            ]
            answers = inquirer.prompt(questions, style=aergo_style)
            try:
                if answers['action'] == 'Back':
                    return
                elif answers['action'] == 'P':
                    self.check_withdrawable_balance()
                elif answers['action'] == 'B':
                    self.check_balances()
                elif answers['action'] == 'I':
                    self.initiate_transfer()
                elif answers['action'] == 'F':
                    self.finalize_transfer()
                elif answers['action'] == 'S':
                    self.edit_settings()
            except (TypeError, KeyboardInterrupt, InvalidArgumentsError,
                    TxError, InsufficientBalanceError, KeyError) as e:
                print('Someting went wrong, check the status of your pending '
                      'transfers\nError msg: {}'.format(e))

    def check_balances(self):
        """Iterate every registered wallet, network and asset and query
        balances.

        """
        col_widths = [24, 55, 23]
        print('Ethereum wallet: ')
        print('=================')
        for wallet, info in self.wallet.config_data('wallet-eth').items():
            print('\n' + wallet + ': ' + info['addr'])
            print_balance_table_header()
            for net_name, net in self.wallet.config_data('networks').items():
                for token_name, token in net['tokens'].items():
                    lines = []
                    if net['type'] == 'ethereum':
                        balance, addr = self.wallet.get_balance_eth(
                            token_name, net_name, account_name=wallet
                        )
                        if balance != 0:
                            line = [net_name, addr,
                                    str(balance/10**18) + ' \U0001f4b0']
                            lines.append(line)
                    for peg in token['pegs']:
                        pegged_network = self.wallet.config_data('networks',
                                                                 peg)
                        if pegged_network['type'] == 'ethereum':
                            balance, addr = self.wallet.get_balance_eth(
                                token_name, peg, net_name, wallet
                            )
                            if balance != 0:
                                line = [peg, addr,
                                        str(balance/10**18) + ' \U0001f4b0']
                                lines.append(line)
                    print_balance_table_lines(lines, token_name,
                                              col_widths)
            print(' ' + '‾' * 120)
        print('Aergo wallet: ')
        print('==============')
        for wallet, info in self.wallet.config_data('wallet').items():
            print('\n' + wallet + ': ' + info['addr'])
            print_balance_table_header()
            for net_name, net in self.wallet.config_data('networks').items():
                for token_name, token in net['tokens'].items():
                    lines = []
                    if net['type'] == 'aergo':
                        balance, addr = self.wallet.get_balance_aergo(
                            token_name, net_name, account_name=wallet
                        )
                        if balance != 0:
                            line = [net_name, addr,
                                    str(balance/10**18) + ' \U0001f4b0']
                            lines.append(line)
                    for peg in token['pegs']:
                        pegged_network = self.wallet.config_data('networks',
                                                                 peg)
                        if pegged_network['type'] == 'aergo' and \
                                token_name != 'aergo_erc20':
                            balance, addr = self.wallet.get_balance_aergo(
                                token_name, peg, net_name, wallet
                            )
                            if balance != 0:
                                line = [peg, addr,
                                        str(balance/10**18) + ' \U0001f4b0']
                                lines.append(line)
                    print_balance_table_lines(lines, token_name,
                                              col_widths)
            print(' ' + '‾' * 120)

    def edit_settings(self):
        """Menu for editing the config file of the currently loaded wallet"""
        while 1:
            questions = [
                {
                    'type': 'list',
                    'name': 'action',
                    'message': 'What would you like to do ? ',
                    'choices': [
                        {
                            'name': 'Register new asset',
                            'value': 'A'
                        },
                        {
                            'name': 'Register new network',
                            'value': 'N'
                        },
                        {
                            'name': 'Register new bridge',
                            'value': 'B'
                        },
                        {
                            'name': 'Register new encrypted private key',
                            'value': 'K'
                        },
                        {
                            'name': 'Update validators set',
                            'value': 'V'
                        },
                        {
                            'name': 'Update anchoring periode',
                            'value': 'UA'
                        },
                        {
                            'name': 'Update finality',
                            'value': 'UF'
                        },
                        'Back',
                    ]
                }
            ]
            answers = inquirer.prompt(questions, style=aergo_style)
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
                elif answers['action'] == 'K':
                    self.register_key()
                elif answers['action'] == 'UA':
                    self.update_t_anchor()
                elif answers['action'] == 'UF':
                    self.update_t_final()
            except (TypeError, KeyboardInterrupt, InvalidArgumentsError) as e:
                print('Someting went wrong, check the status of you pending '
                      'transfers\nError msg: {}'.format(e))

    def create_config(self):
        """Create a new configuration file from scratch.

        This tool registers 2 networks, bridge contracts,
        paths to bridge abis, a private key for each network and
        bridge validators

        """
        new_config = {}
        print("Let's register 2 networks, "
              "validators(optional) and a private key for interacting with "
              "each network.")
        # Register 2 networks
        answers = prompt_new_network()
        net1 = answers['name']
        net1_type = answers['type']
        new_config['networks'] = {net1: {'ip': answers['ip'],
                                         'type': net1_type,
                                         'tokens': {},
                                         'bridges': {}
                                         }
                                  }
        if net1_type == 'ethereum':
            new_config['networks'][net1]['isPOA'] = answers['isPOA']
        answers = prompt_new_network()
        net2 = answers['name']
        net2_type = answers['type']
        new_config['networks'][net2] = {'ip': answers['ip'],
                                        'type': net2_type,
                                        'tokens': {},
                                        'bridges': {}
                                        }
        if net2_type == 'ethereum':
            new_config['networks'][net2]['isPOA'] = answers['isPOA']
        # Register bridge contracts on each network
        if promptYN('Would you like to register a bridge ? '
                    '(needed if already deployed)', 'Yes', 'No'):
            answers = prompt_new_bridge(net1, net2)
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
            # Register paths to abis
            if net1_type == 'ethereum':
                bridge_abi, minted_abi = prompt_bridge_abi_paths()
                bridge_abi = os.path.relpath(bridge_abi, self.root_path)
                minted_abi = os.path.relpath(minted_abi, self.root_path)
                new_config['networks'][net1]['bridges'][net2]['bridge_abi'] = \
                    bridge_abi
                new_config['networks'][net1]['bridges'][net2]['minted_abi'] = \
                    minted_abi
            if net2_type == 'ethereum':
                bridge_abi, minted_abi = prompt_bridge_abi_paths()
                bridge_abi = os.path.relpath(bridge_abi, self.root_path)
                minted_abi = os.path.relpath(minted_abi, self.root_path)
                new_config['networks'][net2]['bridges'][net1]['bridge_abi'] = \
                    bridge_abi
                new_config['networks'][net2]['bridges'][net1]['minted_abi'] = \
                    minted_abi
        # Register a new private key for each network
        new_config['wallet-eth'] = {}
        new_config['wallet'] = {}
        print("Register a private key for {}".format(net1))
        if net1_type == 'ethereum':
            name, addr, privkey_path = prompt_eth_privkey()
            privkey_path = os.path.relpath(privkey_path, self.root_path)
            new_config['wallet-eth'][name] = {"addr": addr,
                                              "keystore": privkey_path}
        else:
            name, addr, privkey = prompt_aergo_privkey()
            new_config['wallet'][name] = {"addr": addr,
                                          "priv_key": privkey}
        print("Register a private key for {}".format(net2))
        if net2_type == 'ethereum':
            name, addr, privkey_path = prompt_eth_privkey()
            privkey_path = os.path.relpath(privkey_path, self.root_path)
            new_config['wallet-eth'][name] = {"addr": addr,
                                              "keystore": privkey_path}
        else:
            name, addr, privkey = prompt_aergo_privkey()
            new_config['wallet'][name] = {"addr": addr,
                                          "priv_key": privkey}

        # Register bridge validators
        if promptYN('Would you like to register validators ? '
                    '(not needed for bridge users)', 'Yes', 'No'):
            validators = prompt_new_validators()
            new_config['validators'] = validators
        else:
            new_config['validators'] = {}

        questions = [
            {
                'type': 'input',
                'name': 'path',
                'message': 'Path to save new config file'
            }
        ]
        path = inquirer.prompt(questions, style=aergo_style)['path']

        with open(path, "w") as f:
            json.dump(new_config, f, indent=4, sort_keys=True)

        print("Config file stored in: {}".format(os.path.abspath(path)))

    def register_bridge(self):
        """Register bridge contracts between 2 already defined networks."""
        net1, net2 = self.prompt_bridge_networks()
        answers = prompt_new_bridge(net1, net2)
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
        # Register paths to abis
        net1_type = self.wallet.config_data('networks', net1, 'type')
        net2_type = self.wallet.config_data('networks', net2, 'type')
        if net1_type == 'ethereum':
            bridge_abi, minted_abi = prompt_bridge_abi_paths()
            bridge_abi = os.path.relpath(bridge_abi, self.root_path)
            minted_abi = os.path.relpath(minted_abi, self.root_path)
            self.wallet.config_data('networks', net1, 'bridges', net2,
                                    'bridge_abi', value=bridge_abi)
            self.wallet.config_data('networks', net1, 'bridges', net2,
                                    'minted_abi', value=minted_abi)
        if net2_type == 'ethereum':
            bridge_abi, minted_abi = prompt_bridge_abi_paths()
            bridge_abi = os.path.relpath(bridge_abi, self.root_path)
            minted_abi = os.path.relpath(minted_abi, self.root_path)
            self.wallet.config_data('networks', net2, 'bridges', net1,
                                    'bridge_abi', value=bridge_abi)
            self.wallet.config_data('networks', net2, 'bridges', net1,
                                    'minted_abi', value=minted_abi)
        self.wallet.save_config()

    def register_asset(self):
        """Register a new asset and it's pegs on other networks in the
        wallet's config.

        """
        networks = self.get_registered_networks()
        name, origin, origin_addr, pegs, peg_addrs = prompt_new_asset(
            networks.copy())
        for net in networks:
            try:
                self.wallet.config_data('networks', net, 'tokens', name)
                print("Asset name already used")
                return
            except KeyError:
                pass
        self.wallet.config_data('networks', origin, 'tokens', name,
                                value={'addr': {}, 'pegs': {}})
        self.wallet.config_data(
            'networks', origin, 'tokens', name, 'addr', value=origin_addr)
        # if ethereum query abi path
        if self.wallet.config_data('networks', origin, 'type') == 'ethereum':
            abi_path = prompt_file_path("Path to the asset's abi text file")
            abi_path = os.path.relpath(abi_path, self.root_path)
            self.wallet.config_data(
                'networks', origin, 'tokens', name, 'abi', value=abi_path)
        for i, peg_net in enumerate(pegs):
            self.wallet.config_data(
                'networks', origin, 'tokens', name, 'pegs', peg_net,
                value=peg_addrs[i])
        self.wallet.save_config()

    def register_network(self):
        """Register a new network in the wallet's config."""
        answers = prompt_new_network()
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

    def register_key(self):
        """Register new key in wallet's config."""
        is_eth_key = promptYN(
            'Which type of key would you like to register ?', 'Ethereum',
            'Aergo'
        )
        if is_eth_key:
            name, addr, privkey_path = prompt_eth_privkey()
            privkey_path = os.path.relpath(privkey_path, self.root_path)
        else:
            name, addr, privkey = prompt_aergo_privkey()

        try:
            self.wallet.config_data('wallet', name)
            print("Key name already used")
            return
        except KeyError:
            pass

        if is_eth_key:
            self.wallet.config_data(
                'wallet-eth', name, value={'addr': addr,
                                           'keystore': privkey_path})
        else:
            self.wallet.config_data(
                'wallet', name, value={'addr': addr, 'priv_key': privkey})
        self.wallet.save_config()

    def register_new_validators(self):
        """Register new validators in the wallet's config."""
        print("WARNING: current validators will be overridden in the config "
              "file")
        validators = prompt_new_validators()
        self.wallet.config_data('validators', value=validators)
        self.wallet.save_config()

    def update_t_anchor(self):
        from_chain, to_chain = self.prompt_transfer_networks()
        t_anchor = prompt_number("New anchoring periode (nb of blocks) of {} "
                                 "onto {}".format(from_chain, to_chain))
        self.wallet.config_data('networks', to_chain, 'bridges', from_chain,
                                't_anchor', value=t_anchor)
        self.wallet.save_config()

    def update_t_final(self):
        from_chain, to_chain = self.prompt_transfer_networks()
        t_final = prompt_number("New finality (nb of blocks) of {}"
                                .format(from_chain))
        self.wallet.config_data('networks', to_chain, 'bridges', from_chain,
                                't_final', value=t_final)
        self.wallet.save_config()

    def get_asset_address(self, asset_name, from_chain, to_chain):
        try:
            addr = self.wallet.config_data(
                'networks', from_chain, 'tokens', asset_name, 'addr')
            return addr
        except KeyError:
            pass
        try:
            addr = self.wallet.config_data(
                'networks', to_chain, 'tokens', asset_name, 'pegs', from_chain)
            return addr
        except KeyError:
            pass
        raise InvalidArgumentsError(
            'asset not properly registered in config.json')

    def initiate_transfer(self):
        """Initiate a new transfer of tokens between 2 networks."""
        from_chain, to_chain, from_assets, to_assets, asset_name, \
            receiver = self.prompt_commun_transfer_params()
        amount = prompt_amount()
        bridge_from = self.wallet.get_bridge_contract_address(from_chain,
                                                              to_chain)
        bridge_to = self.wallet.get_bridge_contract_address(to_chain,
                                                            from_chain)
        asset_addr = self.get_asset_address(asset_name, from_chain, to_chain)
        summary = "Departure chain: {} ({})\n" \
                  "Destination chain: {} ({})\n" \
                  "Asset name: {} ({})\n" \
                  "Receiver at destination: {}\n" \
                  "Amount: {}\n".format(from_chain, bridge_from, to_chain,
                                        bridge_to, asset_name, asset_addr,
                                        receiver, amount)
        deposit_height, tx_hash = 0, ""
        if self.wallet.config_data('networks',
                                   from_chain, 'type') == 'ethereum':
            privkey_name = self.prompt_signing_key('wallet-eth')
            if asset_name in from_assets:
                # if transfering a native asset Lock
                print("Lock transfer summary:\n{}".format(summary))
                if not confirm_transfer():
                    print('Initialize transfer canceled')
                    return
                deposit_height, tx_hash = self.wallet.lock_to_aergo(
                    from_chain, to_chain, asset_name,
                    amount, receiver, privkey_name
                )
            elif (asset_name in to_assets and
                  from_chain in self.wallet.config_data(
                      'networks', to_chain, 'tokens', asset_name, 'pegs')):
                # if transfering a pegged asset Burn
                print("Burn transfer summary:\n{}".format(summary))
                if not confirm_transfer():
                    print('Initialize transfer canceled')
                    return
                deposit_height, tx_hash = self.wallet.burn_to_aergo(
                    from_chain, to_chain, asset_name,
                    amount, receiver, privkey_name
                )
            else:
                print('asset not properly registered in config.json')
                return
        elif self.wallet.config_data('networks',
                                     from_chain, 'type') == 'aergo':
            privkey_name = self.prompt_signing_key('wallet')
            if asset_name in from_assets:
                # if transfering a native asset Lock
                if asset_name == 'aergo':
                    print("Freeze Mainnet Aergo transfer summary:\n{}"
                          .format(summary))
                    if not confirm_transfer():
                        print('Initialize transfer canceled')
                        return
                    deposit_height, tx_hash = self.wallet.freeze(
                        from_chain, to_chain, amount, receiver, privkey_name
                    )
                else:
                    print("Lock transfer summary:\n{}".format(summary))
                    if not confirm_transfer():
                        print('Initialize transfer canceled')
                        return
                    deposit_height, tx_hash = self.wallet.lock_to_eth(
                        from_chain, to_chain, asset_name, amount, receiver,
                        privkey_name
                    )
            elif (asset_name in to_assets and
                  from_chain in self.wallet.config_data(
                      'networks', to_chain, 'tokens', asset_name, 'pegs')):
                # if transfering a pegged asset Burn
                if asset_name == 'aergo_erc20':
                    print("Freeze Mainnet Aergo transfer summary:\n{}"
                          .format(summary))
                    if not confirm_transfer():
                        print('Initialize transfer canceled')
                        return
                    deposit_height, tx_hash = self.wallet.freeze(
                        from_chain, to_chain, asset_name, amount, receiver,
                        privkey_name
                    )
                else:
                    print("Burn transfer summary:\n{}".format(summary))
                    if not confirm_transfer():
                        print('Initialize transfer canceled')
                        return
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

    def finalize_transfer_arguments(self, prompt_last_deposit=True):
        """Prompt the arguments needed to finalize a transfer.

        The arguments can be taken from the pending transfers or
        inputed manually by users.

        Returns:
            List of transfer arguments

        """
        choices = [
            {
                'name': '{}'.format(val),
                'value': val
            } for _, val in self.pending_transfers.items()
        ]
        choices.extend(["Custom transfer", "Back"])
        questions = [
            {
                'type': 'list',
                'name': 'transfer',
                'message': 'Choose a pending transfer',
                'choices': choices
            }
        ]
        answers = inquirer.prompt(questions, style=aergo_style)
        if answers['transfer'] == 'Custom transfer':
            from_chain, to_chain, from_assets, to_assets, asset_name, \
                receiver = self.prompt_commun_transfer_params()
            deposit_height = 0
            if prompt_last_deposit:
                deposit_height = prompt_deposit_height()
        elif answers['transfer'] == 'Back':
            return None
        else:
            from_chain, to_chain, asset_name, receiver, deposit_height = \
                answers['transfer']
            from_assets, to_assets = self.get_registered_assets(from_chain,
                                                                to_chain)

        return (from_chain, to_chain, from_assets, to_assets, asset_name,
                receiver, deposit_height)

    def finalize_transfer(self):
        """Finalize a token transfer between 2 chains."""
        arguments = self.finalize_transfer_arguments()
        if arguments is None:
            return
        from_chain, to_chain, from_assets, to_assets, asset_name, receiver, \
            deposit_height = arguments
        bridge_from = self.wallet.get_bridge_contract_address(from_chain,
                                                              to_chain)
        bridge_to = self.wallet.get_bridge_contract_address(to_chain,
                                                            from_chain)
        asset_addr = self.get_asset_address(asset_name, from_chain, to_chain)
        summary = "Departure chain: {} ({})\n" \
                  "Destination chain: {} ({})\n" \
                  "Asset name: {} ({})\n" \
                  "Receiver at destination: {}\n" \
                  "Block height of lock/burn/freeze: {}\n"\
                  .format(from_chain, bridge_from, to_chain, bridge_to,
                          asset_name, asset_addr, receiver, deposit_height)
        if self.wallet.config_data('networks',
                                   from_chain, 'type') == 'ethereum':
            privkey_name = self.prompt_signing_key('wallet')
            if asset_name in from_assets:
                # if transfering a native asset mint
                if asset_name == 'aergo_erc20':
                    print("Unfreeze Mainnet Aergo transfer summary:\n{}"
                          .format(summary))
                    if not confirm_transfer():
                        print('Finalize transfer canceled')
                        return
                    self.wallet.unfreeze(
                        from_chain, to_chain, receiver, deposit_height,
                        privkey_name
                    )
                else:
                    print("Mint transfer summary:\n{}".format(summary))
                    if not confirm_transfer():
                        print('Finalize transfer canceled')
                        return
                    self.wallet.mint_to_aergo(
                        from_chain, to_chain, asset_name, receiver,
                        deposit_height, privkey_name
                    )
            elif (asset_name in to_assets and
                  from_chain in self.wallet.config_data(
                      'networks', to_chain, 'tokens', asset_name, 'pegs')):
                # if transfering a pegged asset unlock
                print("Unlock transfer summary:\n{}".format(summary))
                if not confirm_transfer():
                    print('Finalize transfer canceled')
                    return
                self.wallet.unlock_to_aergo(
                    from_chain, to_chain, asset_name, receiver, deposit_height,
                    privkey_name
                )
            else:
                print('asset not properly registered in config.json')
                return
        elif self.wallet.config_data('networks',
                                     from_chain, 'type') == 'aergo':
            privkey_name = self.prompt_signing_key('wallet')
            if asset_name == 'aergo':
                print("Unlock transfer summary:\n{}".format(summary))
                if not confirm_transfer():
                    print('Finalize transfer canceled')
                    return
                self.wallet.unlock_to_eth(
                    from_chain, to_chain, 'aergo_erc20',
                    receiver, deposit_height, privkey_name
                )
            elif asset_name in from_assets:
                # if transfering a native asset mint
                print("Mint transfer summary:\n{}".format(summary))
                if not confirm_transfer():
                    print('Finalize transfer canceled')
                    return
                self.wallet.mint_to_eth(
                    from_chain, to_chain, asset_name,
                    receiver, deposit_height,
                    privkey_name
                )
            elif (asset_name in to_assets and
                  from_chain in self.wallet.config_data(
                      'networks', to_chain, 'tokens', asset_name, 'pegs')
                  ):
                # if transfering a pegged asset unlock
                print("Unlock transfer summary:\n{}".format(summary))
                if not confirm_transfer():
                    print('Finalize transfer canceled')
                    return
                self.wallet.unlock_to_eth(
                    from_chain, to_chain, asset_name,
                    receiver, deposit_height, privkey_name
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
        """Check the status of cross chain transfers."""
        arguments = self.finalize_transfer_arguments(
            prompt_last_deposit=False)
        if arguments is None:
            return
        from_chain, to_chain, from_assets, to_assets, asset_name, receiver, \
            _ = arguments

        if self.wallet.config_data('networks',
                                   from_chain, 'type') == 'ethereum':
            if asset_name in from_assets:
                # if native asset check minteable
                if asset_name == 'aergo_erc20':
                    withdrawable, pending = self.wallet.unfreezeable(
                        from_chain, to_chain, receiver)
                else:
                    withdrawable, pending = self.wallet.minteable_to_aergo(
                        from_chain, to_chain, asset_name, receiver
                    )
            elif (asset_name in to_assets and
                  from_chain in self.wallet.config_data(
                      'networks', to_chain, 'tokens', asset_name, 'pegs')):
                # if pegged asset check unlockeable
                withdrawable, pending = self.wallet.unlockeable_to_aergo(
                    from_chain, to_chain, asset_name, receiver
                )
            else:
                print('asset not properly registered in config.json')
                return
        elif self.wallet.config_data('networks',
                                     from_chain, 'type') == 'aergo':
            if asset_name == 'aergo':
                withdrawable, pending = self.wallet.unlockeable_to_eth(
                    from_chain, to_chain, 'aergo_erc20', receiver
                )
            elif asset_name in from_assets:
                # if native asset check minteable
                withdrawable, pending = self.wallet.minteable_to_eth(
                    from_chain, to_chain, asset_name, receiver
                )
            elif (asset_name in to_assets and
                  from_chain in self.wallet.config_data(
                      'networks', to_chain, 'tokens', asset_name, 'pegs')
                  ):
                # if pegged asset check unlockeable
                withdrawable, pending = self.wallet.unlockeable_to_eth(
                    from_chain, to_chain, asset_name, receiver
                )
            else:
                print('asset not properly registered in config.json')
                return
        print("Withdrawable: {}  Pending: {}"
              .format(withdrawable/10**18, pending/10**18))

    def prompt_commun_transfer_params(self):
        """Prompt the common parameters necessary for all transfers.

        Returns:
            List of transfer parameters : from_chain, to_chain, from_assets,
            to_assets, asset_name, receiver

        """
        from_chain, to_chain = self.prompt_transfer_networks()
        from_assets, to_assets = self.get_registered_assets(from_chain,
                                                            to_chain)
        questions = [
            {
                'type': 'list',
                'name': 'asset_name',
                'message': 'Name of asset to transfer',
                'choices': from_assets + to_assets
            },
            {
                'type': 'input',
                'name': 'receiver',
                'message': 'Receiver of assets on other side of bridge'
            }
        ]
        answers = inquirer.prompt(questions, style=aergo_style)
        receiver = answers['receiver']
        asset_name = answers['asset_name']
        return from_chain, to_chain, from_assets, to_assets, asset_name, \
            receiver

    def prompt_signing_key(self, wallet_name):
        """Prompt user to select a private key.

        Note:
            Keys are displayed by name and should have been registered in
            wallet config.

        """
        accounts = self.wallet.config_data(wallet_name)
        questions = [
            {
                'type': 'list',
                'name': 'privkey_name',
                'message': 'Choose account to sign transaction : ',
                'choices': [name for name in accounts]
            }
        ]
        answers = inquirer.prompt(questions, style=aergo_style)
        return answers['privkey_name']

    def prompt_bridge_networks(self):
        """Prompt user to choose 2 networks between registered networks."""
        networks = self.get_registered_networks()
        questions = [
            {
                'type': 'list',
                'name': 'from_chain',
                'message': 'Departure network',
                'choices': networks
            }
        ]
        answers = inquirer.prompt(questions, style=aergo_style)
        from_chain = answers['from_chain']
        networks.remove(from_chain)
        questions = [
            {
                'type': 'list',
                'name': 'to_chain',
                'message': 'Destination network',
                'choices': networks
            }
        ]
        answers = inquirer.prompt(questions, style=aergo_style)
        to_chain = answers['to_chain']
        return from_chain, to_chain

    def prompt_transfer_networks(self):
        """Prompt user to choose 2 networks between registered bridged
        networks.

        """
        networks = self.get_registered_networks()
        questions = [
            {
                'type': 'list',
                'name': 'from_chain',
                'message': 'Departure network',
                'choices': networks
            }
        ]
        answers = inquirer.prompt(questions, style=aergo_style)
        from_chain = answers['from_chain']
        networks = [net for net in
                    self.wallet.config_data('networks', from_chain, 'bridges')]
        if len(networks) == 0:
            raise InvalidArgumentsError('No bridge registered to this network')
        questions = [
            {
                'type': 'list',
                'name': 'to_chain',
                'message': 'Destination network',
                'choices': networks
            }
        ]
        answers = inquirer.prompt(questions, style=aergo_style)
        to_chain = answers['to_chain']
        return from_chain, to_chain

    def get_registered_networks(self):
        """Get the list of networks registered in the wallet config."""
        return [net for net in self.wallet.config_data('networks')]

    def get_registered_assets(self, from_chain, to_chain):
        """Get the list of registered assets on each network."""
        from_assets = [
            asset for asset in self.wallet.config_data(
                'networks', from_chain, 'tokens')
        ]
        to_assets = [
            asset for asset in self.wallet.config_data(
                'networks', to_chain, 'tokens')
        ]
        return from_assets, to_assets

    def store_pending_transfers(self):
        """Record pending transfers in json file so they can be finalized
        later.

        """
        with open(self.root_path
                  + 'ethaergo_cli/pending_transfers.json', 'w') as file:
            json.dump(self.pending_transfers, file, indent=4)


if __name__ == '__main__':
    app = EthMerkleBridgeCli()
    app.start()
