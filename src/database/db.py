import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "smart_closet.db"

def get_conn():
    return sqlite3.connect(DB_PATH)

def create_tables():
    with get_conn() as conn:
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            user_id INTEGER PRIMARY KEY,
            cold_threshold INTEGER NOT NULL,
            hot_threshold INTEGER NOT NULL,
            rain_preference TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """)

        conn.commit()

if __name__ == "__main__":
    create_tables()
    print(f"Database initialized at: {DB_PATH}")
