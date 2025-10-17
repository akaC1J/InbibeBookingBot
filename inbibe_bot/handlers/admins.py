import logging
from typing import Optional

import telebot

from telebot.types import CallbackQuery, Message

from inbibe_bot import storage
from inbibe_bot.bot_instance import bot, ADMIN_GROUP_ID
from inbibe_bot.handlers.booking_actions import finalize_booking_approval
from inbibe_bot.keyboards import build_table_keyboard
from inbibe_bot.models import Booking, Source
from inbibe_bot.storage import bookings, alt_requests, table_requests
from inbibe_bot.utils import format_date_russian, parse_date_time, send_vk_message

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


def _edit_booking_message(call: CallbackQuery, booking: Booking, new_text: str) -> None:
    try:
        bot.edit_message_text(new_text, chat_id=call.message.chat.id, message_id=booking.message_id or -1)
        logger.debug(f"Отредактировано сообщение заявки {booking.id}: {new_text}")
    except Exception as exc:
        logger.error(f"Ошибка редактирования сообщения для заявки {booking.id}: {exc}")
        raise


def _remove_booking_from_storage(booking_id: str) -> None:
    if booking_id in bookings:
        del bookings[booking_id]
        logger.debug(f"Заявка {booking_id} удалена из хранилища.")


@bot.callback_query_handler(func=lambda call: (call.data or "").startswith("approve_alt_"))
def handle_approve_alt_callback(call: CallbackQuery) -> None:
    data = call.data or ""
    booking_id = _extract_booking_id(data, "approve_alt_")
    booking = _get_booking_or_alert(call, booking_id, "изменения даты/времени")
    if not booking:
        return

    logger.info(f"Получен callback approve_alt для заявки {booking_id}")

    msg = bot.send_message(
        ADMIN_GROUP_ID,
        f"Введите новую дату и время в формате 15.09.25 16:43 для заявки (ID: {booking.id}).\n"
        f"(ответьте на это сообщение):",
    )
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

    user_id = booking.user_id
    name = booking.name
    phone = booking.phone
    formatted_date = format_date_russian(booking.date_time)
    time_str = booking.date_time.strftime('%H:%M')

    text_to_user = (
        f"❌ Извините, {name}. Ваша бронь на {formatted_date} в {time_str} была отклонена."
    )
    if booking.source == Source.TG:
        text_to_user += "\nДля новой брони введите /start"
        bot.send_message(user_id, text_to_user)
        logger.info(f"Заявка {booking_id} отклонена. Пользователь {user_id} уведомлён.")
    else:
        sent = send_vk_message(booking.user_id, text_to_user)
        logger.info(
            f"Заявка {booking_id} отклонена. VK-пользователь {booking.user_id} уведомлён: {sent}."
        )

    new_text = (
        "❌ *Заявка брони отклонена:*\n"
        f"🆔 ID: {booking.id}\n"
        f"👤 Имя: {booking.name}\n"
        f"👥 Количество гостей: {booking.guests}\n"
        f"📞 Телефон: {phone}\n"
        f"📅 Дата: {formatted_date}\n"
        f"⏰ Время: {time_str}\n"
        f"🌐 Источник: {booking.source.value}"
    )

    try:
        _edit_booking_message(call, booking, new_text)
    except Exception:
        return

    bot.answer_callback_query(call.id, "Обработано.")
    _remove_booking_from_storage(booking.id)

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
        bot.reply_to(message, "Заявка не найдена.", show_alert=True)
        return

    try:
        assert message.text is not None
        table_numbers = [int(el) for el in message.text.split()]
    except (ValueError, AssertionError):
        bot.reply_to(message, "Пожалуйста, вводите только числа через пробел.")
        return

    if any(num not in storage.actual_tables for num in table_numbers):
        bot.reply_to(message, "Пожалуйста введите только доступные номера столов")
        return

    booking.tables_number = table_numbers

    prompt_id = table_requests.pop(booking.id, None)
    finalize_booking_approval(
        booking,
        table_value=", ".join(str(x) for x in table_numbers),
        admin_chat_id=message.chat.id,
        prompt_message_id=prompt_id,
        extra_admin_message_ids=(message.message_id,),
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


    booking.tables_number = [table_num]

    table_text = "Любой" if table_num == -1 else str(table_num)
    prompt_id = table_requests.pop(booking.id, None)
    finalize_booking_approval(
        booking,
        table_value=table_text,
        admin_chat_id=call.message.chat.id,
        prompt_message_id=prompt_id,
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

    new_date_time = parse_date_time(message.text)
    if new_date_time is None:
        logger.error(f"Ошибка парсинга даты/времени для заявки {booking_id}: {message.text}")
        bot.reply_to(message, "Неверный формат даты/времени. Попробуйте снова.\nОжидаемый формат: MM.DD.YY HH:MM")
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
        table_requests[booking_id] = msg.message_id
        logger.debug(f"Отправлено сообщение выбора стола после изменения даты/времени для {booking_id}, message_id: {msg.message_id}")
    except Exception:
        logger.exception("Не удалось отправить клавиатуру выбора стола после approve_alt для заявки %s", booking_id)

    # Clean up prompt and reply messages
    try:
        bot.delete_message(ADMIN_GROUP_ID, alt_requests[booking_id])
        logger.debug(f"Сообщение с запросом для заявки {booking_id} удалено.")
    except Exception as e:
        logger.error(f"Ошибка удаления сообщения запроса для заявки {booking_id}: {e}")
    try:
        bot.delete_message(ADMIN_GROUP_ID, message.message_id)
        logger.debug(f"Ответное сообщение для заявки {booking_id} удалено.")
    except Exception as e:
        logger.error(f"Ошибка удаления ответного сообщения для заявки {booking_id}: {e}")

    del alt_requests[booking_id]
    logger.debug(f"Заявка {booking_id}: дата/время обновлены, ожидается выбор стола.")
