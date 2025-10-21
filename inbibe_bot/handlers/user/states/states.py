from __future__ import annotations

import logging
import re
from abc import ABC
from datetime import datetime, date, time
from typing import ClassVar

from telebot.types import CallbackQuery, Message, ReplyKeyboardRemove

from inbibe_bot.bot_instance import bot
from inbibe_bot.handlers.user.model import UserState
from inbibe_bot.keyboards import generate_date_keyboard, generate_time_keyboard, get_phone_keyboard
from inbibe_bot.utils import format_date_russian

logger = logging.getLogger(__name__)


# Определяем состояния
STATE_IDLE = "idle"
STATE_WAITING_FOR_NAME = "waiting_for_name"
STATE_WAITING_FOR_PHONE = "waiting_for_phone"
STATE_WAITING_FOR_DATE = "waiting_for_date"
STATE_WAITING_FOR_TIME = "waiting_for_time"
STATE_WAITING_FOR_GUESTS = "waiting_for_guests"


class AbstractState(ABC):
    """Базовый класс состояния."""

    name: ClassVar[str]

    def on_enter(self, machine: "UserStateMachine", user_id: int, state: UserState) -> None:
        """Вызывается при переходе в состояние."""

    def handle_text(
        self,
        machine: "UserStateMachine",
        user_id: int,
        state: UserState,
        text: str,
    ) -> "AbstractState | None":
        """Обработка текстового ввода."""
        logger.debug("Нет обработки текстового ввода для состояния %s", self.name)
        return None

    def handle_contact(
        self,
        machine: "UserStateMachine",
        message: Message,
        state: UserState,
    ) -> "AbstractState | None":
        """Обработка контакта."""
        bot.send_message(message.chat.id, "Пожалуйста, воспользуйтесь кнопками на экране.")
        return None

    def handle_callback(
        self,
        machine: "UserStateMachine",
        call: CallbackQuery,
        state: UserState,
    ) -> "AbstractState | None":
        """Обработка callback-запроса."""
        bot.answer_callback_query(call.id, "Действие недоступно на этом шаге.")
        return None


class IdleState(AbstractState):
    name = STATE_IDLE

    def handle_text(
        self,
        machine: "UserStateMachine",
        user_id: int,
        state: UserState,
        text: str,
    ) -> "AbstractState | None":
        if text.lower() == "начать бронирование":
            bot.send_message(user_id, "Отлично! Как Вас зовут?", reply_markup=ReplyKeyboardRemove())
            return machine.get_state(STATE_WAITING_FOR_NAME)

        bot.send_message(
            user_id,
            "Пожалуйста, нажмите «Начать бронирование», чтобы продолжить.",
            reply_markup=None,
        )
        return None


class AskNameState(AbstractState):
    name = STATE_WAITING_FOR_NAME

    def handle_text(
        self,
        machine: "UserStateMachine",
        user_id: int,
        state: UserState,
        text: str,
    ) -> "AbstractState | None":
        cleaned = text.strip()
        if not cleaned:
            bot.send_message(user_id, "Пожалуйста, укажите ваше имя.")
            return None

        state.data.name = cleaned
        bot.send_message(
            user_id,
            (
                "Введите, пожалуйста, Ваш телефон.\n"
                "Можно поделиться номером, нажав кнопку ниже, или ввести вручную."
            ),
            reply_markup=get_phone_keyboard(),
        )
        return machine.get_state(STATE_WAITING_FOR_PHONE)


class AskPhoneState(AbstractState):
    name = STATE_WAITING_FOR_PHONE
    PHONE_PATTERN = re.compile(r"^(?:\+7|8)\d{10}$")

    def handle_text(
        self,
        machine: "UserStateMachine",
        user_id: int,
        state: UserState,
        text: str,
    ) -> "AbstractState | None":
        phone = text.replace(" ", "")
        if not self.PHONE_PATTERN.match(phone):
            bot.send_message(
                user_id,
                "Неверный формат телефона. Пример: +79261234567 или 89261234567",
            )
            return None

        return self._save_phone_and_request_date(machine, user_id, state, phone)

    def handle_contact(
        self,
        machine: "UserStateMachine",
        message: Message,
        state: UserState,
    ) -> "AbstractState | None":
        if not message.contact:
            bot.send_message(message.chat.id, "Не удалось получить контакт. Попробуйте ещё раз.")
            return None

        phone = message.contact.phone_number
        return self._save_phone_and_request_date(machine, message.chat.id, state, phone)

    def _save_phone_and_request_date(
        self,
        machine: "UserStateMachine",
        user_id: int,
        state: UserState,
        phone: str,
    ) -> "AbstractState | None":
        state.data.phone = phone
        bot.send_message(user_id, "Спасибо! Номер принят.", reply_markup=ReplyKeyboardRemove())
        return machine.get_state(STATE_WAITING_FOR_DATE)


