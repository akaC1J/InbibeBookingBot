from datetime import datetime


def format_date_russian(dt: datetime) -> str:
    d = dt.date()
    formatted = d.strftime("%d.%m")
    weekdays = {
        "Monday": "Понедельник",
        "Tuesday": "Вторник",
        "Wednesday": "Среда",
        "Thursday": "Четверг",
        "Friday": "Пятница",
        "Saturday": "Суббота",
        "Sunday": "Воскресенье",
    }
    weekday_ru = weekdays.get(d.strftime("%A"), "")
    return f"{formatted} ({weekday_ru})"


def parse_date_time(text: str) -> datetime | None:
    try:
        return datetime.strptime(text.strip(), "%d.%m.%y %H:%M")
    except ValueError:
        return None
