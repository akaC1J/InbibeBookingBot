from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Booking:
    booking_id: str
    user_id: int
    name: str
    phone: str
    date_time: datetime
    guests: Optional[int] = None
    message_id: int | None = None


@dataclass
class UserStateData:
    name: Optional[str] = None
    phone: Optional[str] = None
    date_time: datetime | None = None
    guests: Optional[int] = None


@dataclass
class UserState:
    state: str
    data: UserStateData = field(default_factory=UserStateData)
