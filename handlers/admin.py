import config
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from keyboards.inline import admin_main
from utils.states import AdminStates
from database.engine import async_session
from database.models import MediaItem, User
from sqlalchemy import select, func
router = Router()
def is_admin(uid): return uid in config.ADMIN_IDS
@router.message(Command('admin'))
async def cmd_admin(m: types.Message):
    if is_admin(m.from_user.id): await m.answer('لوحة التحكم الإدارية:', reply_markup=admin_main())
@router.callback_query(F.data == 'admin_stats')
async def show_stats(c: types.CallbackQuery):
    async with async_session() as s:
        u_c = await s.scalar(select(func.count(User.id)))
        m_c = await s.scalar(select(func.count(MediaItem.id)))
    await c.message.answer(f'📊 الإحصائيات:\nالمستخدمين: {u_c}\nالمواد: {m_c}')
@router.callback_query(F.data == 'admin_add')
async def add_start(c: types.CallbackQuery, state: FSMContext):
    kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text='كرومات', callback_data='add_cat_chromas')], [types.InlineKeyboardButton(text='تصاميم', callback_data='add_cat_designs')], [types.InlineKeyboardButton(text='مناظر', callback_data='add_cat_landscapes')]])
    await c.message.edit_text('اختر التصنيف الرئيسي:', reply_markup=kb); await state.set_state(AdminStates.choosing_category)
@router.callback_query(AdminStates.choosing_category, F.data.startswith('add_cat_'))
async def add_cat(c: types.CallbackQuery, state: FSMContext):
    cat = c.data.split('_')[-1]; await state.update_data(cat=cat)
    if cat == 'landscapes':
        await state.update_data(sub='none', ident='General')
        await c.message.edit_text('أرسل الملف الآن:'); await state.set_state(AdminStates.uploading_media)
    else:
        kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text='سور', callback_data='add_sub_surahs')], [types.InlineKeyboardButton(text='قراء', callback_data='add_sub_sheikhs')]])
        await c.message.edit_text('اختر التصنيف الفرعي:', reply_markup=kb); await state.set_state(AdminStates.choosing_subcategory)
@router.callback_query(AdminStates.choosing_subcategory, F.data.startswith('add_sub_'))
async def add_sub(c: types.CallbackQuery, state: FSMContext):
    sub = c.data.split('_')[-1]; await state.update_data(sub=sub)
    await c.message.edit_text('اكتب اسم السورة أو القارئ:'); await state.set_state(AdminStates.choosing_identifier)
@router.message(AdminStates.choosing_identifier)
async def add_ident(m: types.Message, state: FSMContext):
    await state.update_data(ident=m.text); await m.answer('أرسل الملف الآن:'); await state.set_state(AdminStates.uploading_media)
@router.message(AdminStates.uploading_media)
async def handle_upload(m: types.Message, state: FSMContext):
    f_id, f_t = None, None
    if m.video: f_id, f_t = m.video.file_id, 'video'
    elif m.photo: f_id, f_t = m.photo[-1].file_id, 'photo'
    elif m.document: f_id, f_t = m.document.file_id, 'document'
    if not f_id: await m.answer('يرجى إرسال ملف صالح.'); return
    await state.update_data(file_id=f_id, file_type=f_t); await m.answer("أرسل الوصف أو اكتب 'skip':"); await state.set_state(AdminStates.entering_caption)
@router.message(AdminStates.entering_caption)
async def save_media(m: types.Message, state: FSMContext):
    data = await state.get_data(); cap = m.text if m.text.lower() != 'skip' else None
    async with async_session() as s:
        s.add(MediaItem(category=data['cat'], subcategory=data['sub'], identifier=data['ident'], file_id=data['file_id'], file_type=data['file_type'], caption=cap))
        await s.commit()
    await m.answer('✅ تم الحفظ!'); await state.clear()