"""
Database models and schema definitions using SQLite via aiosqlite.
All tables are created here with proper indexes and constraints.
"""
import aiosqlite
from typing import Optional, List, Dict, Any
from datetime import datetime


CREATE_TABLES_SQL = """
-- ─── Users ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id     INTEGER UNIQUE NOT NULL,
    username        TEXT,
    first_name      TEXT,
    last_name       TEXT,
    is_admin        INTEGER DEFAULT 0,
    is_blocked      INTEGER DEFAULT 0,
    joined_at       TEXT DEFAULT (datetime('now')),
    last_seen       TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);

-- ─── Categories ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    name_ar     TEXT NOT NULL,
    slug        TEXT UNIQUE NOT NULL,
    icon        TEXT DEFAULT '📁',
    sort_order  INTEGER DEFAULT 0,
    is_active   INTEGER DEFAULT 1,
    created_at  TEXT DEFAULT (datetime('now'))
);

-- ─── Subcategories ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS subcategories (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id     INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    name_ar         TEXT NOT NULL,
    slug            TEXT NOT NULL,
    icon            TEXT DEFAULT '📂',
    sort_order      INTEGER DEFAULT 0,
    is_active       INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(category_id, slug)
);
CREATE INDEX IF NOT EXISTS idx_subcategories_category ON subcategories(category_id);

-- ─── Surahs ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS surahs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    number      INTEGER UNIQUE NOT NULL,
    name_ar     TEXT NOT NULL,
    name_en     TEXT NOT NULL,
    verses      INTEGER DEFAULT 0,
    is_active   INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_surahs_number ON surahs(number);

-- ─── Sheikhs ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sheikhs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name_ar     TEXT NOT NULL,
    name_en     TEXT NOT NULL,
    bio         TEXT,
    is_active   INTEGER DEFAULT 1,
    created_at  TEXT DEFAULT (datetime('now'))
);

-- ─── Albums (for Natural Landscapes) ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS albums (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    subcategory_id  INTEGER REFERENCES subcategories(id) ON DELETE SET NULL,
    name            TEXT NOT NULL,
    name_ar         TEXT NOT NULL,
    description     TEXT,
    cover_file_id   TEXT,
    is_active       INTEGER DEFAULT 1,
    sort_order      INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- ─── Media Items ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS media_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id     INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    subcategory_id  INTEGER REFERENCES subcategories(id) ON DELETE SET NULL,
    surah_id        INTEGER REFERENCES surahs(id) ON DELETE SET NULL,
    sheikh_id       INTEGER REFERENCES sheikhs(id) ON DELETE SET NULL,
    album_id        INTEGER REFERENCES albums(id) ON DELETE SET NULL,
    title           TEXT NOT NULL,
    title_ar        TEXT,
    description     TEXT,
    media_type      TEXT NOT NULL,   -- video, photo, document, audio
    file_id         TEXT NOT NULL,   -- Telegram file_id
    file_unique_id  TEXT,
    file_size       INTEGER,
    duration        INTEGER,         -- seconds (for video/audio)
    thumbnail_id    TEXT,            -- Telegram file_id of thumbnail
    download_count  INTEGER DEFAULT 0,
    is_active       INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_media_category ON media_items(category_id);
CREATE INDEX IF NOT EXISTS idx_media_subcategory ON media_items(subcategory_id);
CREATE INDEX IF NOT EXISTS idx_media_surah ON media_items(surah_id);
CREATE INDEX IF NOT EXISTS idx_media_sheikh ON media_items(sheikh_id);
CREATE INDEX IF NOT EXISTS idx_media_album ON media_items(album_id);

-- ─── Download Logs ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS download_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    media_id    INTEGER NOT NULL REFERENCES media_items(id) ON DELETE CASCADE,
    downloaded_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_downloads_user ON download_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_downloads_media ON download_logs(media_id);

-- ─── Admin Logs ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS admin_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action      TEXT NOT NULL,
    target_type TEXT,
    target_id   INTEGER,
    details     TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_admin_logs_admin ON admin_logs(admin_id);

-- ─── Broadcast Logs ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS broadcast_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message_text    TEXT NOT NULL,
    total_sent      INTEGER DEFAULT 0,
    total_failed    INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now'))
);
"""

