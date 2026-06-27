import os
from datetime import datetime
from dotenv import load_dotenv
from dominion_alpha.memory import get_conn, init_db

load_dotenv()

STARTING_CAPITAL = float(os.getenv("STARTING_CAPITAL", "1000.0"))
LIVE_TRADING = os.getenv("LIVE_TRADING", "false").lower() == "true"
TRAILING_STOP_PCT = float(os.getenv("TRAILING_STOP_PCT", "0.08"))

assert not LIVE_TRADING, "LIVE_TRADING must be false — real execution not implemented"


def get_capital() -> float:
    conn = get_conn()
    row = conn.execute("SELECT value FROM state WHERE key='capital'").fetchone()
    conn.close()
    if row:
        return float(row["value"])
    _set_capital(STARTING_CAPITAL)
    return STARTING_CAPITAL


def _set_capital(amount: float):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO state (key,value) VALUES ('capital',?)", (str(amount),))
    conn.commit()
    conn.close()


def get_open_positions():
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM trades WHERE action='BUY'
        AND token_address NOT IN (SELECT token_address FROM trades WHERE action='SELL')
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def paper_buy(token: dict, size_usd: float) -> dict:
    init_db()
    capital = get_capital()
    if size_usd > capital:
        return {"error": f"insufficient capital ${capital:.2f}"}
    price = token.get("price_usd") or 0
    if not price:
        return {"error": "price is 0"}
    new_capital = capital - size_usd
    _set_capital(new_capital)
    ts = datetime.utcnow().isoformat()
    notes = f"paper|{token.get('thesis', '')[:120]}"
    conn = get_conn()
    conn.execute(
        "INSERT INTO trades (token_address,symbol,action,price,size_usd,pnl,capital_after,timestamp,notes) VALUES (?,?,'BUY',?,?,0,?,?,?)",
        (token["address"], token.get("symbol", "?"), price, size_usd, new_capital, ts, notes)
    )
    conn.commit()
    conn.close()
    return {"status": "paper_buy", "symbol": token.get("symbol"), "price": price, "size_usd": size_usd, "capital_after": new_capital}


def paper_sell(token_address: str, current_price: float, reason: str = "signal") -> dict:
    conn = get_conn()
    buy = conn.execute(
        "SELECT * FROM trades WHERE token_address=? AND action='BUY' ORDER BY id DESC LIMIT 1",
        (token_address,)
    ).fetchone()
    conn.close()
    if not buy:
        return {"error": "no open position"}
    buy = dict(buy)
    entry = buy["price"]
    pct = (current_price - entry) / entry if entry else 0
    pnl = buy["size_usd"] * pct
    capital = get_capital()
    new_capital = capital + buy["size_usd"] + pnl
    _set_capital(new_capital)
    ts = datetime.utcnow().isoformat()
    sell_id = None
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO trades (token_address,symbol,action,price,size_usd,pnl,capital_after,timestamp,notes) VALUES (?,?,'SELL',?,?,?,?,?,?)",
        (token_address, buy["symbol"], current_price, buy["size_usd"], pnl, new_capital, ts, reason)
    )
    sell_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"status": "paper_sell", "id": sell_id, "symbol": buy["symbol"], "entry": entry, "exit": current_price, "pct": round(pct, 4), "pnl": round(pnl, 4), "capital_after": new_capital}


def partial_exit(token_address: str, current_price: float, pct: float = 0.5) -> dict:
    conn = get_conn()
    buy = conn.execute(
        "SELECT * FROM trades WHERE token_address=? AND action='BUY' ORDER BY id DESC LIMIT 1",
        (token_address,)
    ).fetchone()
    conn.close()
    if not buy:
        return {"error": "no open position"}
    buy = dict(buy)
    partial_usd = buy["size_usd"] * pct
    entry = buy["price"]
    trade_pct = (current_price - entry) / entry if entry else 0
    pnl = partial_usd * trade_pct
    capital = get_capital()
    new_capital = capital + partial_usd + pnl
    _set_capital(new_capital)
    ts = datetime.utcnow().isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT INTO trades (token_address,symbol,action,price,size_usd,pnl,capital_after,timestamp,notes) VALUES (?,?,'SELL',?,?,?,?,?,?)",
        (token_address, buy["symbol"], current_price, partial_usd, pnl, new_capital, ts, f"partial_exit_{pct:.0%}")
    )
    conn.commit()
    conn.close()
    return {"status": "partial_exit", "pct_exited": pct, "pnl": round(pnl, 4), "capital_after": new_capital}
