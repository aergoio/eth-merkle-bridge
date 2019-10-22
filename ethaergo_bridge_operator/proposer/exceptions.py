class ValidatorMajorityError(Exception):
    """ Exception raised by proposers when they fail to gather 2/3 validator
    signatures to make an update.
    """
    pass