# ─── 114 Surahs of the Holy Quran ─────────────────────────────────────────────
SURAHS_DATA = [
    (1, "الفاتحة", "Al-Fatihah", 7),
    (2, "البقرة", "Al-Baqarah", 286),
    (3, "آل عمران", "Aal-Imran", 200),
    (4, "النساء", "An-Nisa", 176),
    (5, "المائدة", "Al-Maidah", 120),
    (6, "الأنعام", "Al-Anam", 165),
    (7, "الأعراف", "Al-Araf", 206),
    (8, "الأنفال", "Al-Anfal", 75),
    (9, "التوبة", "At-Tawbah", 129),
    (10, "يونس", "Yunus", 109),
    (11, "هود", "Hud", 123),
    (12, "يوسف", "Yusuf", 111),
    (13, "الرعد", "Ar-Ra'd", 43),
    (14, "إبراهيم", "Ibrahim", 52),
    (15, "الحجر", "Al-Hijr", 99),
    (16, "النحل", "An-Nahl", 128),
    (17, "الإسراء", "Al-Isra", 111),
    (18, "الكهف", "Al-Kahf", 110),
    (19, "مريم", "Maryam", 98),
    (20, "طه", "Ta-Ha", 135),
    (21, "الأنبياء", "Al-Anbiya", 112),
    (22, "الحج", "Al-Hajj", 78),
    (23, "المؤمنون", "Al-Muminun", 118),
    (24, "النور", "An-Nur", 64),
    (25, "الفرقان", "Al-Furqan", 77),
    (26, "الشعراء", "Ash-Shu'ara", 227),
    (27, "النمل", "An-Naml", 93),
    (28, "القصص", "Al-Qasas", 88),
    (29, "العنكبوت", "Al-Ankabut", 69),
    (30, "الروم", "Ar-Rum", 60),
    (31, "لقمان", "Luqman", 34),
    (32, "السجدة", "As-Sajdah", 30),
    (33, "الأحزاب", "Al-Ahzab", 73),
    (34, "سبأ", "Saba", 54),
    (35, "فاطر", "Fatir", 45),
    (36, "يس", "Ya-Sin", 83),
    (37, "الصافات", "As-Saffat", 182),
    (38, "ص", "Sad", 88),
    (39, "الزمر", "Az-Zumar", 75),
    (40, "غافر", "Ghafir", 85),
    (41, "فصلت", "Fussilat", 54),
    (42, "الشورى", "Ash-Shura", 53),
    (43, "الزخرف", "Az-Zukhruf", 89),
    (44, "الدخان", "Ad-Dukhan", 59),
    (45, "الجاثية", "Al-Jathiyah", 37),
    (46, "الأحقاف", "Al-Ahqaf", 35),
    (47, "محمد", "Muhammad", 38),
    (48, "الفتح", "Al-Fath", 29),
    (49, "الحجرات", "Al-Hujurat", 18),
    (50, "ق", "Qaf", 45),
    (51, "الذاريات", "Adh-Dhariyat", 60),
    (52, "الطور", "At-Tur", 49),
    (53, "النجم", "An-Najm", 62),
    (54, "القمر", "Al-Qamar", 55),
    (55, "الرحمن", "Ar-Rahman", 78),
    (56, "الواقعة", "Al-Waqi'ah", 96),
    (57, "الحديد", "Al-Hadid", 29),
    (58, "المجادلة", "Al-Mujadila", 22),
    (59, "الحشر", "Al-Hashr", 24),
    (60, "الممتحنة", "Al-Mumtahanah", 13),
    (61, "الصف", "As-Saf", 14),
    (62, "الجمعة", "Al-Jumu'ah", 11),
    (63, "المنافقون", "Al-Munafiqun", 11),
    (64, "التغابن", "At-Taghabun", 18),
    (65, "الطلاق", "At-Talaq", 12),
    (66, "التحريم", "At-Tahrim", 12),
    (67, "الملك", "Al-Mulk", 30),
    (68, "القلم", "Al-Qalam", 52),
    (69, "الحاقة", "Al-Haqqah", 52),
    (70, "المعارج", "Al-Ma'arij", 44),
    (71, "نوح", "Nuh", 28),
    (72, "الجن", "Al-Jinn", 28),
    (73, "المزمل", "Al-Muzzammil", 20),
    (74, "المدثر", "Al-Muddaththir", 56),
    (75, "القيامة", "Al-Qiyamah", 40),
    (76, "الإنسان", "Al-Insan", 31),
    (77, "المرسلات", "Al-Mursalat", 50),
    (78, "النبأ", "An-Naba", 40),
    (79, "النازعات", "An-Nazi'at", 46),
    (80, "عبس", "Abasa", 42),
    (81, "التكوير", "At-Takwir", 29),
    (82, "الانفطار", "Al-Infitar", 19),
    (83, "المطففين", "Al-Mutaffifin", 36),
    (84, "الانشقاق", "Al-Inshiqaq", 25),
    (85, "البروج", "Al-Buruj", 22),
    (86, "الطارق", "At-Tariq", 17),
    (87, "الأعلى", "Al-Ala", 19),
    (88, "الغاشية", "Al-Ghashiyah", 26),
    (89, "الفجر", "Al-Fajr", 30),
    (90, "البلد", "Al-Balad", 20),
    (91, "الشمس", "Ash-Shams", 15),
    (92, "الليل", "Al-Layl", 21),
    (93, "الضحى", "Ad-Duha", 11),
    (94, "الشرح", "Ash-Sharh", 8),
    (95, "التين", "At-Tin", 8),
    (96, "العلق", "Al-Alaq", 19),
    (97, "القدر", "Al-Qadr", 5),
    (98, "البينة", "Al-Bayyinah", 8),
    (99, "الزلزلة", "Az-Zalzalah", 8),
    (100, "العاديات", "Al-Adiyat", 11),
    (101, "القارعة", "Al-Qari'ah", 11),
    (102, "التكاثر", "At-Takathur", 8),
    (103, "العصر", "Al-Asr", 3),
    (104, "الهمزة", "Al-Humazah", 9),
    (105, "الفيل", "Al-Fil", 5),
    (106, "قريش", "Quraysh", 4),
    (107, "الماعون", "Al-Ma'un", 7),
    (108, "الكوثر", "Al-Kawthar", 3),
    (109, "الكافرون", "Al-Kafirun", 6),
    (110, "النصر", "An-Nasr", 3),
    (111, "المسد", "Al-Masad", 5),
    (112, "الإخلاص", "Al-Ikhlas", 4),
    (113, "الفلق", "Al-Falaq", 5),
    (114, "الناس", "An-Nas", 6),
]

# ─── Default Categories ────────────────────────────────────────────────────────
CATEGORIES_DATA = [
    ("chromas", "كروما", "كروما", "🎬", 1),
    ("designs", "تصاميم", "تصاميم", "🎨", 2),
    ("landscapes", "مناظر طبيعية", "مناظر طبيعية", "🌿", 3),
]

# ─── Default Subcategories ────────────────────────────────────────────────────
SUBCATEGORIES_DATA = [
    # Chromas subcategories
    ("chromas", "surahs", "السور", "السور", "📖", 1),
    ("chromas", "sheikhs", "المشايخ", "المشايخ", "🎙️", 2),
    # Designs subcategories
    ("designs", "surahs", "السور", "السور", "📖", 1),
    ("designs", "sheikhs", "المشايخ", "المشايخ", "🎙️", 2),
    # Natural Landscapes
    ("landscapes", "nature", "الطبيعة", "الطبيعة", "🌿", 1),
]
