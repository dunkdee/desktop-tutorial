import sqlite3
import os
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
            address TEXT UNIQUE, symbol TEXT, name TEXT, chain TEXT,
            price_usd REAL, volume_24h REAL, liquidity_usd REAL, market_cap REAL,
            score REAL, first_seen TEXT, last_updated TEXT
        );
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_address TEXT, symbol TEXT, action TEXT,
            price REAL, size_usd REAL, pnl REAL, capital_after REAL,
            timestamp TEXT, notes TEXT
        );
        CREATE TABLE IF NOT EXISTS state (
            key TEXT PRIMARY KEY, value TEXT
        );
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT, token_address TEXT, data TEXT, source TEXT
        );
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT, token_address TEXT, symbol TEXT, action TEXT,
            score REAL, confidence REAL, thesis TEXT, evidence TEXT, risks TEXT,
            advisor_votes TEXT, approved INTEGER, rejection_reason TEXT
        );
        CREATE TABLE IF NOT EXISTS performance_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT, capital REAL, win_rate REAL,
            profit_factor REAL, expectancy REAL, open_positions INTEGER, total_trades INTEGER
        );
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT, trade_id INTEGER,
            prediction TEXT, reality TEXT, lesson TEXT, advisor_errors TEXT
        );
        CREATE TABLE IF NOT EXISTS advisor_weights (
            name TEXT PRIMARY KEY, weight REAL, accuracy REAL, updated TEXT
        );
    """)
    conn.commit()
    conn.close()


def log_decision(data: dict):
    try:
        conn = get_conn()
        conn.execute("""
            INSERT INTO decisions
            (timestamp,token_address,symbol,action,score,confidence,thesis,evidence,risks,advisor_votes,approved,rejection_reason)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data.get("timestamp"), data.get("token_address"), data.get("symbol"),
            data.get("action"), data.get("score"), data.get("confidence"),
            data.get("thesis"), data.get("evidence"), data.get("risks"),
            data.get("advisor_votes"), data.get("approved"), data.get("rejection_reason"),
        ))
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_advisor_weights() -> dict:
    try:
        conn = get_conn()
        rows = conn.execute("SELECT name, weight FROM advisor_weights").fetchall()
        conn.close()
        return {r["name"]: r["weight"] for r in rows}
    except Exception:
        return {}


def get_memory_stats() -> dict:
    conn = get_conn()
    stats = {}
    for table in ["observations", "decisions", "lessons", "trades", "tokens", "performance_snapshots"]:
        try:
            row = conn.execute(f"SELECT COUNT(*) as c FROM {table}").fetchone()
            stats[table] = row["c"] if row else 0
        except Exception:
            stats[table] = 0
    conn.close()
    return stats
