"""Transaction amount rule.

Flags transactions that exceed a configurable dollar threshold.
Large individual transfers carry higher risk of being proceeds of
crime or terrorist financing, and may trigger regulatory reporting
requirements (e.g., CTRs for amounts over $10,000 in the US).
"""

from app.models import RuleResult


def check_amount(
    amount: float,
    threshold: float = 2000,
) -> RuleResult:
    """Check if the transaction amount exceeds the threshold.

    Returns score_delta=50 if the amount is above the threshold.
    Large transactions always warrant manual review per compliance policy.
    """
    if amount > threshold:
        return RuleResult(
            score_delta=50,
            reasons=[
                f"Transaction amount ${amount:.2f} exceeds "
                f"threshold of ${threshold:.2f}"
            ],
            matched_rules=["LARGE_AMOUNT"],
        )

    return RuleResult(score_delta=0, reasons=[], matched_rules=[])
