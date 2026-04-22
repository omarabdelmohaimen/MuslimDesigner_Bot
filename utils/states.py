from aiogram.fsm.state import State, StatesGroup
class AdminStates(StatesGroup):
    choosing_category = State()
    choosing_subcategory = State()
    choosing_identifier = State()
    uploading_media = State()
    entering_caption = State()
    broadcasting = State()