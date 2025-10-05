import json
import uuid
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler
from typing import Any

import telebot

from inbibe_bot.bot_instance import bot, ADMIN_GROUP_ID
from inbibe_bot.models import Booking, Source
from inbibe_bot.storage import bookings
from inbibe_bot.utils import format_date_russian


# --- Валидация ---------------------------------------------------------------

class ValidationError:
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message

    def to_dict(self) -> dict[str, str]:
        return {"field": self.field, "message": self.message}


def _require(payload: dict[str, Any], field: str) -> ValidationError | None:
    if payload.get(field) in (None, "", []):
        return ValidationError(field, "required")
    return None


def _parse_int(value: Any, field: str) -> tuple[int | None, ValidationError | None]:
    try:
        return int(value), None
    except Exception:
        return None, ValidationError(field, "must be integer")


def _parse_iso_datetime(value: Any, field: str) -> tuple[datetime | None, ValidationError | None]:
    if not isinstance(value, str):
        return None, ValidationError(field, "must be ISO string")
    try:
        # Поддержим 'YYYY-MM-DDTHH:MM' и полноценный ISO
        dt = datetime.fromisoformat(value)
        return dt, None
    except ValueError:
        return None, ValidationError(field, "invalid ISO datetime format")


def validate_booking_payload(payload: dict[str, Any]) -> tuple[Booking | None, list[ValidationError]]:
    errors: list[ValidationError] = []

    # Обязательные поля
    for f in ("user_id", "name", "phone", "date_time", "guests"):
        err = _require(payload, f)
        if err:
            errors.append(err)

    if errors:
        return None, errors

    # user_id
    user_id, err = _parse_int(payload.get("user_id"), "user_id")
    if err:
        errors.append(err)

    # guests
    guests, err = _parse_int(payload.get("guests"), "guests")
    if err:
        errors.append(err)

    # date_time
    dt, err = _parse_iso_datetime(payload.get("date_time"), "date_time")
    if err:
        errors.append(err)

    # name / phone — базовая проверка
    name = str(payload.get("name", "")).strip()
    phone = str(payload.get("phone", "")).strip()

    if errors:
        return None, errors

    booking_id = str(uuid.uuid4())
    booking = Booking(
        id=booking_id,
        user_id=user_id,
        name=name,
        phone=phone,
        date_time=dt,
        guests=guests,
        source=Source.VK,
    )
    return booking, []


# --- HTTP-обработчик ---------------------------------------------------------

class Handler(BaseHTTPRequestHandler):

    # Разрешим preflight для CORS
    def do_OPTIONS(self):
        self.send_response(204)
        self._set_cors()
        self.end_headers()

    def do_POST(self):
        if self.path != "/api/book":
            self.not_found()
            return

        ok, payload_or_err = self._read_json()
        if not ok:
            self._send_json(400, payload_or_err)  # {"error": "..."}
            return

        payload: dict[str, Any] = payload_or_err
        booking, errors = validate_booking_payload(payload)
        if errors:
            self._send_json(422, {
                "error": "validation failed",
                "details": [e.to_dict() for e in errors],
            })
            return

        # Сохраняем и уведомляем админов
        bookings[booking.id] = booking  # type: ignore[arg-type]

        booking_text = (
            f"📥 Новая бронь (VK):\n"
            f"Имя: {booking.name}\n"
            f"Телефон: {booking.phone}\n"
            f"Дата: {format_date_russian(booking.date_time)}\n"
            f"Время: {booking.date_time.strftime('%H:%M')}\n"
            f"Гостей: {booking.guests}"
        )
        markup = telebot.types.InlineKeyboardMarkup(row_width=2)
        btn_approve = telebot.types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve_{booking.id}")
        btn_alt = telebot.types.InlineKeyboardButton("🕘 Изменить дату/время", callback_data=f"approve_alt_{booking.id}")
        btn_reject = telebot.types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{booking.id}")
        markup.add(btn_approve, btn_reject)
        markup.add(btn_alt)
        msg = bot.send_message(ADMIN_GROUP_ID, booking_text, reply_markup=markup)
        booking.message_id = msg.message_id
        if msg:
            self._send_json(200, {"status": "ok", "booking_id": booking.id})
        else:
            self._send_json(500, {"error": "failed to send message to admin group"})


    # --- утилиты ответа/чтения ------------------------------------------------

    def _set_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _send_json(self, status: int, data: dict[str, Any]):
        self.send_response(status)
        self._set_cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _read_json(self) -> tuple[bool, dict[str, Any]]:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return False, {"error": "invalid Content-Length"}

        body = self.rfile.read(max(content_length, 0))
        if not body:
            return False, {"error": "empty body"}

        try:
            return True, json.loads(body.decode("utf-8"))
        except UnicodeDecodeError:
            return False, {"error": "invalid encoding, expected UTF-8"}
        except json.JSONDecodeError:
            return False, {"error": "invalid JSON"}

    # --- маршрут не найден ---
    def not_found(self):
        self._send_json(404, {"error": "Not found"})
