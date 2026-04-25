from __future__ import annotations

import logging

from telebot.types import CallbackQuery, Message

from inbibe_bot.client.bot_factory import Deps, notify_user
from inbibe_bot.client.callbacks import CallbackData
from inbibe_bot.core.booking import Booking
from inbibe_bot.core.errors import InvalidTransition, BookingNotFound

logger = logging.getLogger(__name__)


def register(deps: Deps) -> None:
    bot = deps.bot

    @bot.callback_query_handler(func=lambda call: (call.data or "").startswith(CallbackData.TABLE))
    def handle_table_inline(call: CallbackQuery) -> None:
        try:
            booking_id, table_num = CallbackData.parse_table(call.data or "")
        except (ValueError, IndexError):
            bot.answer_callback_query(call.id, "Неверные данные.", show_alert=True)
            return

        try:
            booking = deps.booking_repo.require(booking_id)
        except BookingNotFound:
            bot.answer_callback_query(call.id, "Заявка не найдена.", show_alert=True)
            return

        try:
            deps.workflow.assign_tables(booking, {table_num})
        except (InvalidTransition, ValueError) as e:
            bot.answer_callback_query(call.id, str(e), show_alert=True)
            return

        _finalize_approval(deps, booking, call.message.chat.id)
        bot.answer_callback_query(call.id, "Стол выбран, бронь подтверждена.")
        logger.info("Заявка %s подтверждена (стол %s)", booking_id, table_num)

    @bot.message_handler(
        func=lambda msg: (
            msg.chat.id == deps.config.admin_group_id
            and msg.reply_to_message is not None
            and deps.booking_repo.find_by_table_request_message_id(msg.reply_to_message.message_id) is not None
        )
    )
    def handle_table_reply(message: Message) -> None:
        booking = deps.booking_repo.find_by_table_request_message_id(
            message.reply_to_message.message_id  # type: ignore[union-attr]
        )
        if not booking:
            return

        deps.ephemeral.register(booking.id, message)

        try:
            assert message.text is not None
            table_numbers = {int(t) for t in message.text.split()}
        except (ValueError, AssertionError):
            reply = bot.reply_to(message, "Пожалуйста, вводите только числа через пробел.")
            deps.ephemeral.register(booking.id, reply)
            return

        try:
            deps.workflow.assign_tables(booking, table_numbers)
        except (InvalidTransition, ValueError) as e:
            reply = bot.reply_to(message, str(e))
            deps.ephemeral.register(booking.id, reply)
            return

        _finalize_approval(deps, booking, message.chat.id)
        logger.info("Заявка %s подтверждена через reply (столы %s)", booking.id, table_numbers)


def _finalize_approval(deps: Deps, booking: Booking, admin_chat_id: int) -> None:
    notify_user(deps, booking, deps.formatter.user_approved(booking))
    try:
        deps.bot.edit_message_text(
            deps.formatter.admin_final(booking),
            chat_id=admin_chat_id,
            message_id=booking.admin_message_id or -1,
            parse_mode="Markdown",
        )
    except Exception:
        logger.error("Не удалось обновить карточку заявки %s", booking.id)
    deps.delivery_queue.enqueue(booking)
    deps.booking_repo.delete(booking.id)
    deps.ephemeral.clear(booking.id)
