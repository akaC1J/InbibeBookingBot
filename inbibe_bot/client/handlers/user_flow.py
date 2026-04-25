from __future__ import annotations

import logging

import telebot
from telebot.types import Message, CallbackQuery, ReplyKeyboardRemove

from inbibe_bot.client.bot_factory import Deps
from inbibe_bot.client.callbacks import CallbackData
from inbibe_bot.client.keyboards import (
    main_menu_keyboard,
    get_phone_keyboard,
    generate_date_keyboard,
    generate_time_keyboard,
)
from inbibe_bot.core.booking import Booking, Source
from inbibe_bot.core.errors import FlowValidationError
from inbibe_bot.core.user_flow import FlowStep
from inbibe_bot.storage.user_registry import register_tg_user

logger = logging.getLogger(__name__)


def register(deps: Deps) -> None:
    bot = deps.bot

    @bot.message_handler(commands=["start"])
    def cmd_start(message: Message) -> None:
        if message.chat.type != "private":
            return
        chat_id = message.chat.id
        register_tg_user(chat_id)
        flow = deps.flow_repo.get_or_create(chat_id)
        flow.start()
        deps.flow_repo.save(flow)
        logger.info("Пользователь %s запустил /start", chat_id)
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

    @bot.message_handler(content_types=["contact"])
    def handle_contact(message: Message) -> None:
        chat_id = message.chat.id
        flow = deps.flow_repo.get(chat_id)
        if not flow or flow.step != FlowStep.PHONE or not message.contact:
            return
        phone = message.contact.phone_number
        try:
            flow.submit_phone(phone)
        except FlowValidationError as e:
            bot.send_message(chat_id, str(e))
            return
        deps.flow_repo.save(flow)
        bot.send_message(chat_id, "Спасибо! Номер принят.", reply_markup=ReplyKeyboardRemove())
        bot.send_message(chat_id, "Выберите дату бронирования:", reply_markup=generate_date_keyboard())
        logger.info("Пользователь %s поделился контактом", chat_id)

    @bot.callback_query_handler(func=lambda call: (call.data or "").startswith(CallbackData.DATE))
    def handle_date_callback(call: CallbackQuery) -> None:
        chat_id = call.from_user.id
        flow = deps.flow_repo.get(chat_id)
        if not flow or flow.step != FlowStep.DATE:
            bot.answer_callback_query(call.id, "Выбор даты больше неактуален.")
            return
        try:
            selected_date = CallbackData.parse_date(call.data or "")
        except ValueError:
            bot.answer_callback_query(call.id, "Неверная дата.")
            return
        flow.submit_date(selected_date)
        deps.flow_repo.save(flow)
        bot.answer_callback_query(call.id, "Дата выбрана.")
        bot.send_message(
            chat_id,
            f"Выберите время бронирования на {selected_date.strftime('%d.%m')}:",
            reply_markup=generate_time_keyboard(selected_date),
        )

    @bot.callback_query_handler(func=lambda call: (call.data or "").startswith(CallbackData.TIME))
    def handle_time_callback(call: CallbackQuery) -> None:
        chat_id = call.from_user.id
        flow = deps.flow_repo.get(chat_id)
        if not flow or flow.step != FlowStep.TIME:
            bot.answer_callback_query(call.id, "Выбор времени больше неактуален.")
            return
        try:
            selected_dt = CallbackData.parse_time(call.data or "")
        except ValueError:
            bot.answer_callback_query(call.id, "Ошибка формата времени.")
            return
        flow.submit_time(selected_dt)
        deps.flow_repo.save(flow)
        bot.answer_callback_query(call.id, "Время выбрано.")
        bot.send_message(
            chat_id,
            f"Отлично! 📅\nВы выбрали {selected_dt:%d.%m в %H:%M}.\nТеперь введите количество гостей:",
        )

    @bot.message_handler(func=lambda msg: msg.chat.type == "private")
    def handle_message(message: Message) -> None:
        chat_id = message.chat.id
        text = (message.text or "").strip()
        flow = deps.flow_repo.get(chat_id)

        if not flow or flow.step == FlowStep.IDLE:
            bot.send_message(chat_id, "Пожалуйста, начните с команды /start")
            return

        if flow.step == FlowStep.NAME:
            flow.submit_name(text)
            deps.flow_repo.save(flow)
            bot.send_message(
                chat_id,
                "Введите, пожалуйста, Ваш телефон.\n"
                "Можно поделиться номером, нажав кнопку ниже, или ввести вручную.",
                reply_markup=get_phone_keyboard(),
            )
            return

        if flow.step == FlowStep.PHONE:
            try:
                flow.submit_phone(text)
            except FlowValidationError as e:
                bot.send_message(chat_id, str(e))
                return
            deps.flow_repo.save(flow)
            bot.send_message(chat_id, "Спасибо! Номер принят.", reply_markup=ReplyKeyboardRemove())
            bot.send_message(chat_id, "Выберите дату бронирования:", reply_markup=generate_date_keyboard())
            return

        if flow.step == FlowStep.GUESTS:
            if not text.isdigit():
                bot.send_message(chat_id, "Пожалуйста, введите количество гостей (числом).")
                return
            booking = flow.submit_guests(int(text), Source.TG)
            deps.flow_repo.delete(chat_id)
            deps.booking_repo.add(booking)
            bot.send_message(chat_id, "Спасибо! Ваша заявка отправлена. Мы скоро с Вами свяжемся!")
            _notify_admins(deps, booking)
            logger.info("Создана бронь TG %s для пользователя %s", booking.id, chat_id)


def _notify_admins(deps: Deps, booking: Booking) -> None:
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve_{booking.id}"),
        telebot.types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{booking.id}"),
    )
    markup.add(
        telebot.types.InlineKeyboardButton("🕘 Изменить дату/время", callback_data=f"approve_alt_{booking.id}")
    )
    msg = deps.bot.send_message(
        deps.config.admin_group_id,
        deps.formatter.admin_new(booking),
        reply_markup=markup,
    )
    booking.admin_message_id = msg.message_id
    deps.booking_repo.update(booking)
    logger.info("Заявка %s отправлена администраторам", booking.id)