class AskDateState(AbstractState):
    name = STATE_WAITING_FOR_DATE

    def on_enter(self, machine: "UserStateMachine", user_id: int, state: UserState) -> None:
        bot.send_message(
            user_id,
            "Выберите дату бронирования:",
            reply_markup=generate_date_keyboard(),
        )

    def handle_text(
        self,
        machine: "UserStateMachine",
        user_id: int,
        state: UserState,
        text: str,
    ) -> "AbstractState | None":
        parsed_date = self._parse_textual_date(text)
        if not parsed_date:
            bot.send_message(user_id, "Не удалось распознать дату. Пожалуйста, воспользуйтесь кнопками ниже.")
            return None

        state.data.date_time = datetime.combine(parsed_date, time.min)
        return machine.get_state(STATE_WAITING_FOR_TIME)

    def handle_callback(
        self,
        machine: "UserStateMachine",
        call: CallbackQuery,
        state: UserState,
    ) -> "AbstractState | None":
        data = call.data or ""
        if not data.startswith("date_"):
            bot.answer_callback_query(call.id, "Неверный формат callback.")
            return None

        try:
            selected_date = datetime.strptime(data.split("_", 1)[1], "%Y-%m-%d").date()
        except ValueError:
            bot.answer_callback_query(call.id, "Неверная дата.")
            return None

        state.data.date_time = datetime.combine(selected_date, time.min)
        bot.answer_callback_query(call.id, "Дата выбрана.")
        return machine.get_state(STATE_WAITING_FOR_TIME)

    @staticmethod
    def _parse_textual_date(text: str) -> date | None:
        cleaned = text.strip()
        if not cleaned:
            return None

        for fmt in ("%d.%m.%Y", "%d.%m.%y", "%d.%m"):
            try:
                parsed = datetime.strptime(cleaned, fmt)
                if fmt == "%d.%m":
                    today = date.today()
                    parsed = parsed.replace(year=today.year)
                    if parsed.date() < today:
                        parsed = parsed.replace(year=today.year + 1)
                return parsed.date()
            except ValueError:
                continue
        return None


class AskTimeState(AbstractState):
    name = STATE_WAITING_FOR_TIME

    def on_enter(self, machine: "UserStateMachine", user_id: int, state: UserState) -> None:
        if not state.data.date_time:
            bot.send_message(user_id, "Сначала выберите дату бронирования.")
            return

        booking_date = state.data.date_time.date()
        bot.send_message(
            user_id,
            f"Выберите время бронирования на {booking_date.strftime('%d.%m')}:",
            reply_markup=generate_time_keyboard(booking_date),
        )

    def handle_text(
        self,
        machine: "UserStateMachine",
        user_id: int,
        state: UserState,
        text: str,
    ) -> "AbstractState | None":
        parsed_time = self._parse_time(text)
        if not parsed_time or not state.data.date_time:
            bot.send_message(user_id, "Не удалось распознать время. Пожалуйста, выберите его из списка.")
            return None

        combined = datetime.combine(state.data.date_time.date(), parsed_time)
        state.data.date_time = combined
        return machine.get_state(STATE_WAITING_FOR_GUESTS)

    def handle_callback(
        self,
        machine: "UserStateMachine",
        call: CallbackQuery,
        state: UserState,
    ) -> "AbstractState | None":
        data = call.data or ""
        if data == "ignore":
            bot.answer_callback_query(call.id, "Выберите время из списка ниже.")
            return None

        if not data.startswith("time_"):
            bot.answer_callback_query(call.id, "Неверный формат callback.")
            return None

        try:
            _, time_str = data.split("time_", 1)
            selected_dt = datetime.strptime(time_str, "%Y-%m-%d_%H:%M")
        except (ValueError, IndexError):
            bot.answer_callback_query(call.id, "Ошибка формата времени.")
            return None

        state.data.date_time = selected_dt
        bot.answer_callback_query(call.id, "Время выбрано.")
        return machine.get_state(STATE_WAITING_FOR_GUESTS)

    @staticmethod
    def _parse_time(text: str) -> time | None:
        cleaned = text.strip()
        if not cleaned:
            return None

        for fmt in ("%H:%M", "%-H:%M", "%H.%M"):
            try:
                return datetime.strptime(cleaned, fmt).time()
            except ValueError:
                continue
        return None


class AskGuestsState(AbstractState):
    name = STATE_WAITING_FOR_GUESTS

    def on_enter(self, machine: "UserStateMachine", user_id: int, state: UserState) -> None:
        bot.send_message(user_id, "Укажите количество гостей (числом).")

    def handle_text(
        self,
        machine: "UserStateMachine",
        user_id: int,
        state: UserState,
        text: str,
    ) -> "AbstractState | None":
        cleaned = text.strip()
        if not cleaned.isdigit():
            bot.send_message(user_id, "Пожалуйста, введите количество гостей цифрами.")
            return None

        guests = int(cleaned)
        if guests <= 0:
            bot.send_message(user_id, "Количество гостей должно быть положительным числом.")
            return None

        state.data.guests = guests
        booking = machine.finalize_booking(user_id, state)
        if booking:
            bot.send_message(
                user_id,
                (
                    "Спасибо! Ваша заявка отправлена. Мы скоро с Вами свяжемся!\n\n"
                    f"Имя: {booking.name}\n"
                    f"Телефон: {booking.phone}\n"
                    f"Дата: {format_date_russian(booking.date_time)}\n"
                    f"Время: {booking.date_time:%H:%M}\n"
                    f"Гостей: {booking.guests}"
                ),
            )
        return None


from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from inbibe_bot.handlers.user.user_state_machine import UserStateMachine

