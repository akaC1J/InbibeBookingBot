from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler
from typing import Any

import telebot

from inbibe_bot.core.booking import Booking, Source
from inbibe_bot.core.formatter import BookingFormatter
from inbibe_bot.server.dto import BookingRequest, BookingResponse, BookingValidationError
from inbibe_bot.shared.id_gen import gen_id
from inbibe_bot.storage.booking_repository import BookingRepository
from inbibe_bot.storage.delivery_queue import ApprovedBookingQueue
from inbibe_bot.storage.user_registry import register_vk_user

logger = logging.getLogger(__name__)


@dataclass
class BookingApiDeps:
    bot: telebot.TeleBot
    admin_group_id: int
    booking_repo: BookingRepository
    delivery_queue: ApprovedBookingQueue
    formatter: BookingFormatter


def handle_get_bookings(handler: BaseHTTPRequestHandler, queue: ApprovedBookingQueue) -> None:
    bookings = queue.drain()
    if bookings:
        logger.info("Отправлена информация о %d одобренных бронях", len(bookings))
    _send_raw_json(handler, 200, [b.to_dict() for b in bookings])


def handle_health(handler: BaseHTTPRequestHandler) -> None:
    _send_json(handler, 200, BookingResponse.ok())


def handle_post_booking(handler: BaseHTTPRequestHandler, deps: BookingApiDeps) -> None:
    ok, payload_or_err = _read_json(handler)
    if not ok:
        assert isinstance(payload_or_err, BookingResponse)
        _send_json(handler, 400, payload_or_err)
        return

    assert isinstance(payload_or_err, BookingRequest)

    booking = Booking(
        id=gen_id(),
        user_id=payload_or_err.user_id or -1,
        name=payload_or_err.name,
        phone=payload_or_err.phone,
        date_time=payload_or_err.date_time,
        guests=payload_or_err.guests,
        source=Source.VK,
    )
    deps.booking_repo.add(booking)

    if payload_or_err.user_id is not None:
        register_vk_user(payload_or_err.user_id)

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve_{booking.id}"),
        telebot.types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{booking.id}"),
    )
    markup.add(
        telebot.types.InlineKeyboardButton("🕘 Изменить дату/время", callback_data=f"approve_alt_{booking.id}")
    )

    msg = deps.bot.send_message(
        deps.admin_group_id,
        deps.formatter.admin_new(booking),
        reply_markup=markup,
    )
    booking.admin_message_id = msg.message_id
    deps.booking_repo.update(booking)

    _send_json(handler, 200, BookingResponse.ok())


def _read_json(handler: BaseHTTPRequestHandler) -> tuple[bool, BookingRequest | BookingResponse]:
    try:
        content_length = int(handler.headers.get("Content-Length", "0"))
    except (TypeError, ValueError):
        return False, BookingResponse.fail(error="invalid Content-Length")

    body = handler.rfile.read(max(content_length, 0))
    if not body:
        return False, BookingResponse.fail(error="empty body")

    try:
        decoded = body.decode("utf-8")
        parsed = json.loads(decoded)
        logging.info("Получен запрос бронирования: %s", json.dumps(parsed, ensure_ascii=False))
        return True, BookingRequest.from_json(parsed)
    except UnicodeDecodeError:
        return False, BookingResponse.fail(error="invalid encoding, expected UTF-8")
    except json.JSONDecodeError:
        return False, BookingResponse.fail(error="invalid JSON")
    except BookingValidationError as e:
        return False, BookingResponse.fail(error=str(e))


def _send_json(handler: BaseHTTPRequestHandler, status: int, response: BookingResponse) -> None:
    handler.send_response(status)
    _set_cors(handler)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.end_headers()
    handler.wfile.write(json.dumps(response.to_dict(), ensure_ascii=False).encode("utf-8"))


def _send_raw_json(handler: BaseHTTPRequestHandler, status: int, data: Any) -> None:
    handler.send_response(status)
    _set_cors(handler)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.end_headers()
    handler.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))


def _set_cors(handler: BaseHTTPRequestHandler) -> None:
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
