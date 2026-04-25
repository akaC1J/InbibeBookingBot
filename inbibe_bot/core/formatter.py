from __future__ import annotations

from datetime import datetime

from inbibe_bot.core.booking import Booking
from inbibe_bot.shared.datetime_utils import format_date_russian


class BookingFormatter:

    @staticmethod
    def admin_new(booking: Booking) -> str:
        return (
            f"📥 Новая бронь ({booking.source.value}):\n"
            f"ID: {booking.id}\n"
            f"Имя: {booking.name}\n"
            f"Телефон: {booking.phone}\n"
            f"Дата: {format_date_russian(booking.date_time)}\n"
            f"Время: {booking.date_time.strftime('%H:%M')}\n"
            f"Гостей: {booking.guests}"
        )

    @staticmethod
    def admin_final(booking: Booking) -> str:
        approved = booking.status.value == "approved"
        status_line = "✅ *Заявка брони подтверждена:*" if approved else "❌ *Заявка брони отклонена:*"
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

    @staticmethod
    def admin_table_prompt(booking: Booking) -> str:
        return (
            f"Выберите номер стола для заявки (ID: {booking.id})\n"
            f"(или ответьте на это сообщение с номерами столов через пробел):"
        )

    @staticmethod
    def admin_alt_datetime_prompt(booking: Booking, suggested: datetime) -> str:
        return (
            f"Введите новую дату и время в формате {suggested.strftime('%d.%m.%y %H:%M')} "
            f"для заявки (ID: {booking.id}).\n"
            f"(ответьте на это сообщение):"
        )

    @staticmethod
    def user_approved(booking: Booking) -> str:
        formatted_date = format_date_russian(booking.date_time)
        time_str = booking.date_time.strftime("%H:%M")
        return (
            f"✅ {booking.name}, ваша бронь на {formatted_date} в {time_str} подтверждена.\n"
            f"Для новой брони введите /start"
        )

    @staticmethod
    def user_rejected(booking: Booking) -> str:
        formatted_date = format_date_russian(booking.date_time)
        time_str = booking.date_time.strftime("%H:%M")
        return f"❌ Извините, {booking.name}. Ваша бронь на {formatted_date} в {time_str} была отклонена.\nДля новой брони введите /start"
