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
    hot_min INTEGER,
    hot_max INTEGER,
    moderate_min INTEGER,
    moderate_max INTEGER,
    cold_min INTEGER,
    cold_max INTEGER,
    hot_clothing TEXT,
    moderate_clothing TEXT,
    cold_clothing TEXT,
    extreme_cold_clothing TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            user_id INTEGER PRIMARY KEY,
            location TEXT DEFAULT 'Arlington,TX,US',
            temperature_unit TEXT DEFAULT 'fahrenheit',
            led_hot_color TEXT DEFAULT 'red',
            led_moderate_color TEXT DEFAULT 'yellow',
            led_cold_color TEXT DEFAULT 'blue',
            led_extreme_cold_color TEXT DEFAULT 'purple',
            theme TEXT DEFAULT 'dark',
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS closets (
            closet_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            closet_name TEXT DEFAULT 'Closet 1',
            wled_ip TEXT DEFAULT '192.168.1.165',
            status TEXT DEFAULT 'offline',
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """)

        conn.commit()

if __name__ == "__main__":
    create_tables()
    print(f"Database initialized at: {DB_PATH}")