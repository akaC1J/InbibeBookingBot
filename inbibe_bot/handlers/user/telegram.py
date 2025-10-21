from __future__ import annotations

import logging

from telebot.types import CallbackQuery, Message, ReplyKeyboardRemove

from inbibe_bot.bot_instance import ADMIN_GROUP_ID, bot
from inbibe_bot.handlers.user.user_state_machine import UserStateMachine
from inbibe_bot.keyboards import main_menu_keyboard
from inbibe_bot.models import Booking
from inbibe_bot.utils import format_date_russian

logger = logging.getLogger(__name__)


def _notify_admins_about_booking(booking: Booking) -> None:
    """Отправляет уведомление администраторам о новой броне."""

    booking_text = (
        f"📥 Новая бронь (TG):\n"
        f"ID: {booking.id}\n"
        f"Имя: {booking.name}\n"
        f"Телефон: {booking.phone}\n"
        f"Дата: {format_date_russian(booking.date_time)}\n"
        f"Время: {booking.date_time:%H:%M}\n"
        f"Гостей: {booking.guests}"
    )

    if ADMIN_GROUP_ID:
        bot.send_message(ADMIN_GROUP_ID, booking_text)
    logger.info("Администраторы уведомлены о брони %s", booking.id)


machine = UserStateMachine(on_booking_created=_notify_admins_about_booking)


# === /start ==================================================================
@bot.message_handler(commands=["start"])
def cmd_start(message: Message) -> None:
    """Обрабатывает команду /start — приветствие и инициализация состояния."""

    chat_id = message.chat.id
    chat_type = message.chat.type
    logger.info("Получена команда /start от chat_id=%s", chat_id)

    if chat_type != "private":
        logger.debug("Игнорируем /start для чата типа %s", chat_type)
        return

    machine.reset_state(chat_id)

    bot.send_message(
        chat_id,
        (
            "Добро пожаловать в бар *Инбайб*!\n"
            "Мы работаем каждый день с *15:00 до 03:00*,\n"
            "а по *пятницам и субботам* — до *05:00*.\n\n"
            "Чтобы начать бронирование, нажмите кнопку «Начать бронирование».\n"
            "Если хотите начать заново — введите /start."
        ),
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown",
    )
    logger.info("Приветственное сообщение отправлено пользователю %s", chat_id)


# === Обработка сообщений =====================================================


@bot.message_handler(func=lambda msg: msg.chat.type == "private", content_types=["text"])
def handle_message(message: Message) -> None:
    """Основная логика состояний бронирования."""

    chat_id = message.chat.id
    text = (message.text or "").strip()
    logger.debug("Сообщение от %s: %s", chat_id, text)

    if not machine.has_state(chat_id):
        bot.send_message(chat_id, "Пожалуйста, начните с команды /start", reply_markup=ReplyKeyboardRemove())
        return

    machine.process_text(chat_id, text)


# === Обработка контакта =====================================================


@bot.message_handler(content_types=["contact"])
def handle_contact(message: Message) -> None:
    """Получение телефона через кнопку «Отправить контакт»."""

    chat_id = message.chat.id
    logger.debug("Контакт от %s", chat_id)

    if not machine.has_state(chat_id):
        logger.warning("Пользователь %s не найден при отправке контакта", chat_id)
        bot.send_message(chat_id, "Пожалуйста, начните с команды /start", reply_markup=ReplyKeyboardRemove())
        return

    machine.process_contact(message)


# === Callback: выбор даты и времени ==========================================


@bot.callback_query_handler(func=lambda call: (call.data or "").startswith("date_"))
def handle_date_callback(call: CallbackQuery) -> None:
    logger.debug("Callback даты от %s: %s", call.from_user.id, call.data)
    handled = machine.process_callback(call)
    if not handled:
        bot.answer_callback_query(call.id, "Выбор даты больше неактуален.")


@bot.callback_query_handler(func=lambda call: (call.data or "").startswith("time_") or (call.data or "") == "ignore")
def handle_time_callback(call: CallbackQuery) -> None:
    logger.debug("Callback времени от %s: %s", call.from_user.id, call.data)
    handled = machine.process_callback(call)
    if not handled:
        bot.answer_callback_query(call.id, "Выбор времени больше неактуален.")


# === Вспомогательное =========================================================


__all__ = [
    "cmd_start",
    "handle_message",
    "handle_contact",
    "handle_date_callback",
    "handle_time_callback",
    "machine",
]

