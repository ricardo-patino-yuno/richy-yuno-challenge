"""Structuring detection rule.

Identifies attempts to break large transactions into smaller ones to
evade reporting thresholds (e.g., the $10,000 CTR threshold in the US).
Example: sending 5 x $500 in 30 minutes instead of 1 x $2,500.

We look for 3+ transactions from the same sender within a time window
where all amounts are within 20% of each other -- indicating deliberate
splitting. The algorithm finds the largest cluster of similar amounts
by checking, for each amount, how many others fall within +/-20% of it.
"""

from datetime import datetime, timedelta

from app.models import RuleResult
from app.storage.memory import MemoryStore


def check_structuring(
    sender_name: str,
    amount: float,
    store: MemoryStore,
    timestamp: datetime,
    window_minutes: int = 30,
    min_count: int = 3,
    amount_variance: float = 0.20,
) -> RuleResult:
    """Detect potential transaction structuring by the sender.

    Retrieves recent transactions within the time window, includes the
    current transaction amount, and checks whether any cluster of
    `min_count` or more amounts are all within `amount_variance` (20%)
    of each other.
    """
    # Lookback window for related transactions
    window_start = timestamp - timedelta(minutes=window_minutes)
    recent_txns = store.get_by_sender(sender_name, since=window_start)

    # Combine historical amounts with the current transaction amount
    all_amounts = [t.amount for t in recent_txns] + [amount]

    # Not enough transactions to constitute structuring
    if len(all_amounts) < min_count:
        return RuleResult(score_delta=0, reasons=[], matched_rules=[])

    # For each amount, count how many others are within +/- variance.
    # If any single amount serves as a "center" with >= min_count neighbors
    # (including itself), we flag structuring.
    max_cluster_size = 0
    best_center = 0.0
    best_cluster_amounts: list[float] = []

    for center in all_amounts:
        lower_bound = center * (1 - amount_variance)
        upper_bound = center * (1 + amount_variance)
        cluster = [a for a in all_amounts if lower_bound <= a <= upper_bound]

        if len(cluster) > max_cluster_size:
            max_cluster_size = len(cluster)
            best_center = center
            best_cluster_amounts = cluster

    if max_cluster_size >= min_count:
        avg_amount = sum(best_cluster_amounts) / len(best_cluster_amounts)
        return RuleResult(
            score_delta=50,
            reasons=[
                f"Potential structuring detected: {max_cluster_size} transactions "
                f"of similar amounts (~${avg_amount:.2f}) within "
                f"{window_minutes} minutes"
            ],
            matched_rules=["STRUCTURING_DETECTED"],
        )

    return RuleResult(score_delta=0, reasons=[], matched_rules=[])
