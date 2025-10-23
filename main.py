import logging
import time

from requests import ReadTimeout
from telebot.apihelper import ApiTelegramException

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

    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()

    logging.info("🤖 Telegram-бот запущен")

    while True:
        try:
            # none_stop=True поможет с мелкими сбоями
            bot.polling(none_stop=True, interval=0, timeout=60)

        except (ReadTimeout, ConnectionError) as e:
            logging.error(f"⚠️ Сетевая ошибка: {e}")
            logging.info("🔄 Переподключение через 5 секунд...")
            time.sleep(5)

        except KeyboardInterrupt:
            logging.info("🛑 Остановка бота...")
            break

        except Exception as e:
            logging.error(f"❌ Неожиданная ошибка: {e}", exc_info=True)
            logging.info("🔄 Перезапуск через 15 секунд...")
            time.sleep(15)
