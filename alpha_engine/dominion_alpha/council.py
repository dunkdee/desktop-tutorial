import os
import logging
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("alpha.council")

BUY_THRESHOLD = float(os.getenv("MIN_SCORE", "0.82"))
WATCH_THRESHOLD = 0.65
SKEPTIC_VETO = 0.35


class Advisor:
    name = "base"
    weight = 1.0

    def evaluate(self, token: dict) -> dict:
        return {"score": 0.5, "confidence": 0.5, "reason": "base", "recommendation": "HOLD"}


class LiquidityAdvisor(Advisor):
    name = "liquidity"
    weight = 1.5

    def evaluate(self, token):
        liq = token.get("liquidity_usd") or token.get("liquidity") or 0
        if liq < 5_000:
            return {"score": 0.05, "confidence": 0.97, "reason": f"critical: liq ${liq:,.0f}", "recommendation": "SKIP"}
        if liq < 25_000:
            return {"score": 0.30, "confidence": 0.87, "reason": f"low liq ${liq:,.0f}", "recommendation": "SKIP"}
        if liq < 100_000:
            return {"score": 0.60, "confidence": 0.78, "reason": f"moderate liq ${liq:,.0f}", "recommendation": "WATCH"}
        if liq < 500_000:
            return {"score": 0.84, "confidence": 0.87, "reason": f"good liq ${liq:,.0f}", "recommendation": "BUY"}
        return {"score": 0.93, "confidence": 0.92, "reason": f"strong liq ${liq:,.0f}", "recommendation": "BUY"}


class VolumeAdvisor(Advisor):
    name = "volume"
    weight = 1.2

    def evaluate(self, token):
        v1h = token.get("volume_1h") or 0
        v24 = token.get("volume_24h") or 0
        if v24 < 500:
            return {"score": 0.08, "confidence": 0.92, "reason": "near-zero volume", "recommendation": "SKIP"}
        if v1h > v24 * 0.15:
            return {"score": 0.90, "confidence": 0.82, "reason": f"accelerating ${v1h:,.0f}/1h", "recommendation": "BUY"}
        if v24 > 500_000:
            return {"score": 0.88, "confidence": 0.83, "reason": f"strong vol ${v24:,.0f}", "recommendation": "BUY"}
        if v24 > 50_000:
            return {"score": 0.72, "confidence": 0.73, "reason": f"decent vol ${v24:,.0f}", "recommendation": "WATCH"}
        if v24 > 5_000:
            return {"score": 0.50, "confidence": 0.65, "reason": f"low vol ${v24:,.0f}", "recommendation": "WATCH"}
        return {"score": 0.25, "confidence": 0.72, "reason": f"minimal vol ${v24:,.0f}", "recommendation": "SKIP"}


class MomentumAdvisor(Advisor):
    name = "momentum"
    weight = 1.3

    def evaluate(self, token):
        v1h = token.get("volume_1h") or 0
        liq = token.get("liquidity_usd") or token.get("liquidity") or 1
        pc5m = token.get("price_change_5m") or 0
        pc1h = token.get("price_change_1h") or 0
        ratio = v1h / liq if liq > 0 else 0
        if pc5m > 15 or pc1h > 40:
            return {"score": 0.18, "confidence": 0.87, "reason": f"parabolic +{pc5m:.0f}%/5m — likely topped", "recommendation": "SKIP"}
        if ratio > 2.0 and pc1h > 0:
            return {"score": 0.92, "confidence": 0.84, "reason": f"strong momentum ratio={ratio:.2f} +{pc1h:.1f}%", "recommendation": "BUY"}
        if ratio > 0.5 and pc1h >= 0:
            return {"score": 0.78, "confidence": 0.74, "reason": f"good momentum ratio={ratio:.2f}", "recommendation": "BUY"}
        if ratio > 0.1:
            return {"score": 0.55, "confidence": 0.62, "reason": f"moderate ratio={ratio:.2f}", "recommendation": "WATCH"}
        return {"score": 0.22, "confidence": 0.72, "reason": "low momentum", "recommendation": "SKIP"}


