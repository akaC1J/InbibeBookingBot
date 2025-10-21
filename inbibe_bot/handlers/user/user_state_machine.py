import logging

from inbibe_bot.bot_instance import bot
from inbibe_bot.handlers.user.model import UserState
from inbibe_bot.handlers.user.states.states import IdleState, AskNameState, AskPhoneState, AskDateState, AskTimeState, \
    AskGuestsState, AbstractState

logger = logging.getLogger(__name__)

DEFAULT_TRANSITIONS: dict[AbstractState, AbstractState] = {
    IdleState(): AskNameState(),
    AskNameState(): AskPhoneState(),
    AskPhoneState(): AskDateState(),
    AskDateState(): AskTimeState(),
    AskTimeState(): AskGuestsState(),
}

class UserStateMachine:
    def __init__(self, transitions=None):
        self.transitions = dict(transitions or DEFAULT_TRANSITIONS)
        self.context: dict[int, UserState] = {}
        self._parse_transitions(self.transitions)

    def process(self, user_id: int, user_input: str):
        """Передаёт ввод текущему состоянию и меняет состояние"""
        current_state = self.context.get(user_id, None)
        if current_state is None:
            bot.send_message(user_id, "Пожалуйста, начните с команды /start")
            logger.warning("Пользователь %s не найден в user_states", chat_id)
            return None

        current_state.state.handle_input(self, user_id, current_state, user_input)

        self.state.handle_input(self, user_input, current_state, user_input)
        if self.state.is_final():
            self.finalize()
        return self.state.prompt(

    def finalize(self):
        print("\n--- Отправляем бронь ---")
        for k, v in self.context.items():
            print(f"{k}: {v}")
        print("------------------------\n")
        self.state = AskNameState()
        self.context.clear()

    def get_current_state(self, user_id: int):
        return self.context.get(user_id, None)

    def reset_state(self, user_id: int):
        self.context.pop(user_id, None)


    def _parse_transitions(self, transitions: dict[AbstractState, AbstractState]):
        sources = set(transitions.keys())
        targets = set(transitions.values())
        self.start_state = next(iter(sources - targets))
        self.end_state = next(iter(targets - sources))