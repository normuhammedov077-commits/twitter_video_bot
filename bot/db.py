import os
import sqlite3
from typing import Optional


DB_PATH = os.getenv("BOT_DB_PATH", os.path.expanduser("~/.twitter_bot_data.sqlite3"))


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS stats (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id TEXT,
              url TEXT,
              video_id TEXT,
              quality TEXT,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def record_stat(user_id: str, url: str, video_id: str, quality: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO stats (user_id, url, video_id, quality) VALUES (?, ?, ?, ?)",
            (user_id, url, video_id, quality),
        )
        conn.commit()
    finally:
        conn.close()


def recent_stats(limit: int = 10):
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            "SELECT user_id, url, video_id, quality, created_at FROM stats ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return cur.fetchall()
    finally:
        conn.close()



