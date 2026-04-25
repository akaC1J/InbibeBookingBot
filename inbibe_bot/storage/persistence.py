from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from inbibe_bot.core.booking import Booking
from inbibe_bot.core.user_flow import UserFlow, UserFlowData, FlowStep
from inbibe_bot.storage.booking_repository import BookingRepository
from inbibe_bot.storage.delivery_queue import ApprovedBookingQueue
from inbibe_bot.storage.ephemeral_messages import EphemeralMessageService
from inbibe_bot.storage.user_flow_repository import UserFlowRepository

STATE_VERSION = 2
logger = logging.getLogger(__name__)


class StatePersister:
    def __init__(
        self,
        path: Path,
        bookings: BookingRepository,
        flows: UserFlowRepository,
        queue: ApprovedBookingQueue,
        ephemeral: EphemeralMessageService,
    ) -> None:
        self._path = path
        self._bookings = bookings
        self._flows = flows
        self._queue = queue
        self._ephemeral = ephemeral

    def save(self) -> None:
        try:
            data = {
                "version": STATE_VERSION,
                "bookings": [b.to_dict() for b in self._bookings.list_all()],
                "user_flows": [_flow_to_dict(f) for f in self._flows.list_all()],
                "pending_delivery": [b.to_dict() for b in self._queue.snapshot()],
                "ephemeral_messages": self._ephemeral.snapshot(),
            }
            self._path.parent.mkdir(exist_ok=True)
            self._path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            logger.info("Состояние сохранено в %s", self._path)
        except Exception:
            logger.exception("Ошибка при сохранении состояния")

    def load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            version = data.get("version", 1)
            if version < STATE_VERSION:
                logger.warning(
                    "Формат state.json v%s устарел (текущий v%s). Стартуем с чистым состоянием.",
                    version, STATE_VERSION,
                )
                return

            for b in data.get("bookings", []):
                self._bookings.add(Booking.from_dict(b))

            for f in data.get("user_flows", []):
                self._flows.save(_flow_from_dict(f))

            for b in data.get("pending_delivery", []):
                self._queue.enqueue(Booking.from_dict(b))

            self._ephemeral.restore(data.get("ephemeral_messages", {}))

            logger.info("Состояние восстановлено из %s", self._path)
        except Exception:
            logger.exception("Ошибка при загрузке состояния, стартуем с чистым состоянием")


def _flow_to_dict(flow: UserFlow) -> dict:
    return {
        "user_id": flow.user_id,
        "step": flow.step.value,
        "data": {
            "name": flow.data.name,
            "phone": flow.data.phone,
            "date_time": flow.data.date_time.isoformat() if flow.data.date_time else None,
            "guests": flow.data.guests,
        },
    }


def _flow_from_dict(d: dict) -> UserFlow:
    data = d["data"]
    return UserFlow(
        user_id=d["user_id"],
        step=FlowStep(d["step"]),
        data=UserFlowData(
            name=data["name"],
            phone=data["phone"],
            date_time=datetime.fromisoformat(data["date_time"]) if data.get("date_time") else None,
            guests=data["guests"],
        ),
    )
