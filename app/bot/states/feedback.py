from aiogram.fsm.state import StatesGroup, State


class FeedbackStates(StatesGroup):
    feedback = State()
    message_sent = State()
