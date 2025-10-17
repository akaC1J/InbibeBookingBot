from datetime import date, timedelta, datetime

import telebot


def main_menu_keyboard() -> telebot.types.ReplyKeyboardMarkup:
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn = telebot.types.KeyboardButton("Начать бронирование")
    markup.add(btn)
    return markup


def get_phone_keyboard() -> telebot.types.ReplyKeyboardMarkup:
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn_share = telebot.types.KeyboardButton("Поделиться номером", request_contact=True)
    markup.add(btn_share)
    return markup


def generate_date_keyboard() -> telebot.types.InlineKeyboardMarkup:
    markup = telebot.types.InlineKeyboardMarkup()
    today = date.today()
    dates = [today + timedelta(days=i) for i in range(31)]
    row = []
    for d in dates:
        btn_text = d.strftime("%d.%m")
        btn = telebot.types.InlineKeyboardButton(text=btn_text, callback_data=f"date_{d.strftime('%Y-%m-%d')}")
        row.append(btn)
        if len(row) == 5:
            markup.row(*row)
            row = []
    if row:
        markup.row(*row)
    return markup


def generate_alt_date_keyboard(booking_id : str) -> telebot.types.InlineKeyboardMarkup:
    markup = telebot.types.InlineKeyboardMarkup()
    today = date.today()
    dates = [today + timedelta(days=i) for i in range(31)]
    row = []
    for d in dates:
        btn_text = d.strftime("%d.%m")
        btn = telebot.types.InlineKeyboardButton(text=btn_text,
                                                 callback_data=f"alt_date_{booking_id}_{d.strftime('%Y-%m-%d')}")
        row.append(btn)
        if len(row) == 5:
            markup.row(*row)
            row = []
    if row:
        markup.row(*row)
    return markup


def generate_alt_time_keyboard(booking_id: str, booking_date: date) -> telebot.types.InlineKeyboardMarkup:
    markup = telebot.types.InlineKeyboardMarkup()
    start_time = datetime.combine(booking_date, datetime.strptime("15:00", "%H:%M").time())
    end_time = datetime.combine(booking_date, datetime.strptime("23:45", "%H:%M").time())
    buttons = []
    current_time = start_time
    while current_time <= end_time:
        time_str = current_time.strftime("%H:%M")
        btn = telebot.types.InlineKeyboardButton(text=time_str,
                                                 callback_data=f"alt_time_{booking_id}_{booking_date.strftime('%Y-%m-%d')}_{time_str}")
        buttons.append(btn)
        current_time += timedelta(minutes=15)
    row = []
    for btn in buttons:
        row.append(btn)
        if len(row) == 4:
            markup.row(*row)
            row = []
    if row:
        markup.row(*row)
    return markup


def generate_time_keyboard(booking_date: date) -> telebot.types.InlineKeyboardMarkup:
    markup = telebot.types.InlineKeyboardMarkup()
    wd = booking_date.weekday()
    if wd in [5, 6]:
        early_start = datetime.combine(booking_date, datetime.strptime("00:00", "%H:%M").time())
        early_end = datetime.combine(booking_date, datetime.strptime("04:45", "%H:%M").time())
    else:
        early_start = datetime.combine(booking_date, datetime.strptime("00:00", "%H:%M").time())
        early_end = datetime.combine(booking_date, datetime.strptime("02:45", "%H:%M").time())

    label_early = telebot.types.InlineKeyboardButton(text="Ночное время", callback_data="ignore")
    markup.row(label_early)
    early_buttons = []
    current_time = early_start
    while current_time <= early_end:
        time_str = current_time.strftime("%H:%M")
        btn = telebot.types.InlineKeyboardButton(text=time_str,
                                                 callback_data=f"time_{current_time.strftime('%Y-%m-%d_%H:%M')}")
        early_buttons.append(btn)
        current_time += timedelta(minutes=15)
    row = []
    for btn in early_buttons:
        row.append(btn)
        if len(row) == 4:
            markup.row(*row)
            row = []
    if row:
        markup.row(*row)

    main_start = datetime.combine(booking_date, datetime.strptime("15:00", "%H:%M").time())
    main_end = datetime.combine(booking_date, datetime.strptime("23:45", "%H:%M").time())
    label_main = telebot.types.InlineKeyboardButton(text="Дневное время", callback_data="ignore")
    markup.row(label_main)
    main_buttons = []
    current_time = main_start
    while current_time <= main_end:
        time_str = current_time.strftime("%H:%M")
        btn = telebot.types.InlineKeyboardButton(text=time_str,
                                                 callback_data=f"time_{current_time.strftime('%Y-%m-%d_%H:%M')}")
        main_buttons.append(btn)
        current_time += timedelta(minutes=15)
    row = []
    for btn in main_buttons:
        row.append(btn)
        if len(row) == 4:
            markup.row(*row)
            row = []
    if row:
        markup.row(*row)
    return markup

def build_table_keyboard(booking_id: str, tables_number: list[int]) -> telebot.types.InlineKeyboardMarkup:
    markup = telebot.types.InlineKeyboardMarkup(row_width=5)

    # Создаём кнопки от 1 до table_count
    buttons = [
        telebot.types.InlineKeyboardButton(text=str(num), callback_data=f"table_{booking_id}_{num}")
        for num in tables_number
    ]

    # Раскладываем кнопки по рядам по 5 штук
    for i in range(0, len(buttons), 5):
        markup.row(*buttons[i:i + 5])

    return markup