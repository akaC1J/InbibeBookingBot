import logging
import os

import telebot

TG_API_KEY = os.getenv("TG_API_KEY")  # Ваш токен бота
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID") or 0) # ID группы администраторов
WEBHOOK_URL = os.getenv("WEBHOOK_URL") # Публичный URL для вебхука
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")


if TG_API_KEY is None or ADMIN_GROUP_ID is None:
    raise Exception("Не заданы необходимые переменные окружения")

logger = logging.getLogger(__name__)

bot = telebot.TeleBot(TG_API_KEY)
logger.debug(f'Бот сконфигурирован API_KEY:{TG_API_KEY}, ID группы администраторов {ADMIN_GROUP_ID}')
