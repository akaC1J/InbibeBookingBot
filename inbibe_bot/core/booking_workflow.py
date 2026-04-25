from __future__ import annotations

from datetime import datetime

from inbibe_bot.core.booking import Booking, BookingStatus
from inbibe_bot.core.errors import InvalidTransition, BookingNotFound

_ALLOWED: set[tuple[BookingStatus, BookingStatus]] = {
    (BookingStatus.PENDING, BookingStatus.AWAITING_TABLE),
    (BookingStatus.PENDING, BookingStatus.AWAITING_NEW_DATETIME),
    (BookingStatus.PENDING, BookingStatus.REJECTED),
    (BookingStatus.AWAITING_TABLE, BookingStatus.APPROVED),
    (BookingStatus.AWAITING_TABLE, BookingStatus.REJECTED),
    (BookingStatus.AWAITING_NEW_DATETIME, BookingStatus.AWAITING_TABLE),
    (BookingStatus.AWAITING_NEW_DATETIME, BookingStatus.REJECTED),
}


class BookingWorkflow:
    """Чистая доменная логика переходов статусов брони. Не знает про Telegram/HTTP/storage."""

    def __init__(self, allowed_tables: set[int]) -> None:
        self._allowed_tables = allowed_tables

    def request_table_selection(self, booking: Booking) -> Booking:
        self._ensure_transition(booking, BookingStatus.AWAITING_TABLE)
        booking.status = BookingStatus.AWAITING_TABLE
        return booking

    def request_new_datetime(self, booking: Booking) -> Booking:
        self._ensure_transition(booking, BookingStatus.AWAITING_NEW_DATETIME)
        booking.status = BookingStatus.AWAITING_NEW_DATETIME
        return booking

    def apply_new_datetime(self, booking: Booking, new_dt: datetime) -> Booking:
        booking.date_time = new_dt
        return booking

    def assign_tables(self, booking: Booking, tables: set[int]) -> Booking:
        invalid = tables - self._allowed_tables
        if invalid:
            raise ValueError(f"Недопустимые номера столов: {sorted(invalid)}")
        self._ensure_transition(booking, BookingStatus.APPROVED)
        booking.table_numbers = tables
        booking.status = BookingStatus.APPROVED
        return booking

    def reject(self, booking: Booking) -> Booking:
        self._ensure_transition(booking, BookingStatus.REJECTED)
        booking.status = BookingStatus.REJECTED
        return booking

    def _ensure_transition(self, booking: Booking, target: BookingStatus) -> None:
        if (booking.status, target) not in _ALLOWED:
            raise InvalidTransition(booking.status, target, booking.id)
