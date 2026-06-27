import math
from datetime import datetime
from dominion_alpha.memory import get_conn


def compute_performance() -> dict:
    conn = get_conn()
    sells = conn.execute("SELECT * FROM trades WHERE action='SELL' ORDER BY timestamp").fetchall()
    conn.close()

    if not sells:
        return {
            "total_trades": 0, "wins": 0, "losses": 0,
            "win_rate": 0.0, "profit_factor": 0.0, "expectancy": 0.0,
            "avg_win": 0.0, "avg_loss": 0.0, "sharpe_estimate": 0.0,
            "total_pnl": 0.0, "capital_curve": [],
        }

    pnls = [float(r["pnl"]) for r in sells]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    win_rate = len(wins) / len(pnls)
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = abs(sum(losses) / len(losses)) if losses else 0
    pf_denom = abs(sum(losses))
    profit_factor = (sum(wins) / pf_denom) if pf_denom > 0 else (999.0 if wins else 0.0)
    expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

    sharpe = 0.0
    if len(pnls) >= 3:
        mean = sum(pnls) / len(pnls)
        variance = sum((p - mean) ** 2 for p in pnls) / len(pnls)
        std = math.sqrt(variance) if variance > 0 else 0
        sharpe = round((mean / std) * math.sqrt(252), 3) if std > 0 else 0.0

    return {
        "total_trades": len(pnls),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(win_rate, 4),
        "profit_factor": round(profit_factor, 3),
        "expectancy": round(expectancy, 4),
        "avg_win": round(avg_win, 4),
        "avg_loss": round(avg_loss, 4),
        "sharpe_estimate": sharpe,
        "total_pnl": round(sum(pnls), 4),
        "capital_curve": [float(r["capital_after"]) for r in sells][-50:],
    }


def snapshot_performance(open_positions: int = 0):
    from dominion_alpha.paper_broker import get_capital
    perf = compute_performance()
    conn = get_conn()
    conn.execute("""
        INSERT INTO performance_snapshots
        (timestamp,capital,win_rate,profit_factor,expectancy,open_positions,total_trades)
        VALUES (?,?,?,?,?,?,?)
    """, (
        datetime.utcnow().isoformat(), get_capital(),
        perf["win_rate"], perf["profit_factor"], perf["expectancy"],
        open_positions, perf["total_trades"],
    ))
    conn.commit()
    conn.close()
