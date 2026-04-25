from __future__ import annotations

import queue

from inbibe_bot.core.booking import Booking


class ApprovedBookingQueue:
    def __init__(self) -> None:
        self._q: queue.Queue[Booking] = queue.Queue()

    def enqueue(self, booking: Booking) -> None:
        self._q.put(booking)

    def drain(self) -> list[Booking]:
        items: list[Booking] = []
        while True:
            try:
                items.append(self._q.get_nowait())
            except queue.Empty:
                break
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
