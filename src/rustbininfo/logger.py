import logging

logger = logging.getLogger("rustbininfo")
logger.addHandler(logging.NullHandler())

LOG_FILENAME = "rustbininfo.log"


def get_log_handler():
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    log_handler = logging.StreamHandler()
    log_handler.setFormatter(formatter)
    return log_handler
