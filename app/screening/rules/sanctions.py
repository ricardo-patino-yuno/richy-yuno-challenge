"""Sanctions list matching rule.

Checks sender AND recipient names against a sanctions list using fuzzy
string matching. Uses thefuzz for fuzzy matching to catch name variations
like "Mohammad Ahmad" vs "Mohammed Ahmed" -- common in cross-border
remittances where transliteration differences are frequent.

Two matching strategies:
  - fuzz.ratio(): overall character-level string similarity
  - fuzz.token_sort_ratio(): handles name reordering
    ("Ahmad Mohammad" vs "Mohammad Ahmad")

The higher of the two scores is used. A threshold of 85 balances catching
real variants without generating excessive false positives.
"""

import re

from thefuzz import fuzz

from app.models import RuleResult


def _normalize_name(name: str) -> str:
    """Lowercase, strip, and collapse multiple spaces."""
    return re.sub(r"\s+", " ", name.strip().lower())


def check_sanctions(
    sender_name: str,
    recipient_name: str,
    sanctions_list: list[str],
    threshold: int = 85,
) -> RuleResult:
    """Screen sender and recipient names against the sanctions list.

    Returns a RuleResult with score_delta=100 if any name matches a
    sanctioned entity above the similarity threshold, or score_delta=0
    if no match is found.
    """
    reasons: list[str] = []
    matched_rules: list[str] = []

    # Check both sender and recipient against every sanctioned name
    names_to_check = [
        ("Sender", sender_name),
        ("Recipient", recipient_name),
    ]

    for role, name in names_to_check:
        normalized_name = _normalize_name(name)
        for sanctioned in sanctions_list:
            normalized_sanctioned = _normalize_name(sanctioned)

            # Use the higher of two fuzzy matching strategies:
            # ratio() for overall similarity, token_sort_ratio() for reordered tokens
            score = max(
                fuzz.ratio(normalized_name, normalized_sanctioned),
                fuzz.token_sort_ratio(normalized_name, normalized_sanctioned),
            )

            if score >= threshold:
                reasons.append(
                    f"{role} '{name}' matches sanctioned entity "
                    f"'{sanctioned}' (similarity: {score}%)"
                )
                # Only add the rule tag once, even if multiple names match
                if "SANCTIONS_MATCH" not in matched_rules:
                    matched_rules.append("SANCTIONS_MATCH")

    # Sanctions match is an instant denial -- score_delta of 100
    score_delta = 100 if matched_rules else 0

    return RuleResult(
        score_delta=score_delta,
        reasons=reasons,
        matched_rules=matched_rules,
    )
