import logging

from inbibe_bot.bot_instance import bot, ADMIN_GROUP_ID
from inbibe_bot.storage import bookings, alt_requests
from inbibe_bot.utils import format_date_russian, parse_date_time

logger = logging.getLogger(__name__)


@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_alt_") or
                                              call.data.startswith("approve_") or
                                              call.data.startswith("reject_"))  # type: ignore
def callback_handler(call):
    data = call.data
    logger.info(f"Получен callback с данными: {data}")

    if data.startswith("approve_alt_"):
        booking_id = data.split("_", 2)[2]
        booking = bookings.get(booking_id)
        if not booking:
            logger.error(f"Заявка с id {booking_id} не найдена для изменения даты/времени.")
            bot.answer_callback_query(call.id, "Заявка не найдена.", show_alert=True)
            return
        msg = bot.send_message(
            ADMIN_GROUP_ID,
            f"Введите новую дату и время в формате 15.09.25 16:43 для заявки (телефон: {booking.phone}).\n"
            f"(ответьте на это сообщение):",
        )
        alt_requests[booking_id] = msg.message_id
        logger.info(
            f"Инструкция для изменения даты/времени отправлена в админ-группу для заявки {booking_id}, message_id: {msg.message_id}"
        )
        bot.answer_callback_query(call.id, "Ожидается новая дата/время.")
        return

    if data.startswith("approve_"):
        booking_id = data.split("_", 1)[1]
        booking = bookings.get(booking_id)
        if not booking:
            logger.error(f"Заявка с id {booking_id} не найдена для подтверждения.")
            bot.answer_callback_query(call.id, "Заявка не найдена.", show_alert=True)
            return
        user_id = booking.user_id
        name = booking.name
        phone = booking.phone
        formatted_date = format_date_russian(booking.date_time)
        time_str = booking.date_time.strftime('%H:%M')
        bot.send_message(
            user_id,
            f"✅ Поздравляем, {name}! Ваша бронь на {formatted_date} в {time_str} подтверждена.\nДля новой брони введите /start",
        )
        new_text = f"✅ Заявка от {name} ({phone}) на {formatted_date} в {time_str} подтверждена."
        logger.info(f"Заявка {booking_id} подтверждена. Пользователь {user_id} уведомлён.")
    elif data.startswith("reject_"):
        booking_id = data.split("_", 1)[1]
        booking = bookings.get(booking_id)
        if not booking:
            logger.error(f"Заявка с id {booking_id} не найдена для отклонения.")
            bot.answer_callback_query(call.id, "Заявка не найдена.", show_alert=True)
            return
        user_id = booking.user_id
        name = booking.name
        phone = booking.phone
        formatted_date = format_date_russian(booking.date_time)
        time_str = booking.date_time.strftime('%H:%M')
        bot.send_message(
            user_id,
            f"❌ Извините, {name}. Ваша бронь на {formatted_date} в {time_str} была отклонена.\nДля новой брони введите /start",
        )
        new_text = f"❌ Заявка от {name} ({phone}) на {formatted_date} в {time_str} отклонена."
        logger.info(f"Заявка {booking_id} отклонена. Пользователь {user_id} уведомлён.")

    try:
        bot.edit_message_text(new_text, chat_id=call.message.chat.id, message_id=booking.message_id)
        logger.debug(f"Отредактировано сообщение заявки {booking_id}: {new_text}")
    except Exception as e:
        logger.error(f"Ошибка редактирования сообщения для заявки {booking_id}: {e}")
    bot.answer_callback_query(call.id, "Обработано.")
    if booking_id in bookings:
        del bookings[booking_id]
        logger.debug(f"Заявка {booking_id} удалена из хранилища.")


@bot.message_handler(func=lambda message: message.chat.id == ADMIN_GROUP_ID and
                                          message.reply_to_message and
                                          message.reply_to_message.message_id in alt_requests.values())  # type: ignore
def handle_alt_date_time(message):
    booking_id = None
    for b_id, msg_id in alt_requests.items():
        if msg_id == message.reply_to_message.message_id:
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
    formatted_date = format_date_russian(new_date_time)
    time_str = new_date_time.time().strftime('%H:%M')

    bot.send_message(
        booking.user_id,
        f"✅ Поздравляем, {booking.name}! Ваша бронь подтверждена на {formatted_date} в {time_str}.\nДля новой брони введите /start",
    )
    new_text = f"✅ Заявка от {booking.name} ({booking.phone}) на {formatted_date} в {time_str} подтверждена."
    logger.info(
        f"Заявка {booking_id} на новое время  {formatted_date} в {time_str} подтверждена. Пользователь {booking.user_id} уведомлён."
    )

    try:
        bot.edit_message_text(new_text, chat_id=ADMIN_GROUP_ID, message_id=booking.message_id)
        logger.debug(f"Сообщение заявки {booking_id} обновлено: {new_text}")
    except Exception as e:
        logger.error(f"Ошибка редактирования сообщения заявки {booking_id}: {e}")

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
    logger.debug(f"Заявка {booking_id} обновлена и удалена из списка alt_requests.")
