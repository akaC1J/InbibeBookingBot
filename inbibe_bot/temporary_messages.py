"""Utilities for managing temporary admin messages that should be cleaned up."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import DefaultDict, List, Tuple

from telebot.types import Message

from inbibe_bot.bot_instance import bot

logger = logging.getLogger(__name__)

_EphemeralMessage = Tuple[int, int]
_EphemeralStorage = DefaultDict[str, List[_EphemeralMessage]]
_ephemeral_messages: _EphemeralStorage = defaultdict(list)


def _register_ephemeral_message(booking_id: str, chat_id: int, message_id: int) -> None:
    _ephemeral_messages[booking_id].append((chat_id, message_id))
    logger.debug(
        "Зарегистрировано временное сообщение для заявки %s (chat_id=%s, message_id=%s)",
        booking_id,
        chat_id,
        message_id,
    )


def clear_ephemeral_messages(booking_id: str) -> None:
    """Удалить и забыть все временные сообщения, связанные с заявкой."""

    messages = _ephemeral_messages.pop(booking_id, [])
    for chat_id, message_id in messages:
        try:
            bot.delete_message(chat_id, message_id)
            logger.debug(
                "Удалено временное сообщение для заявки %s (chat_id=%s, message_id=%s)",
                booking_id,
                chat_id,
                message_id,
            )
        except Exception as exc:  # pragma: no cover - зависит от Telegram API
            logger.warning(
                "Не удалось удалить временное сообщение для заявки %s: %s",
                booking_id,
                exc,
            )


def send_ephemeral_reply(booking_id: str, message: Message, text: str, **kwargs) -> Message:
    """Отправить reply-сообщение, которое будет удалено при следующем шаге."""

    reply = bot.reply_to(message, text, **kwargs)
    _register_ephemeral_message(booking_id, message.chat.id, reply.message_id)
    return reply


def send_ephemeral_message(booking_id: str, chat_id: int, text: str, **kwargs) -> Message:
    """Отправить сообщение, которое будет удалено при следующем шаге."""

    sent = bot.send_message(chat_id, text, **kwargs)
    _register_ephemeral_message(booking_id, chat_id, sent.message_id)
    return sent
