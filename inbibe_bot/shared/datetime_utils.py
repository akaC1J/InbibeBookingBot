from __future__ import annotations

from datetime import datetime, timezone, timedelta

MSK = timezone(timedelta(hours=3))

_WEEKDAYS_RU = {
    "Monday": "Понедельник",
    "Tuesday": "Вторник",
    "Wednesday": "Среда",
    "Thursday": "Четверг",
    "Friday": "Пятница",
    "Saturday": "Суббота",
    "Sunday": "Воскресенье",
}


def format_date_russian(dt: datetime) -> str:
    d = dt.date()
    weekday_ru = _WEEKDAYS_RU.get(d.strftime("%A"), "")
    return f"{d.strftime('%d.%m')} ({weekday_ru})"


def parse_admin_datetime(text: str | None) -> datetime | None:
    """Парсит дату/время в формате DD.MM.YY HH:MM, который вводит администратор вручную."""
    if text is None:
        return None
    try:
        return datetime.strptime(text.strip(), "%d.%m.%y %H:%M")
    except ValueError:
        return None
