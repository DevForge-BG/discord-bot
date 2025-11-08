import aiosqlite
import asyncio

DB_PATH = "devforge.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    github_username TEXT,
    is_student INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    repo_url TEXT,
    status TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS repos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_full_name TEXT NOT NULL UNIQUE,
    channel_id INTEGER NOT NULL
);
"""

_db = None

async def get_db():
    global _db
    if _db is None:
        _db = await aiosqlite.connect(DB_PATH)
        await _db.executescript(SCHEMA)
        await _db.commit()
    return _db

async def close_db():
    global _db
    if _db is not None:
        await _db.close()
        _db = None

if __name__ == "__main__":
    asyncio.run(get_db())
