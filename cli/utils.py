import inquirer


def confirm_transfer():
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


def get_amount():
    while 1:
        try:
            questions = [
                inquirer.Text(
                    'amount',
                    message="Amount of assets to transfer",
                )
            ]
            answers = inquirer.prompt(questions)
            amount = int(answers['amount']) * 10**18
            break
        except ValueError:
            print("Invalid amount")
    return amount


def get_asset_abi(path):
    with open(path, "r") as f:
        abi = f.read()
    return abi


def get_deposit_height():
    questions = [
        inquirer.Text(
            'height',
            message="Block height of deposit (0 to try finalization anyway)",
        )
    ]
    answers = inquirer.prompt(questions)
    return int(answers['height'])


def get_bridge(net1, net2):
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


def get_network():
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


def get_eth_privkey():
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


def get_abi():
    while 1:
        questions = [
            inquirer.Text(
                'abi_path',
                message="Path to abi"
            )
        ]
        answers = inquirer.prompt(questions)
        abi_path = answers['abi_path']
        try:
            with open(abi_path, "r") as f:
                f.read()
            break
        except (IsADirectoryError, FileNotFoundError):
            print("Invalid abi path")
    return abi_path


def get_aergo_privkey():
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


def get_new_asset(networks):
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


def get_validators():
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
