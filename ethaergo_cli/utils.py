import PyInquirer as inquirer

aergo_style = inquirer.style_from_dict({
    inquirer.Token.Separator: '#FF36AD',
    inquirer.Token.QuestionMark: '#FF36AD bold',
    inquirer.Token.Selected: '',  # default
    inquirer.Token.Pointer: '#FF36AD bold',  # AWS orange
    inquirer.Token.Instruction: '',  # default
    inquirer.Token.Answer: '#FF36AD bold',  # AWS orange
    inquirer.Token.Question: 'bold',
})


def confirm_transfer():
    return promptYN(
        'Confirm you want to execute tranfer tx', 'Yes, execute transfer',
        'No, get me out of here!'
    )


def promptYN(q, y, n):
    """Prompt user to procede with a transfer of not."""
    questions = [
        {
            'type': 'list',
            'name': 'confirm',
            'message': q,
            'choices': [
                {
                    'name': y,
                    'value': True
                },
                {
                    'name': n,
                    'value': False
                }
            ]
        }
    ]
    answers = inquirer.prompt(questions, style=aergo_style)
    return answers['confirm']


def prompt_number(message, formator=int):
    """Prompt a number."""
    while 1:
        questions = [
            {
                'type': 'input',
                'name': 'num',
                'message': message
            }
        ]
        answers = inquirer.prompt(questions, style=aergo_style)
        try:
            num = formator(answers['num'])
            break
        except ValueError:
            print("Invalid number")
    return num


def prompt_amount():
    """Prompt a number of tokens to transfer."""
    return prompt_number("Amount of assets to transfer", format_amount)


def format_amount(num: str):
    """Format a float string to an integer with 18 decimals.

    Example:
        '2.3' -> 2300000000000000000

    """
    periode = num.find('.')
    if periode == -1:
        return int(num) * 10**18
    decimals = 0
    for i, digit in enumerate(num[periode + 1:]):
        decimals += int(digit) * 10**(17 - i)
    return int(num[:periode]) * 10**18 + decimals


def prompt_deposit_height():
    """Prompt the block number of deposit."""
    return prompt_number("Block height of deposit (0 to try finalization "
                         "anyway)")


def prompt_gas_price():
    """Prompt aergo and eth gas price"""
    aergo_gas_price = prompt_number("Aergo gas price")
    eth_gas_price = prompt_number("Ethereum gas price")
    return aergo_gas_price, eth_gas_price


def prompt_new_bridge(net1, net2):
    """Prompt user to input bridge contracts and tempo.

    For each contract on each bridged network, provide:
    - bridge contract address
    - anchoring periode
    - finality of the anchored chain

    """
    print('Bridge between {} and {}'.format(net1, net2))
    questions = [
        {
            'type': 'input',
            'name': 'bridge1',
            'message': 'Bridge contract address on {}'.format(net1)
        },
        {
            'type': 'input',
            'name': 'oracle1',
            'message': 'Oracle address on {}'.format(net1)
        },
        {
            'type': 'input',
            'name': 't_anchor1',
            'message': 'Anchoring periode of {} on {}'.format(net2, net1)
        },
        {
            'type': 'input',
            'name': 't_final1',
            'message': 'Finality of {}'.format(net2)
        },
        {
            'type': 'input',
            'name': 'bridge2',
            'message': 'Bridge contract address on {}'.format(net2)
        },
        {
            'type': 'input',
            'name': 'oracle2',
            'message': 'Oracle contract address on {}'.format(net2)
        },
        {
            'type': 'input',
            'name': 't_anchor2',
            'message': 'Anchoring periode of {} on {}'.format(net1, net2)
        },
        {
            'type': 'input',
            'name': 't_final2',
            'message': 'Finality of {}'.format(net1)
        },
        {
            'type': 'input',
            'name': 'unfreeze_fee',
            'message': 'Aergo native unfreeze fee'
        }
    ]
    return inquirer.prompt(questions, style=aergo_style)


