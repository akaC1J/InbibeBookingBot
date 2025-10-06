from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler
from typing import Any, TypedDict, TypeAlias, cast

import telebot

from inbibe_bot.bot_instance import bot, ADMIN_GROUP_ID
from inbibe_bot.models import Booking, Source
from inbibe_bot.server.model import BookingResponse, BookingRequest, BookingValidationError
from inbibe_bot.storage import bookings
from inbibe_bot.utils import format_date_russian

# === Типы ====================================================================

JSONDict: TypeAlias = dict[str, Any]


# === Валидация ==============================================================

@dataclass(slots=True, frozen=True)
class ValidationError:
    field: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"field": self.field, "message": self.message}


def _require(payload: JSONDict, field: str) -> ValidationError | None:
    """Проверяет обязательное поле."""
    if payload.get(field) in (None, "", []):
        return ValidationError(field, "required")
    return None


def _parse_int(value: Any, field: str) -> tuple[int | None, ValidationError | None]:
    """Пробует привести значение к int."""
    if isinstance(value, bool):  # bool — подтип int, исключаем
        return None, ValidationError(field, "must be integer")
    try:
        return int(value), None
    except (TypeError, ValueError):
        return None, ValidationError(field, "must be integer")


MSK = timezone(timedelta(hours=3))


def _parse_iso_datetime(value: Any, field: str) -> tuple[datetime | None, ValidationError | None]:
    """Парсит ISO-дату с поддержкой 'YYYY-MM-DDTHH:MM'."""
    if not isinstance(value, str):
        return None, ValidationError(field, "must be ISO string")

    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=MSK)
        return dt.astimezone(MSK), None
    except ValueError:
        return None, ValidationError(field, "invalid ISO datetime format")


# === HTTP-обработчик =========================================================

class Handler(BaseHTTPRequestHandler):
    """HTTP API: POST /api/book"""

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._set_cors()
        self.end_headers()

    def do_POST(self) -> None:
        if self.path != "/api/book":
            self.not_found()
            return

        ok, payload_or_err = self._read_json()
        if not ok:
            # Narrow type: after ok == False, payload_or_err must be a BookingResponse
            assert isinstance(payload_or_err, BookingResponse)
            self._send_json(400, payload_or_err)
            return

        # Narrow type: after ok == True, payload_or_err must be a BookingRequest
        assert isinstance(payload_or_err, BookingRequest)

        booking = Booking(id=str(uuid.uuid4()),
                          user_id=payload_or_err.user_id or -1,
                          name=payload_or_err.name,
                          phone=payload_or_err.phone,
                          date_time=payload_or_err.date_time,
                          guests=payload_or_err.guests,
                          source=Source.VK
                          )

        bookings[booking.id] = booking

        booking_text = (
            f"📥 Новая бронь (VK):\n"
            f"Имя: {booking.name}\n"
            f"Телефон: {booking.phone}\n"
            f"Дата: {format_date_russian(booking.date_time)}\n"
            f"Время: {booking.date_time.strftime('%H:%M')}\n"
            f"Гостей: {booking.guests}"
        )

        markup = telebot.types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            telebot.types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve_{booking.id}"),
            telebot.types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{booking.id}"),
        )
        markup.add(
            telebot.types.InlineKeyboardButton("🕘 Изменить дату/время", callback_data=f"approve_alt_{booking.id}")
        )

        msg = bot.send_message(ADMIN_GROUP_ID, booking_text, reply_markup=markup)
        booking.message_id = msg.message_id

        self._send_json(200, BookingResponse.ok())

    # --- Утилиты -------------------------------------------------------------

    def _set_cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _send_json(self, status: int, response: BookingResponse) -> None:
        self.send_response(status)
        self._set_cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()

        self.wfile.write(json.dumps(response.to_dict(), ensure_ascii=False).encode("utf-8"))

    def _read_json(self) -> tuple[bool, BookingRequest | BookingResponse]:
        """Считывает тело JSON и возвращает (ok, data)."""
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except (TypeError, ValueError):
            return False, BookingResponse.fail(error="invalid Content-Length")

        body = self.rfile.read(max(content_length, 0))
        if not body:
            return False, BookingResponse.fail(error="empty body")

        try:
            return True, BookingRequest.from_json(json.loads(body.decode("utf-8")))
        except UnicodeDecodeError:
            return False, BookingResponse.fail(error="invalid encoding, expected UTF-8")
        except json.JSONDecodeError:
            return False, BookingResponse.fail(error="invalid JSON")
        except BookingValidationError as e:
            return False, BookingResponse.fail(error=str(e))

    def not_found(self) -> None:
        self._send_json(404, BookingResponse.fail(error="Not found"))
