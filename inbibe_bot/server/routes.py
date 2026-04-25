from __future__ import annotations

import logging
from dataclasses import dataclass

import telebot
from flask import Flask, Response

from inbibe_bot.core.formatter import BookingFormatter
from inbibe_bot.server import booking_api, telegram_webhook
from inbibe_bot.server.booking_api import BookingApiDeps
from inbibe_bot.storage.booking_repository import BookingRepository
from inbibe_bot.storage.delivery_queue import ApprovedBookingQueue

logger = logging.getLogger(__name__)


@dataclass
class ServerDeps:
    bot: telebot.TeleBot
    admin_group_id: int
    webhook_secret: str
    booking_repo: BookingRepository
    delivery_queue: ApprovedBookingQueue
    formatter: BookingFormatter


class _SkipBookingsAccessLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not ("GET /api/bookings" in msg and " 200 " in msg)


def build_app(deps: ServerDeps) -> Flask:
    app = Flask(__name__)
    app.json.ensure_ascii = False  # type: ignore[attr-defined]

    api_deps = BookingApiDeps(
        bot=deps.bot,
        admin_group_id=deps.admin_group_id,
        booking_repo=deps.booking_repo,
        delivery_queue=deps.delivery_queue,
        formatter=deps.formatter,
    )

    @app.after_request
    def _cors(response: Response) -> Response:
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

    @app.get("/api/health")
    def health() -> Response:
        return booking_api.handle_health()

    @app.get("/api/bookings")
    def get_bookings() -> Response:
        return booking_api.handle_get_bookings(deps.delivery_queue)

    @app.post("/api/book")
    def post_booking() -> tuple[Response, int]:
        return booking_api.handle_post_booking(api_deps)

    @app.post("/webhook")
    def webhook() -> tuple[str, int]:
        return telegram_webhook.handle_webhook(deps.bot, deps.webhook_secret)

    logging.getLogger("werkzeug").addFilter(_SkipBookingsAccessLogFilter())

    return app
