import logging

logger = logging.getLogger("proposer")
logger.setLevel(logging.INFO)

file_formatter = logging.Formatter(
    '{"level": "%(levelname)s", "time": "%(asctime)s", '
    '"thread": "%(name)s", "function": "%(funcName)s", '
    '"message": %(message)s'
)
stream_formatter = logging.Formatter("%(name)s: %(message)s")


file_handler = logging.FileHandler('logs/proposer.log')
file_handler.setFormatter(file_formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(stream_formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)
