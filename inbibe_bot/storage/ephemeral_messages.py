from __future__ import annotations

import logging
from collections import defaultdict
from typing import Callable, DefaultDict

import telebot

logger = logging.getLogger(__name__)


class EphemeralMessageService:
    """Управляет временными сообщениями в админ-чате, связанными с заявкой."""

    def __init__(self, bot: telebot.TeleBot) -> None:
        self._bot = bot
        self._messages: DefaultDict[str, list[tuple[int, int]]] = defaultdict(list)
        self._on_change: Callable[[], None] | None = None

    def set_change_callback(self, fn: Callable[[], None]) -> None:
        self._on_change = fn

    def register(self, booking_id: str, message: telebot.types.Message) -> None:
        self._messages[booking_id].append((message.chat.id, message.message_id))
        logger.debug(
            "Зарегистрировано временное сообщение для заявки %s (chat_id=%s, message_id=%s)",
            booking_id, message.chat.id, message.message_id,
        )
        self._notify()

    def clear(self, booking_id: str) -> None:
        for chat_id, message_id in self._messages.pop(booking_id, []):
            try:
                self._bot.delete_message(chat_id, message_id)
                logger.debug("Удалено временное сообщение (заявка %s, message_id=%s)", booking_id, message_id)
            except Exception as exc:
                logger.warning("Не удалось удалить временное сообщение заявки %s: %s", booking_id, exc)
        self._notify()

    def snapshot(self) -> dict[str, list[list[int]]]:
        return {k: [list(m) for m in v] for k, v in self._messages.items()}

    def restore(self, data: dict[str, list[list[int]]]) -> None:
        self._messages.clear()
        for k, v in data.items():
            self._messages[k] = [(chat_id, msg_id) for chat_id, msg_id in v]

    def _notify(self) -> None:
        if self._on_change:
            self._on_change()
