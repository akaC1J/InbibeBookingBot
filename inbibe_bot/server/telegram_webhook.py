from __future__ import annotations

import logging
from http.server import BaseHTTPRequestHandler

import telebot

logger = logging.getLogger(__name__)


def handle_webhook(
    handler: BaseHTTPRequestHandler,
    bot: telebot.TeleBot,
    webhook_secret: str,
) -> None:
    secret = handler.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret != webhook_secret:
        handler.send_response(403)
        handler.end_headers()
        return

    try:
        content_length = int(handler.headers.get("Content-Length", 0))
    except (TypeError, ValueError):
        handler.send_response(400)
        handler.end_headers()
        return

    if content_length <= 0:
        handler.send_response(400)
        handler.end_headers()
        return

    try:
        raw_body = handler.rfile.read(content_length)
        json_string = raw_body.decode("utf-8")
    except Exception:
        handler.send_response(400)
        handler.end_headers()
        return

    try:
        update = telebot.types.Update.de_json(json_string)
    except Exception:
        handler.send_response(400)
        handler.end_headers()
        return

    try:
        bot.process_new_updates([update])
    except Exception:
        logger.exception("Ошибка обработки webhook update")
        handler.send_response(500)
        handler.end_headers()
        return

    handler.send_response(200)
    handler.end_headers()
