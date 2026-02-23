"""Tests for the score aggregation and decision logic."""

from app.models import RuleResult
from app.screening.scorer import aggregate_results


class TestAggregateResults:
    def test_no_rules_triggered(self):
        results = [
            RuleResult(score_delta=0, reasons=[], matched_rules=[]),
            RuleResult(score_delta=0, reasons=[], matched_rules=[]),
        ]
        score, decision, reasons, rules = aggregate_results(results)
        assert score == 0
        assert decision == "APPROVED"
        assert reasons == []
        assert rules == []

    def test_sanctions_always_denied(self):
        results = [
            RuleResult(score_delta=100, reasons=["match"], matched_rules=["SANCTIONS_MATCH"]),
        ]
        score, decision, reasons, rules = aggregate_results(results)
        assert decision == "DENIED"
        assert score == 100

    def test_sanctions_denied_even_with_low_score(self):
        """SANCTIONS_MATCH overrides score-based logic."""
        results = [
            RuleResult(score_delta=10, reasons=["match"], matched_rules=["SANCTIONS_MATCH"]),
        ]
        score, decision, reasons, rules = aggregate_results(results)
        assert decision == "DENIED"

    def test_score_exactly_50_is_review(self):
        results = [
            RuleResult(score_delta=50, reasons=["risk"], matched_rules=["HIGH_RISK_COUNTRY"]),
        ]
        score, decision, reasons, rules = aggregate_results(results)
        assert score == 50
        assert decision == "REVIEW"

    def test_score_49_is_approved(self):
        results = [
            RuleResult(score_delta=49, reasons=["risk"], matched_rules=["SOME_RULE"]),
        ]
        score, decision, reasons, rules = aggregate_results(results)
        assert score == 49
        assert decision == "APPROVED"

    def test_multiple_flags_stack(self):
        results = [
            RuleResult(score_delta=50, reasons=["country"], matched_rules=["HIGH_RISK_COUNTRY"]),
            RuleResult(score_delta=50, reasons=["amount"], matched_rules=["LARGE_AMOUNT"]),
        ]
        score, decision, reasons, rules = aggregate_results(results)
        assert score == 100
        assert decision == "REVIEW"  # Not DENIED — no sanctions
        assert "HIGH_RISK_COUNTRY" in rules
        assert "LARGE_AMOUNT" in rules

    def test_score_capped_at_100(self):
        results = [
            RuleResult(score_delta=50, reasons=["a"], matched_rules=["A"]),
            RuleResult(score_delta=50, reasons=["b"], matched_rules=["B"]),
            RuleResult(score_delta=50, reasons=["c"], matched_rules=["C"]),
        ]
        score, decision, reasons, rules = aggregate_results(results)
        assert score == 100  # 150 capped to 100

    def test_reasons_aggregated(self):
        results = [
            RuleResult(score_delta=50, reasons=["reason1", "reason2"], matched_rules=["A"]),
            RuleResult(score_delta=50, reasons=["reason3"], matched_rules=["B"]),
        ]
        _, _, reasons, _ = aggregate_results(results)
        assert reasons == ["reason1", "reason2", "reason3"]

    def test_matched_rules_aggregated(self):
        results = [
            RuleResult(score_delta=50, reasons=[], matched_rules=["A", "B"]),
            RuleResult(score_delta=50, reasons=[], matched_rules=["C"]),
        ]
        _, _, _, rules = aggregate_results(results)
        assert rules == ["A", "B", "C"]

    def test_empty_results_list(self):
        score, decision, reasons, rules = aggregate_results([])
        assert score == 0
        assert decision == "APPROVED"
        assert reasons == []
        assert rules == []

    def test_sanctions_plus_other_flags(self):
        """Sanctions match + other flags should still be DENIED."""
        results = [
            RuleResult(score_delta=100, reasons=["sanctions"], matched_rules=["SANCTIONS_MATCH"]),
            RuleResult(score_delta=50, reasons=["country"], matched_rules=["HIGH_RISK_COUNTRY"]),
        ]
        score, decision, reasons, rules = aggregate_results(results)
        assert decision == "DENIED"
        assert score == 100  # capped
        assert len(reasons) == 2
