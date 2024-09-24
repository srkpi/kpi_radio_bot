from aiogram.fsm.state import StatesGroup, State


class PlayerStates(StatesGroup):
    now_playing = State()
