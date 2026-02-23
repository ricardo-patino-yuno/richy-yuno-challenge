"""Score aggregation and decision logic.

The decision is DETERMINISTIC: same input + same history = same output.
Priority:
  - Sanctions match always -> DENIED (regardless of total score)
  - Otherwise, cumulative score determines outcome:
    - score >= 50 -> REVIEW (manual compliance review needed)
    - score < 50  -> APPROVED (transaction can proceed)
"""

from app.models import RuleResult


def aggregate_results(
    rule_results: list[RuleResult],
) -> tuple[int, str, list[str], list[str]]:
    """Combine results from all rule checks into a final decision.

    Args:
        rule_results: List of RuleResult from each compliance rule.

    Returns:
        Tuple of (risk_score, decision, all_reasons, all_matched_rules).
    """
    total_score = 0
    all_reasons: list[str] = []
    all_matched_rules: list[str] = []

    for result in rule_results:
        total_score += result.score_delta
        all_reasons.extend(result.reasons)
        all_matched_rules.extend(result.matched_rules)

    # Cap the cumulative score at 100
    total_score = min(total_score, 100)

    # Decision priority: sanctions override everything
    if "SANCTIONS_MATCH" in all_matched_rules:
        decision = "DENIED"
    elif total_score >= 50:
        decision = "REVIEW"
    else:
        decision = "APPROVED"

    return total_score, decision, all_reasons, all_matched_rules
