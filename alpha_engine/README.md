# Dominion Alpha Engine

Token scanner + paper trading engine. Live at `http://localhost:8787`.

## Architecture

- **scanner.py** — DexScreener API, fetches new pairs across Solana/ETH/Base
- **council.py** — 4 advisors vote on each token (liquidity, volume, market cap, momentum)
- **governor.py** — orchestrates scan/score/entry/exit cycle every N minutes
- **risk.py** — enforces position limits, stop-loss, take-profit
- **paper_broker.py** — simulated trades, zero real money
- **memory.py** — SQLite persistence (trades, state, tokens)
- **api.py** — FastAPI dashboard on port 8787
- **cli.py** — `scan-once | status | trades`

## Commands

```bash
source .venv/bin/activate
python -m dominion_alpha.cli scan-once
python -m dominion_alpha.cli status
python -m dominion_alpha.cli trades
```

## Config (.env)

| Key | Default | Description |
|-----|---------|-------------|
| STARTING_CAPITAL | 1000.0 | Paper capital in USD |
| MAX_POSITION_PCT | 0.05 | 5% per trade |
| MAX_OPEN_POSITIONS | 5 | Max concurrent positions |
| STOP_LOSS_PCT | 0.10 | 10% stop loss |
| TAKE_PROFIT_PCT | 0.30 | 30% take profit |
| MIN_SCORE | 0.65 | Minimum council score to enter |
| MIN_LIQUIDITY | 25000 | Minimum liquidity in USD |
| SCAN_INTERVAL_MINUTES | 5 | How often governor scans |
| LIVE_TRADING | false | **Never set to true without exchange integration** |
