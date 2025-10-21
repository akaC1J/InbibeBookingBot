from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - только для подсказок типов
    from inbibe_bot.handlers.user.states.states import AbstractState


@dataclass
class UserStateData:
    """Данные, которые собираются от пользователя в процессе бронирования."""

    name: str = ""
    phone: str = ""
    date_time: datetime | None = None
    guests: int = 0


@dataclass
class UserState:
    """Текущее состояние пользователя внутри state machine."""

    state: "AbstractState"
    data: UserStateData = field(default_factory=UserStateData)
