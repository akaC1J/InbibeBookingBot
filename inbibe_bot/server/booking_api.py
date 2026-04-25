from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import telebot
from flask import Response, jsonify, request

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


def handle_get_bookings(queue: ApprovedBookingQueue) -> Response:
    bookings = queue.drain()
    if bookings:
        logger.info("Отправлена информация о %d одобренных бронях", len(bookings))
    return jsonify([b.to_dict() for b in bookings])


def handle_health() -> Response:
    return jsonify(BookingResponse.ok().to_dict())


def handle_post_booking(deps: BookingApiDeps) -> tuple[Response, int]:
    parsed_or_err = _parse_booking_request()
    if isinstance(parsed_or_err, BookingResponse):
        return jsonify(parsed_or_err.to_dict()), 400

    booking = Booking(
        id=gen_id(),
        user_id=parsed_or_err.user_id or -1,
        name=parsed_or_err.name,
        phone=parsed_or_err.phone,
        date_time=parsed_or_err.date_time,
        guests=parsed_or_err.guests,
        source=Source.VK,
    )
    deps.booking_repo.add(booking)

    if parsed_or_err.user_id is not None:
        register_vk_user(parsed_or_err.user_id)

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

    return jsonify(BookingResponse.ok().to_dict()), 200


def _parse_booking_request() -> BookingRequest | BookingResponse:
    raw = request.get_data()
    if not raw:
        return BookingResponse.fail(error="empty body")

    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError:
        return BookingResponse.fail(error="invalid encoding, expected UTF-8")

    try:
        parsed = json.loads(decoded)
    except json.JSONDecodeError:
        return BookingResponse.fail(error="invalid JSON")

    logging.info("Получен запрос бронирования: %s", json.dumps(parsed, ensure_ascii=False))

    try:
        return BookingRequest.from_json(parsed)
    except BookingValidationError as e:
        return BookingResponse.fail(error=str(e))
