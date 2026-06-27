import sqlite3
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("ALPHA_DB_PATH", "alpha.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT UNIQUE,
            symbol TEXT,
            name TEXT,
            chain TEXT,
            price_usd REAL,
            volume_24h REAL,
            liquidity REAL,
            market_cap REAL,
            score REAL,
            first_seen TEXT,
            last_updated TEXT
        );
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_address TEXT,
            symbol TEXT,
            action TEXT,
            price REAL,
            size_usd REAL,
            pnl REAL,
            capital_after REAL,
            timestamp TEXT,
            notes TEXT
        );
        CREATE TABLE IF NOT EXISTS state (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    conn.commit()
    conn.close()
