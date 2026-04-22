from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
from utils.surahs import SURAHS
class Nav(CallbackData, prefix='nav'):
    action: str; cat: str = 'none'; sub: str = 'none'; id: str = 'none'; page: int = 0
def main_menu():
    b = InlineKeyboardBuilder()
    b.button(text='🎬 كرومات', callback_data=Nav(action='menu', cat='chromas'))
    b.button(text='🎨 تصاميم', callback_data=Nav(action='menu', cat='designs'))
    b.button(text='🌿 مناظر طبيعية', callback_data=Nav(action='menu', cat='landscapes'))
    b.adjust(1)
    return b.as_markup()
def sub_menu(cat):
    b = InlineKeyboardBuilder()
    b.button(text='📖 سور القرآن', callback_data=Nav(action='list', cat=cat, sub='surahs'))
    b.button(text='🎙️ القراء', callback_data=Nav(action='list', cat=cat, sub='sheikhs'))
    b.button(text='🔙 عودة', callback_data=Nav(action='back'))
    b.adjust(1)
    return b.as_markup()
def surahs_kb(cat, sub, page=0):
    b = InlineKeyboardBuilder()
    start, end = page*20, (page+1)*20
    for s in SURAHS[start:end]: b.button(text=s, callback_data=Nav(action='items', cat=cat, sub=sub, id=s))
    b.adjust(2)
    if page > 0: b.row(InlineKeyboardBuilder().button(text='⬅️', callback_data=Nav(action='list', cat=cat, sub=sub, page=page-1)).as_markup().inline_keyboard[0][0])
    if end < len(SURAHS): b.row(InlineKeyboardBuilder().button(text='➡️', callback_data=Nav(action='list', cat=cat, sub=sub, page=page+1)).as_markup().inline_keyboard[0][0])
    b.row(InlineKeyboardBuilder().button(text='🏠 الرئيسية', callback_data=Nav(action='back')).as_markup().inline_keyboard[0][0])
    return b.as_markup()
def admin_main():
    b = InlineKeyboardBuilder()
    b.button(text='➕ إضافة محتوى', callback_data='admin_add')
    b.button(text='📊 الإحصائيات', callback_data='admin_stats')
    b.adjust(1)
    return b.as_markup()