class MarketCapAdvisor(Advisor):
    name = "market_cap"
    weight = 1.0

    def evaluate(self, token):
        mc = token.get("market_cap") or token.get("fdv") or 0
        if mc == 0:
            return {"score": 0.42, "confidence": 0.40, "reason": "no MC data", "recommendation": "WATCH"}
        if mc < 10_000:
            return {"score": 0.20, "confidence": 0.75, "reason": f"dust cap ${mc:,.0f}", "recommendation": "SKIP"}
        if mc < 200_000:
            return {"score": 0.65, "confidence": 0.72, "reason": f"micro ${mc:,.0f} — high risk/reward", "recommendation": "WATCH"}
        if mc < 2_000_000:
            return {"score": 0.90, "confidence": 0.87, "reason": f"sweet spot ${mc:,.0f}", "recommendation": "BUY"}
        if mc < 20_000_000:
            return {"score": 0.65, "confidence": 0.77, "reason": f"small cap ${mc:,.0f}", "recommendation": "WATCH"}
        if mc < 200_000_000:
            return {"score": 0.40, "confidence": 0.78, "reason": f"mid cap ${mc:,.0f} — limited upside", "recommendation": "SKIP"}
        return {"score": 0.18, "confidence": 0.88, "reason": f"large cap ${mc:,.0f}", "recommendation": "SKIP"}


class WhaleAdvisor(Advisor):
    name = "whale"
    weight = 1.2

    def evaluate(self, token):
        ratio = token.get("buy_sell_ratio") or 1.0
        buys = token.get("txns_buys_1h") or 0
        sells = token.get("txns_sells_1h") or 0
        total = buys + sells
        if total < 3:
            return {"score": 0.38, "confidence": 0.42, "reason": "too few txns", "recommendation": "WATCH"}
        if ratio > 4.0:
            return {"score": 0.22, "confidence": 0.82, "reason": f"extreme ratio {ratio:.1f}x — pump signal", "recommendation": "SKIP"}
        if ratio > 1.5:
            return {"score": 0.87, "confidence": 0.80, "reason": f"healthy buy pressure {ratio:.1f}x", "recommendation": "BUY"}
        if ratio > 0.8:
            return {"score": 0.65, "confidence": 0.67, "reason": f"balanced {ratio:.1f}x", "recommendation": "WATCH"}
        return {"score": 0.22, "confidence": 0.82, "reason": f"sell pressure {ratio:.1f}x", "recommendation": "SKIP"}


class TokenHealthAdvisor(Advisor):
    name = "token_health"
    weight = 1.4

    def evaluate(self, token):
        age_h = token.get("pair_age_hours") or 0
        pc24 = token.get("price_change_24h") or 0
        txns = token.get("total_txns_1h") or 0
        if age_h < 0.17:
            return {"score": 0.08, "confidence": 0.97, "reason": f"< 10min old ({age_h*60:.0f}min)", "recommendation": "SKIP"}
        if age_h < 1:
            score = 0.78 if txns > 10 else 0.55
            return {"score": score, "confidence": 0.72, "reason": f"fresh {age_h:.1f}h {txns} txns", "recommendation": "WATCH"}
        if age_h < 24:
            score = 0.87 if txns > 20 else 0.68
            return {"score": score, "confidence": 0.80, "reason": f"new {age_h:.1f}h {txns} txns/1h", "recommendation": "BUY" if score >= 0.82 else "WATCH"}
        if age_h < 168:
            return {"score": 0.68, "confidence": 0.73, "reason": f"{age_h:.0f}h established", "recommendation": "WATCH"}
        if pc24 < -50:
            return {"score": 0.18, "confidence": 0.87, "reason": f"dying: {pc24:.0f}% 24h", "recommendation": "SKIP"}
        return {"score": 0.48, "confidence": 0.67, "reason": f"aged {age_h:.0f}h", "recommendation": "WATCH"}


class HolderGrowthAdvisor(Advisor):
    name = "holder_growth"
    weight = 1.1

    def evaluate(self, token):
        buys = token.get("txns_buys_1h") or 0
        v5m = token.get("volume_5m") or 0
        v1h = token.get("volume_1h") or 0
        accel = v5m / (v1h / 12) if v1h > 0 else 0
        if buys > 80 and accel > 1.5:
            return {"score": 0.91, "confidence": 0.78, "reason": f"{buys} buys/1h accel {accel:.1f}x", "recommendation": "BUY"}
        if buys > 30:
            return {"score": 0.76, "confidence": 0.68, "reason": f"{buys} buys this hour", "recommendation": "WATCH"}
        if buys > 10:
            return {"score": 0.58, "confidence": 0.62, "reason": f"light buying {buys} txns", "recommendation": "WATCH"}
        return {"score": 0.28, "confidence": 0.67, "reason": "minimal buyer activity", "recommendation": "SKIP"}


