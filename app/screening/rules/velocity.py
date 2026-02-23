"""Transaction velocity rule.

Detects unusual frequency of transactions from the same sender.
More than 5 transactions in 1 hour is a red flag for money laundering
or fraud. Legitimate remittance customers typically send 1-2 transactions
per week, so a burst of activity in a short window warrants review.
"""

from datetime import datetime, timedelta

from app.models import RuleResult
from app.storage.memory import MemoryStore


def check_velocity(
    sender_name: str,
    store: MemoryStore,
    timestamp: datetime,
    threshold: int = 5,
    window_minutes: int = 60,
) -> RuleResult:
    """Check if the sender exceeds the transaction velocity threshold.

    Looks back `window_minutes` from the given timestamp and counts
    how many transactions the sender already has. If the count exceeds
    `threshold`, the rule fires with score_delta=30.
    """
    # Calculate the start of the lookback window
    window_start = timestamp - timedelta(minutes=window_minutes)

    # Retrieve the sender's recent transactions within the window
    recent_txns = store.get_by_sender(sender_name, since=window_start)
    # Include the current transaction in the count (not yet stored)
    count = len(recent_txns) + 1

    if count > threshold:
        return RuleResult(
            score_delta=50,
            reasons=[
                f"Sender has {count} transactions in the last "
                f"{window_minutes} minutes (threshold: {threshold})"
            ],
            matched_rules=["VELOCITY_EXCEEDED"],
        )

    return RuleResult(score_delta=0, reasons=[], matched_rules=[])
