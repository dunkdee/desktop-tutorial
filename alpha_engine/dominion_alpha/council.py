from typing import Dict


class CouncilMember:
    name = "base"
    weight = 1.0

    def score(self, token: dict) -> float:
        return 0.5


class LiquidityAdvisor(CouncilMember):
    name = "liquidity"
    weight = 1.5

    def score(self, token):
        liq = token.get("liquidity") or 0
        if liq < 10_000: return 0.1
        if liq < 50_000: return 0.4
        if liq < 500_000: return 0.7
        return 0.9


class VolumeAdvisor(CouncilMember):
    name = "volume"
    weight = 1.2

    def score(self, token):
        vol = token.get("volume_24h") or 0
        if vol < 1_000: return 0.1
        if vol < 10_000: return 0.4
        if vol < 100_000: return 0.7
        return 0.9


class MarketCapAdvisor(CouncilMember):
    name = "market_cap"
    weight = 1.0

    def score(self, token):
        mc = token.get("market_cap") or 0
        if mc == 0: return 0.3
        if mc < 100_000: return 0.7
        if mc < 1_000_000: return 0.85
        if mc < 10_000_000: return 0.6
        return 0.3


class MomentumAdvisor(CouncilMember):
    name = "momentum"
    weight = 1.3

    def score(self, token):
        vol = token.get("volume_24h") or 0
        liq = token.get("liquidity") or 1
        ratio = vol / liq if liq > 0 else 0
        if ratio > 2.0: return 0.9
        if ratio > 0.5: return 0.7
        if ratio > 0.1: return 0.5
        return 0.2


COUNCIL = [
    LiquidityAdvisor(),
    VolumeAdvisor(),
    MarketCapAdvisor(),
    MomentumAdvisor(),
]


def convene(token: dict) -> dict:
    total_weight = sum(m.weight for m in COUNCIL)
    votes: Dict[str, float] = {}
    weighted_sum = 0.0
    for m in COUNCIL:
        s = m.score(token)
        votes[m.name] = round(s, 3)
        weighted_sum += s * m.weight
    final_score = weighted_sum / total_weight
    if final_score >= 0.65:
        verdict = "BUY"
    elif final_score >= 0.40:
        verdict = "HOLD"
    else:
        verdict = "SKIP"
    return {"score": round(final_score, 4), "votes": votes, "verdict": verdict}
