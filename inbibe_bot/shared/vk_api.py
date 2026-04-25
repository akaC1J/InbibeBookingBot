from __future__ import annotations

import logging
from datetime import datetime

import requests  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

VK_API_URL = "https://api.vk.com/method/messages.send"


def send_vk_message(user_id: int, message: str, *, token: str, api_version: str) -> bool:
    """Отправляет сообщение VK-пользователю от имени группы."""
    try:
        resp = requests.post(
            VK_API_URL,
            data={
                "user_id": user_id,
                "random_id": int(datetime.now().timestamp() * 1000),
                "message": message,
                "access_token": token,
                "v": api_version,
            },
            timeout=10,
        )
        data = resp.json()
        return "response" in data and isinstance(data["response"], int)
    except Exception:
        logger.warning("Сообщение пользователю VK %s не было отправлено", user_id)
        return False
