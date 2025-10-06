from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

class Source(str, Enum):
    TG = "Telegram"
    VK = "VK"


@dataclass
class Booking:
    id: str
    user_id: int
    name: str
    phone: str
    date_time: datetime
    guests: int
    message_id: int | None = None
    source: Source = Source.TG


@dataclass
class UserStateData:
    name: str = ""
    phone: str = ""
    date_time: datetime = datetime.now()
    guests: int = 0


@dataclass
class UserState:
    state: str
    data: UserStateData = field(default_factory=lambda: UserStateData())
