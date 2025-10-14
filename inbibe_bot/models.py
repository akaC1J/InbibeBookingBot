from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

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
    table_number: int = -1  # -1 = Any
    message_id: int | None = None
    source: Source = Source.TG

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "phone": self.phone,
            "date_time": self.date_time.isoformat(),
            "guests": self.guests,
            "table_number": self.table_number,
            "source": self.source.value,
        }


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
