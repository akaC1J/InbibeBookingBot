from __future__ import annotations

from threading import RLock
from typing import Callable

from inbibe_bot.core.user_flow import UserFlow


class UserFlowRepository:
    def __init__(self) -> None:
        self._data: dict[int, UserFlow] = {}
        self._lock = RLock()
        self._on_change: Callable[[], None] | None = None

    def set_change_callback(self, fn: Callable[[], None]) -> None:
        self._on_change = fn

    def get_or_create(self, user_id: int) -> UserFlow:
        with self._lock:
            if user_id not in self._data:
                self._data[user_id] = UserFlow(user_id=user_id)
        return self._data[user_id]

    def get(self, user_id: int) -> UserFlow | None:
        with self._lock:
            return self._data.get(user_id)

    def save(self, flow: UserFlow) -> None:
        with self._lock:
            self._data[flow.user_id] = flow
        self._notify()

    def delete(self, user_id: int) -> None:
        with self._lock:
            self._data.pop(user_id, None)
        self._notify()

    def list_all(self) -> list[UserFlow]:
        with self._lock:
            return list(self._data.values())

    def _notify(self) -> None:
        if self._on_change:
            self._on_change()
