from __future__ import annotations

from threading import RLock
from typing import Callable

from inbibe_bot.core.booking import Booking, BookingStatus
from inbibe_bot.core.errors import BookingNotFound

_TERMINAL = {BookingStatus.APPROVED, BookingStatus.REJECTED}


class BookingRepository:
    def __init__(self) -> None:
        self._data: dict[str, Booking] = {}
        self._lock = RLock()
        self._on_change: Callable[[], None] | None = None

    def set_change_callback(self, fn: Callable[[], None]) -> None:
        self._on_change = fn

    def add(self, booking: Booking) -> None:
        with self._lock:
            self._data[booking.id] = booking
        self._notify()

    def get(self, booking_id: str) -> Booking | None:
        with self._lock:
            return self._data.get(booking_id)

    def require(self, booking_id: str) -> Booking:
        booking = self.get(booking_id)
        if booking is None:
            raise BookingNotFound(booking_id)
        return booking

    def update(self, booking: Booking) -> None:
        with self._lock:
            self._data[booking.id] = booking
        self._notify()

    def delete(self, booking_id: str) -> None:
        with self._lock:
            self._data.pop(booking_id, None)
        self._notify()

    def list_active(self) -> list[Booking]:
        with self._lock:
            return [b for b in self._data.values() if b.status not in _TERMINAL]

    def list_all(self) -> list[Booking]:
        with self._lock:
            return list(self._data.values())

    def find_by_admin_message_id(self, message_id: int) -> Booking | None:
        with self._lock:
            return next(
                (b for b in self._data.values() if b.admin_message_id == message_id),
                None,
            )

    def find_by_table_request_message_id(self, message_id: int) -> Booking | None:
        with self._lock:
            return next(
                (b for b in self._data.values() if b.table_request_message_id == message_id),
                None,
            )

    def find_by_alt_request_message_id(self, message_id: int) -> Booking | None:
        with self._lock:
            return next(
                (b for b in self._data.values() if b.alt_request_message_id == message_id),
                None,
            )

    def _notify(self) -> None:
        if self._on_change:
            self._on_change()
