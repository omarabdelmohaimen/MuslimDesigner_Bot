from aiogram import Router, F, types
from keyboards.inline import Nav, main_menu, sub_menu, surahs_kb
from database.engine import async_session
from database.models import MediaItem
from sqlalchemy import select
router = Router()
@router.callback_query(Nav.filter(F.action == 'back'))
async def go_home(c: types.CallbackQuery): await c.message.edit_text('القائمة الرئيسية:', reply_markup=main_menu())
@router.callback_query(Nav.filter(F.action == 'menu'))
async def show_menu(c: types.CallbackQuery, cd: Nav):
    if cd.cat == 'landscapes': await list_items_logic(c, cd.cat, 'none', 'General')
    else: await c.message.edit_text(f'قسم {cd.cat}:', reply_markup=sub_menu(cd.cat))
@router.callback_query(Nav.filter(F.action == 'list'))
async def show_list(c: types.CallbackQuery, cd: Nav):
    if cd.sub == 'surahs': await c.message.edit_text('اختر السورة:', reply_markup=surahs_kb(cd.cat, cd.sub, cd.page))
    else: await c.answer('سيتم إضافة القراء قريباً', show_alert=True)
async def list_items_logic(c, cat, sub, ident):
    async with async_session() as s:
        stmt = select(MediaItem).where(MediaItem.category == cat)
        if sub != 'none': stmt = stmt.where(MediaItem.subcategory == sub)
        if ident != 'none': stmt = stmt.where(MediaItem.identifier == ident)
        res = await s.execute(stmt); items = res.scalars().all()
    if not items: await c.answer('لا يوجد محتوى متوفر حالياً', show_alert=True); return
    for i in items:
        if i.file_type == 'video': await c.message.answer_video(i.file_id, caption=i.caption)
        elif i.file_type == 'photo': await c.message.answer_photo(i.file_id, caption=i.caption)
        else: await c.message.answer_document(i.file_id, caption=i.caption)
@router.callback_query(Nav.filter(F.action == 'items'))
async def list_items(c: types.CallbackQuery, cd: Nav): await list_items_logic(c, cd.cat, cd.sub, cd.id)