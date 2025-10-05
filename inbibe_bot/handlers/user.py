# Команда /start – приветствие и начало бронирования
import logging
import re
import uuid
from datetime import datetime

import telebot

from inbibe_bot.bot_instance import bot, ADMIN_GROUP_ID
from inbibe_bot.keyboards import (
    main_menu_keyboard,
    get_phone_keyboard,
    generate_date_keyboard,
    generate_time_keyboard,
)
from inbibe_bot.states import (
    STATE_WAITING_FOR_GUESTS,
    STATE_WAITING_FOR_TIME,
    STATE_IDLE,
    STATE_WAITING_FOR_NAME,
    STATE_WAITING_FOR_PHONE,
    STATE_WAITING_FOR_DATE,
)
from inbibe_bot.storage import user_states, bookings
from inbibe_bot.models import Booking, UserState
from inbibe_bot.utils import format_date_russian

logger = logging.getLogger(__name__)


@bot.message_handler(commands=["start"])  # type: ignore
def cmd_start(message):
    chat_id = message.chat.id
    logger.info(f"Получена команда /start от chat_id {chat_id}")
    if message.chat.type != "private":
        logger.debug(f"Команда /start проигнорирована для типа чата: {message.chat.type}")
        return
    if chat_id in user_states:
        logger.debug(f"Удаляем старое состояние пользователя {chat_id}")
        del user_states[chat_id]
    user_states[chat_id] = UserState(STATE_IDLE)
    logger.debug(f"Установлено состояние пользователя {chat_id} в {STATE_IDLE}")
    bot.send_message(
        chat_id,
        "Добро пожаловать в бар *Инбайб*!\n"
        "Мы работаем для вас каждый день с *15:00 до 03:00*,\n"
        "а по *пятницам и субботам* — с *15:00 до 05:00*.\n\n"
        "Чтобы начать бронирование, нажмите кнопку «Начать бронирование».\n"
        "Если хотите начать заново, введите команду /start.",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown",
    )
    logger.info(f"Приветственное сообщение отправлено пользователю {chat_id}")


