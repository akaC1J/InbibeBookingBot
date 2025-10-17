import os
import logging
from logging.handlers import TimedRotatingFileHandler

LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "inbibe-bot.log")

os.makedirs(LOG_DIR, exist_ok=True)


def setup_logging() -> None:
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATEFMT)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = TimedRotatingFileHandler(
        LOG_FILE,
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.suffix = "-%Y-%m-%d.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)

    if not root_logger.handlers:
        root_logger.addHandler(console_handler)
        # root_logger.addHandler(file_handler)

    logging.getLogger("inbibe_bot").setLevel(logging.DEBUG)
