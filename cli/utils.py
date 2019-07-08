import inquirer


def confirm_transfer():
    """Prompt user to procede with a transfer of not."""
    questions = [
        inquirer.List(
            'confirm',
            message="Confirm you want to execute tranfer tx",
            choices=[
                ('Yes, execute transfer', True),
                ('No, get me out of here!', False)
            ]
        )
    ]
    answers = inquirer.prompt(questions)
    return answers['confirm']


def prompt_number(message, formator=int):
    """Prompt a number."""
    while 1:
        questions = [
            inquirer.Text(
                'num',
                message=message,
            )
        ]
        answers = inquirer.prompt(questions)
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
    for i, digit in enumerate(num[periode+1:]):
        decimals += int(digit) * 10**(17-i)
    return int(num[:periode]) * 10**18 + decimals


def prompt_deposit_height():
    """Prompt the block number of deposit."""
    return prompt_number("Block height of deposit (0 to try finalization "
                         "anyway)")


def prompt_new_bridge(net1, net2):
    """Prompt user to input bridge contracts and tempo.

    For each contract on each bridged network, provide:
    - bridge contract address
    - anchoring periode
    - finality of the anchored chain

    """
    print('Bridge between {} and {}'.format(net1, net2))
    questions = [
        inquirer.Text(
            'bridge1',
            message="Bridge contract address on {}".format(net1)
        ),
        inquirer.Text(
            't_anchor1',
            message="Anchoring periode of {} on {}".format(net2, net1)
        ),
        inquirer.Text(
            't_final1',
            message="Finality of {}".format(net2)
        ),
        inquirer.Text(
            'bridge2',
            message="Bridge contract address on {}".format(net2)
        ),
        inquirer.Text(
            't_anchor2',
            message="Anchoring periode of {} on {}".format(net1, net2)
        ),
        inquirer.Text(
            't_final2',
            message="Finality of {}".format(net1)
        )
    ]
    return inquirer.prompt(questions)


def prompt_file_path(message):
    """Prompt user to input a path to a file and check it exists."""
    while 1:
        questions = [
            inquirer.Text(
                'path',
                message=message
            )
        ]
        answers = inquirer.prompt(questions)
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
    return bridge_abi, minted_abi


def prompt_new_network():
    """Prompt user to input a new network's information:
    - Name
    - IP/url
    - Network type (aergo/eth)
    - is POA (only needed for ethereum)

    """
    questions = [
        inquirer.Text(
            'name',
            message="Network name"
        ),
        inquirer.Text(
            'ip',
            message="Network IP"
        ),
        inquirer.List(
            'type',
            message="Network type",
            choices=[
                'ethereum',
                'aergo'
            ]
        )
    ]
    answers = inquirer.prompt(questions)
    if answers['type'] == 'ethereum':
        questions = [
            inquirer.List(
                'isPOA',
                message='Is this an Ethereum POA network ?',
                choices=[True, False]
            )
        ]
        is_poa = inquirer.prompt(questions)['isPOA']
        answers['isPOA'] = is_poa
    return answers


def prompt_eth_privkey():
    """Prompt use to input a new ethereum private key.

    Returns:
        - name of the key
        - address of the key
        - path to the json key file

    """
    while 1:
        questions = [
            inquirer.Text(
                'privkey_name',
                message="Give your key a short descriptive name"
            ),
            inquirer.Text(
                'privkey',
                message="Path to json keystore"
            ),
            inquirer.Text(
                'addr',
                message="Ethereum address matching private key"
            )
        ]
        answers = inquirer.prompt(questions)
        privkey_name = answers['privkey_name']
        privkey_path = answers['privkey']
        addr = answers['addr']
        try:
            with open(privkey_path, "r") as f:
                f.read()
            break
        except (IsADirectoryError, FileNotFoundError):
            print("Invalid key path")
    return privkey_name, addr, privkey_path


def prompt_aergo_privkey():
    """Prompt user to input a new aergo private key.

    Returns:
        - name of the key
        - address of the key
        - encrypted private key

    """
    questions = [
        inquirer.Text(
            'privkey_name',
            message="Give your key a short descriptive name"
        ),
        inquirer.Text(
            'privkey',
            message="Encrypted exported key string"
        ),
        inquirer.Text(
            'addr',
            message="Aergo address matching private key"
        )
    ]
    answers = inquirer.prompt(questions)
    privkey = answers['privkey']
    privkey_name = answers['privkey_name']
    addr = answers['addr']
    return privkey_name, addr, privkey


def prompt_new_asset(networks):
    """Prompt user to input a new asset by providing the following:
    - asset name
    - origin network (where it was first issued)
    - address on origin network
    - other networks where the asset exists as a peg
    - address of pegs

    """
    questions = [
        inquirer.Text(
            'name',
            message="Asset name ('aergo_erc20' and 'aergo' are "
                    "used for the real Aergo)"
        ),
        inquirer.List(
            'origin',
            message="Origin network "
                    "(where the token was originally issued)",
            choices=networks
        ),
        inquirer.Text(
            'origin_addr',
            message="Asset address"
        ),
        inquirer.List(
            'add_peg',
            message="Add pegged asset on another network",
            choices=[True, False]
        )
    ]
    answers = inquirer.prompt(questions)
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
            inquirer.List(
                'peg',
                message="Pegged network",
                choices=networks
            ),
            inquirer.Text(
                'peg_addr',
                message="Asset address"
            ),
            inquirer.List(
                'add_peg',
                message="Add another pegged asset on another network",
                choices=['Yes', 'No']
            )
        ]
        answers = inquirer.prompt(questions)
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
            inquirer.Text(
                'addr',
                message='Aergo Address',
            ),
            inquirer.Text(
                'eth-addr',
                message='Ethereum Address',
            ),
            inquirer.Text(
                'ip',
                message='Validator ip',
            ),
            inquirer.List(
                'add_val',
                message='Add next validator ?',
                choices=[True, False]
            )
        ]
        answers = inquirer.prompt(questions)
        validators.append({'addr': answers['addr'],
                           'eth-addr': answers['eth-addr'],
                           'ip': answers['ip']}
                          )
        add_val = answers['add_val']
    return validators
