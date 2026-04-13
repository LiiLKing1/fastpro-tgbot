import aiosqlite
from datetime import datetime
from typing import Optional, List

DB_PATH = "bot.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                joined_at TIMESTAMP,
                language TEXT DEFAULT 'uz'
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                url TEXT,
                platform TEXT,
                status TEXT,
                created_at TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        ''')
        # Majburiy obuna kanallari/botlar/guruhlar
        await db.execute('''
            CREATE TABLE IF NOT EXISTS forced_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                chat_title TEXT,
                chat_type TEXT DEFAULT 'channel',
                added_at TIMESTAMP
            )
        ''')
        await db.commit()

async def user_exists(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone() is not None

async def add_user(user_id: int, username: str = None, first_name: str = None, last_name: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            '''INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, joined_at)
               VALUES (?, ?, ?, ?, ?)''',
            (user_id, username, first_name, last_name, datetime.now())
        )
        await db.commit()

async def set_user_lang(user_id: int, lang: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))
        await db.commit()

async def get_user_lang(user_id: int) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT language FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 'uz'

async def log_download(user_id: int, url: str, platform: str, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            '''INSERT INTO history (user_id, url, platform, status, created_at)
               VALUES (?, ?, ?, ?, ?)''',
            (user_id, url, platform, status, datetime.now())
        )
        await db.commit()

async def get_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            total_users = (await cursor.fetchone())[0]
            
        async with db.execute("SELECT COUNT(*) FROM history WHERE status='success'") as cursor:
            total_downloads = (await cursor.fetchone())[0]

        async with db.execute("SELECT COUNT(*) FROM history WHERE status LIKE 'failed%'") as cursor:
            failed_downloads = (await cursor.fetchone())[0]

        async with db.execute("SELECT platform, COUNT(*) as count FROM history GROUP BY platform ORDER BY count DESC LIMIT 1") as cursor:
            row = await cursor.fetchone()
            most_used_platform = row[0] if row else "None"

        # Bugungi statistika
        today = datetime.now().strftime('%Y-%m-%d')
        async with db.execute("SELECT COUNT(*) FROM users WHERE DATE(joined_at) = ?", (today,)) as cursor:
            today_users = (await cursor.fetchone())[0]

        async with db.execute("SELECT COUNT(*) FROM history WHERE DATE(created_at) = ? AND status='success'", (today,)) as cursor:
            today_downloads = (await cursor.fetchone())[0]

        return {
            "total_users": total_users,
            "total_downloads": total_downloads,
            "failed_downloads": failed_downloads,
            "most_used_platform": most_used_platform,
            "today_users": today_users,
            "today_downloads": today_downloads
        }

async def get_all_user_ids() -> List[int]:
    """Barcha userlarning ID ro'yxatini qaytaradi (broadcast uchun)"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

# ===== Majburiy obuna (Forced Subscription) =====

async def add_forced_channel(chat_id: str, chat_title: str, chat_type: str = "channel"):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO forced_channels (chat_id, chat_title, chat_type, added_at) VALUES (?, ?, ?, ?)",
            (chat_id, chat_title, chat_type, datetime.now())
        )
        await db.commit()

async def remove_forced_channel(channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM forced_channels WHERE id = ?", (channel_id,))
        await db.commit()

async def get_forced_channels() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, chat_id, chat_title, chat_type FROM forced_channels") as cursor:
            rows = await cursor.fetchall()
            return [{"id": r[0], "chat_id": r[1], "chat_title": r[2], "chat_type": r[3]} for r in rows]
