from aiogram.fsm.state import StatesGroup, State


class OrderStates(StatesGroup):
    input = State()
    day = State()
    ether = State()
    banned = State()
