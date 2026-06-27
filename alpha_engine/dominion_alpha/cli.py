import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dominion_alpha.memory import init_db, get_conn
from dominion_alpha.paper_broker import get_capital, get_open_positions
from dominion_alpha.governor import run_cycle, scan_and_score


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "scan-once":
        init_db()
        print("[alpha] scanning DexScreener...")
        result = asyncio.run(run_cycle())
        print(f"[alpha] tokens scanned : {result['tokens_scanned']}")
        print(f"[alpha] capital        : ${result['capital']:,.2f}")
        print(f"[alpha] open positions : {result['open_positions']}")
        print("[alpha] top picks:")
        for t in result.get("top_picks", []):
            print(f"  {t.get('symbol','?'):10} score={t.get('score',0):.3f}  verdict={t.get('verdict','?')}  liq=${t.get('liquidity',0):,.0f}")

    elif cmd == "status":
        init_db()
        print(f"Capital: ${get_capital():,.2f}")
        pos = get_open_positions()
        print(f"Open positions: {len(pos)}")
        for p in pos:
            print(f"  {p['symbol']:10} entry=${p['price']:.8f}  size=${p['size_usd']:.2f}")

    elif cmd == "trades":
        conn = get_conn()
        rows = conn.execute("SELECT * FROM trades ORDER BY id DESC LIMIT 20").fetchall()
        conn.close()
        if not rows:
            print("No trades yet.")
        for r in rows:
            print(f"[{r['timestamp'][:16]}] {r['action']:4}  {r['symbol']:10}  ${r['price']:.8f}  size=${r['size_usd']:.2f}  pnl=${r['pnl']:.2f}")

    else:
        print("Usage: python -m dominion_alpha.cli [scan-once|status|trades]")
        sys.exit(1)


if __name__ == "__main__":
    main()
