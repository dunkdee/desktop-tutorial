import httpx
import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

CHAINS = os.getenv("CHAINS", "solana,ethereum,base").split(",")
DEX_BASE = "https://api.dexscreener.com/latest/dex"


def normalize_pair(pair: dict) -> dict:
    base = pair.get("baseToken") or {}
    return {
        "address": base.get("address", ""),
        "symbol": base.get("symbol", ""),
        "name": base.get("name", ""),
        "chain": pair.get("chainId", ""),
        "price_usd": float(pair.get("priceUsd") or 0),
        "volume_24h": float((pair.get("volume") or {}).get("h24") or 0),
        "liquidity": float((pair.get("liquidity") or {}).get("usd") or 0),
        "market_cap": float(pair.get("marketCap") or 0),
        "last_updated": datetime.utcnow().isoformat(),
    }


async def scan_new_pairs(chains=None):
    if chains is None:
        chains = CHAINS
    results = []
    async with httpx.AsyncClient(timeout=15) as client:
        for chain in chains:
            try:
                r = await client.get(f"{DEX_BASE}/search?q={chain}")
                if r.status_code == 200:
                    pairs = (r.json().get("pairs") or [])[:30]
                    for p in pairs:
                        t = normalize_pair(p)
                        if t["address"]:
                            results.append(t)
            except Exception as e:
                print(f"[scanner] {chain} error: {e}")
    return results


async def fetch_token(address: str):
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(f"{DEX_BASE}/tokens/{address}")
            if r.status_code == 200:
                pairs = r.json().get("pairs") or []
                if pairs:
                    return normalize_pair(pairs[0])
        except Exception:
            pass
    return None
