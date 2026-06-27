import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dominion_alpha.memory import init_db, get_conn
from dominion_alpha.paper_broker import get_capital, get_open_positions
from dominion_alpha.governor import run_cycle, scan_and_score
from dominion_alpha.performance import compute_performance
from dominion_alpha.learning import get_lessons, get_current_weights


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    init_db()

    if cmd == "scan-once":
        print("[alpha] scanning DexScreener (v2 — real token discovery)...")
        result = asyncio.run(run_cycle())
        print(f"[alpha] tokens scanned  : {result['tokens_scanned']}")
        print(f"[alpha] capital         : ${result['capital']:,.2f}")
        print(f"[alpha] open positions  : {result['open_positions']}")
        print(f"[alpha] governor        : {'KILL' if result['governor']['kill_switch'] else 'ACTIVE'} | threshold={result['governor']['threshold']}")
        print(f"[alpha] top 20 tokens:")
        print(f"  {'Symbol':12} {'Chain':8} {'Score':6} {'Verdict':6} {'Liquidity':12} {'MC':12} {'Age':6} Thesis")
        print(f"  {'-'*100}")
        for t in result.get("top_picks", []):
            print(f"  {str(t.get('symbol','?')):12} {str(t.get('chain','')):8} {t.get('score',0):.3f}  {str(t.get('verdict','')):6} ${float(t.get('liquidity') or 0):>10,.0f}  ${float(t.get('mc') or 0):>10,.0f}  {float(t.get('age_h') or 0):4.1f}h  {str(t.get('thesis',''))[:50]}")
        if result.get("errors"):
            print(f"[alpha] errors: {result['errors']}")

    elif cmd == "status":
        print(f"[alpha] Capital         : ${get_capital():,.2f}")
        pos = get_open_positions()
        print(f"[alpha] Open positions  : {len(pos)}")
        for p in pos:
            print(f"  {p['symbol']:12} entry=${p['price']:.8f}  size=${p['size_usd']:.2f}  opened={p['timestamp'][:16]}")

    elif cmd == "trades":
        conn = get_conn()
        rows = conn.execute("SELECT * FROM trades ORDER BY id DESC LIMIT 20").fetchall()
        conn.close()
        if not rows:
            print("No trades yet.")
        for r in rows:
            pnl_str = f"pnl=${float(r['pnl']):.4f}" if r['action'] == 'SELL' else ""
            print(f"[{r['timestamp'][:16]}] {r['action']:4}  {r['symbol']:12}  ${float(r['price']):.8f}  size=${float(r['size_usd']):.2f}  {pnl_str}")

    elif cmd == "performance":
        perf = compute_performance()
        print(f"[alpha] Performance Report")
        print(f"  Total trades    : {perf['total_trades']}")
        print(f"  Wins / Losses   : {perf['wins']} / {perf['losses']}")
        print(f"  Win rate        : {perf['win_rate']:.1%}")
        print(f"  Profit factor   : {perf['profit_factor']:.3f}")
        print(f"  Expectancy      : ${perf['expectancy']:.4f}")
        print(f"  Avg win         : ${perf['avg_win']:.4f}")
        print(f"  Avg loss        : ${perf['avg_loss']:.4f}")
        print(f"  Sharpe estimate : {perf['sharpe_estimate']:.3f}")
        print(f"  Total PnL       : ${perf['total_pnl']:.4f}")

    elif cmd == "weights":
        weights = get_current_weights()
        print(f"[alpha] Advisor Weights (live)")
        print(f"  {'Advisor':20} {'Weight':8} {'Accuracy'}")
        print(f"  {'-'*40}")
        for name, v in sorted(weights.items(), key=lambda x: -x[1]['weight']):
            print(f"  {name:20} {v['weight']:.4f}   {v['accuracy']:.1%}")

    elif cmd == "lessons":
        lessons = get_lessons(10)
        if not lessons:
            print("No lessons yet.")
        for l in lessons:
            print(f"[{l['timestamp'][:16]}] {l['lesson']}")

    elif cmd == "decisions":
        conn = get_conn()
        rows = conn.execute("SELECT * FROM decisions ORDER BY id DESC LIMIT 20").fetchall()
        conn.close()
        if not rows:
            print("No decisions logged yet.")
        for d in rows:
            status = "APPROVED" if d['approved'] else f"REJECTED: {d['rejection_reason']}"
            print(f"[{d['timestamp'][:16]}] {d['action']:4}  {d['symbol']:12}  score={float(d['score'] or 0):.3f}  {status}")

    else:
        print("Usage: python -m dominion_alpha.cli [scan-once|status|trades|performance|weights|lessons|decisions]")
        sys.exit(1)


if __name__ == "__main__":
    main()
