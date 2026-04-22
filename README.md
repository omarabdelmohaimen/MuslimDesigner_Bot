# 🕌 بوت القرآن الكريم — Quran Media Bot

A complete, production-ready Telegram bot for delivering Quran media content (Chromas, Designs, Natural Landscapes) with a full Arabic admin panel built inside Telegram.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- Your Telegram user ID (from [@userinfobot](https://t.me/userinfobot))

### Installation

```bash
# 1. Navigate to bot directory
cd bot

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example ../.env
# Edit .env and fill in BOT_TOKEN and ADMIN_IDS

# 5. Run the bot
cd ..
python -m bot.main
```

### Environment Variables (`.env`)

```env
BOT_TOKEN=your_telegram_bot_token
ADMIN_IDS=123456789          # comma-separated for multiple admins
DB_PATH=bot/quran_bot.db     # SQLite database path
```

---

## 📐 Bot Structure

```
Main Menu
├── 🎬 كروما (Chromas)
│   ├── 📖 السور (All 114 Surahs → Media list)
│   └── 🎙️ المشايخ (Sheikhs → Media list)
│
├── 🎨 تصاميم (Designs)
│   ├── 📖 السور (All 114 Surahs → Media list)
│   └── 🎙️ المشايخ (Sheikhs → Media list)
│
└── 🌿 مناظر طبيعية (Natural Landscapes)
    └── 🗂️ Albums → Media list
```

---

## 🛡️ Admin Panel

Access via `/admin` command (admins only).

### Features:
| Feature | Description |
|---------|-------------|
| ➕ Add Media | 5-step wizard: category → subcategory → surah/sheikh → title → upload |
| 📋 List Media | Browse all uploaded files with pagination |
| ✏️ Edit Media | Edit titles and metadata |
| 🗑️ Delete Media | Delete with confirmation dialog |
| 📖 Manage Surahs | Add, edit, delete Quran surahs |
| 🎙️ Manage Sheikhs | Add, edit, delete sheikhs |
| 🗂️ Manage Albums | Add, edit, delete albums for landscapes |
| 📊 Statistics | Users, media, downloads, categories count |
| 📢 Broadcast | Send messages to all users |
| 🔍 Search | Search media by title |
| 📜 Logs | View last 15 admin actions |

### Adding Media (Step-by-Step):
1. `/admin` → **➕ إضافة محتوى**
2. Choose category (كروما / تصاميم / مناظر)
3. Choose subcategory (سور / مشايخ / طبيعة)
4. Select surah, sheikh, or album (or skip)
5. Enter title in English, then Arabic
6. Upload the file (video/photo/audio/document)

### Adding a Sheikh:
1. `/admin` → **🎙️ إدارة المشايخ**
2. **➕ إضافة شيخ**
3. Enter Arabic name → English name → bio (or /skip)

---

## 🗄️ Database Schema

| Table | Purpose |
|-------|---------|
| `users` | All bot users with admin flags |
| `categories` | Main categories (Chromas, Designs, Landscapes) |
| `subcategories` | Sub-sections (Surahs, Sheikhs, Nature) |
| `surahs` | All 114 Quranic surahs (pre-seeded) |
| `sheikhs` | Sheikhs added via admin panel |
| `albums` | Albums for Natural Landscapes section |
| `media_items` | Uploaded files with Telegram file_id |
| `download_logs` | Per-user download history |
| `admin_logs` | Admin action audit trail |
| `broadcast_logs` | Broadcast message history |

---

## 🚀 Production Deployment

### systemd Service (Linux VPS)

```bash
# Create service file
sudo nano /etc/systemd/system/quran-bot.service
```

```ini
[Unit]
Description=Quran Media Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/quran-bot
ExecStart=/opt/quran-bot/venv/bin/python -m bot.main
EnvironmentFile=/opt/quran-bot/.env
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable quran-bot
sudo systemctl start quran-bot

# Check status
sudo systemctl status quran-bot

# Live logs
sudo journalctl -u quran-bot -f
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY bot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "-m", "bot.main"]
```

```bash
docker build -t quran-bot .
docker run -d --name quran-bot \
  -e BOT_TOKEN=your_token \
  -e ADMIN_IDS=123456789 \
  -v $(pwd)/data:/app/bot \
  quran-bot
```

---

## 📁 Project Structure

```
bot/
├── main.py                   # Entry point
├── config.py                 # Configuration
├── requirements.txt          # Dependencies
├── .env.example              # Environment template
│
├── database/
│   ├── models.py             # Schema + 114 surahs seed data
│   └── db.py                 # Async CRUD operations
│
├── keyboards/
│   ├── user_kb.py            # User-facing keyboards
│   └── admin_kb.py           # Admin keyboards
│
├── middlewares/
│   ├── user_middleware.py    # Auto-register users
│   └── admin_middleware.py   # Block non-admins
│
├── handlers/
│   ├── user/
│   │   ├── start.py          # /start, /menu, home
│   │   ├── browse.py         # Category browsing
│   │   └── media.py          # Media detail + download
│   └── admin/
│       ├── menu.py           # Admin menu + stats
│       ├── media_upload.py   # Add media (FSM)
│       ├── media_manage.py   # List/edit/delete/search
│       ├── surah_manage.py   # Surah CRUD
│       ├── sheikh_manage.py  # Sheikh CRUD
│       ├── album_manage.py   # Album CRUD
│       └── broadcast.py      # Mass broadcast
│
└── utils/
    ├── states.py             # FSM state groups
    └── helpers.py            # Utility functions
```

---

## 🔧 Extending the Bot

### Add a new category:
```sql
INSERT INTO categories (name, name_ar, slug, icon) 
VALUES ('Recitations', 'تلاوات', 'recitations', '🎙️');
```

### Add a new sheikh via API (in admin panel):
Use `/admin` → 🎙️ إدارة المشايخ → ➕ إضافة شيخ

### Extend PAGE_SIZE:
Edit `config.py`:
```python
PAGE_SIZE: int = 20  # default is 10
```

---

## 📜 License

MIT License — Free to use, modify, and distribute.
