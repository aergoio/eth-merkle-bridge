import re

from aergo.herapy.utils.encoding import decode_b58_check


def is_ethereum_address(address: str):
    if address[:2] != '0x':
        return False
    match = re.match("^[a-fA-F0-9]*$", address[2:])
    if match is None:
        return False
    if len(address) != 42:
        return False
    return True


def is_aergo_address(address: str):
    if address[0] != 'A':
        return False
    try:
        decode_b58_check(address)
    except ValueError:
        return False
    if len(address) != 52:
        return False
    return True
