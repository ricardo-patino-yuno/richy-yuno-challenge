"""Tests for the large amount rule."""

from app.screening.rules.amount import check_amount


class TestCheckAmount:
    def test_above_threshold(self):
        result = check_amount(2500.0)
        assert result.score_delta == 50
        assert "LARGE_AMOUNT" in result.matched_rules
        assert any("2500" in r for r in result.reasons)

    def test_exactly_at_threshold(self):
        """$2000 is NOT > $2000, should not trigger."""
        result = check_amount(2000.0)
        assert result.score_delta == 0
        assert result.matched_rules == []

    def test_just_above_threshold(self):
        result = check_amount(2000.01)
        assert result.score_delta == 50

    def test_below_threshold(self):
        result = check_amount(500.0)
        assert result.score_delta == 0

    def test_zero_amount(self):
        result = check_amount(0.0)
        assert result.score_delta == 0

    def test_very_large_amount(self):
        result = check_amount(50000.0)
        assert result.score_delta == 50
        assert any("50000" in r for r in result.reasons)

    def test_custom_threshold_lower(self):
        result = check_amount(1500.0, threshold=1000)
        assert result.score_delta == 50

    def test_custom_threshold_higher(self):
        result = check_amount(2500.0, threshold=5000)
        assert result.score_delta == 0

    def test_negative_amount(self):
        result = check_amount(-100.0)
        assert result.score_delta == 0

    def test_small_amount(self):
        result = check_amount(50.0)
        assert result.score_delta == 0

    def test_reason_includes_threshold(self):
        result = check_amount(3000.0, threshold=2000)
        assert any("2000" in r for r in result.reasons)
