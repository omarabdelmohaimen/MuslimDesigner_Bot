"""
Admin panel inline keyboards.
All labels kept in Arabic for consistency with the user interface.
"""
from __future__ import annotations

from typing import List, Dict, Optional

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


class AdminKeyboards:
    """Factory class for all admin keyboards."""

    # ── Admin Main Menu ────────────────────────────────────────────────────────
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        buttons = [
            ("➕ إضافة محتوى",        "admin_add_media"),
            ("📋 قائمة المحتوى",      "admin_list_media"),
            ("🔍 بحث في المحتوى",     "admin_search"),
            ("📖 إدارة السور",        "admin_surahs"),
            ("🎙️ إدارة المشايخ",      "admin_sheikhs"),
            ("🗂️ إدارة الألبومات",    "admin_albums"),
            ("📊 إحصائيات البوت",     "admin_stats"),
            ("📢 إرسال بث",           "admin_broadcast"),
            ("📜 سجل الإجراءات",      "admin_logs"),
            ("🏠 الرئيسية",           "home"),
        ]
        for text, cb in buttons:
            builder.button(text=text, callback_data=cb)
        builder.adjust(2)
        return builder.as_markup()

    # ── Add Media – choose category ────────────────────────────────────────────
    @staticmethod
    def choose_category(categories: List[Dict]) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for cat in categories:
            builder.button(
                text=f"{cat['icon']} {cat['name_ar']}",
                callback_data=f"adm_cat:{cat['id']}",
            )
        builder.button(text="🔙 رجوع", callback_data="admin_menu")
        builder.adjust(1)
        return builder.as_markup()

    # ── Add Media – choose subcategory ─────────────────────────────────────────
    @staticmethod
    def choose_subcategory(
        subcategories: List[Dict], category_id: int
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for sub in subcategories:
            builder.button(
                text=f"{sub['icon']} {sub['name_ar']}",
                callback_data=f"adm_sub:{sub['id']}:cat:{category_id}",
            )
        builder.button(text="🔙 رجوع", callback_data="admin_add_media")
        builder.adjust(1)
        return builder.as_markup()

    # ── Add Media – choose surah ───────────────────────────────────────────────
    @staticmethod
    def choose_surah(
        surahs: List[Dict], sub_id: int, cat_id: int, page: int = 1, total_pages: int = 1
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for s in surahs:
            builder.button(
                text=f"{s['number']}. {s['name_ar']}",
                callback_data=f"adm_surah:{s['id']}:sub:{sub_id}:cat:{cat_id}",
            )
        builder.adjust(2)

        nav = []
        if page > 1:
            nav.append(InlineKeyboardButton(
                text="◀️", callback_data=f"adm_surah_page:{page-1}:sub:{sub_id}:cat:{cat_id}"
            ))
        if page < total_pages:
            nav.append(InlineKeyboardButton(
                text="▶️", callback_data=f"adm_surah_page:{page+1}:sub:{sub_id}:cat:{cat_id}"
            ))
        if nav:
            builder.row(*nav)

        builder.row(
            InlineKeyboardButton(
                text="⏭️ تخطي (بدون سورة)",
                callback_data=f"adm_surah:0:sub:{sub_id}:cat:{cat_id}",
            )
        )
        builder.row(
            InlineKeyboardButton(text="🔙 رجوع", callback_data=f"adm_sub:{sub_id}:cat:{cat_id}")
        )
        return builder.as_markup()

    # ── Add Media – choose sheikh ──────────────────────────────────────────────
    @staticmethod
    def choose_sheikh(
        sheikhs: List[Dict], sub_id: int, cat_id: int, surah_id: int = 0
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for sh in sheikhs:
            builder.button(
                text=f"🎙️ {sh['name_ar']}",
                callback_data=f"adm_sheikh:{sh['id']}:sub:{sub_id}:cat:{cat_id}:sur:{surah_id}",
            )
        builder.button(
            text="⏭️ تخطي (بدون شيخ)",
            callback_data=f"adm_sheikh:0:sub:{sub_id}:cat:{cat_id}:sur:{surah_id}",
        )
        builder.button(text="🔙 رجوع", callback_data=f"adm_sub:{sub_id}:cat:{cat_id}")
        builder.adjust(1)
        return builder.as_markup()

    # ── Add Media – choose album ───────────────────────────────────────────────
    @staticmethod
    def choose_album(
        albums: List[Dict], sub_id: int, cat_id: int
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for a in albums:
            builder.button(
                text=f"🗂️ {a['name_ar']}",
                callback_data=f"adm_album:{a['id']}:sub:{sub_id}:cat:{cat_id}",
            )
        builder.button(
            text="⏭️ تخطي (بدون ألبوم)",
            callback_data=f"adm_album:0:sub:{sub_id}:cat:{cat_id}",
        )
        builder.button(text="🔙 رجوع", callback_data=f"adm_sub:{sub_id}:cat:{cat_id}")
        builder.adjust(1)
        return builder.as_markup()

    # ── Manage Media Item ──────────────────────────────────────────────────────
    @staticmethod
    def media_item_actions(media_id: int) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="✏️ تعديل العنوان",
                callback_data=f"adm_edit_title:{media_id}",
            ),
            InlineKeyboardButton(
                text="🗑️ حذف",
                callback_data=f"adm_del_confirm:{media_id}",
            ),
        )
        builder.row(
            InlineKeyboardButton(
                text="🔙 رجوع", callback_data="admin_list_media"
            )
        )
        return builder.as_markup()

    # ── Confirm Delete ─────────────────────────────────────────────────────────
    @staticmethod
    def confirm_delete(media_id: int) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="✅ نعم، احذف",
                callback_data=f"adm_del:{media_id}",
            ),
            InlineKeyboardButton(
                text="❌ إلغاء",
                callback_data="admin_list_media",
            ),
        )
        return builder.as_markup()

    # ── Media List Navigation ──────────────────────────────────────────────────
    @staticmethod
    def media_list_nav(page: int, total_pages: int) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        nav = []
        if page > 1:
            nav.append(InlineKeyboardButton(
                text="◀️ السابق", callback_data=f"adm_media_list:{page-1}"
            ))
        if page < total_pages:
            nav.append(InlineKeyboardButton(
                text="▶️ التالي", callback_data=f"adm_media_list:{page+1}"
            ))
        if nav:
            builder.row(*nav)
        builder.row(InlineKeyboardButton(text="🔙 القائمة الرئيسية", callback_data="admin_menu"))
        return builder.as_markup()

    # ── Surah Management ──────────────────────────────────────────────────────
    @staticmethod
    def surah_actions(surah_id: int) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="✏️ تعديل",
                callback_data=f"adm_edit_surah:{surah_id}",
            ),
            InlineKeyboardButton(
                text="🗑️ حذف",
                callback_data=f"adm_del_surah_confirm:{surah_id}",
            ),
        )
        builder.row(InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_surahs"))
        return builder.as_markup()

    # ── Sheikh Management ─────────────────────────────────────────────────────
    @staticmethod
    def sheikh_actions(sheikh_id: int) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="✏️ تعديل",
                callback_data=f"adm_edit_sheikh:{sheikh_id}",
            ),
            InlineKeyboardButton(
                text="🗑️ حذف",
                callback_data=f"adm_del_sheikh_confirm:{sheikh_id}",
            ),
        )
        builder.row(InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_sheikhs"))
        return builder.as_markup()

    # ── Album Management ──────────────────────────────────────────────────────
    @staticmethod
    def album_actions(album_id: int) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="✏️ تعديل",
                callback_data=f"adm_edit_album:{album_id}",
            ),
            InlineKeyboardButton(
                text="🗑️ حذف",
                callback_data=f"adm_del_album_confirm:{album_id}",
            ),
        )
        builder.row(InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_albums"))
        return builder.as_markup()

    # ── Surahs List (admin) ───────────────────────────────────────────────────
    @staticmethod
    def surahs_list(
        surahs: List[Dict], page: int, total_pages: int
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for s in surahs:
            builder.button(
                text=f"{s['number']}. {s['name_ar']}",
                callback_data=f"adm_view_surah:{s['id']}",
            )
        builder.adjust(2)

        nav = []
        if page > 1:
            nav.append(InlineKeyboardButton(
                text="◀️", callback_data=f"adm_surahs_page:{page-1}"
            ))
        if page < total_pages:
            nav.append(InlineKeyboardButton(
                text="▶️", callback_data=f"adm_surahs_page:{page+1}"
            ))
        if nav:
            builder.row(*nav)

        builder.row(
            InlineKeyboardButton(text="➕ إضافة سورة", callback_data="adm_add_surah"),
            InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_menu"),
        )
        return builder.as_markup()

    # ── Sheikhs List (admin) ──────────────────────────────────────────────────
    @staticmethod
    def sheikhs_list(sheikhs: List[Dict]) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for sh in sheikhs:
            builder.button(
                text=f"🎙️ {sh['name_ar']}",
                callback_data=f"adm_view_sheikh:{sh['id']}",
            )
        builder.adjust(1)
        builder.row(
            InlineKeyboardButton(text="➕ إضافة شيخ", callback_data="adm_add_sheikh"),
            InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_menu"),
        )
        return builder.as_markup()

    # ── Albums List (admin) ───────────────────────────────────────────────────
    @staticmethod
    def albums_list(albums: List[Dict]) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for a in albums:
            builder.button(
                text=f"🗂️ {a['name_ar']}",
                callback_data=f"adm_view_album:{a['id']}",
            )
        builder.adjust(1)
        builder.row(
            InlineKeyboardButton(text="➕ إضافة ألبوم", callback_data="adm_add_album"),
            InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_menu"),
        )
        return builder.as_markup()

    # ── Generic back to admin menu ─────────────────────────────────────────────
    @staticmethod
    def back_to_admin() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 القائمة الرئيسية للإدارة", callback_data="admin_menu")
        return builder.as_markup()

    # ── Cancel FSM ────────────────────────────────────────────────────────────
    @staticmethod
    def cancel(back_cb: str = "admin_menu") -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(text="❌ إلغاء", callback_data=back_cb)
        return builder.as_markup()