@bot.message_handler(func=lambda message: message.chat.type == "private")  # type: ignore
def handle_message(message):
    chat_id = message.chat.id
    text = message.text.strip()
    logger.debug(f"Получено сообщение от {chat_id}: {text}")

    if chat_id in user_states and user_states[chat_id].state == STATE_IDLE:
        logger.debug(f"Пользователь {chat_id} в состоянии {STATE_IDLE}")
        if text.lower() == "начать бронирование":
            user_states[chat_id].state = STATE_WAITING_FOR_NAME
            logger.info(f"Пользователь {chat_id} перешел в состояние {STATE_WAITING_FOR_NAME}")
            bot.send_message(chat_id, "Отлично! Как Вас зовут?", reply_markup=telebot.types.ReplyKeyboardRemove())
            return
        else:
            logger.debug(f"Пользователь {chat_id} не нажал 'начать бронирование'")
            bot.send_message(chat_id, "Пожалуйста, нажмите кнопку «Начать бронирование», чтобы начать процесс.")
            return

    if chat_id not in user_states:
        logger.error(f"Пользователь {chat_id} не найден в user_states")
        bot.send_message(chat_id, "Пожалуйста, начните с команды /start")
        return

    state = user_states[chat_id].state
    data = user_states[chat_id].data

    if state == STATE_WAITING_FOR_NAME:
        data.name = text
        user_states[chat_id].state = STATE_WAITING_FOR_PHONE
        logger.info(f"Пользователь {chat_id} ввел имя: {text}")
        logger.debug(f"Состояние пользователя {chat_id} изменено на {STATE_WAITING_FOR_PHONE}")
        bot.send_message(
            chat_id,
            "Введите, пожалуйста, Ваш телефон.\n"
            "Вы можете поделиться номером, нажав кнопку ниже, или ввести его вручную.",
            reply_markup=get_phone_keyboard(),
        )
    elif state == STATE_WAITING_FOR_PHONE:
        pattern = r"^(?:\+7|8)\d{10}$"
        if not re.match(pattern, text):
            logger.debug(f"Неверный формат телефона от пользователя {chat_id}: {text}")
            bot.send_message(chat_id, "Неверный формат телефона. Пример: +79261234567 или 89261234567")
            return
        data.phone = text
        user_states[chat_id].state = STATE_WAITING_FOR_DATE
        logger.info(
            f"Пользователь {chat_id} ввел телефон: {text}. Состояние изменено на {STATE_WAITING_FOR_DATE}"
        )
        bot.send_message(chat_id, "Спасибо! Номер принят", reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.send_message(chat_id, "Выберите дату бронирования:", reply_markup=generate_date_keyboard())
    elif state == STATE_WAITING_FOR_GUESTS:
        if not text.isdigit():
            logger.debug(f"Неверный ввод числа гостей от пользователя {chat_id}: {text}")
            bot.send_message(chat_id, "Пожалуйста, введите число гостей.")
            return
        data.guests = int(text)
        booking_id = str(uuid.uuid4())
        booking = Booking(booking_id, chat_id, data.name, data.phone, data.date_time, data.guests)
        bookings[booking_id] = booking
        logger.info(f"Создана заявка: {booking}")
        bot.send_message(chat_id, "Спасибо! Ваша заявка отправлена. Для подтверждения мы с Вами свяжемся!.")
        del user_states[chat_id]
        booking_text = (
            f"📥 Новая бронь (TG):\n"
            f"Имя: {booking.name}\n"
            f"Телефон: {booking.phone}\n"
            f"Дата: {format_date_russian(booking.date_time)}\n"
            f"Время: {booking.date_time.strftime('%H:%M')}\n"
            f"Гостей: {booking.guests}"
        )
        markup = telebot.types.InlineKeyboardMarkup(row_width=3)
        btn_approve = telebot.types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve_{booking_id}")
        btn_alt = telebot.types.InlineKeyboardButton(
            "🕘 Изменить дату/время", callback_data=f"approve_alt_{booking_id}"
        )
        btn_reject = telebot.types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{booking_id}")
        markup.add(btn_approve, btn_reject)
        markup.add(btn_alt)
        msg = bot.send_message(ADMIN_GROUP_ID, booking_text, reply_markup=markup)
        booking.message_id = msg.message_id
        logger.info(
            f"Заявка отправлена в группу администраторов. message_id: {msg.message_id}"
        )


@bot.message_handler(content_types=["contact"])  # type: ignore
def handle_contact(message):
    chat_id = message.chat.id
    if chat_id not in user_states:
        logger.error(
            f"Пользователь {chat_id} не найден в user_states при обработке контакта"
        )
        return
    if user_states[chat_id].state == STATE_WAITING_FOR_PHONE:
        phone = message.contact.phone_number
        user_states[chat_id].data.phone = phone
        user_states[chat_id].state = STATE_WAITING_FOR_DATE
        logger.info(
            f"Пользователь {chat_id} поделился контактом. Телефон: {phone}. Состояние изменено на {STATE_WAITING_FOR_DATE}"
        )
        bot.send_message(chat_id, "Спасибо! Номер принят", reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.send_message(chat_id, "Выберите дату бронирования:", reply_markup=generate_date_keyboard())


@bot.callback_query_handler(func=lambda call: call.data.startswith("date_"))  # type: ignore
def handle_date_callback(call):
    chat_id = call.from_user.id
    logger.info(f"Получен callback выбора даты от {chat_id}: {call.data}")
    if chat_id not in user_states or user_states[chat_id].state != STATE_WAITING_FOR_DATE:
        logger.error(f"Пользователь {chat_id} не находится в состоянии ожидания даты")
        bot.answer_callback_query(call.id, "Время выбора даты истекло или неактуально.")
        return
    selected_date_str = call.data.split("_", 1)[1]
    try:
        selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
        logger.debug(f"Пользователь {chat_id} выбрал дату: {selected_date}")
    except Exception as e:
        logger.error(f"Ошибка при разборе даты от пользователя {chat_id}: {e}")
        bot.answer_callback_query(call.id, "Неверная дата.")
        return
    user_states[chat_id].state = STATE_WAITING_FOR_TIME
    markup = generate_time_keyboard(selected_date)

    bot.send_message(
        chat_id,
        f"Выберите время бронирования на {selected_date.strftime('%d.%m')}:",
        reply_markup=markup,
    )

    bot.answer_callback_query(call.id, "Дата выбрана.")
    logger.debug(f"Состояние пользователя {chat_id} изменено на {STATE_WAITING_FOR_TIME}")


@bot.callback_query_handler(func=lambda call: call.data.startswith("time_"))  # type: ignore
def handle_time_callback(call):
    chat_id = call.from_user.id
    logger.info(f"Получен callback выбора времени от {chat_id}: {call.data}")
    if chat_id not in user_states or user_states[chat_id].state != STATE_WAITING_FOR_TIME:
        logger.error(f"Пользователь {chat_id} не находится в состоянии ожидания времени")
        bot.answer_callback_query(call.id, "Время выбора неактуально.")
        return
    _, time_data = call.data.split("time_", 1)
    try:
        selected_dt = datetime.strptime(time_data, "%Y-%m-%d_%H:%M")
        logger.debug(f"Пользователь {chat_id} выбрал время: {selected_dt}")
    except Exception as e:
        logger.error(f"Ошибка при разборе времени для пользователя {chat_id}: {e}")
        bot.answer_callback_query(call.id, "Ошибка формата времени.")
        return
    user_states[chat_id].data.date_time = selected_dt
    user_states[chat_id].state = STATE_WAITING_FOR_GUESTS

    bot.send_message(
        chat_id,
        f"Отлично! 📅\n"
        f"Вы выбрали {selected_dt:%d.%m в %H:%M}.\n"
        "Теперь введите количество гостей:"
    )

    bot.answer_callback_query(call.id, "Время выбрано.")
    logger.debug(f"Состояние пользователя {chat_id} изменено на {STATE_WAITING_FOR_GUESTS}")