class SocialSentimentAdvisor(Advisor):
    name = "social_sentiment"
    weight = 0.8

    def evaluate(self, token):
        has_socials = token.get("has_socials") or False
        has_website = token.get("has_website") or False
        links = token.get("profile_links") or 0
        score = 0.30
        parts = []
        if has_website:
            score += 0.28
            parts.append("website")
        if has_socials:
            score += 0.32
            parts.append("socials")
        if links >= 3:
            score += 0.08
            parts.append(f"{links} links")
        score = min(score, 0.95)
        rec = "BUY" if score >= 0.82 else ("WATCH" if score >= 0.65 else "SKIP")
        return {"score": round(score, 3), "confidence": 0.65, "reason": ", ".join(parts) or "no presence", "recommendation": rec}


class NewsAdvisor(Advisor):
    name = "news"
    weight = 0.7

    def evaluate(self, token):
        has_w = token.get("has_website") or False
        has_s = token.get("has_socials") or False
        name = token.get("name") or ""
        score = 0.38 + (0.25 if has_w else 0) + (0.22 if has_s else 0) + (0.08 if len(name) > 3 else 0)
        score = min(score, 0.92)
        return {"score": round(score, 3), "confidence": 0.55, "reason": f"web={has_w} socials={has_s}", "recommendation": "WATCH"}


class RiskAdvisor(Advisor):
    name = "risk"
    weight = 1.5

    def evaluate(self, token):
        age_h = token.get("pair_age_hours") or 0
        liq = token.get("liquidity_usd") or token.get("liquidity") or 0
        pc5m = abs(token.get("price_change_5m") or 0)
        pc1h = abs(token.get("price_change_1h") or 0)
        ratio = token.get("buy_sell_ratio") or 1.0
        if age_h < 0.17:
            return {"score": 0.03, "confidence": 0.99, "reason": "CRITICAL: < 10min — rug risk", "recommendation": "SKIP"}
        if liq < 10_000:
            return {"score": 0.08, "confidence": 0.97, "reason": f"CRITICAL: liq ${liq:,.0f} — exit blocked", "recommendation": "SKIP"}
        if pc5m > 60:
            return {"score": 0.12, "confidence": 0.93, "reason": f"CRITICAL: +{pc5m:.0f}% in 5m — topped", "recommendation": "SKIP"}
        if ratio > 5.0:
            return {"score": 0.18, "confidence": 0.88, "reason": f"WARNING: ratio {ratio:.1f}x — coordinated pump", "recommendation": "SKIP"}
        rs = 0.92
        if age_h < 1: rs -= 0.12
        if liq < 50_000: rs -= 0.08
        if pc1h > 25: rs -= 0.12
        return {"score": max(round(rs, 3), 0.10), "confidence": 0.82, "reason": f"age={age_h:.1f}h liq=${liq:,.0f} 1h={pc1h:.0f}%", "recommendation": "BUY" if rs >= 0.82 else "WATCH"}


class ExecutionAdvisor(Advisor):
    name = "execution"
    weight = 1.0

    def evaluate(self, token):
        liq = token.get("liquidity_usd") or token.get("liquidity") or 0
        v1h = token.get("volume_1h") or 0
        pos_size = 50.0
        if liq <= 0:
            return {"score": 0.08, "confidence": 0.88, "reason": "no liquidity", "recommendation": "SKIP"}
        impact = (pos_size / liq) * 100
        if impact > 5:
            return {"score": 0.18, "confidence": 0.82, "reason": f"impact {impact:.1f}% — slippage", "recommendation": "SKIP"}
        if impact > 1:
            return {"score": 0.65, "confidence": 0.77, "reason": f"moderate impact {impact:.2f}%", "recommendation": "WATCH"}
        if v1h > liq * 0.5:
            return {"score": 0.92, "confidence": 0.82, "reason": f"active market impact={impact:.2f}%", "recommendation": "BUY"}
        return {"score": 0.82, "confidence": 0.74, "reason": f"clean execution impact={impact:.2f}%", "recommendation": "BUY"}


