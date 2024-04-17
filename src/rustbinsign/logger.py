import logging

logger = logging.getLogger("rustbinsign")
logger.addHandler(logging.NullHandler())

LOG_FILENAME = "rustbinsign.log"


def get_log_handler():
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    log_handler = logging.StreamHandler()
    log_handler.setFormatter(formatter)
    return log_handler
