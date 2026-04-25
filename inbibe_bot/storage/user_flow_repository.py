from __future__ import annotations

from threading import RLock

from inbibe_bot.core.user_flow import UserFlow, FlowStep


class UserFlowRepository:
    def __init__(self) -> None:
        self._data: dict[int, UserFlow] = {}
        self._lock = RLock()

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

    def delete(self, user_id: int) -> None:
        with self._lock:
            self._data.pop(user_id, None)

    def list_all(self) -> list[UserFlow]:
        with self._lock:
            return list(self._data.values())
