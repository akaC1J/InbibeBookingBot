from __future__ import annotations

from datetime import datetime, date


class CallbackData:
    """Парсеры и билдеры для callback_data строк."""

    # Prefixes
    DATE = "date_"
    TIME = "time_"
    APPROVE = "approve_"
    APPROVE_ALT = "approve_alt_"
    REJECT = "reject_"
    TABLE = "table_"

    @staticmethod
    def parse_date(data: str) -> date:
        return datetime.strptime(data[len(CallbackData.DATE):], "%Y-%m-%d").date()

    @staticmethod
    def parse_time(data: str) -> datetime:
        return datetime.strptime(data[len(CallbackData.TIME):], "%Y-%m-%d_%H:%M")

    @staticmethod
    def parse_booking_id(data: str, prefix: str) -> str:
        return data[len(prefix):]

    @staticmethod
    def parse_table(data: str) -> tuple[str, int]:
        """Возвращает (booking_id, table_num)."""
        _, booking_id, tail = data.split("_", 2)
        return booking_id, int(tail)
