"""Country risk rule.

Checks whether the destination country is classified as a high-risk
jurisdiction. High-risk countries typically include those subject to
international sanctions, known for terrorism financing, or with
inadequate AML controls (per FATF grey/black lists).
"""

from app.models import RuleResult


def check_country(
    destination_country: str,
    high_risk_countries: set[str],
) -> RuleResult:
    """Check if the destination country is in the high-risk set.

    Country codes are compared in uppercase (ISO 3166-1 alpha-2).
    Returns score_delta=50 if the country is high-risk, 0 otherwise.
    High-risk jurisdictions always warrant manual review per compliance policy.
    """
    country_upper = destination_country.strip().upper()

    if country_upper in high_risk_countries:
        return RuleResult(
            score_delta=50,
            reasons=[
                f"Destination country '{country_upper}' is a high-risk jurisdiction"
            ],
            matched_rules=["HIGH_RISK_COUNTRY"],
        )

    return RuleResult(score_delta=0, reasons=[], matched_rules=[])
