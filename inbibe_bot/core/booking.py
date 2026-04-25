from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class BookingStatus(str, Enum):
    PENDING = "pending"
    AWAITING_TABLE = "awaiting_table"
    AWAITING_NEW_DATETIME = "awaiting_new_datetime"
    APPROVED = "approved"
    REJECTED = "rejected"


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
    source: Source
    status: BookingStatus = BookingStatus.PENDING
    table_numbers: set[int] = field(default_factory=set)
    admin_message_id: int | None = None
    table_request_message_id: int | None = None
    alt_request_message_id: int | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "phone": self.phone,
            "date_time": self.date_time.isoformat(),
            "guests": self.guests,
            "source": self.source.value,
            "status": self.status.value,
            "table_numbers": list(self.table_numbers),
            "admin_message_id": self.admin_message_id,
            "table_request_message_id": self.table_request_message_id,
            "alt_request_message_id": self.alt_request_message_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Booking":
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            name=data["name"],
            phone=data["phone"],
            date_time=datetime.fromisoformat(data["date_time"]),
            guests=data["guests"],
            source=Source(data.get("source", Source.TG.value)),
            status=BookingStatus(data.get("status", BookingStatus.PENDING.value)),
            table_numbers=set(data.get("table_numbers", [])),
            admin_message_id=data.get("admin_message_id"),
            table_request_message_id=data.get("table_request_message_id"),
            alt_request_message_id=data.get("alt_request_message_id"),
        )
