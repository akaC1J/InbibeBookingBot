from __future__ import annotations

import logging
from typing import Callable, Dict

from telebot.types import CallbackQuery, Message

from inbibe_bot.bot_instance import bot
from inbibe_bot.handlers.user.model import UserState, UserStateData
from inbibe_bot.handlers.user.states.states import (
    AbstractState,
    AskDateState,
    AskGuestsState,
    AskNameState,
    AskPhoneState,
    AskTimeState,
    IdleState,
    STATE_IDLE,
)
from inbibe_bot.models import Booking
from inbibe_bot.storage import bookings
from inbibe_bot import utils

logger = logging.getLogger(__name__)


class UserStateMachine:
    """State machine, управляющая диалогом бронирования."""

    def __init__(self, *, on_booking_created: Callable[[Booking], None] | None = None) -> None:
        self._states: Dict[str, AbstractState] = {
            STATE_IDLE: IdleState(),
            AskNameState.name: AskNameState(),
            AskPhoneState.name: AskPhoneState(),
            AskDateState.name: AskDateState(),
            AskTimeState.name: AskTimeState(),
            AskGuestsState.name: AskGuestsState(),
        }
        self._context: Dict[int, UserState] = {}
        self._on_booking_created = on_booking_created

    # ----------------------------------------------------------------------------
    # Статус пользователей
    # ----------------------------------------------------------------------------
    def reset_state(self, user_id: int) -> None:
        """Сбрасывает состояние пользователя к начальному (idle)."""

        logger.debug("Reset state for user %s", user_id)
        self._context[user_id] = UserState(state=self.get_state(STATE_IDLE), data=UserStateData())

    def has_state(self, user_id: int) -> bool:
        return user_id in self._context

    def get_current_state(self, user_id: int) -> UserState | None:
        return self._context.get(user_id)

    # ----------------------------------------------------------------------------
    # Обработка ввода
    # ----------------------------------------------------------------------------
    def process_text(self, user_id: int, text: str) -> None:
        state_obj = self._ensure_state(user_id)
        if not state_obj:
            return

        logger.debug("Process text in state %s for user %s", state_obj.state.name, user_id)
        next_state = state_obj.state.handle_text(self, user_id, state_obj, text)
        if next_state:
            self._set_state(user_id, next_state)

    def process_contact(self, message: Message) -> None:
        user_id = message.chat.id
        state_obj = self._ensure_state(user_id)
        if not state_obj:
            return

        logger.debug("Process contact in state %s for user %s", state_obj.state.name, user_id)
        next_state = state_obj.state.handle_contact(self, message, state_obj)
        if next_state:
            self._set_state(user_id, next_state)

    def process_callback(self, call: CallbackQuery) -> bool:
        user_id = call.from_user.id
        state_obj = self._ensure_state(user_id, notify=False)
        if not state_obj:
            bot.answer_callback_query(call.id, "Выбор больше неактуален.")
            return False

        logger.debug("Process callback in state %s for user %s", state_obj.state.name, user_id)
        next_state = state_obj.state.handle_callback(self, call, state_obj)
        if next_state:
            self._set_state(user_id, next_state)
        return True

    # ----------------------------------------------------------------------------
    # Переходы и финализация
    # ----------------------------------------------------------------------------
    def get_state(self, state_name: str) -> AbstractState:
        try:
            return self._states[state_name]
        except KeyError as exc:
            raise ValueError(f"Unknown state: {state_name}") from exc

    def _set_state(self, user_id: int, next_state: AbstractState) -> None:
        state_obj = self._context.get(user_id)
        if not state_obj:
            logger.warning("Trying to set state for unknown user %s", user_id)
            return

        logger.debug("Transition user %s to state %s", user_id, next_state.name)
        state_obj.state = next_state
        next_state.on_enter(self, user_id, state_obj)

    def finalize_booking(self, user_id: int, state: UserState) -> Booking | None:
        if not state.data.date_time:
            bot.send_message(user_id, "Не выбрана дата бронирования. Попробуйте начать заново командой /start.")
            self._context.pop(user_id, None)
            return None

        booking = Booking(
            id=utils.gen_id(),
            user_id=user_id,
            name=state.data.name,
            phone=state.data.phone,
            date_time=state.data.date_time,
            guests=state.data.guests,
        )

        bookings[booking.id] = booking
        logger.info("Создана бронь %s для пользователя %s", booking.id, user_id)

        if self._on_booking_created:
            try:
                self._on_booking_created(booking)
            except Exception:  # pragma: no cover - уведомление не должно ломать поток
                logger.exception("Не удалось уведомить администраторов о брони %s", booking.id)

        # Завершаем сценарий — удаляем текущее состояние
        self._context.pop(user_id, None)
        return booking

    def set_booking_callback(self, callback: Callable[[Booking], None] | None) -> None:
        self._on_booking_created = callback

    # ----------------------------------------------------------------------------
    # Вспомогательные методы
    # ----------------------------------------------------------------------------
    def _ensure_state(self, user_id: int, *, notify: bool = True) -> UserState | None:
        state = self._context.get(user_id)
        if state:
            return state

        if notify:
            bot.send_message(user_id, "Пожалуйста, начните с команды /start")
        logger.warning("Пользователь %s не найден в контексте состояний", user_id)
        return None


__all__ = ["UserStateMachine"]

