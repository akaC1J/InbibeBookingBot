from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Final

from inbibe_bot.core.booking import Booking, Source
from inbibe_bot.core.errors import FlowValidationError
from inbibe_bot.shared.id_gen import gen_id

PHONE_PATTERN: Final[re.Pattern[str]] = re.compile(r"^(?:\+7|8)\d{10}$")


class FlowStep(str, Enum):
    IDLE = "idle"
    NAME = "name"
    PHONE = "phone"
    DATE = "date"
    TIME = "time"
    GUESTS = "guests"
    DONE = "done"


@dataclass
class UserFlowData:
    name: str = ""
    phone: str = ""
    date_time: datetime | None = None
    guests: int = 0


@dataclass
class UserFlow:
    user_id: int
    step: FlowStep = FlowStep.IDLE
    data: UserFlowData = field(default_factory=UserFlowData)

    def start(self) -> None:
        self.step = FlowStep.NAME
        self.data = UserFlowData()

    def submit_name(self, name: str) -> None:
        self.data.name = name
        self.step = FlowStep.PHONE

    def submit_phone(self, phone: str) -> None:
        if not PHONE_PATTERN.match(phone):
            raise FlowValidationError("Неверный формат телефона. Пример: +79261234567 или 89261234567")
        self.data.phone = phone
        self.step = FlowStep.DATE

    def submit_date(self, d: date) -> None:
        self.data.date_time = datetime.combine(d, datetime.min.time())
        self.step = FlowStep.TIME

    def submit_time(self, dt: datetime) -> None:
        self.data.date_time = dt
        self.step = FlowStep.GUESTS

    def submit_guests(self, count: int, source: Source) -> Booking:
        self.data.guests = count
        self.step = FlowStep.DONE
        return Booking(
            id=gen_id(),
            user_id=self.user_id,
            name=self.data.name,
            phone=self.data.phone,
            date_time=self.data.date_time or datetime.now(),
            guests=self.data.guests,
            source=source,
        )
