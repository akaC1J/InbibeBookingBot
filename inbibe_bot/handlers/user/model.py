from dataclasses import dataclass

from inbibe_bot.handlers.user.states.states import AbstractState


@dataclass
class UserStateData:
    name: str = ""
    phone: str = ""
    date_time: datetime = field(default_factory=datetime.now)
    guests: int = 0


@dataclass
class UserState:
    state: AbstractState
    data: UserStateData = field(default_factory=lambda: UserStateData())