def prompt_file_path(message):
    """Prompt user to input a path to a file and check it exists."""
    while 1:
        questions = [
            {
                'type': 'input',
                'name': 'path',
                'message': message
            }
        ]
        answers = inquirer.prompt(questions, style=aergo_style)
        path = answers['path']
        try:
            with open(path, "r") as f:
                f.read()
            break
        except (IsADirectoryError, FileNotFoundError):
            print("Invalid path")
    return path


def prompt_bridge_abi_paths():
    """Prompt user to input paths to text files containing abis."""
    bridge_abi = prompt_file_path("Path to Ethereum bridge abi text file")
    minted_abi = prompt_file_path("Path to Ethereum bridge minted token abi "
                                  "text file")
    oracle_abi = prompt_file_path("Path to Ethereum oracle abi text file")
    return bridge_abi, minted_abi, oracle_abi


def prompt_new_network():
    """Prompt user to input a new network's information:
    - Name
    - IP/url
    - Network type (aergo/eth)
    - is POA (only needed for ethereum)

    """
    questions = [
        {
            'type': 'input',
            'name': 'name',
            'message': 'Network name'
        },
        {
            'type': 'input',
            'name': 'ip',
            'message': 'Network IP'
        },
        {
            'type': 'list',
            'name': 'type',
            'message': 'Network type',
            'choices': ['ethereum', 'aergo']
        }
    ]
    answers = inquirer.prompt(questions, style=aergo_style)
    if answers['type'] == 'ethereum':
        is_poa = promptYN(
            'Is this an Ethereum POA network ?', 'Yes', 'No'
        )
        answers['isPOA'] = is_poa
    add_providers = promptYN(
        'Add redundant providers for validator data source security ?',
        'Yes', 'No'
    )
    if add_providers:
        answers['providers'] = prompt_providers()
    else:
        answers['providers'] = []
    return answers


def prompt_providers():
    """Prompt user to input provider ip.
    If not registered, the validator will use the single 'ip' field in
    config.json
    """
    providers = []
    add_val = True
    while add_val:
        questions = [
            {
                'type': 'input',
                'name': 'ip',
                'message': 'Provider ip',
            },
            {
                'type': 'list',
                'name': 'add_val',
                'message': 'Add next provider ?',
                'choices': [
                    {
                        'name': 'Yes',
                        'value': True
                    },
                    {
                        'name': 'No',
                        'value': False
                    }
                ]
            }
        ]
        answers = inquirer.prompt(questions, style=aergo_style)
        providers.append(answers['ip'])
        add_val = answers['add_val']
    return providers


def prompt_eth_keystore():
    """Prompt use to input a new ethereum private key.

    Returns:
        - name of the key
        - address of the key
        - path to the json key file

    """
    while 1:
        questions = [
            {
                'type': 'input',
                'name': 'account_name',
                'message': 'Give your key a short descriptive name'
            },
            {
                'type': 'input',
                'name': 'privkey',
                'message': 'Path to Ethereum keystore'
            },
            {
                'type': 'input',
                'name': 'addr',
                'message': 'Ethereum address matching private key'
            }
        ]
        answers = inquirer.prompt(questions, style=aergo_style)
        account_name = answers['account_name']
        privkey_path = answers['privkey']
        addr = answers['addr']
        try:
            with open(privkey_path, "r") as f:
                f.read()
            break
        except (IsADirectoryError, FileNotFoundError):
            print("Invalid key path")
    return account_name, addr, privkey_path


def prompt_aergo_keystore():
    """Prompt user to input a new aergo private key.

    Returns:
        - name of the key
        - address of the key
        - path to keystore

    """
    while 1:
        questions = [
            {
                'type': 'input',
                'name': 'account_name',
                'message': 'Give your key a short descriptive name'
            },
            {
                'type': 'input',
                'name': 'privkey',
                'message': 'Path to Aergo Keystore'
            },
            {
                'type': 'input',
                'name': 'addr',
                'message': 'Aergo address matching private key'
            }
        ]
        answers = inquirer.prompt(questions, style=aergo_style)
        privkey_path = answers['privkey']
        account_name = answers['account_name']
        addr = answers['addr']
        try:
            with open(privkey_path, "r") as f:
                f.read()
            break
        except (IsADirectoryError, FileNotFoundError):
            print("Invalid key path")
    return account_name, addr, privkey_path


