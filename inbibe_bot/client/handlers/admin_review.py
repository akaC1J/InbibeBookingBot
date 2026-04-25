from __future__ import annotations

import logging
from datetime import datetime, timedelta

from telebot.types import CallbackQuery

from inbibe_bot.client.bot_factory import Deps, notify_user
from inbibe_bot.client.callbacks import CallbackData
from inbibe_bot.client.keyboards import build_table_keyboard
from inbibe_bot.core.errors import InvalidTransition, BookingNotFound

logger = logging.getLogger(__name__)


def register(deps: Deps) -> None:
    bot = deps.bot

    @bot.callback_query_handler(func=lambda call: (call.data or "").startswith(CallbackData.APPROVE_ALT))
    def handle_approve_alt(call: CallbackQuery) -> None:
        booking_id = CallbackData.parse_booking_id(call.data or "", CallbackData.APPROVE_ALT)
        try:
            booking = deps.booking_repo.require(booking_id)
        except BookingNotFound:
            bot.answer_callback_query(call.id, "Заявка не найдена.", show_alert=True)
            return
        try:
            deps.workflow.request_new_datetime(booking)
        except InvalidTransition:
            bot.answer_callback_query(call.id, "Действие неактуально.", show_alert=True)
            return
        deps.booking_repo.update(booking)

        suggested = datetime.now() + timedelta(hours=2)
        msg = bot.send_message(
            deps.config.admin_group_id,
            deps.formatter.admin_alt_datetime_prompt(booking, suggested),
        )
        deps.ephemeral.register(booking_id, msg)
        booking.alt_request_message_id = msg.message_id
        deps.booking_repo.update(booking)
        bot.answer_callback_query(call.id, "Ожидается новая дата/время.")
        logger.info("Запрошено изменение даты/времени для заявки %s", booking_id)

    @bot.callback_query_handler(
        func=lambda call: (call.data or "").startswith(CallbackData.APPROVE)
        and not (call.data or "").startswith(CallbackData.APPROVE_ALT)
    )
    def handle_approve(call: CallbackQuery) -> None:
        booking_id = CallbackData.parse_booking_id(call.data or "", CallbackData.APPROVE)
        try:
            booking = deps.booking_repo.require(booking_id)
        except BookingNotFound:
            bot.answer_callback_query(call.id, "Заявка не найдена.", show_alert=True)
            return
        try:
            deps.workflow.request_table_selection(booking)
        except InvalidTransition:
            bot.answer_callback_query(call.id, "Действие неактуально.", show_alert=True)
            return
        deps.booking_repo.update(booking)

        try:
            kb = build_table_keyboard(booking_id, list(deps.config.actual_tables))
            msg = bot.send_message(
                deps.config.admin_group_id,
                deps.formatter.admin_table_prompt(booking),
                reply_markup=kb,
            )
            deps.ephemeral.register(booking_id, msg)
            booking.table_request_message_id = msg.message_id
            deps.booking_repo.update(booking)
            bot.answer_callback_query(call.id, "Выберите номер стола")
        except Exception:
            logger.exception("Ошибка при отправке клавиатуры стола для заявки %s", booking_id)
            bot.answer_callback_query(call.id, "Ошибка при отправке клавиатуры", show_alert=True)

    @bot.callback_query_handler(func=lambda call: (call.data or "").startswith(CallbackData.REJECT))
    def handle_reject(call: CallbackQuery) -> None:
        booking_id = CallbackData.parse_booking_id(call.data or "", CallbackData.REJECT)
        try:
            booking = deps.booking_repo.require(booking_id)
        except BookingNotFound:
            bot.answer_callback_query(call.id, "Заявка не найдена.", show_alert=True)
            return
        try:
            deps.workflow.reject(booking)
        except InvalidTransition:
            bot.answer_callback_query(call.id, "Действие неактуально.", show_alert=True)
            return
        deps.booking_repo.update(booking)

        notify_user(deps, booking, deps.formatter.user_rejected(booking))
        try:
            bot.edit_message_text(
                deps.formatter.admin_final(booking),
                chat_id=call.message.chat.id,
                message_id=booking.admin_message_id or -1,
                parse_mode="Markdown",
            )
        except Exception:
            logger.error("Не удалось обновить карточку заявки %s", booking_id)

        bot.answer_callback_query(call.id, "Обработано.")
        deps.booking_repo.delete(booking_id)
        deps.ephemeral.clear(booking_id)
        logger.info("Заявка %s отклонена", booking_id)
