import logging
import os

import telebot

API_KEY = os.getenv("api_key")  # Ваш токен бота

ADMIN_GROUP_ID = int(os.getenv("admin_group_id") or 0) # ID группы администраторов

logger = logging.getLogger(__name__)

bot = telebot.TeleBot(API_KEY)
logger.debug(f'Бот сконфигурирован API_KEY:{API_KEY}, ID группы администраторов {ADMIN_GROUP_ID}')
