from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

MSK = timezone(timedelta(hours=3))


class BookingValidationError(ValueError):
    pass


@dataclass
class BookingResponse:
    success: bool
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def ok(cls) -> "BookingResponse":
        return cls(success=True)

    @classmethod
    def fail(cls, error: str) -> "BookingResponse":
        return cls(success=False, error=error)


@dataclass
class BookingRequest:
    user_id: Optional[int]
    name: str
    phone: str
    date_time: datetime
    guests: int

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "BookingRequest":
        try:
            for field in ("name", "phone", "date_time", "guests"):
                if field not in data or data[field] in (None, "", []):
                    raise BookingValidationError(f"Поле '{field}' обязательно")

            user_id: Optional[int] = None
            if "user_id" in data and data["user_id"] not in (None, ""):
                user_id = int(data["user_id"])

            try:
                dt = datetime.fromisoformat(str(data["date_time"])).astimezone(MSK)
            except Exception as e:
                raise BookingValidationError(f"Поле 'date_time' должно быть в ISO формате: {e}")

            guests = int(data["guests"])
            if guests <= 0:
                raise BookingValidationError("Количество гостей должно быть больше нуля")

            return cls(
                user_id=user_id,
                name=str(data["name"]).strip(),
                phone=str(data["phone"]).strip(),
                date_time=dt,
                guests=guests,
            )
        except (KeyError, TypeError, ValueError) as e:
            raise BookingValidationError(f"Невалидные данные бронирования: {e}")
