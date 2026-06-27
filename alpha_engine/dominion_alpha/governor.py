import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from dotenv import load_dotenv
from dominion_alpha.scanner import scan_new_pairs, fetch_token
from dominion_alpha.council import convene
from dominion_alpha.risk import check_entry, check_exit, check_portfolio_risk
from dominion_alpha.paper_broker import get_capital, get_open_positions, paper_buy, paper_sell
from dominion_alpha.memory import init_db, log_decision, get_advisor_weights, get_conn

load_dotenv()

SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL_MINUTES", "5")) * 60
CONFIDENCE_THRESHOLD = float(os.getenv("MIN_SCORE", "0.82"))
MAX_DAILY_LOSS_PCT = float(os.getenv("MAX_DAILY_LOSS_PCT", "0.20"))

logger = logging.getLogger("alpha.governor")
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(name)s %(message)s")


@dataclass
class GovernorState:
    kill_switch: bool = False
    confidence_threshold: float = CONFIDENCE_THRESHOLD
    max_daily_loss_pct: float = MAX_DAILY_LOSS_PCT
    session_start_capital: float = 0.0
    errors: List[str] = field(default_factory=list)
    last_cycle_ts: Optional[str] = None
    last_scan_count: int = 0
    last_top_tokens: list = field(default_factory=list)
    cycles_run: int = 0
    version: str = "2.0"


_state = GovernorState()


def get_state() -> GovernorState:
    return _state


def toggle_kill_switch() -> bool:
    _state.kill_switch = not _state.kill_switch
    logger.warning(f"KILL SWITCH {'ACTIVATED' if _state.kill_switch else 'DEACTIVATED'}")
    return _state.kill_switch


def _check_daily_loss() -> bool:
    if _state.session_start_capital <= 0:
        return False
    current = get_capital()
    loss_pct = (_state.session_start_capital - current) / _state.session_start_capital
    return loss_pct >= _state.max_daily_loss_pct


def _governor_approve(token: dict, council_result: dict, risk_result: dict):
    if _state.kill_switch:
        return False, "kill switch active"
    if council_result.get("skeptic_override"):
        return False, f"skeptic veto"
    if council_result["score"] < _state.confidence_threshold:
        return False, f"score {council_result['score']:.3f} < {_state.confidence_threshold}"
    if not risk_result["approved"]:
        return False, "; ".join(risk_result.get("reasons", ["risk check failed"]))
    if _check_daily_loss():
        return False, "daily loss limit reached"
    return True, "approved"


async def emergency_exit_all() -> dict:
    positions = get_open_positions()
    results = []
    for pos in positions:
        try:
            current = await fetch_token(pos["token_address"])
            price = (current.get("price_usd") or 0) if current else 0
            if not price:
                price = pos["price"]
            result = paper_sell(pos["token_address"], price, reason="emergency_exit")
            results.append(result)
            logger.warning(f"EMERGENCY EXIT {pos['symbol']} pnl=${result.get('pnl', 0):.2f}")
        except Exception as e:
            results.append({"error": str(e), "symbol": pos.get("symbol")})
    return {"emergency_exit": True, "closed": len(results), "results": results}


async def scan_and_score() -> list:
    weights = get_advisor_weights()
    tokens = await scan_new_pairs()
    scored = []
    for t in tokens:
        if not t.get("address"):
            continue
        result = convene(t, weights)
        t.update(result)
        scored.append(t)
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


