"""Helper utilities for booking approval flows used by admin handlers."""

from __future__ import annotations

import logging
from typing import Iterable, Optional

from inbibe_bot.bot_instance import bot
from inbibe_bot.models import Booking, Source
from inbibe_bot.storage import bookings, not_sent_bookings
from inbibe_bot.utils import format_date_russian, send_vk_message

logger = logging.getLogger(__name__)


def _notify_user_booking_approved(booking: Booking, formatted_date: str, time_str: str) -> None:
    """Send confirmation message to the user about an approved booking."""

    text_to_user = f"✅ {booking.name}, ваша бронь на {formatted_date} в {time_str} подтверждена."
    if booking.source == Source.TG:
        text_to_user += "\nДля новой брони введите /start"
        try:
            bot.send_message(booking.user_id, text_to_user)
        except Exception:
            logger.exception("Не удалось отправить подтверждение пользователю TG %s", booking.user_id)
    else:
        try:
            send_vk_message(booking.user_id, text_to_user)
        except Exception:
            logger.exception("Не удалось отправить подтверждение пользователю VK %s", booking.user_id)


def _build_admin_confirmation_text(booking: Booking, table_label: str, table_value: str) -> str:
    return (
        "✅ *Заявка брони подтверждена:*\n"
        f"🆔 ID: {booking.id}\n"
        f"👤 Имя: {booking.name}\n"
        f"👥 Количество гостей: {booking.guests}\n"
        f"📞 Телефон: {booking.phone}\n"
        f"📅 Дата: {format_date_russian(booking.date_time)}\n"
        f"⏰ Время: {booking.date_time.strftime('%H:%M')}\n"
        f"{table_label}: {table_value}\n"
        f"🌐 Источник: {booking.source.value}"
    )


def finalize_booking_approval(
    booking: Booking,
    *,
    table_label: str,
    table_value: str,
    admin_chat_id: int,
    prompt_message_id: Optional[int] = None,
    extra_admin_message_ids: Iterable[int] = (),
) -> None:
    """Finalize the booking approval workflow shared across admin handlers."""

    formatted_date = format_date_russian(booking.date_time)
    time_str = booking.date_time.strftime("%H:%M")

    _notify_user_booking_approved(booking, formatted_date, time_str)

    new_text = _build_admin_confirmation_text(booking, table_label, table_value)
    try:
        bot.edit_message_text(new_text, chat_id=admin_chat_id, message_id=booking.message_id or -1)
    except Exception as exc:
        logger.error("Ошибка редактирования сообщения для заявки %s: %s", booking.id, exc)

    if prompt_message_id:
        try:
            bot.delete_message(admin_chat_id, prompt_message_id)
            logger.debug(
                "Сообщение выбора стола для заявки %s (message_id=%s) удалено",
                booking.id,
                prompt_message_id,
            )
        except Exception as exc:
            logger.error("Ошибка удаления сообщения выбора стола для заявки %s: %s", booking.id, exc)

    for message_id in extra_admin_message_ids:
        try:
            bot.delete_message(admin_chat_id, message_id)
        except Exception as exc:
            logger.error("Ошибка удаления дополнительного сообщения админа %s для заявки %s: %s", message_id, booking.id, exc)

    try:
        not_sent_bookings.append(booking)
    except Exception:
        logger.exception("Failed to enqueue approved booking %s", booking.id)

    if booking.id in bookings:
        try:
            del bookings[booking.id]
        except Exception:
            logger.exception("Не удалось удалить заявку %s из хранилища", booking.id)
