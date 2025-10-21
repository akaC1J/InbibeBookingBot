from abc import ABC, abstractmethod
from typing import Final, re

from telebot.types import ReplyKeyboardRemove

from inbibe_bot.bot_instance import bot
from inbibe_bot.handlers.user.model import UserState
from inbibe_bot.keyboards import get_phone_keyboard

# Определяем состояния
STATE_IDLE = "idle"  # приветствие, пока не начато бронирование
STATE_WAITING_FOR_NAME = "waiting_for_name"
STATE_WAITING_FOR_PHONE = "waiting_for_phone"
STATE_WAITING_FOR_DATE = "waiting_for_date"
STATE_WAITING_FOR_TIME = "waiting_for_time"
STATE_WAITING_FOR_GUESTS = "waiting_for_guests"

 # === Интерфейс состояния ===
class AbstractState(ABC):

    @abstractmethod
    def handle_input(self, user_id: int, state: UserState, user_input: str):
        pass

    @abstractmethod
    def get_state_name(self) -> str:
        pass

# === Конкретные состояния ===
class IdleState(AbstractState):


    def handle_input(self, user_id: int, state: UserState, user_input: str):
        if user_input.lower() == "начать бронирование":
            bot.send_message(user_id, "Отлично! Как Вас зовут?", reply_markup=ReplyKeyboardRemove())
            return
        bot.send_message(user_id, "Пожалуйста, нажмите «Начать бронирование», чтобы начать.")

    def get_state_name(self) -> str:
        return STATE_IDLE

class AskNameState(AbstractState):

    def handle_input(self, user_id: int, state: UserState, user_input: str):
        state.data.name = user_input
        bot.send_message(
            user_id,
            (
                "Введите, пожалуйста, Ваш телефон.\n"
                "Можно поделиться номером, нажав кнопку ниже, или ввести вручную."
            ),
            reply_markup=get_phone_keyboard(),
        )

    def get_state_name(self) -> str:
        return STATE_WAITING_FOR_NAME


class AskPhoneState(AbstractState):
    PHONE_PATTERN: Final[re.Pattern[str]] = re.compile(r"^(?:\+7|8)\d{10}$")

    def handle_input(self, user_id: int, state: UserState, user_input: str):
        if not AskPhoneState.PHONE_PATTERN.match(user_input):
            bot.send_message(user_id, "Неверный формат телефона. Пример: +79261234567 или 89261234567")
            return
        state.data.phone = user_input
        bot.send_message(user_id, "Спасибо! Номер принят.", reply_markup=ReplyKeyboardRemove())
        bot.send_message(user_id, "Выберите дату бронирования:", reply_markup=generate_date_keyboard())

    def get_state_name(self) -> str:
        return STATE_WAITING_FOR_PHONE

class AskDateState(AbstractState):

    def handle_input(self, context, user_input, state, input1):
        try:
            ctx.context["date_time"] = datetime.fromisoformat(user_input)
        except ValueError:
            print("Некорректный формат, попробуйте ещё раз.")
            return
        ctx.state = AskGuestsAbstractState()

    def get_state_name(self) -> str:
        return STATE_WAITING_FOR_DATE

class AskTimeState(AbstractState):

    def handle_input(self, context, user_input, state, input1):
        try:
            ctx.context["date_time"] = datetime.fromisoformat(user_input)
        except ValueError:
            print("Некорректный формат, попробуйте ещё раз.")
            return
        ctx.state = AskGuestsAbstractState()

    def get_state_name(self) -> str:
        return STATE_WAITING_FOR_TIME


class AskGuestsState(AbstractState):

    def handle_input(self, context, user_input, state, input1):

        )

    def get_state_name(self) -> str:
        return STATE_WAITING_FOR_GUESTS


class FinishAbstractState(AbstractState):

    def handle_input(self, context, user_input, state, input1):
        pass

    def is_final(self):
        return True