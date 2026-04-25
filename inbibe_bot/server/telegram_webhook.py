from __future__ import annotations

import logging

import telebot
from flask import request

logger = logging.getLogger(__name__)


def handle_webhook(bot: telebot.TeleBot, webhook_secret: str) -> tuple[str, int]:
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret != webhook_secret:
        return "", 403

    raw = request.get_data()
    if not raw:
        return "", 400

    try:
        json_string = raw.decode("utf-8")
    except UnicodeDecodeError:
        return "", 400

    try:
        update = telebot.types.Update.de_json(json_string)
    except Exception:
        return "", 400

    try:
        bot.process_new_updates([update])
    except Exception:
        logger.exception("Ошибка обработки webhook update")
        return "", 500

    return "", 200
