import logging
import sys
import time
import socketserver

from requests import ReadTimeout, ConnectionError
from telebot.apihelper import ApiTelegramException

from inbibe_bot.logging_config import setup_logging

# Register handlers
# noinspection PyUnresolvedReferences
import inbibe_bot.handlers.admins  # noqa: F401
# noinspection PyUnresolvedReferences
import inbibe_bot.handlers.user  # noqa: F401
from inbibe_bot.server.handler import Handler
from inbibe_bot.bot_instance import bot, WEBHOOK_URL


def run_http_server() -> None:
    with socketserver.TCPServer(("", 8000), Handler) as httpd:
        logging.info("🌐 HTTP сервер запущен на порту 8000")
        httpd.serve_forever()


if __name__ == "__main__":
    setup_logging()

    if WEBHOOK_URL:
        bot.remove_webhook()
        # Даем время Telegram обработать удаление и освободить ресурсы
        time.sleep(1)
        bot.set_webhook(url=WEBHOOK_URL + "/webhook")
        logging.info(f"✅ Webhook установлен: {WEBHOOK_URL}/webhook")
    else:
        logging.error("❌ WEBHOOK_URL не задан, запуск невозможен")
        sys.exit(1)

    logging.info("🤖 Telegram-бот запущен (Event-driven mode)")

    try:
        run_http_server()
    except KeyboardInterrupt:
        logging.info("🛑 Остановка бота...")
    finally:
        if WEBHOOK_URL:
            bot.remove_webhook()
            logging.info("🧹 Webhook удален")
