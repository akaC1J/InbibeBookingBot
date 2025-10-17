import logging
from datetime import datetime, timedelta
from typing import Optional

from telebot.types import CallbackQuery, Message

from inbibe_bot import storage
from inbibe_bot.bot_instance import bot, ADMIN_GROUP_ID
from inbibe_bot.handlers.booking_actions import finalize_booking_approval, finalize_booking_actions, \
    set_final_booking_text, notify_user_booking_status
from inbibe_bot.keyboards import build_table_keyboard
from inbibe_bot.models import Booking
from inbibe_bot.storage import bookings, alt_requests, table_requests
from inbibe_bot.temporary_messages import register_ephemeral_message
from inbibe_bot.utils import parse_date_time

logger = logging.getLogger(__name__)


def _extract_booking_id(data: str, prefix: str) -> str:
    return data[len(prefix):]


def _get_booking_or_alert(call: CallbackQuery, booking_id: str, action_description: str) -> Optional[Booking]:
    booking = bookings.get(booking_id)
    if booking:
        return booking

    logger.error(f"Заявка с id {booking_id} не найдена для {action_description}.")
    bot.answer_callback_query(call.id, "Заявка не найдена.", show_alert=True)
    return None

@bot.callback_query_handler(func=lambda call: (call.data or "").startswith("approve_alt_"))
def handle_approve_alt_callback(call: CallbackQuery) -> None:
    data = call.data or ""
    booking_id = _extract_booking_id(data, "approve_alt_")
    booking = _get_booking_or_alert(call, booking_id, "изменения даты/времени")
    if not booking:
        return

    logger.info(f"Получен callback approve_alt для заявки {booking_id}")

    suggested_time = (datetime.now() + timedelta(hours=2)).strftime("%d.%m.%y %H:%M")

    msg = bot.send_message(
        ADMIN_GROUP_ID,
        f"Введите новую дату и время в формате {suggested_time} для заявки (ID: {booking.id}).\n"
        f"(ответьте на это сообщение):",
    )
    register_ephemeral_message(booking_id, msg)
    alt_requests[booking_id] = msg.message_id
    logger.info(
        f"Инструкция для изменения даты/времени отправлена в админ-группу для заявки {booking_id}, message_id: {msg.message_id}"
    )
    bot.answer_callback_query(call.id, "Ожидается новая дата/время.")


@bot.callback_query_handler(
    func=lambda call: (call.data or "").startswith("approve_") and not (call.data or "").startswith("approve_alt_")
)
def handle_approve_callback(call: CallbackQuery) -> None:
    data = call.data or ""
    booking_id = _extract_booking_id(data, "approve_")
    booking = _get_booking_or_alert(call, booking_id, "подтверждения")
    if not booking:
        return

    logger.info(f"Получен callback approve для заявки {booking_id}")

    try:
        kb = build_table_keyboard(booking_id, storage.actual_tables)
        msg = bot.send_message(
            ADMIN_GROUP_ID,
            f"Выберите номер стола для заявки (ID: {booking.id})\n"
            f"(или ответьте на это сообщение с номерами столов через пробел):",
            reply_markup=kb,
        )
        register_ephemeral_message(booking_id, msg)
        table_requests[booking_id] = msg.message_id
        logger.debug(f"Отправлено сообщение выбора стола для {booking_id}, message_id: {msg.message_id}")
        bot.answer_callback_query(call.id, "Выберите номер стола")
    except Exception:
        logger.exception("Не удалось отправить клавиатуру выбора стола для заявки %s", booking_id)
        bot.answer_callback_query(call.id, "Ошибка при отправке клавиатуры", show_alert=True)


@bot.callback_query_handler(func=lambda call: (call.data or "").startswith("reject_"))
def handle_reject_callback(call: CallbackQuery) -> None:
    data = call.data or ""
    booking_id = _extract_booking_id(data, "reject_")
    booking = _get_booking_or_alert(call, booking_id, "отклонения")
    if not booking:
        return

    logger.info(f"Получен callback reject для заявки {booking_id}")
    notify_user_booking_status(booking, False)

    try:
        set_final_booking_text(call.message.chat.id, booking, False)
    except Exception:
        return

    bot.answer_callback_query(call.id, "Обработано.")
    finalize_booking_actions(booking.id)