async def run_cycle() -> dict:
    init_db()
    ts = datetime.utcnow().isoformat()
    logger.info("--- cycle start ---")
    _state.cycles_run += 1

    if _state.session_start_capital == 0:
        _state.session_start_capital = get_capital()

    try:
        tokens = await scan_and_score()
    except Exception as e:
        err = f"scan error: {e}"
        logger.error(err)
        _state.errors = ([err] + _state.errors)[:10]
        tokens = []

    _state.last_scan_count = len(tokens)
    _state.last_top_tokens = tokens[:20]
    logger.info(f"scanned {len(tokens)} tokens")

    capital = get_capital()
    open_pos = get_open_positions()

    # Check exits
    for pos in open_pos:
        try:
            current = await fetch_token(pos["token_address"])
            if current and current.get("price_usd"):
                ex = check_exit(pos["price"], current["price_usd"])
                if ex["exit"]:
                    result = paper_sell(pos["token_address"], current["price_usd"], reason=ex["reason"])
                    pnl = result.get("pnl", 0)
                    logger.info(f"EXIT {pos['symbol']}: {ex['reason']} pnl=${pnl:.2f}")
                    # trigger learning
                    if result.get("id"):
                        try:
                            from dominion_alpha.learning import post_trade_analysis
                            post_trade_analysis(result["id"])
                        except Exception:
                            pass
        except Exception as e:
            logger.error(f"exit check {pos.get('symbol')}: {e}")

    if _check_daily_loss():
        logger.warning("DAILY LOSS LIMIT — skipping entries")
        _state.last_cycle_ts = ts
        return _build_summary(ts, tokens)

    if _state.kill_switch:
        logger.warning("KILL SWITCH — skipping entries")
        _state.last_cycle_ts = ts
        return _build_summary(ts, tokens)

    portfolio_ok = check_portfolio_risk(capital, len(get_open_positions()))
    buys = 0

    for t in tokens:
        if t.get("verdict") != "BUY" or buys >= 2:
            break
        if not portfolio_ok:
            break
        open_pos_now = get_open_positions()
        risk = check_entry(t, t["score"], capital, len(open_pos_now))
        approved, reason = _governor_approve(t, t, risk)

        log_decision({
            "timestamp": datetime.utcnow().isoformat(),
            "token_address": t["address"],
            "symbol": t.get("symbol", "?"),
            "action": "BUY" if approved else "SKIP",
            "score": t["score"],
            "confidence": t.get("confidence", 0),
            "thesis": t.get("thesis", ""),
            "evidence": str(t.get("votes", {}))[:600],
            "risks": str(t.get("risks", [])),
            "advisor_votes": str(t.get("votes", {})),
            "approved": 1 if approved else 0,
            "rejection_reason": "" if approved else reason,
        })

        if approved:
            res = paper_buy(t, risk["size_usd"])
            if "error" not in res:
                logger.info(f"ENTRY {t['symbol']} score={t['score']:.3f} size=${risk['size_usd']:.2f}")
                capital = res.get("capital_after", capital)
                buys += 1

    # snapshot performance periodically
    if _state.cycles_run % 12 == 0:
        try:
            from dominion_alpha.performance import snapshot_performance
            snapshot_performance(open_positions=len(get_open_positions()))
        except Exception:
            pass

    _state.last_cycle_ts = ts
    return _build_summary(ts, tokens)


def _build_summary(ts: str, tokens: list) -> dict:
    return {
        "ts": ts,
        "tokens_scanned": len(tokens),
        "capital": get_capital(),
        "open_positions": len(get_open_positions()),
        "governor": {
            "kill_switch": _state.kill_switch,
            "threshold": _state.confidence_threshold,
            "version": _state.version,
            "cycles_run": _state.cycles_run,
            "daily_loss_triggered": _check_daily_loss(),
        },
        "top_picks": [
            {
                "symbol": t.get("symbol"), "score": t.get("score"),
                "verdict": t.get("verdict"), "liquidity": t.get("liquidity_usd"),
                "chain": t.get("chain"), "thesis": t.get("thesis", ""),
                "age_h": t.get("pair_age_hours"), "mc": t.get("market_cap"),
            }
            for t in tokens[:20]
        ],
        "errors": _state.errors[:5],
    }


async def run_loop():
    while True:
        try:
            await run_cycle()
        except Exception as e:
            err = f"loop error: {e}"
            logger.error(err)
            _state.errors = ([err] + _state.errors)[:10]
        await asyncio.sleep(SCAN_INTERVAL)
