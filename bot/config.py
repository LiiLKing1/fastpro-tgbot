import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in environment variables.")

ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: List[int] = []
if ADMIN_IDS_STR:
    ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_STR.split(",") if x.strip().isdigit()]

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///bot.db")
TEMP_DIR = os.getenv("TEMP_DIR", "downloads")

# Ensure temp directory exists
os.makedirs(TEMP_DIR, exist_ok=True)
