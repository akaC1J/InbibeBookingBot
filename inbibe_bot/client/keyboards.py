from __future__ import annotations

from datetime import date, timedelta, datetime

import telebot


def main_menu_keyboard() -> telebot.types.ReplyKeyboardMarkup:
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(telebot.types.KeyboardButton("Начать бронирование"))
    return markup


def get_phone_keyboard() -> telebot.types.ReplyKeyboardMarkup:
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(telebot.types.KeyboardButton("Поделиться номером", request_contact=True))
    return markup


def generate_date_keyboard() -> telebot.types.InlineKeyboardMarkup:
    markup = telebot.types.InlineKeyboardMarkup()
    today = date.today()
    row: list[telebot.types.InlineKeyboardButton] = []
    for i in range(31):
        d = today + timedelta(days=i)
        row.append(
            telebot.types.InlineKeyboardButton(
                text=d.strftime("%d.%m"),
                callback_data=f"date_{d.strftime('%Y-%m-%d')}",
            )
        )
        if len(row) == 5:
            markup.row(*row)
            row = []
    if row:
        markup.row(*row)
    return markup


def generate_time_keyboard(booking_date: date) -> telebot.types.InlineKeyboardMarkup:
    markup = telebot.types.InlineKeyboardMarkup()
    wd = booking_date.weekday()

    if wd in (5, 6):
        early_end_time = "04:45"
    else:
        early_end_time = "02:45"

    early_start = datetime.combine(booking_date, datetime.strptime("00:00", "%H:%M").time())
    early_end = datetime.combine(booking_date, datetime.strptime(early_end_time, "%H:%M").time())
    markup.row(telebot.types.InlineKeyboardButton(text="Ночное время", callback_data="ignore"))
    _add_time_row(markup, booking_date, early_start, early_end)

    main_start = datetime.combine(booking_date, datetime.strptime("15:00", "%H:%M").time())
    main_end = datetime.combine(booking_date, datetime.strptime("23:45", "%H:%M").time())
    markup.row(telebot.types.InlineKeyboardButton(text="Дневное время", callback_data="ignore"))
    _add_time_row(markup, booking_date, main_start, main_end)

    return markup


def build_table_keyboard(booking_id: str, tables: list[int] | tuple[int, ...]) -> telebot.types.InlineKeyboardMarkup:
    markup = telebot.types.InlineKeyboardMarkup(row_width=5)
    buttons = [
        telebot.types.InlineKeyboardButton(text=str(num), callback_data=f"table_{booking_id}_{num}")
        for num in tables
    ]
    for i in range(0, len(buttons), 5):
        markup.row(*buttons[i:i + 5])
    return markup


def _add_time_row(
    markup: telebot.types.InlineKeyboardMarkup,
    booking_date: date,
    start: datetime,
    end: datetime,
) -> None:
    row: list[telebot.types.InlineKeyboardButton] = []
    current = start
    while current <= end:
        row.append(
            telebot.types.InlineKeyboardButton(
                text=current.strftime("%H:%M"),
                callback_data=f"time_{current.strftime('%Y-%m-%d_%H:%M')}",
            )
        )
        if len(row) == 4:
            markup.row(*row)
            row = []
        current += timedelta(minutes=15)
    if row:
        markup.row(*row)
