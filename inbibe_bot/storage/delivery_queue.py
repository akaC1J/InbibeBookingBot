from __future__ import annotations

import queue
from typing import Callable

from inbibe_bot.core.booking import Booking


class ApprovedBookingQueue:
    def __init__(self) -> None:
        self._q: queue.Queue[Booking] = queue.Queue()
        self._on_change: Callable[[], None] | None = None

    def set_change_callback(self, fn: Callable[[], None]) -> None:
        self._on_change = fn

    def enqueue(self, booking: Booking) -> None:
        self._q.put(booking)
        self._notify()

    def drain(self) -> list[Booking]:
        items: list[Booking] = []
        while True:
            try:
                items.append(self._q.get_nowait())
            except queue.Empty:
                break
        if items:
            self._notify()
        return items

    def snapshot(self) -> list[Booking]:
        """Возвращает содержимое очереди не разрушая её (для сохранения состояния)."""
        items: list[Booking] = []
        while True:
            try:
                items.append(self._q.get_nowait())
            except queue.Empty:
                break
        for item in items:
            self._q.put(item)
        return items

    def _notify(self) -> None:
        if self._on_change:
            self._on_change()
