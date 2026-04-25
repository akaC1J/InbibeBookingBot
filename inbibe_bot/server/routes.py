from __future__ import annotations

import logging
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler

import telebot

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


def build_handler(deps: ServerDeps) -> type[BaseHTTPRequestHandler]:
    _api_deps = BookingApiDeps(
        bot=deps.bot,
        admin_group_id=deps.admin_group_id,
        booking_repo=deps.booking_repo,
        delivery_queue=deps.delivery_queue,
        formatter=deps.formatter,
    )

    class Handler(BaseHTTPRequestHandler):
        def do_OPTIONS(self) -> None:
            self.send_response(204)
            self._set_cors()
            self.end_headers()

        def do_GET(self) -> None:
            if self.path == "/api/bookings":
                booking_api.handle_get_bookings(self, deps.delivery_queue)
            elif self.path == "/api/health":
                booking_api.handle_health(self)
            else:
                self._not_found()

        def do_POST(self) -> None:
            if self.path == "/webhook":
                telegram_webhook.handle_webhook(self, deps.bot, deps.webhook_secret)
            elif self.path == "/api/book":
                booking_api.handle_post_booking(self, _api_deps)
            else:
                self._not_found()

        def _set_cors(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

        def _not_found(self) -> None:
            import json
            self.send_response(404)
            self._set_cors()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                json.dumps({"success": False, "error": "Not found"}, ensure_ascii=False).encode()
            )

        def log_request(self, code: int | str = "-", size: int | str = "-") -> None:
            if code == 200 and getattr(self, "path", "") == "/api/bookings":
                return
            super().log_request(code, size)

    return Handler
