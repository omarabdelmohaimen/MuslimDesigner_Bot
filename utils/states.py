"""
FSM State definitions for the admin panel flows.
"""
from aiogram.fsm.state import State, StatesGroup


class AddMediaStates(StatesGroup):
    """States for uploading new media."""
    choosing_category    = State()
    choosing_subcategory = State()
    choosing_surah       = State()
    choosing_sheikh      = State()
    choosing_album       = State()
    entering_title       = State()
    entering_title_ar    = State()
    uploading_file       = State()


class EditMediaStates(StatesGroup):
    editing_title    = State()
    editing_title_ar = State()


class AddSurahStates(StatesGroup):
    entering_number  = State()
    entering_name_ar = State()
    entering_name_en = State()
    entering_verses  = State()


class EditSurahStates(StatesGroup):
    choosing_field   = State()
    entering_value   = State()


class AddSheikhStates(StatesGroup):
    entering_name_ar = State()
    entering_name_en = State()
    entering_bio     = State()


class EditSheikhStates(StatesGroup):
    choosing_field = State()
    entering_value = State()


class AddAlbumStates(StatesGroup):
    entering_name    = State()
    entering_name_ar = State()
    entering_desc    = State()


class BroadcastStates(StatesGroup):
    entering_message = State()
    confirming       = State()


class SearchStates(StatesGroup):
    entering_query = State()