def prompt_new_asset(networks):
    """Prompt user to input a new asset by providing the following:
    - asset name
    - origin network (where it was first issued)
    - address on origin network
    - other networks where the asset exists as a peg
    - address of pegs

    """
    questions = [
        {
            'type': 'input',
            'name': 'name',
            'message': "Asset name ('aergo_erc20' and 'aergo' are "
                       "used for the real Aergo)"
        },
        {
            'type': 'list',
            'name': 'origin',
            'message': 'Origin network '
                       '(where the token was originally issued)',
            'choices': networks
        },
        {
            'type': 'input',
            'name': 'origin_addr',
            'message': 'Asset address'
        },
        {
            'type': 'list',
            'name': 'add_peg',
            'message': 'Add pegged asset on another network',
            'choices': [
                {
                    'name': 'Yes',
                    'value': True
                },
                {
                    'name': 'No',
                    'value': False
                }
            ]
        }
    ]
    answers = inquirer.prompt(questions, style=aergo_style)
    name = answers['name']
    origin = answers['origin']
    origin_addr = answers['origin_addr']
    networks.remove(origin)
    add_peg = answers['add_peg']
    pegs = []
    peg_addrs = []
    while add_peg:
        if len(networks) == 0:
            print('All pegged assets are registered in know networks')
            break
        questions = [
            {
                'type': 'list',
                'name': 'peg',
                'message': 'Pegged network',
                'choices': networks
            },
            {
                'type': 'input',
                'name': 'peg_addr',
                'message': 'Asset address'
            },
            {
                'type': 'list',
                'name': 'add_peg',
                'message': 'Add another pegged asset on another network',
                'choices': ['Yes', 'No']
            }
        ]
        answers = inquirer.prompt(questions, style=aergo_style)
        peg = answers['peg']
        peg_addr = answers['peg_addr']
        add_peg = answers['add_peg']
        networks.remove(peg)
        pegs.append(peg)
        peg_addrs.append(peg_addr)
    return name, origin, origin_addr, pegs, peg_addrs


def prompt_new_validators():
    """Prompt user to input validators

    Note:
        The list of validators must have the same order as defined in the
        bridge contracts

    Returns:
        List of ordered validators

    """

    print("WARNING : Validators must be registered in the correct order")
    validators = []
    add_val = True
    while add_val:
        questions = [
            {
                'type': 'input',
                'name': 'addr',
                'message': 'Aergo Address',
            },
            {
                'type': 'input',
                'name': 'eth-addr',
                'message': 'Ethereum Address',
            },
            {
                'type': 'input',
                'name': 'ip',
                'message': 'Validator ip',
            },
            {
                'type': 'list',
                'name': 'add_val',
                'message': 'Add next validator ?',
                'choices': [
                    {
                        'name': 'Yes',
                        'value': True
                    },
                    {
                        'name': 'No',
                        'value': False
                    }
                ]
            }
        ]
        answers = inquirer.prompt(questions, style=aergo_style)
        validators.append({'addr': answers['addr'],
                           'eth-addr': answers['eth-addr'],
                           'ip': answers['ip']}
                          )
        add_val = answers['add_val']
    return validators


def print_balance_table_header():
    print(' ' + '_' * 120)
    print('|' + ' Name'.ljust(16) + '| Network'.ljust(24)
          + '| Token Address'.ljust(55) + '| Balance'.ljust(25) + '|')


def print_balance_table_lines(lines, token_name, col_widths):
    if len(lines) > 0:
        print('|' + '‾' * 16 + '|' + '‾' * 103 + '|')
        print('| ' + token_name.ljust(15) + '|'.ljust(104) + '|')
        for line in lines:
            print(
                '|' + '\t\t | '
                + "".join(col.ljust(col_widths[i])
                          for i, col in enumerate(line))
                + '|'
            )
