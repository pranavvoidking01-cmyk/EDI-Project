from collections.abc import Mapping, Sequence


TIER_BASE_SCORES = {
    "urgent": 0.9,
    "informational": 0.45,
    "routine": 0.15,
}


def calculate_priority_score(
    tier: str,
    temporal_entities: Sequence[Mapping[str, str]],
    contact_priority_weight: float = 1.0,
    group_muted: bool = False,
) -> float:
    """Combine NLP tier, temporal signals, contact importance, and mute state."""
    normalized_tier = tier.strip().lower()
    base_score = TIER_BASE_SCORES.get(normalized_tier, TIER_BASE_SCORES["routine"])
    temporal_bonus = min(0.2, len(temporal_entities) * 0.05)
    contact_bonus = max(0.0, min(1.0, contact_priority_weight)) * 0.15
    mute_penalty = 0.2 if group_muted else 0.0

    score = base_score * 0.65 + temporal_bonus + contact_bonus - mute_penalty
    if normalized_tier == "urgent":
        score = max(score, 0.8)
    return round(max(0.0, min(1.0, score)), 3)
