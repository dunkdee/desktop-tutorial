import os
from dotenv import load_dotenv

load_dotenv()

MAX_POSITION_PCT = float(os.getenv("MAX_POSITION_PCT", "0.05"))
MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", "5"))
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "0.10"))
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "0.30"))
TRAILING_STOP_PCT = float(os.getenv("TRAILING_STOP_PCT", "0.08"))
MIN_SCORE = float(os.getenv("MIN_SCORE", "0.82"))
MIN_LIQUIDITY = float(os.getenv("MIN_LIQUIDITY", "50000"))
MAX_PORTFOLIO_DEPLOYED = float(os.getenv("MAX_PORTFOLIO_DEPLOYED_PCT", "0.60"))


def check_entry(token: dict, score: float, capital: float, open_positions: int) -> dict:
    reasons = []
    approved = True
    if score < MIN_SCORE:
        approved = False
        reasons.append(f"score {score:.3f} < threshold {MIN_SCORE}")
    liq = token.get("liquidity_usd") or token.get("liquidity") or 0
    if liq < MIN_LIQUIDITY:
        approved = False
        reasons.append(f"liq ${liq:,.0f} < ${MIN_LIQUIDITY:,.0f}")
    if open_positions >= MAX_OPEN_POSITIONS:
        approved = False
        reasons.append(f"max positions ({MAX_OPEN_POSITIONS}) reached")
    if capital <= 10:
        approved = False
        reasons.append("insufficient capital")
    size_usd = round(capital * MAX_POSITION_PCT, 2)
    return {
        "approved": approved,
        "size_usd": size_usd,
        "stop_loss_pct": STOP_LOSS_PCT,
        "take_profit_pct": TAKE_PROFIT_PCT,
        "trailing_stop_pct": TRAILING_STOP_PCT,
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


def check_portfolio_risk(capital: float, open_positions: int) -> bool:
    if open_positions >= MAX_OPEN_POSITIONS:
        return False
    avg_pos = capital * MAX_POSITION_PCT
    deployed_est = open_positions * avg_pos
    total_est = capital + deployed_est
    deployed_pct = deployed_est / total_est if total_est > 0 else 0
    return deployed_pct < MAX_PORTFOLIO_DEPLOYED
