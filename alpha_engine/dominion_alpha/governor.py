import asyncio
import logging
import os
from datetime import datetime
from dotenv import load_dotenv
from dominion_alpha.scanner import scan_new_pairs, fetch_token
from dominion_alpha.council import convene
from dominion_alpha.risk import check_entry, check_exit
from dominion_alpha.paper_broker import get_capital, get_open_positions, paper_buy, paper_sell
from dominion_alpha.memory import init_db

load_dotenv()

SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL_MINUTES", "5")) * 60

logger = logging.getLogger("alpha.governor")
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(name)s %(message)s")


async def scan_and_score():
    tokens = await scan_new_pairs()
    scored = []
    for t in tokens:
        if not t.get("address"):
            continue
        result = convene(t)
        t["score"] = result["score"]
        t["verdict"] = result["verdict"]
        t["votes"] = result["votes"]
        scored.append(t)
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


async def run_cycle() -> dict:
    init_db()
    logger.info("--- cycle start ---")
    tokens = await scan_and_score()
    logger.info(f"scanned {len(tokens)} tokens")
    capital = get_capital()
    open_pos = get_open_positions()

    # check exits
    for pos in open_pos:
        current = await fetch_token(pos["token_address"])
        if current and current.get("price_usd"):
            ex = check_exit(pos["price"], current["price_usd"])
            if ex["exit"]:
                result = paper_sell(pos["token_address"], current["price_usd"])
                logger.info(f"EXIT {pos['symbol']}: {ex['reason']} pnl=${result.get('pnl', 0):.2f}")

    # check entries
    buys = 0
    for t in tokens:
        if t["verdict"] != "BUY" or buys >= 2:
            break
        open_pos = get_open_positions()
        risk = check_entry(t, t["score"], capital, len(open_pos))
        if risk["approved"]:
            res = paper_buy(t, risk["size_usd"])
            logger.info(f"ENTRY {t['symbol']} score={t['score']:.3f} size=${risk['size_usd']:.2f}")
            capital = res.get("capital_after", capital)
            buys += 1

    return {
        "ts": datetime.utcnow().isoformat(),
        "tokens_scanned": len(tokens),
        "capital": get_capital(),
        "open_positions": len(get_open_positions()),
        "top_picks": [{"symbol": t.get("symbol"), "score": t.get("score"), "verdict": t.get("verdict"), "liquidity": t.get("liquidity")} for t in tokens[:5]],
    }


async def run_loop():
    while True:
        try:
            await run_cycle()
        except Exception as e:
            logger.error(f"cycle error: {e}")
        await asyncio.sleep(SCAN_INTERVAL)
