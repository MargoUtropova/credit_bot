from aiogram.fsm.state import State, StatesGroup


class CardForm(StatesGroup):
    """
    FSM для добавления новой карты и изменения существующей.
    """
    editing = State()
    waiting_for_value = State()
    