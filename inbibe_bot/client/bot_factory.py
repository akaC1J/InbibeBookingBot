from __future__ import annotations

import logging
from dataclasses import dataclass

import telebot

from inbibe_bot.config import AppConfig
from inbibe_bot.core.booking import Booking, Source
from inbibe_bot.core.booking_workflow import BookingWorkflow
from inbibe_bot.core.formatter import BookingFormatter
from inbibe_bot.storage.booking_repository import BookingRepository
from inbibe_bot.storage.delivery_queue import ApprovedBookingQueue
from inbibe_bot.storage.ephemeral_messages import EphemeralMessageService
from inbibe_bot.storage.user_flow_repository import UserFlowRepository
from inbibe_bot.shared.vk_api import send_vk_message

logger = logging.getLogger(__name__)


@dataclass
class Deps:
    bot: telebot.TeleBot
    config: AppConfig
    booking_repo: BookingRepository
    flow_repo: UserFlowRepository
    delivery_queue: ApprovedBookingQueue
    ephemeral: EphemeralMessageService
    workflow: BookingWorkflow
    formatter: BookingFormatter


def build_bot(config: AppConfig) -> telebot.TeleBot:
    return telebot.TeleBot(config.tg_api_key)


def notify_user(deps: Deps, booking: Booking, text: str) -> None:
    if booking.source == Source.TG:
        try:
            deps.bot.send_message(booking.user_id, text)
        except Exception:
            logger.exception("Не удалось уведомить TG-пользователя %s", booking.user_id)
    else:
        if deps.config.vk_access_token:
            try:
                send_vk_message(
                    booking.user_id,
                    text,
                    token=deps.config.vk_access_token,
                    api_version=deps.config.vk_api_version,
                )
            except Exception:
                logger.exception("Не удалось уведомить VK-пользователя %s", booking.user_id)
        else:
            logger.warning("VK_ACCESS_TOKEN не задан, уведомление не отправлено")


def register_all_handlers(deps: Deps) -> None:
    from inbibe_bot.client.handlers import user_flow, admin_review, table_selection, alt_datetime
    user_flow.register(deps)
    admin_review.register(deps)
    table_selection.register(deps)
    alt_datetime.register(deps)
