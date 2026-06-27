import httpx
import asyncio
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("alpha.scanner")

CHAINS_TARGET = set(os.getenv("CHAINS", "solana,base").split(","))

NATIVE_SYMBOLS = {
    "SOL", "WSOL", "ETH", "WETH", "BTC", "WBTC",
    "USDC", "USDT", "BNB", "WBNB", "MATIC", "AVAX",
    "ARB", "OP", "DAI", "BUSD", "TUSD", "FRAX",
}

DEX_BASE = "https://api.dexscreener.com"
HEADERS = {"Accept": "application/json", "User-Agent": "DominionAlpha/2.0"}


def normalize_pair(pair: dict, profile: dict = None) -> dict:
    base = pair.get("baseToken") or {}
    volume = pair.get("volume") or {}
    price_change = pair.get("priceChange") or {}
    txns = pair.get("txns") or {}
    txns_1h = txns.get("h1") or {}
    liq_data = pair.get("liquidity") or {}

    buys_1h = int(txns_1h.get("buys") or 0)
    sells_1h = int(txns_1h.get("sells") or 0)
    buy_sell_ratio = (buys_1h / sells_1h) if sells_1h > 0 else (2.0 if buys_1h > 0 else 1.0)

    pair_age_hours = 0.0
    pair_created = pair.get("pairCreatedAt")
    if pair_created:
        try:
            age_ms = datetime.utcnow().timestamp() * 1000 - int(pair_created)
            pair_age_hours = max(age_ms / 3_600_000, 0)
        except Exception:
            pass

    profile = profile or {}
    links = profile.get("links") or []
    has_website = any(str(l.get("type", "")).lower() == "website" for l in links)
    has_socials = any(str(l.get("type", "")).lower() in ("twitter", "telegram", "discord") for l in links)

    liq_usd = float(liq_data.get("usd") or 0)
    return {
        "address": base.get("address", ""),
        "symbol": base.get("symbol", ""),
        "name": base.get("name", ""),
        "chain": pair.get("chainId", ""),
        "pair_address": pair.get("pairAddress", ""),
        "dex_id": pair.get("dexId", ""),
        "price_usd": float(pair.get("priceUsd") or 0),
        "volume_5m": float(volume.get("m5") or 0),
        "volume_1h": float(volume.get("h1") or 0),
        "volume_24h": float(volume.get("h24") or 0),
        "liquidity_usd": liq_usd,
        "liquidity": liq_usd,
        "market_cap": float(pair.get("marketCap") or 0),
        "fdv": float(pair.get("fdv") or 0),
        "price_change_5m": float(price_change.get("m5") or 0),
        "price_change_1h": float(price_change.get("h1") or 0),
        "price_change_24h": float(price_change.get("h24") or 0),
        "txns_buys_1h": buys_1h,
        "txns_sells_1h": sells_1h,
        "total_txns_1h": buys_1h + sells_1h,
        "buy_sell_ratio": round(buy_sell_ratio, 3),
        "pair_age_hours": round(pair_age_hours, 3),
        "has_website": has_website,
        "has_socials": has_socials,
        "profile_links": len(links),
        "last_updated": datetime.utcnow().isoformat(),
    }


def is_native(symbol: str) -> bool:
    return (symbol or "").upper() in NATIVE_SYMBOLS


async def _get_profiles(client: httpx.AsyncClient) -> list:
    try:
        r = await client.get(f"{DEX_BASE}/token-profiles/latest/v1", headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json()
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning(f"token-profiles: {e}")
    return []


async def _get_boosts(client: httpx.AsyncClient) -> list:
    results = []
    for ep in ["/token-boosts/latest/v1", "/token-boosts/active/v1"]:
        try:
            r = await client.get(f"{DEX_BASE}{ep}", headers=HEADERS, timeout=15)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    results.extend(data)
        except Exception as e:
            logger.warning(f"{ep}: {e}")
    return results


async def _fetch_pairs(client: httpx.AsyncClient, address: str) -> list:
    try:
        r = await client.get(f"{DEX_BASE}/latest/dex/tokens/{address}", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json().get("pairs") or []
    except Exception:
        pass
    return []


async def scan_new_pairs(chains=None) -> list:
    if chains is None:
        chains = CHAINS_TARGET

    seen = set()
    candidates = []
    profile_map = {}

    async with httpx.AsyncClient(timeout=20) as client:
        profiles, boosts = await asyncio.gather(
            _get_profiles(client),
            _get_boosts(client),
        )

        for item in profiles + boosts:
            chain_id = item.get("chainId", "")
            addr = item.get("tokenAddress", "")
            if not addr or chain_id not in chains:
                continue
            if addr not in seen:
                seen.add(addr)
                candidates.append({"chainId": chain_id, "address": addr})
                profile_map[addr] = item

        logger.info(f"discovered {len(candidates)} candidates on {chains}")

        sem = asyncio.Semaphore(8)

        async def _process(c):
            async with sem:
                addr = c["address"]
                pairs = await _fetch_pairs(client, addr)
                if not pairs:
                    return None
                pairs.sort(
                    key=lambda p: float((p.get("liquidity") or {}).get("usd") or 0),
                    reverse=True,
                )
                best = pairs[0]
                sym = (best.get("baseToken") or {}).get("symbol", "")
                if is_native(sym):
                    return None
                return normalize_pair(best, profile_map.get(addr, {}))

        results = await asyncio.gather(*[_process(c) for c in candidates[:80]])

    valid = [t for t in results if t and t.get("address") and t.get("price_usd", 0) > 0]
    logger.info(f"scanner: {len(valid)} valid tokens")
    return valid


async def fetch_token(address: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        pairs = await _fetch_pairs(client, address)
        if pairs:
            pairs.sort(
                key=lambda p: float((p.get("liquidity") or {}).get("usd") or 0),
                reverse=True,
            )
            return normalize_pair(pairs[0])
    return {}
