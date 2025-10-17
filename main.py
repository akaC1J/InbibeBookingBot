import logging

from inbibe_bot.logging_config import setup_logging

# Register handlers
# noinspection PyUnresolvedReferences
import inbibe_bot.handlers.admins  # noqa: F401
# noinspection PyUnresolvedReferences
import inbibe_bot.handlers.user  # noqa: F401
from inbibe_bot.server.handler import Handler

import threading
import socketserver
from inbibe_bot.bot_instance import bot


def run_http_server() -> None:
    with socketserver.TCPServer(("", 8000), Handler) as httpd:
        logging.info("🌐 HTTP сервер запущен на порту 8000")
        httpd.serve_forever()


if __name__ == "__main__":
    setup_logging()

    # Запускаем HTTP-сервер в отдельном потоке
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()

    logging.info("🤖 Telegram-бот запущен")
    bot.polling(none_stop=True)
