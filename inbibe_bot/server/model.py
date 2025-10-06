
from dataclasses import dataclass, asdict, field
from typing import Any, Optional


@dataclass
class BookingResponse:
    success: bool
    error: Optional[str] = None
    details: Optional[list[dict[str, Any]]] = None

    def to_dict(self) -> dict[str, Any]:
        """Превращает в готовый JSON-объект."""
        return asdict(self)

    @classmethod
    def ok(cls) -> "BookingResponse":
        """Быстро создать успешный ответ."""
        return cls(success=True)

    @classmethod
    def fail(cls, error: str, details: Optional[list[dict[str, Any]]] = None) -> "BookingResponse":
        """Быстро создать ответ с ошибкой."""
        return cls(success=False, error=error, details=details)
