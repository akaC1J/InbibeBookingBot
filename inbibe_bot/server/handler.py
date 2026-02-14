from __future__ import annotations

import json
import logging
import queue
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler
from typing import Any, TypeAlias

import telebot

from inbibe_bot import storage
from inbibe_bot import utils
from inbibe_bot.bot_instance import bot, ADMIN_GROUP_ID, WEBHOOK_SECRET
from inbibe_bot.models import Booking, Source
from inbibe_bot.server.model import BookingResponse, BookingRequest, BookingValidationError
from inbibe_bot.utils import format_date_russian

# === Типы ====================================================================

JSONDict: TypeAlias = dict[str, Any]
logger = logging.getLogger(__name__)

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

    _disabled_request_logging_paths: set[str] = set()

    @classmethod
    def set_request_logging(cls, path: str, enabled: bool) -> None:
        """Включает или отключает стандартное логирование BaseHTTPRequestHandler для ручки."""
        if enabled:
            cls._disabled_request_logging_paths.discard(path)
            return

        cls._disabled_request_logging_paths.add(path)

    def log_message(self, format: str, *args: Any) -> None:
        request_path = self.path.split("?", 1)[0]
        if request_path in self._disabled_request_logging_paths:
            return

        super().log_message(format, *args)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._set_cors()
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/api/bookings":
            new_bookings = []

            # Опустошаем очередь и собираем все элементы
            while True:
                try:
                    booking = storage.not_sent_bookings.get_nowait()
                    new_bookings.append(booking.to_dict())
                except queue.Empty:
                    break

            if new_bookings:
                logger.info("Отправлена информация о новых бронях в количестве %d", len(new_bookings))

            self._send_raw_json(200, new_bookings)
        elif self.path == "/api/health":
            self._send_json(200, BookingResponse.ok())
        else:
            self.not_found()

    def do_POST(self) -> None:
        if self.path == "/webhook":
            self._handle_webhook()
            return

        if self.path == "/api/book":
            self._handle_booking()
            return

        self.not_found()

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

    def _send_raw_json(self, status: int, data: Any) -> None:
        """Sends arbitrary JSON-serializable data with proper headers."""
        self.send_response(status)
        self._set_cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

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
            decoded = body.decode("utf-8")
            parsed_json = json.loads(decoded)
            # 🔹 Логируем только валидный JSON
            logging.info(
                "Получен запрос бронирования. Полученный JSON: %s",
                json.dumps(parsed_json, ensure_ascii=False)
            )

            return True, BookingRequest.from_json(parsed_json)

        except UnicodeDecodeError:
            return False, BookingResponse.fail(error="invalid encoding, expected UTF-8")
        except json.JSONDecodeError:
            return False, BookingResponse.fail(error="invalid JSON")
        except BookingValidationError as e:
            return False, BookingResponse.fail(error=str(e))

    def _handle_webhook(self) -> None:
        # 1. Проверка secret token
        secret = self.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if secret != WEBHOOK_SECRET:
            self.send_response(403)
            self.end_headers()
            return

        # 2. Проверка Content-Length
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except (TypeError, ValueError):
            self.send_response(400)
            self.end_headers()
            return

        if content_length <= 0:
            self.send_response(400)
            self.end_headers()
            return

        # 3. Чтение тела
        try:
            raw_body = self.rfile.read(content_length)
            json_string = raw_body.decode("utf-8")
        except Exception:
            self.send_response(400)
            self.end_headers()
            return

        # 4. Парсинг Update
        try:
            update = telebot.types.Update.de_json(json_string)
        except Exception:
            self.send_response(400)
            self.end_headers()
            return

        # 5. Передача в бот
        try:
            bot.process_new_updates([update])
        except Exception:
            # важно не раскрывать внутренние ошибки наружу
            self.send_response(500)
            self.end_headers()
            return

        # 6. Успешный ответ
        self.send_response(200)
        self.end_headers()


    def _handle_booking(self) -> None:
        ok, payload_or_err = self._read_json()
        if not ok:
            # Narrow type: after ok == False, payload_or_err must be a BookingResponse
            assert isinstance(payload_or_err, BookingResponse)
            self._send_json(400, payload_or_err)
            return

        # Narrow type: after ok == True, payload_or_err must be a BookingRequest
        assert isinstance(payload_or_err, BookingRequest)

        booking = Booking(
            id=utils.gen_id(),
            user_id=payload_or_err.user_id or -1,
            name=payload_or_err.name,
            phone=payload_or_err.phone,
            date_time=payload_or_err.date_time,
            guests=payload_or_err.guests,
            source=Source.VK,
        )

        storage.bookings[booking.id] = booking

        booking_text = (
            f"📥 Новая бронь (VK):\n"
            f"ID: {booking.id}\n"
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

    def not_found(self) -> None:
        self._send_json(404, BookingResponse.fail(error="Not found"))

    def log_request(self, code: int | str = "-", size: int | str = "-") ->None:
        # Логировать всё, кроме запросов с 200 на /api/booking
        if code == 200 and getattr(self, "path", "") == "/api/bookings":
            return
        super().log_request(code, size)


Handler.set_request_logging("/webhook", enabled=False)
