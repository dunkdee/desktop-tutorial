import asyncio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from dominion_alpha.memory import get_conn, init_db
from dominion_alpha.paper_broker import get_capital, get_open_positions
from dominion_alpha.governor import scan_and_score, run_cycle, run_loop

app = FastAPI(title="Dominion Alpha Engine", version="1.0.0")


@app.on_event("startup")
async def startup():
    init_db()
    asyncio.create_task(run_loop())


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    capital = get_capital()
    positions = get_open_positions()
    conn = get_conn()
    rows = conn.execute("SELECT * FROM trades ORDER BY id DESC LIMIT 20").fetchall()
    conn.close()
    trades_html = "".join(
        f"<tr><td>{r['timestamp'][:16]}</td><td>{r['symbol']}</td>"
        f"<td style='color:{'#00ff88' if r['action']=='BUY' else '#ff4444'}'>{r['action']}</td>"
        f"<td>${float(r['price']):.8f}</td><td>${float(r['size_usd']):.2f}</td>"
        f"<td style='color:{'#00ff88' if float(r['pnl'])>=0 else '#ff4444'}'>${float(r['pnl']):.2f}</td></tr>"
        for r in rows
    )
    pos_html = "".join(
        f"<tr><td>{p['symbol']}</td><td>${float(p['price']):.8f}</td><td>${float(p['size_usd']):.2f}</td></tr>"
        for p in positions
    ) or "<tr><td colspan=3>No open positions</td></tr>"
    return HTMLResponse(f"""
    <html><head><title>Dominion Alpha</title>
    <meta http-equiv='refresh' content='30'>
    <style>body{{font-family:monospace;background:#070710;color:#00ff88;padding:20px;margin:0}}
    h1{{color:#00ff88;border-bottom:1px solid #333;padding-bottom:10px}}
    .grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:15px;margin:20px 0}}
    .card{{background:#0d0d1a;border:1px solid #1a1a3a;padding:15px;border-radius:6px}}
    .card h3{{color:#888;margin:0 0 8px}}.card h2{{margin:0;font-size:24px}}
    table{{width:100%;border-collapse:collapse;margin-top:10px}}
    th{{color:#888;text-align:left;border-bottom:1px solid #222;padding:6px}}
    td{{padding:6px;border-bottom:1px solid #111}}
    </style></head><body>
    <h1>⚡ DOMINION ALPHA ENGINE</h1>
    <div class='grid'>
    <div class='card'><h3>Capital</h3><h2>${capital:,.2f}</h2></div>
    <div class='card'><h3>Open Positions</h3><h2>{len(positions)}</h2></div>
    <div class='card'><h3>Mode</h3><h2 style='color:#ffaa00'>PAPER</h2></div>
    </div>
    <div style='background:#0d0d1a;border:1px solid #1a1a3a;padding:15px;border-radius:6px;margin:10px 0'>
    <h3 style='color:#888'>Open Positions</h3>
    <table><tr><th>Symbol</th><th>Entry</th><th>Size</th></tr>{pos_html}</table></div>
    <div style='background:#0d0d1a;border:1px solid #1a1a3a;padding:15px;border-radius:6px;margin:10px 0'>
    <h3 style='color:#888'>Recent Trades</h3>
    <table><tr><th>Time</th><th>Symbol</th><th>Action</th><th>Price</th><th>Size</th><th>PnL</th></tr>
    {trades_html}</table></div>
    </body></html>
    """)


@app.get("/health")
async def health():
    return {"status": "ok", "engine": "dominion-alpha", "mode": "paper"}


@app.get("/capital")
async def capital_endpoint():
    return {"capital": get_capital()}


@app.get("/positions")
async def positions_endpoint():
    return {"positions": get_open_positions()}


@app.get("/scan")
async def scan_endpoint():
    tokens = await scan_and_score()
    return {"count": len(tokens), "top": tokens[:10]}


@app.get("/cycle")
async def cycle_endpoint():
    return await run_cycle()


@app.get("/trades")
async def trades_endpoint():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM trades ORDER BY id DESC LIMIT 50").fetchall()
    conn.close()
    return {"trades": [dict(r) for r in rows]}
