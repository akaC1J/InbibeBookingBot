from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, date
from typing import Any, Final

import telebot
from telebot.types import Message, CallbackQuery, ReplyKeyboardRemove

from inbibe_bot import utils
from inbibe_bot.bot_instance import bot, ADMIN_GROUP_ID
from inbibe_bot.handlers.user.states import states
from inbibe_bot.handlers.user.user_state_machine import UserStateMachine
from inbibe_bot.keyboards import (
    main_menu_keyboard,
    get_phone_keyboard,
    generate_date_keyboard,
    generate_time_keyboard,
)
from inbibe_bot.models import Booking

from inbibe_bot.storage import, bookings
from inbibe_bot.utils import format_date_russian

logger = logging.getLogger(__name__)

machine = UserStateMachine()


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

@bot.message_handler(func=lambda msg: msg.chat.type == "private")
def handle_message(message: Message) -> None:
    """Основная логика состояний бронирования."""
    chat_id = message.chat.id
    text = (message.text or "").strip()
    logger.debug("Сообщение от %s: %s", chat_id, text)


    # === NAME → PHONE ===
    if state == STATE_WAITING_FOR_NAME:
        data.name = text
        state_obj.state = STATE_WAITING_FOR_PHONE

        return

    # === PHONE → DATE ===
    if state == STATE_WAITING_FOR_PHONE:

        return

    # === GUESTS → BOOKING ===
    if state == STATE_WAITING_FOR_GUESTS:
        if not text.isdigit():
            bot.send_message(chat_id, "Пожалуйста, введите количество гостей (числом).")
            return

        data.guests = int(text)

        booking = Booking(
            id=utils.gen_id(),
            user_id=chat_id,
            name=data.name,
            phone=data.phone,
            date_time=data.date_time,
            guests=data.guests,
        )

        bookings[booking.id] = booking
        del user_states[chat_id]

        bot.send_message(chat_id, "Спасибо! Ваша заявка отправлена. Мы скоро с Вами свяжемся!")
        _notify_admins_about_booking(booking)
        return


# === Обработка контакта =====================================================

@bot.message_handler(content_types=["contact"])
def handle_contact(message: Message) -> None:
    """Получение телефона через кнопку «Отправить контакт»."""
    chat_id = message.chat.id
    state_obj = machine.get_current_state(chat_id)

    if not state_obj:
        logger.warning("Пользователь %s не найден при отправке контакта", chat_id)
        return

    if message.contact:
        phone = message.contact.phone_number
        state_obj.context.phone = phone
        state_obj.state = STATE_WAITING_FOR_DATE

        bot.send_message(chat_id, "Спасибо! Номер принят.", reply_markup=ReplyKeyboardRemove())
        bot.send_message(chat_id, "Выберите дату бронирования:", reply_markup=generate_date_keyboard())
        logger.info("Пользователь %s поделился контактом: %s", chat_id, phone)


# === Callback: выбор даты ====================================================

@bot.callback_query_handler(func=lambda call: call.context.startswith("date_"))
def handle_date_callback(call: CallbackQuery) -> None:
    chat_id = call.from_user.id
    state_obj = user_states.get(chat_id)
    if not state_obj or state_obj.state != STATE_WAITING_FOR_DATE:
        bot.answer_callback_query(call.id, "Выбор даты больше неактуален.")
        return

    if call.data is None:
        bot.answer_callback_query(call.id, "Некорректный callback.")
        return

    selected_date_str = call.data.split("_", 1)[1]
    try:
        selected_date: date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
    except ValueError:
        bot.answer_callback_query(call.id, "Неверная дата.")
        return

    state_obj.state = STATE_WAITING_FOR_TIME
    bot.answer_callback_query(call.id, "Дата выбрана.")
    bot.send_message(
        chat_id,
        f"Выберите время бронирования на {selected_date.strftime('%d.%m')}:",
        reply_markup=generate_time_keyboard(selected_date),
    )


# === Callback: выбор времени =================================================

@bot.callback_query_handler(func=lambda call: call.context.startswith("time_"))
def handle_time_callback(call: CallbackQuery) -> None:
    chat_id = call.from_user.id
    state_obj = user_states.get(chat_id)
    if not state_obj or state_obj.state != STATE_WAITING_FOR_TIME:
        bot.answer_callback_query(call.id, "Выбор времени больше неактуален.")
        return

    try:
        if call.data is None:
            bot.answer_callback_query(call.id, "Некорректный callback.")
            return

        _, time_str = call.data.split("time_", 1)
        selected_dt = datetime.strptime(time_str, "%Y-%m-%d_%H:%M")
    except (ValueError, IndexError):
        bot.answer_callback_query(call.id, "Ошибка формата времени.")
        return

    state_obj.context.date_time = selected_dt
    state_obj.state = STATE_WAITING_FOR_GUESTS

    bot.answer_callback_query(call.id, "Время выбрано.")
    bot.send_message(
        chat_id,
        f"Отлично! 📅\nВы выбрали {selected_dt:%d.%m в %H:%M}.\nТеперь введите количество гостей:",
    )


# === Вспомогательное =========================================================

def _notify_admins_about_booking(booking: Booking) -> None:
    """Отправляет уведомление администраторам о новой броне."""
    booking_text = (
        f"📥 Новая бронь (TG):\n"
        f"ID: {booking.id}\n"
        f"Имя: {booking.name}\n"
        f"Телефон: {booking.phone}\n"
        f"Дата: {format_date_russian(booking.date_time)}\n"
        f"Время: {booking.date_time.strftime('%H:%M')}\n"
        f"Гостей: {booking.guests}"
    )

    markup = telebot.types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        telebot.types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve_{booking.id}"),
        telebot.types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{booking.id}"),
    )
    markup.add(
        telebot.types.InlineKeyboardButton("🕘 Изменить дату/время", callback_data=f"approve_alt_{booking.id}")
    )

    msg = bot.send_message(ADMIN_GROUP_ID, booking_text, reply_markup=markup)
    booking.message_id = msg.message_id
    logger.info("Заявка %s отправлена в группу администраторов", booking.id)
