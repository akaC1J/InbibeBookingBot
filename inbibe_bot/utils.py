import logging
import random
import string
from datetime import datetime
import os
import requests

VK_API_URL = "https://api.vk.com/method/messages.send"
VK_GROUP_TOKEN = os.getenv("VK_ACCESS_TOKEN")
VK_API_VERSION = os.getenv("VK_API_VERSION") or "5.199"


def send_vk_message(user_id: int, message: str) -> bool:
    """Send a message to a VK user on behalf of the group.

    Requires env VK_GROUP_TOKEN (or VK_ACCESS_TOKEN) with messages permission.
    Returns True on success, False otherwise.
    """
    if not VK_GROUP_TOKEN:
        # No token configured
        return False
    try:
        payload = {
            "user_id": user_id,
            "random_id": int(datetime.now().timestamp() * 1000),
            "message": message,
            "access_token": VK_GROUP_TOKEN,
            "v": VK_API_VERSION,
        }
        resp = requests.post(VK_API_URL, data=payload, timeout=10)
        data = resp.json()
        return "response" in data and isinstance(data["response"], int)
    except Exception:
        logging.warning(f"Сообщение пользователю {user_id} не было отправлено")
        return False


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


def parse_date_time(text: str | None) -> datetime | None:
    if text is None:
        return None
    try:
        return datetime.strptime(text.strip(), "%d.%m.%y %H:%M")
    except ValueError:
        return None


def gen_id() -> str:
    prefix = random.choice(string.ascii_lowercase)  # случайная буква A–Z
    now = datetime.now().strftime("%y%m%d")  # YYMMDD
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
    return f"{prefix}{now}-{suffix}"
