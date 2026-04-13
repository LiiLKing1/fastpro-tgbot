import aiosqlite
from datetime import datetime

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
        await db.commit()

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

        async with db.execute("SELECT COUNT(*) FROM history WHERE status='failed'") as cursor:
            failed_downloads = (await cursor.fetchone())[0]

        async with db.execute("SELECT platform, COUNT(*) as count FROM history GROUP BY platform ORDER BY count DESC LIMIT 1") as cursor:
            row = await cursor.fetchone()
            most_used_platform = row[0] if row else "None"
            
        return {
            "total_users": total_users,
            "total_downloads": total_downloads,
            "failed_downloads": failed_downloads,
            "most_used_platform": most_used_platform
        }
