import logging
from datetime import datetime
from dominion_alpha.memory import get_conn

logger = logging.getLogger("alpha.learning")

DEFAULT_WEIGHTS = {
    "liquidity": 1.5, "volume": 1.2, "momentum": 1.3, "market_cap": 1.0,
    "whale": 1.2, "token_health": 1.4, "holder_growth": 1.1,
    "social_sentiment": 0.8, "news": 0.7, "risk": 1.5,
    "execution": 1.0, "skeptic": 1.6,
}
WEIGHT_MIN, WEIGHT_MAX = 0.3, 3.0
LEARN_WIN, LEARN_LOSS = 0.02, 0.01


def _ensure_weights():
    conn = get_conn()
    existing = {r["name"] for r in conn.execute("SELECT name FROM advisor_weights").fetchall()}
    ts = datetime.utcnow().isoformat()
    for name, w in DEFAULT_WEIGHTS.items():
        if name not in existing:
            conn.execute(
                "INSERT OR IGNORE INTO advisor_weights (name,weight,accuracy,updated) VALUES (?,?,?,?)",
                (name, w, 0.5, ts)
            )
    conn.commit()
    conn.close()


def post_trade_analysis(sell_trade_id: int):
    _ensure_weights()
    conn = get_conn()
    trade = conn.execute("SELECT * FROM trades WHERE id=? AND action='SELL'", (sell_trade_id,)).fetchone()
    if not trade:
        conn.close()
        return
    trade = dict(trade)
    was_win = float(trade.get("pnl") or 0) > 0
    symbol = trade.get("symbol", "?")
    decision = conn.execute(
        "SELECT * FROM decisions WHERE token_address=? AND action='BUY' ORDER BY id DESC LIMIT 1",
        (trade["token_address"],)
    ).fetchone()
    conn.close()

    advisor_errors = {}
    if decision:
        decision = dict(decision)
        try:
            votes_raw = decision.get("advisor_votes") or "{}"
            votes = eval(votes_raw) if votes_raw.startswith("{") else {}
        except Exception:
            votes = {}
        for name, vote in votes.items():
            if isinstance(vote, dict):
                predicted_win = vote.get("rec", "WATCH") == "BUY"
                correct = predicted_win == was_win
                advisor_errors[name] = {"predicted": vote.get("rec"), "correct": correct}
                _adjust_weight(name, correct)

    lesson = f"{'WIN' if was_win else 'LOSS'} ${float(trade.get('pnl',0)):.2f} on {symbol}"
    conn = get_conn()
    conn.execute(
        "INSERT INTO lessons (timestamp,trade_id,prediction,reality,lesson,advisor_errors) VALUES (?,?,?,?,?,?)",
        (datetime.utcnow().isoformat(), sell_trade_id, "BUY", "WIN" if was_win else "LOSS", lesson, str(advisor_errors))
    )
    conn.commit()
    conn.close()
    logger.info(f"learning: {lesson}")


def _adjust_weight(name: str, was_correct: bool):
    conn = get_conn()
    row = conn.execute("SELECT weight, accuracy FROM advisor_weights WHERE name=?", (name,)).fetchone()
    if not row:
        conn.close()
        return
    w = float(row["weight"])
    acc = float(row["accuracy"] or 0.5)
    if was_correct:
        w = min(w + LEARN_WIN, WEIGHT_MAX)
        acc = acc * 0.9 + 0.1
    else:
        w = max(w - LEARN_LOSS, WEIGHT_MIN)
        acc = acc * 0.9
    conn.execute(
        "UPDATE advisor_weights SET weight=?, accuracy=?, updated=? WHERE name=?",
        (round(w, 4), round(acc, 4), datetime.utcnow().isoformat(), name)
    )
    conn.commit()
    conn.close()


def get_lessons(limit: int = 10) -> list:
    try:
        conn = get_conn()
        rows = conn.execute("SELECT * FROM lessons ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_current_weights() -> dict:
    _ensure_weights()
    conn = get_conn()
    rows = conn.execute("SELECT name, weight, accuracy FROM advisor_weights").fetchall()
    conn.close()
    return {r["name"]: {"weight": round(r["weight"], 4), "accuracy": round(r["accuracy"] or 0, 4)} for r in rows}
