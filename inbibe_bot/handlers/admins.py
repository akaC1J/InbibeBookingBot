import logging

from inbibe_bot.bot_instance import bot, ADMIN_GROUP_ID
from inbibe_bot.models import Source
from inbibe_bot.storage import bookings, alt_requests
from inbibe_bot.utils import format_date_russian, parse_date_time, send_vk_message

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
        formatted_date = format_date_russian(booking.date_time)
        time_str = booking.date_time.strftime('%H:%M')

        text_to_user = (
            f"✅ {booking.name}, ваша бронь на {formatted_date} в {time_str} подтверждена."
        )
        if booking.source == Source.TG:
            text_to_user += "\nДля новой брони введите /start"
            bot.send_message(booking.user_id, text_to_user)
            logger.info(f"Заявка {booking_id} подтверждена. Пользователь {booking.user_id} уведомлён.")

        else:
            sent = send_vk_message(booking.user_id, text_to_user)
            logger.info(
                f"Заявка {booking_id} подтверждена. VK-пользователь {booking.user_id} уведомлён: {sent}."
            )

        new_text = (
            "✅ *Заявка брони подтверждена:*\n"
            f"👤 Имя: {booking.user_id}\n"
            f"👥 Количество гостей: {booking.guests}\n"
            f"📞 Телефон: {booking.phone}\n"
            f"📅 Дата: {formatted_date}\n"
            f"⏰ Время: {time_str}\n"
            f"🌐 Источник: {booking.source.value}"
        )
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
            f"👤 Имя: {name}\n"
            f"👥 Количество гостей: {booking.guests}\n"
            f"📞 Телефон: {phone}\n"
            f"📅 Дата: {formatted_date}\n"
            f"⏰ Время: {time_str}\n"
            f"🌐 Источник: {booking.source.value}"
        )

    try:
        # noinspection PyUnboundLocalVariable
        bot.edit_message_text(new_text, chat_id=call.message.chat.id, message_id=booking.message_id)
        logger.debug(f"Отредактировано сообщение заявки {booking.id}: {new_text}")
    except Exception as e:
        logger.error(f"Ошибка редактирования сообщения для заявки {booking.id}: {e}")
    bot.answer_callback_query(call.id, "Обработано.")
    if booking.id in bookings:
        del bookings[booking.id]
        logger.debug(f"Заявка {booking.id} удалена из хранилища.")


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

    text_to_user = (
        f"✅ {booking.name}, ваша бронь на {formatted_date} в {time_str} подтверждена."
    )

    if booking.source == Source.TG:
        text_to_user += "\nДля новой брони введите /start"
        bot.send_message(
            booking.user_id,
            text_to_user,
        )
    else:
        send_vk_message(booking.user_id, text_to_user)


    new_text = (
        "✅ *Заявка брони подтверждена:*\n"
        f"👤 Имя: {booking.user_id}\n"
        f"👥 Количество гостей: {booking.guests}\n"
        f"📞 Телефон: {booking.phone}\n"
        f"📅 Дата: {formatted_date}\n"
        f"⏰ Время: {time_str}\n"
        f"🌐 Источник: {booking.source.value}"
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
