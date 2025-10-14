import logging
import telebot

from telebot.types import CallbackQuery, Message

from inbibe_bot.bot_instance import bot, ADMIN_GROUP_ID
from inbibe_bot.models import Source
from inbibe_bot.storage import bookings, alt_requests, ready_bookings, table_requests
from inbibe_bot.utils import format_date_russian, parse_date_time, send_vk_message

logger = logging.getLogger(__name__)


def _build_table_keyboard(booking_id: str) -> telebot.types.InlineKeyboardMarkup:
    markup = telebot.types.InlineKeyboardMarkup(row_width=5)
    buttons = [
        telebot.types.InlineKeyboardButton(text=str(i), callback_data=f"table_{booking_id}_{i}")
        for i in range(1, 11)
    ]
    any_btn = telebot.types.InlineKeyboardButton(text="Любой", callback_data=f"table_{booking_id}_any")
    # Arrange buttons in rows of 5
    for i in range(0, 10, 5):
        markup.row(*buttons[i:i+5])
    markup.row(any_btn)
    return markup


@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_alt_") or
                                              call.data.startswith("approve_") or
                                              call.data.startswith("reject_"))
def callback_handler(call: CallbackQuery) -> None:
    data = call.data
    if data is None:
        logger.error(f"Неверный callback id: {call.id}")
        return

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
            f"Введите новую дату и время в формате 15.09.25 16:43 для заявки (ID: {booking.id}).\n"
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
        if not booking :
            logger.error(f"Заявка с id {booking_id} не найдена для подтверждения.")
            bot.answer_callback_query(call.id, "Заявка не найдена.", show_alert=True)
            return
        # Ask for table selection instead of immediate approval
        try:
            kb = _build_table_keyboard(booking_id)
            msg = bot.send_message(
                ADMIN_GROUP_ID,
                f"Выберите номер стола для заявки (ID: {booking.id}):",
                reply_markup=kb,
            )
            table_requests[booking_id] = msg.message_id
            logger.debug(f"Отправлено сообщение выбора стола для {booking_id}, message_id: {msg.message_id}")
            bot.answer_callback_query(call.id, "Выберите номер стола")
        except Exception:
            logger.exception("Не удалось отправить клавиатуру выбора стола для заявки %s", booking_id)
            bot.answer_callback_query(call.id, "Ошибка при отправке клавиатуры", show_alert=True)
        return
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
            f"🆔 ID: {booking.id}\n"
            f"👤 Имя: {booking.name}\n"
            f"👥 Количество гостей: {booking.guests}\n"
            f"📞 Телефон: {phone}\n"
            f"📅 Дата: {formatted_date}\n"
            f"⏰ Время: {time_str}\n"
            f"🌐 Источник: {booking.source.value}"
        )

    # noinspection PyUnboundLocalVariable
    assert booking is not None
    try:
        # noinspection PyUnboundLocalVariable
        bot.edit_message_text(new_text, chat_id=call.message.chat.id, message_id=booking.message_id or -1)
        logger.debug(f"Отредактировано сообщение заявки {booking.id}: {new_text}")
    except Exception as e:
        logger.error(f"Ошибка редактирования сообщения для заявки {booking.id}: {e}")
        return

    bot.answer_callback_query(call.id, "Обработано.")

    if booking.id in bookings:
        del bookings[booking.id]
        logger.debug(f"Заявка {booking.id} удалена из хранилища.")


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
    if tail == "any":
        table_num = -1
    else:
        try:
            table_num = int(tail)
        except ValueError:
            bot.answer_callback_query(call.id, "Неверный номер стола.", show_alert=True)
            return
    booking.table_number = table_num

    formatted_date = format_date_russian(booking.date_time)
    time_str = booking.date_time.strftime('%H:%M')

    # Notify user
    text_to_user = (
        f"✅ {booking.name}, ваша бронь на {formatted_date} в {time_str} подтверждена."
    )
    if booking.source == Source.TG:
        text_to_user += "\nДля новой брони введите /start"
        try:
            bot.send_message(booking.user_id, text_to_user)
        except Exception:
            logging.exception("Не удалось отправить подтверждение пользователю TG %s", booking.user_id)
    else:
        try:
            send_vk_message(booking.user_id, text_to_user)
        except Exception:
            logging.exception("Не удалось отправить подтверждение пользователю VK %s", booking.user_id)

    # Edit admin message to approved
    table_text = "Любой" if table_num == -1 else str(table_num)
    new_text = (
        "✅ *Заявка брони подтверждена:*\n"
        f"🆔 ID: {booking.id}\n"
        f"👤 Имя: {booking.name}\n"
        f"👥 Количество гостей: {booking.guests}\n"
        f"📞 Телефон: {booking.phone}\n"
        f"📅 Дата: {formatted_date}\n"
        f"⏰ Время: {time_str}\n"
        f"🪑 Стол: {table_text}\n"
        f"🌐 Источник: {booking.source.value}"
    )
    try:
        bot.edit_message_text(new_text, chat_id=call.message.chat.id, message_id=booking.message_id or -1)
    except Exception as e:
        logging.error("Ошибка редактирования сообщения для заявки %s: %s", booking.id, e)

    # Delete the admin prompt message for table selection
    try:
        prompt_id = table_requests.pop(booking.id, None)
        if prompt_id:
            bot.delete_message(ADMIN_GROUP_ID, prompt_id)
            logging.debug("Сообщение выбора стола для заявки %s (message_id=%s) удалено", booking.id, prompt_id)
    except Exception as e:
        logging.error("Ошибка удаления сообщения выбора стола для заявки %s: %s", booking.id, e)

    # Enqueue and cleanup
    try:
        ready_bookings.append(booking)
    except Exception:
        logging.exception("Failed to enqueue approved booking %s", booking.id)

    if booking.id in bookings:
        try:
            del bookings[booking.id]
        except Exception:
            logging.exception("Не удалось удалить заявку %s из хранилища", booking.id)

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
    formatted_date = format_date_russian(new_date_time)
    time_str = new_date_time.time().strftime('%H:%M')

    # Ask admin to choose a table number now
    try:
        kb = _build_table_keyboard(booking_id)
        msg = bot.send_message(
            ADMIN_GROUP_ID,
            f"Дата/время обновлены. Выберите номер стола для заявки (ID: {booking.id}):",
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