@bot.message_handler(func=lambda message: message.chat.id == ADMIN_GROUP_ID and
                                          message.reply_to_message and
                                          message.reply_to_message.message_id in table_requests.values())
def handle_table_selection_reply(message: Message) -> None:
    booking_id = None
    for b_id, msg_id in table_requests.items():
        if message.reply_to_message and msg_id == message.reply_to_message.message_id:
            booking_id = b_id
            break

    if not booking_id:
        logger.error("Не удалось определить booking_id по message.reply_to_message.message_id.")
        return

    booking = bookings.get(booking_id)
    if not booking:
        logging.error("Бронирование %s не найдено при выборе стола", booking_id)
        bot.reply_to(message, "Заявка не найдена.")
        return

    register_ephemeral_message(booking_id, message)

    try:
        assert message.text is not None
        table_numbers = {int(el) for el in message.text.split()}
    except (ValueError, AssertionError):
        register_ephemeral_message(booking_id,
                                   bot.reply_to(message, "Пожалуйста, вводите только числа через пробел."))
        return

    if any(num not in storage.actual_tables for num in table_numbers):
        register_ephemeral_message(booking_id,
                                   bot.reply_to(message, "Пожалуйста введите только доступные номера столов"))
        return

    booking.table_numbers = table_numbers

    finalize_booking_approval(
        booking,
        admin_chat_id=message.chat.id,
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("table_"))
def handle_table_selection(call: CallbackQuery) -> None:
    data = call.data or ""
    parts = data.split("_", 2)
    if len(parts) != 3:
        bot.answer_callback_query(call.id, "Неверные данные.", show_alert=True)
        return
    _, booking_id, tail = parts
    booking = bookings.get(booking_id)
    if not booking:
        logging.error("Бронирование %s не найдено при выборе стола", booking_id)
        bot.answer_callback_query(call.id, "Заявка не найдена.", show_alert=True)
        return

    try:
        table_num = int(tail)
    except ValueError:
        bot.answer_callback_query(call.id, "Неверный номер стола.", show_alert=True)
        return


    booking.table_numbers = {table_num}
    finalize_booking_approval(
        booking,
        admin_chat_id=call.message.chat.id,
    )

    bot.answer_callback_query(call.id, "Стол выбран, бронь подтверждена.")


@bot.message_handler(func=lambda message: message.chat.id == ADMIN_GROUP_ID and
                                          message.reply_to_message and
                                          message.reply_to_message.message_id in alt_requests.values())
def handle_alt_date_time(message: Message) -> None:
    booking_id = None
    for b_id, msg_id in alt_requests.items():
        if message.reply_to_message and msg_id == message.reply_to_message.message_id:
            booking_id = b_id
            break
    if not booking_id:
        logger.error("Не удалось определить booking_id по message.reply_to_message.message_id.")
        return
    logger.info(
        f"Для заявки {booking_id} получено ответное сообщение для изменения даты/времени: {message.text}"
    )
    booking = bookings.get(booking_id)
    if not booking:
        logger.error(f"Заявка с id {booking_id} не найдена при обновлении даты/времени.")
        bot.reply_to(message, "Заявка не найдена.")
        return

    register_ephemeral_message(booking_id, message)
    new_date_time = parse_date_time(message.text)
    if new_date_time is None:
        logger.error(f"Ошибка парсинга даты/времени для заявки {booking_id}: {message.text}")
        register_ephemeral_message(booking_id,
                                   bot.reply_to(message,
                                                "Неверный формат даты/времени. Попробуйте снова.\nОжидаемый формат: MM.DD.YY HH:MM"))
        return

    booking.date_time = new_date_time

    # Ask admin to choose a table number now
    try:
        kb = build_table_keyboard(booking_id, storage.actual_tables)
        msg = bot.send_message(
            ADMIN_GROUP_ID,
            f"Дата/время обновлены. Выберите номер стола для заявки (ID: {booking.id}):"
            f"(или ответьте на это сообщение с номерами столов через пробел):",
            reply_markup=kb,
        )
        register_ephemeral_message(booking_id, msg)
        table_requests[booking_id] = msg.message_id
    except Exception:
        logger.exception("Не удалось отправить клавиатуру выбора стола после approve_alt для заявки %s", booking_id)

    del alt_requests[booking_id]
    logger.debug(f"Заявка {booking_id}: дата/время обновлены, ожидается выбор стола.")
