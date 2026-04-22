"""
Database manager – all async CRUD operations via aiosqlite.
"""
from __future__ import annotations

import aiosqlite
import asyncio
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from bot.config import config
from bot.database.models import (
    CREATE_TABLES_SQL,
    SURAHS_DATA,
    CATEGORIES_DATA,
    SUBCATEGORIES_DATA,
)


class Database:
    """Singleton async database manager."""

    _instance: Optional["Database"] = None
    _db: Optional[aiosqlite.Connection] = None

    def __new__(cls) -> "Database":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def connect(self) -> None:
        """Open the SQLite connection and initialise schema."""
        self._db = await aiosqlite.connect(config.DB_PATH)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA foreign_keys = ON")
        await self._db.execute("PRAGMA journal_mode = WAL")
        await self._db.commit()
        await self._init_schema()

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    async def _init_schema(self) -> None:
        """Create tables and seed initial data."""
        # Execute all CREATE TABLE statements
        for statement in CREATE_TABLES_SQL.split(";"):
            stmt = statement.strip()
            if stmt:
                await self._db.execute(stmt)
        await self._db.commit()
        await self._seed_data()

    async def _seed_data(self) -> None:
        """Insert default data if tables are empty."""
        # Seed surahs
        async with self._db.execute("SELECT COUNT(*) FROM surahs") as cur:
            count = (await cur.fetchone())[0]
        if count == 0:
            await self._db.executemany(
                "INSERT OR IGNORE INTO surahs (number, name_ar, name_en, verses) VALUES (?,?,?,?)",
                SURAHS_DATA,
            )

        # Seed categories
        async with self._db.execute("SELECT COUNT(*) FROM categories") as cur:
            count = (await cur.fetchone())[0]
        if count == 0:
            await self._db.executemany(
                "INSERT OR IGNORE INTO categories (slug, name, name_ar, icon, sort_order) VALUES (?,?,?,?,?)",
                CATEGORIES_DATA,
            )

        # Seed subcategories
        async with self._db.execute("SELECT COUNT(*) FROM subcategories") as cur:
            count = (await cur.fetchone())[0]
        if count == 0:
            for cat_slug, sub_slug, name, name_ar, icon, order in SUBCATEGORIES_DATA:
                async with self._db.execute(
                    "SELECT id FROM categories WHERE slug=?", (cat_slug,)
                ) as cur:
                    row = await cur.fetchone()
                if row:
                    await self._db.execute(
                        """INSERT OR IGNORE INTO subcategories
                           (category_id, slug, name, name_ar, icon, sort_order)
                           VALUES (?,?,?,?,?,?)""",
                        (row["id"], sub_slug, name, name_ar, icon, order),
                    )

        await self._db.commit()

    # ─────────────────────────────────────────────────────────────────────────
    # Helper
    # ─────────────────────────────────────────────────────────────────────────
    async def fetchone(self, sql: str, params: tuple = ()) -> Optional[Dict]:
        async with self._db.execute(sql, params) as cur:
            row = await cur.fetchone()
        return dict(row) if row else None

    async def fetchall(self, sql: str, params: tuple = ()) -> List[Dict]:
        async with self._db.execute(sql, params) as cur:
            rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def execute(self, sql: str, params: tuple = ()) -> int:
        cur = await self._db.execute(sql, params)
        await self._db.commit()
        return cur.lastrowid

    # ─────────────────────────────────────────────────────────────────────────
    # Users
    # ─────────────────────────────────────────────────────────────────────────
    async def upsert_user(
        self,
        telegram_id: int,
        username: Optional[str],
        first_name: Optional[str],
        last_name: Optional[str],
    ) -> Dict:
        existing = await self.fetchone(
            "SELECT * FROM users WHERE telegram_id=?", (telegram_id,)
        )
        if existing:
            await self.execute(
                """UPDATE users SET username=?, first_name=?, last_name=?,
                   last_seen=datetime('now') WHERE telegram_id=?""",
                (username, first_name, last_name, telegram_id),
            )
            return await self.fetchone(
                "SELECT * FROM users WHERE telegram_id=?", (telegram_id,)
            )
        await self.execute(
            """INSERT INTO users (telegram_id, username, first_name, last_name)
               VALUES (?,?,?,?)""",
            (telegram_id, username, first_name, last_name),
        )
        return await self.fetchone(
            "SELECT * FROM users WHERE telegram_id=?", (telegram_id,)
        )

    async def get_user(self, telegram_id: int) -> Optional[Dict]:
        return await self.fetchone(
            "SELECT * FROM users WHERE telegram_id=?", (telegram_id,)
        )

    async def get_all_users(self) -> List[Dict]:
        return await self.fetchall("SELECT * FROM users WHERE is_blocked=0")

    async def get_user_count(self) -> int:
        row = await self.fetchone("SELECT COUNT(*) as cnt FROM users")
        return row["cnt"] if row else 0

    async def set_admin(self, telegram_id: int, is_admin: bool) -> None:
        await self.execute(
            "UPDATE users SET is_admin=? WHERE telegram_id=?",
            (1 if is_admin else 0, telegram_id),
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Categories
    # ─────────────────────────────────────────────────────────────────────────
    async def get_categories(self) -> List[Dict]:
        return await self.fetchall(
            "SELECT * FROM categories WHERE is_active=1 ORDER BY sort_order"
        )

    async def get_category(self, cat_id: int) -> Optional[Dict]:
        return await self.fetchone("SELECT * FROM categories WHERE id=?", (cat_id,))

    async def get_category_by_slug(self, slug: str) -> Optional[Dict]:
        return await self.fetchone(
            "SELECT * FROM categories WHERE slug=?", (slug,)
        )

    async def add_category(self, name: str, name_ar: str, slug: str, icon: str) -> int:
        return await self.execute(
            "INSERT INTO categories (name, name_ar, slug, icon) VALUES (?,?,?,?)",
            (name, name_ar, slug, icon),
        )

    async def update_category(self, cat_id: int, **kwargs) -> None:
        fields = ", ".join(f"{k}=?" for k in kwargs)
        await self.execute(
            f"UPDATE categories SET {fields} WHERE id=?",
            (*kwargs.values(), cat_id),
        )

    async def delete_category(self, cat_id: int) -> None:
        await self.execute("DELETE FROM categories WHERE id=?", (cat_id,))

    # ─────────────────────────────────────────────────────────────────────────
    # Subcategories
    # ─────────────────────────────────────────────────────────────────────────
    async def get_subcategories(self, category_id: int) -> List[Dict]:
        return await self.fetchall(
            """SELECT * FROM subcategories
               WHERE category_id=? AND is_active=1
               ORDER BY sort_order""",
            (category_id,),
        )

    async def get_subcategory(self, sub_id: int) -> Optional[Dict]:
        return await self.fetchone(
            "SELECT * FROM subcategories WHERE id=?", (sub_id,)
        )

    async def add_subcategory(
        self, category_id: int, name: str, name_ar: str, slug: str, icon: str
    ) -> int:
        return await self.execute(
            """INSERT INTO subcategories (category_id, name, name_ar, slug, icon)
               VALUES (?,?,?,?,?)""",
            (category_id, name, name_ar, slug, icon),
        )

    async def delete_subcategory(self, sub_id: int) -> None:
        await self.execute("DELETE FROM subcategories WHERE id=?", (sub_id,))

    # ─────────────────────────────────────────────────────────────────────────
    # Surahs
    # ─────────────────────────────────────────────────────────────────────────
    async def get_surahs(self, page: int = 1) -> List[Dict]:
        offset = (page - 1) * config.PAGE_SIZE
        return await self.fetchall(
            "SELECT * FROM surahs WHERE is_active=1 ORDER BY number LIMIT ? OFFSET ?",
            (config.PAGE_SIZE, offset),
        )

    async def get_all_surahs(self) -> List[Dict]:
        return await self.fetchall(
            "SELECT * FROM surahs WHERE is_active=1 ORDER BY number"
        )

    async def get_surah(self, surah_id: int) -> Optional[Dict]:
        return await self.fetchone("SELECT * FROM surahs WHERE id=?", (surah_id,))

    async def get_surah_count(self) -> int:
        row = await self.fetchone("SELECT COUNT(*) as cnt FROM surahs WHERE is_active=1")
        return row["cnt"] if row else 0

    async def add_surah(self, number: int, name_ar: str, name_en: str, verses: int) -> int:
        return await self.execute(
            "INSERT OR REPLACE INTO surahs (number, name_ar, name_en, verses) VALUES (?,?,?,?)",
            (number, name_ar, name_en, verses),
        )

    async def update_surah(self, surah_id: int, **kwargs) -> None:
        fields = ", ".join(f"{k}=?" for k in kwargs)
        await self.execute(
            f"UPDATE surahs SET {fields} WHERE id=?",
            (*kwargs.values(), surah_id),
        )

    async def delete_surah(self, surah_id: int) -> None:
        await self.execute("DELETE FROM surahs WHERE id=?", (surah_id,))

    # ─────────────────────────────────────────────────────────────────────────
    # Sheikhs
    # ─────────────────────────────────────────────────────────────────────────
    async def get_sheikhs(self) -> List[Dict]:
        return await self.fetchall(
            "SELECT * FROM sheikhs WHERE is_active=1 ORDER BY name_ar"
        )

    async def get_sheikh(self, sheikh_id: int) -> Optional[Dict]:
        return await self.fetchone("SELECT * FROM sheikhs WHERE id=?", (sheikh_id,))

    async def add_sheikh(self, name_ar: str, name_en: str, bio: str = "") -> int:
        return await self.execute(
            "INSERT INTO sheikhs (name_ar, name_en, bio) VALUES (?,?,?)",
            (name_ar, name_en, bio),
        )

    async def update_sheikh(self, sheikh_id: int, **kwargs) -> None:
        fields = ", ".join(f"{k}=?" for k in kwargs)
        await self.execute(
            f"UPDATE sheikhs SET {fields} WHERE id=?",
            (*kwargs.values(), sheikh_id),
        )

    async def delete_sheikh(self, sheikh_id: int) -> None:
        await self.execute("DELETE FROM sheikhs WHERE id=?", (sheikh_id,))

    # ─────────────────────────────────────────────────────────────────────────
    # Albums
    # ─────────────────────────────────────────────────────────────────────────
    async def get_albums(self, subcategory_id: Optional[int] = None) -> List[Dict]:
        if subcategory_id:
            return await self.fetchall(
                """SELECT * FROM albums WHERE subcategory_id=? AND is_active=1
                   ORDER BY sort_order, name""",
                (subcategory_id,),
            )
        return await self.fetchall(
            "SELECT * FROM albums WHERE is_active=1 ORDER BY sort_order, name"
        )

    async def get_album(self, album_id: int) -> Optional[Dict]:
        return await self.fetchone("SELECT * FROM albums WHERE id=?", (album_id,))

    async def add_album(
        self, name: str, name_ar: str, subcategory_id: Optional[int] = None,
        description: str = ""
    ) -> int:
        return await self.execute(
            """INSERT INTO albums (name, name_ar, subcategory_id, description)
               VALUES (?,?,?,?)""",
            (name, name_ar, subcategory_id, description),
        )

    async def update_album(self, album_id: int, **kwargs) -> None:
        fields = ", ".join(f"{k}=?" for k in kwargs)
        await self.execute(
            f"UPDATE albums SET {fields} WHERE id=?",
            (*kwargs.values(), album_id),
        )

    async def delete_album(self, album_id: int) -> None:
        await self.execute("DELETE FROM albums WHERE id=?", (album_id,))

    # ─────────────────────────────────────────────────────────────────────────
    # Media Items
    # ─────────────────────────────────────────────────────────────────────────
    async def get_media(
        self,
        category_id: Optional[int] = None,
        subcategory_id: Optional[int] = None,
        surah_id: Optional[int] = None,
        sheikh_id: Optional[int] = None,
        album_id: Optional[int] = None,
        page: int = 1,
        search: Optional[str] = None,
    ) -> List[Dict]:
        conditions = ["m.is_active=1"]
        params: list = []

        if category_id:
            conditions.append("m.category_id=?")
            params.append(category_id)
        if subcategory_id:
            conditions.append("m.subcategory_id=?")
            params.append(subcategory_id)
        if surah_id:
            conditions.append("m.surah_id=?")
            params.append(surah_id)
        if sheikh_id:
            conditions.append("m.sheikh_id=?")
            params.append(sheikh_id)
        if album_id:
            conditions.append("m.album_id=?")
            params.append(album_id)
        if search:
            conditions.append("(m.title LIKE ? OR m.title_ar LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])

        where = " AND ".join(conditions)
        offset = (page - 1) * config.PAGE_SIZE
        params.extend([config.PAGE_SIZE, offset])

        return await self.fetchall(
            f"""SELECT m.*,
                       s.name_ar  AS surah_name_ar,
                       s.number   AS surah_number,
                       sh.name_ar AS sheikh_name_ar,
                       a.name_ar  AS album_name_ar
                FROM media_items m
                LEFT JOIN surahs   s  ON m.surah_id  = s.id
                LEFT JOIN sheikhs  sh ON m.sheikh_id = sh.id
                LEFT JOIN albums   a  ON m.album_id  = a.id
                WHERE {where}
                ORDER BY m.created_at DESC
                LIMIT ? OFFSET ?""",
            tuple(params),
        )

    async def count_media(
        self,
        category_id: Optional[int] = None,
        subcategory_id: Optional[int] = None,
        surah_id: Optional[int] = None,
        sheikh_id: Optional[int] = None,
        album_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> int:
        conditions = ["is_active=1"]
        params: list = []
        if category_id:
            conditions.append("category_id=?")
            params.append(category_id)
        if subcategory_id:
            conditions.append("subcategory_id=?")
            params.append(subcategory_id)
        if surah_id:
            conditions.append("surah_id=?")
            params.append(surah_id)
        if sheikh_id:
            conditions.append("sheikh_id=?")
            params.append(sheikh_id)
        if album_id:
            conditions.append("album_id=?")
            params.append(album_id)
        if search:
            conditions.append("(title LIKE ? OR title_ar LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])

        where = " AND ".join(conditions)
        row = await self.fetchone(
            f"SELECT COUNT(*) as cnt FROM media_items WHERE {where}", tuple(params)
        )
        return row["cnt"] if row else 0

    async def get_media_item(self, media_id: int) -> Optional[Dict]:
        return await self.fetchone(
            """SELECT m.*,
                      s.name_ar  AS surah_name_ar,
                      s.number   AS surah_number,
                      sh.name_ar AS sheikh_name_ar,
                      a.name_ar  AS album_name_ar,
                      c.name_ar  AS category_name_ar
               FROM media_items m
               LEFT JOIN surahs      s  ON m.surah_id   = s.id
               LEFT JOIN sheikhs     sh ON m.sheikh_id  = sh.id
               LEFT JOIN albums      a  ON m.album_id   = a.id
               LEFT JOIN categories  c  ON m.category_id= c.id
               WHERE m.id=?""",
            (media_id,),
        )

    async def add_media(
        self,
        category_id: int,
        title: str,
        media_type: str,
        file_id: str,
        file_unique_id: str = "",
        subcategory_id: Optional[int] = None,
        surah_id: Optional[int] = None,
        sheikh_id: Optional[int] = None,
        album_id: Optional[int] = None,
        title_ar: str = "",
        description: str = "",
        file_size: int = 0,
        duration: int = 0,
        thumbnail_id: str = "",
    ) -> int:
        return await self.execute(
            """INSERT INTO media_items
               (category_id, subcategory_id, surah_id, sheikh_id, album_id,
                title, title_ar, description, media_type, file_id, file_unique_id,
                file_size, duration, thumbnail_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                category_id, subcategory_id, surah_id, sheikh_id, album_id,
                title, title_ar, description, media_type, file_id, file_unique_id,
                file_size, duration, thumbnail_id,
            ),
        )

    async def update_media(self, media_id: int, **kwargs) -> None:
        kwargs["updated_at"] = datetime.now().isoformat()
        fields = ", ".join(f"{k}=?" for k in kwargs)
        await self.execute(
            f"UPDATE media_items SET {fields} WHERE id=?",
            (*kwargs.values(), media_id),
        )

    async def delete_media(self, media_id: int) -> None:
        await self.execute("DELETE FROM media_items WHERE id=?", (media_id,))

    async def increment_download(self, media_id: int) -> None:
        await self.execute(
            "UPDATE media_items SET download_count=download_count+1 WHERE id=?",
            (media_id,),
        )

    async def get_media_count(self) -> int:
        row = await self.fetchone(
            "SELECT COUNT(*) as cnt FROM media_items WHERE is_active=1"
        )
        return row["cnt"] if row else 0

    async def get_total_downloads(self) -> int:
        row = await self.fetchone(
            "SELECT COALESCE(SUM(download_count),0) as total FROM media_items"
        )
        return row["total"] if row else 0

    # ─────────────────────────────────────────────────────────────────────────
    # Download Logs
    # ─────────────────────────────────────────────────────────────────────────
    async def log_download(self, user_id: int, media_id: int) -> None:
        db_user = await self.fetchone("SELECT id FROM users WHERE telegram_id=?", (user_id,))
        if db_user:
            await self.execute(
                "INSERT INTO download_logs (user_id, media_id) VALUES (?,?)",
                (db_user["id"], media_id),
            )
        await self.increment_download(media_id)

    # ─────────────────────────────────────────────────────────────────────────
    # Admin Logs
    # ─────────────────────────────────────────────────────────────────────────
    async def log_admin_action(
        self,
        admin_telegram_id: int,
        action: str,
        target_type: str = "",
        target_id: int = 0,
        details: str = "",
    ) -> None:
        admin = await self.fetchone(
            "SELECT id FROM users WHERE telegram_id=?", (admin_telegram_id,)
        )
        if admin:
            await self.execute(
                """INSERT INTO admin_logs (admin_id, action, target_type, target_id, details)
                   VALUES (?,?,?,?,?)""",
                (admin["id"], action, target_type, target_id, details),
            )

    async def get_admin_logs(self, limit: int = 20) -> List[Dict]:
        return await self.fetchall(
            """SELECT al.*, u.username, u.first_name
               FROM admin_logs al
               JOIN users u ON al.admin_id = u.id
               ORDER BY al.created_at DESC
               LIMIT ?""",
            (limit,),
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Stats
    # ─────────────────────────────────────────────────────────────────────────
    async def get_stats(self) -> Dict:
        user_count = await self.get_user_count()
        media_count = await self.get_media_count()
        total_downloads = await self.get_total_downloads()

        row_cats = await self.fetchone("SELECT COUNT(*) as cnt FROM categories WHERE is_active=1")
        cat_count = row_cats["cnt"] if row_cats else 0

        row_subs = await self.fetchone("SELECT COUNT(*) as cnt FROM subcategories WHERE is_active=1")
        sub_count = row_subs["cnt"] if row_subs else 0

        row_surahs = await self.fetchone("SELECT COUNT(*) as cnt FROM surahs WHERE is_active=1")
        surah_count = row_surahs["cnt"] if row_surahs else 0

        row_sheikhs = await self.fetchone("SELECT COUNT(*) as cnt FROM sheikhs WHERE is_active=1")
        sheikh_count = row_sheikhs["cnt"] if row_sheikhs else 0

        row_albums = await self.fetchone("SELECT COUNT(*) as cnt FROM albums WHERE is_active=1")
        album_count = row_albums["cnt"] if row_albums else 0

        return {
            "users": user_count,
            "media": media_count,
            "categories": cat_count,
            "subcategories": sub_count,
            "surahs": surah_count,
            "sheikhs": sheikh_count,
            "albums": album_count,
            "downloads": total_downloads,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Search
    # ─────────────────────────────────────────────────────────────────────────
    async def search_media(self, query: str, page: int = 1) -> List[Dict]:
        return await self.get_media(search=query, page=page)

    async def search_media_count(self, query: str) -> int:
        return await self.count_media(search=query)


# Global singleton
db = Database()
