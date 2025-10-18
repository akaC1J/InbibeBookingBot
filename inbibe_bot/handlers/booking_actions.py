"""Helper utilities for booking approval flows used by admin handlers."""

from __future__ import annotations

import logging

from inbibe_bot.bot_instance import bot
from inbibe_bot.models import Booking, Source
from inbibe_bot.storage import bookings, not_sent_bookings, table_requests, alt_requests
from inbibe_bot.utils import format_date_russian, send_vk_message
from inbibe_bot.temporary_messages import clear_ephemeral_messages

logger = logging.getLogger(__name__)


def notify_user_booking_status(
        booking: Booking,
        approved: bool,
) -> None:
    """Отправить пользователю уведомление о результате брони."""

    formatted_date = format_date_russian(booking.date_time)
    time_str = booking.date_time.strftime("%H:%M")

    if approved:
        text_to_user = f"✅ {booking.name}, ваша бронь на {formatted_date} в {time_str} подтверждена."
        log_action = "подтверждена"
    else:
        text_to_user = f"❌ Извините, {booking.name}. Ваша бронь на {formatted_date} в {time_str} была отклонена."
        log_action = "отклонена"

    if booking.source == Source.TG:
        text_to_user += "\nДля новой брони введите /start"
        try:
            bot.send_message(booking.user_id, text_to_user)
            logger.info("Заявка %s %s. Пользователь TG %s уведомлён.", booking.id, log_action, booking.user_id)
        except Exception:
            logger.exception("Не удалось уведомить пользователя TG %s о том, что заявка %s.", booking.user_id,
                             log_action)
    else:
        try:
            sent = send_vk_message(booking.user_id, text_to_user)
            logger.info(
                "Заявка %s %s. VK-пользователь %s уведомлён: %s.",
                booking.id, log_action, booking.user_id, sent,
            )
        except Exception:
            logger.exception("Не удалось уведомить пользователя VK %s о том, что заявка %s.", booking.user_id,
                             log_action)


def _build_admin_final_text(booking: Booking, is_success: bool) -> str:
    status_line = "✅ *Заявка брони подтверждена:*" if is_success else "❌ *Заявка брони отклонена:*"
    tables = ", ".join(str(x) for x in sorted(booking.table_numbers)) or "—"

    return (
        f"{status_line}\n"
        f"🆔 ID: {booking.id}\n"
        f"👤 Имя: {booking.name}\n"
        f"👥 Количество гостей: {booking.guests}\n"
        f"📞 Телефон: {booking.phone}\n"
        f"📅 Дата: {format_date_russian(booking.date_time)}\n"
        f"⏰ Время: {booking.date_time.strftime('%H:%M')}\n"
        f"🪑 Столы: {tables}\n"
        f"🌐 Источник: {booking.source.value}"
    )


def finalize_booking_approval(
        booking: Booking,
        *,
        admin_chat_id: int,
) -> None:
    """Finalize the booking approval workflow shared across admin handlers."""

    notify_user_booking_status(booking, True)
    set_final_booking_text(admin_chat_id, booking)
    logger.info("Бронь %s была подтверждена", booking.id)
    try:
        not_sent_bookings.put(booking)
    except Exception:
        logger.exception("Failed to enqueue approved booking %s", booking.id)
    finalize_booking_actions(booking.id)


def finalize_booking_actions(booking_id: str) -> None:
    clear_ephemeral_messages(booking_id)
    try:
        del bookings[booking_id]
        table_requests.pop(booking_id, None)
        alt_requests.pop(booking_id, None)
    except Exception:
        logger.exception("Не удалось удалить заявку %s из хранилища", booking_id)


def set_final_booking_text(chat_id: int, booking: Booking, is_success: bool = True) -> None:
    try:
        new_text = _build_admin_final_text(booking, is_success)
        bot.edit_message_text(new_text, chat_id=chat_id, message_id=booking.message_id or -1)
        logger.debug(f"Установлено финальное сообщение заявки {booking.id} со статусом {is_success}")
    except Exception as exc:
        logger.error(f"Ошибка установки финального сообщения для заявки {booking.id}: {exc}")
        raise
