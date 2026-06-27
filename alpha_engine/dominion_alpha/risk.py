import os
from dotenv import load_dotenv

load_dotenv()

MAX_POSITION_PCT = float(os.getenv("MAX_POSITION_PCT", "0.05"))
MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", "5"))
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "0.10"))
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "0.30"))
MIN_SCORE = float(os.getenv("MIN_SCORE", "0.65"))
MIN_LIQUIDITY = float(os.getenv("MIN_LIQUIDITY", "25000"))


def check_entry(token: dict, score: float, capital: float, open_positions: int) -> dict:
    reasons = []
    approved = True
    if score < MIN_SCORE:
        approved = False
        reasons.append(f"score {score:.3f} below min {MIN_SCORE}")
    liq = token.get("liquidity") or 0
    if liq < MIN_LIQUIDITY:
        approved = False
        reasons.append(f"liquidity ${liq:,.0f} below min ${MIN_LIQUIDITY:,.0f}")
    if open_positions >= MAX_OPEN_POSITIONS:
        approved = False
        reasons.append(f"max positions ({MAX_OPEN_POSITIONS}) reached")
    size_usd = round(capital * MAX_POSITION_PCT, 2)
    return {
        "approved": approved,
        "size_usd": size_usd,
        "stop_loss_pct": STOP_LOSS_PCT,
        "take_profit_pct": TAKE_PROFIT_PCT,
        "reasons": reasons,
    }


def check_exit(entry_price: float, current_price: float) -> dict:
    if not entry_price:
        return {"exit": False, "reason": "no entry price"}
    pct = (current_price - entry_price) / entry_price
    if pct <= -STOP_LOSS_PCT:
        return {"exit": True, "reason": f"stop loss ({pct:.1%})"}
    if pct >= TAKE_PROFIT_PCT:
        return {"exit": True, "reason": f"take profit ({pct:.1%})"}
    return {"exit": False, "reason": f"holding ({pct:.1%})"}
