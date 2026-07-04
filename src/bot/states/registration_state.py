from aiogram.fsm.state import State, StatesGroup


class RegistrationState(StatesGroup):
    waiting_for_invite_code = State()
    waiting_for_email = State()
    waiting_for_surname = State()
    waiting_for_name = State()
    waiting_for_last_name = State()
    waiting_for_password = State()
    waiting_for_repeat_password = State()