class SkepticAdvisor(Advisor):
    """Attempts to REJECT every trade. Scores low = veto."""
    name = "skeptic"
    weight = 1.6

    def evaluate(self, token):
        age_h = token.get("pair_age_hours") or 0
        liq = token.get("liquidity_usd") or token.get("liquidity") or 0
        pc5m = token.get("price_change_5m") or 0
        mc = token.get("market_cap") or 0
        ratio = token.get("buy_sell_ratio") or 1.0
        has_socials = token.get("has_socials") or False
        has_website = token.get("has_website") or False
        rejections = []
        if age_h < 0.17:
            rejections.append(f"< 10min ({age_h*60:.0f}min)")
        if liq < 10_000:
            rejections.append(f"liq ${liq:,.0f}")
        if pc5m > 50:
            rejections.append(f"+{pc5m:.0f}%/5m pump")
        if ratio > 4:
            rejections.append(f"ratio {ratio:.1f}x")
        if not has_socials and not has_website:
            rejections.append("no social/web")
        if 0 < mc < 5_000:
            rejections.append(f"MC ${mc:,.0f} dust")
        if len(rejections) >= 2:
            return {"score": 0.08, "confidence": 0.94, "reason": f"VETO: {'; '.join(rejections)}", "recommendation": "SKIP"}
        if len(rejections) == 1:
            return {"score": 0.48, "confidence": 0.82, "reason": f"concern: {rejections[0]}", "recommendation": "WATCH"}
        return {"score": 0.84, "confidence": 0.72, "reason": "no disqualifiers — reluctant approval", "recommendation": "BUY"}


COUNCIL: List[Advisor] = [
    LiquidityAdvisor(),
    VolumeAdvisor(),
    MomentumAdvisor(),
    MarketCapAdvisor(),
    WhaleAdvisor(),
    TokenHealthAdvisor(),
    HolderGrowthAdvisor(),
    SocialSentimentAdvisor(),
    NewsAdvisor(),
    RiskAdvisor(),
    ExecutionAdvisor(),
    SkepticAdvisor(),
]


def convene(token: dict, advisor_weights: dict = None) -> dict:
    votes: Dict[str, dict] = {}
    weighted_sum = 0.0
    total_weight = 0.0
    skeptic_score = None
    risks = []

    for advisor in COUNCIL:
        w = advisor.weight
        if advisor_weights and advisor.name in advisor_weights:
            try:
                w = float(advisor_weights[advisor.name])
            except Exception:
                pass
        result = advisor.evaluate(token)
        votes[advisor.name] = result
        weighted_sum += result["score"] * w
        total_weight += w
        if advisor.name == "skeptic":
            skeptic_score = result["score"]
        if result["recommendation"] == "SKIP" and result["confidence"] >= 0.80:
            risks.append(result["reason"])

    final_score = weighted_sum / total_weight if total_weight > 0 else 0
    skeptic_override = skeptic_score is not None and skeptic_score < SKEPTIC_VETO
    avg_confidence = sum(v["confidence"] for v in votes.values()) / len(votes) if votes else 0

    if skeptic_override:
        verdict = "SKIP"
        thesis = f"Skeptic veto: {votes.get('skeptic', {}).get('reason', '')}"
    elif final_score >= BUY_THRESHOLD:
        verdict = "BUY"
        buy_reasons = [v["reason"] for v in votes.values() if v["recommendation"] == "BUY"][:2]
        thesis = f"Score {final_score:.3f} — {'; '.join(buy_reasons)}"
    elif final_score >= WATCH_THRESHOLD:
        verdict = "WATCH"
        thesis = f"Score {final_score:.3f} — monitoring"
    else:
        verdict = "SKIP"
        thesis = f"Score {final_score:.3f} — low conviction"

    return {
        "score": round(final_score, 4),
        "confidence": round(avg_confidence, 3),
        "verdict": verdict,
        "votes": {n: {"score": v["score"], "conf": v["confidence"], "reason": v["reason"], "rec": v["recommendation"]} for n, v in votes.items()},
        "thesis": thesis,
        "risks": risks[:5],
        "skeptic_override": skeptic_override,
    }
