from aiogram.fsm.state import StatesGroup, State


class HelpStates(StatesGroup):
    select = State()
