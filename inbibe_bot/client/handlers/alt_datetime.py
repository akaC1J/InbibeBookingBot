from __future__ import annotations

import logging

from telebot.types import Message

from inbibe_bot.client.bot_factory import Deps
from inbibe_bot.client.keyboards import build_table_keyboard
from inbibe_bot.shared.datetime_utils import parse_admin_datetime

logger = logging.getLogger(__name__)


def register(deps: Deps) -> None:
    bot = deps.bot

    @bot.message_handler(
        func=lambda msg: (
            msg.chat.id == deps.config.admin_group_id
            and msg.reply_to_message is not None
            and deps.booking_repo.find_by_alt_request_message_id(msg.reply_to_message.message_id) is not None
        )
    )
    def handle_alt_datetime_reply(message: Message) -> None:
        booking = deps.booking_repo.find_by_alt_request_message_id(
            message.reply_to_message.message_id  # type: ignore[union-attr]
        )
        if not booking:
            return

        deps.ephemeral.register(booking.id, message)

        new_dt = parse_admin_datetime(message.text)
        if new_dt is None:
            reply = bot.reply_to(
                message,
                "Неверный формат даты/времени. Попробуйте снова.\nОжидаемый формат: DD.MM.YY HH:MM",
            )
            deps.ephemeral.register(booking.id, reply)
            return

        deps.workflow.apply_new_datetime(booking, new_dt)
        deps.workflow.request_table_selection(booking)
        booking.alt_request_message_id = None
        deps.booking_repo.update(booking)

        try:
            kb = build_table_keyboard(booking.id, list(deps.config.actual_tables))
            msg = bot.send_message(
                deps.config.admin_group_id,
                deps.formatter.admin_table_prompt(booking),
                reply_markup=kb,
            )
            deps.ephemeral.register(booking.id, msg)
            booking.table_request_message_id = msg.message_id
            deps.booking_repo.update(booking)
        except Exception:
            logger.exception("Ошибка при отправке клавиатуры стола после alt_datetime для заявки %s", booking.id)

        logger.info("Заявка %s: дата/время обновлены на %s", booking.id, new_dt)
