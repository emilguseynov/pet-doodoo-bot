from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    waiting_for_pet_name = State()
    waiting_for_invite_code = State()
