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
    questions = [
        inquirer.Text(
            'amount',
            message="Amount of assets to transfer : ",
        )
    ]
    answers = inquirer.prompt(questions)
    return int(answers['amount']) * 10**18


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
