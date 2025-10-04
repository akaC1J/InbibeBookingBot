import os

from inbibe_bot.logging_config import setup_logging
from inbibe_bot.bot_instance import bot

# Register handlers
# noinspection PyUnresolvedReferences
import inbibe_bot.handlers.admins  # noqa: F401
# noinspection PyUnresolvedReferences
import inbibe_bot.handlers.user  # noqa: F401

if __name__ == "__main__":
    setup_logging()
    bot.polling(none_stop=True)
