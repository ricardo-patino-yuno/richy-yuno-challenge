"""Tests for the sanctions matching rule."""

from app.screening.rules.sanctions import check_sanctions, _normalize_name


class TestNormalizeName:
    def test_lowercase(self):
        assert _normalize_name("JOHN DOE") == "john doe"

    def test_strip_whitespace(self):
        assert _normalize_name("  john doe  ") == "john doe"

    def test_collapse_multiple_spaces(self):
        assert _normalize_name("john   doe") == "john doe"

    def test_mixed(self):
        assert _normalize_name("  JOHN   DOE  ") == "john doe"


class TestCheckSanctions:
    def test_exact_sender_match(self, sanctions_list):
        result = check_sanctions("Mohammad Ahmad", "Clean Person", sanctions_list)
        assert result.score_delta == 100
        assert "SANCTIONS_MATCH" in result.matched_rules
        assert any("Sender" in r and "Mohammad Ahmad" in r for r in result.reasons)

    def test_exact_recipient_match(self, sanctions_list):
        result = check_sanctions("Clean Person", "Ali Hassan", sanctions_list)
        assert result.score_delta == 100
        assert "SANCTIONS_MATCH" in result.matched_rules
        assert any("Recipient" in r and "Ali Hassan" in r for r in result.reasons)

    def test_fuzzy_sender_match(self, sanctions_list):
        result = check_sanctions("Muhammed Ahmad", "Clean Person", sanctions_list)
        assert result.score_delta == 100
        assert "SANCTIONS_MATCH" in result.matched_rules

    def test_token_sort_match(self, sanctions_list):
        """Name reordering should still match via token_sort_ratio."""
        result = check_sanctions("Ahmad Mohammad", "Clean Person", sanctions_list)
        assert result.score_delta == 100
        assert "SANCTIONS_MATCH" in result.matched_rules

    def test_both_sender_and_recipient_match(self, sanctions_list):
        result = check_sanctions("Mohammad Ahmad", "Ali Hassan", sanctions_list)
        assert result.score_delta == 100
        assert "SANCTIONS_MATCH" in result.matched_rules
        sender_reasons = [r for r in result.reasons if "Sender" in r]
        recipient_reasons = [r for r in result.reasons if "Recipient" in r]
        assert len(sender_reasons) > 0
        assert len(recipient_reasons) > 0

    def test_no_match_clean_names(self, sanctions_list):
        result = check_sanctions("Maria Garcia", "Rosa Delgado", sanctions_list)
        assert result.score_delta == 0
        assert result.matched_rules == []
        assert result.reasons == []

    def test_organization_match(self, sanctions_list):
        result = check_sanctions("Al-Rashid Trading Company", "Someone", sanctions_list)
        assert result.score_delta == 100
        assert "SANCTIONS_MATCH" in result.matched_rules

    def test_below_threshold_no_match(self, sanctions_list):
        """A name that's vaguely similar but below 85 should not match."""
        result = check_sanctions("Maria Ahmad", "Clean Person", sanctions_list)
        assert result.score_delta == 0

    def test_case_insensitive(self, sanctions_list):
        result = check_sanctions("MOHAMMAD AHMAD", "Clean", sanctions_list)
        assert result.score_delta == 100

    def test_custom_threshold(self, sanctions_list):
        """With threshold=100, only exact matches trigger."""
        result = check_sanctions("Muhammed Ahmad", "Clean", sanctions_list, threshold=100)
        assert result.score_delta == 0

    def test_custom_threshold_exact(self, sanctions_list):
        result = check_sanctions("Mohammad Ahmad", "Clean", sanctions_list, threshold=100)
        assert result.score_delta == 100

    def test_empty_sanctions_list(self):
        result = check_sanctions("Mohammad Ahmad", "Ali Hassan", [])
        assert result.score_delta == 0
        assert result.matched_rules == []

    def test_sanctions_match_appears_once(self, sanctions_list):
        """SANCTIONS_MATCH should only appear once even if multiple names match."""
        result = check_sanctions("Mohammad Ahmad", "Ali Hassan", sanctions_list)
        assert result.matched_rules.count("SANCTIONS_MATCH") == 1

    def test_close_variant_victor_petroff(self, sanctions_list):
        result = check_sanctions("Viktor Petrof", "Clean", sanctions_list)
        assert result.score_delta == 100

    def test_similarity_percentage_in_reasons(self, sanctions_list):
        result = check_sanctions("Mohammad Ahmad", "Clean", sanctions_list)
        assert any("similarity:" in r for r in result.reasons)
