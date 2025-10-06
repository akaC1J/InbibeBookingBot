from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Any, Optional


@dataclass
class BookingResponse:
    success: bool
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Превращает в готовый JSON-объект."""
        return asdict(self)

    @classmethod
    def ok(cls) -> BookingResponse:
        """Быстро создать успешный ответ."""
        return cls(success=True)

    @classmethod
    def fail(cls, error: str) -> BookingResponse:
        """Быстро создать ответ с ошибкой."""
        return cls(success=False, error=error)

class BookingValidationError(ValueError):
    """Ошибка при разборе или валидации данных бронирования."""
    pass

MSK = timezone(timedelta(hours=3))
@dataclass
class BookingRequest:
    user_id: Optional[int]
    name: str
    phone: str
    date_time: datetime
    guests: int

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> BookingRequest:
        """Создаёт и валидирует объект BookingRequest из JSON-словаря."""
        try:
            # Проверка обязательных полей
            for field in ("name", "phone", "date_time", "guests"):
                if field not in data or data[field] in (None, "", []):
                    raise BookingValidationError(f"Поле '{field}' обязательно")

            # Преобразование и строгая проверка типов
            user_id = None
            if "user_id" in data and data["user_id"] not in (None, ""):
                user_id = int(data["user_id"])

            name = str(data["name"]).strip()
            phone = str(data["phone"]).strip()

            # Проверка даты (ISO 8601)
            try:
                dt = datetime.fromisoformat(data["date_time"]).astimezone(MSK)
            except Exception as e:
                raise BookingValidationError(
                    f"Поле 'date_time' должно быть в ISO формате: {e}"
                )

            # Проверка гостей
            guests = int(data["guests"])
            if guests <= 0:
                raise BookingValidationError("Количество гостей должно быть больше нуля")

            return cls(
                user_id=user_id,
                name=name,
                phone=phone,
                date_time=dt,
                guests=guests,
            )

        except (KeyError, TypeError, ValueError) as e:
            raise BookingValidationError(f"Невалидные данные бронирования: {e}")
