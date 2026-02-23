"""Tests for the country risk rule."""

from app.screening.rules.country_risk import check_country


class TestCheckCountry:
    def test_high_risk_country_iran(self, high_risk_countries):
        result = check_country("IR", high_risk_countries)
        assert result.score_delta == 50
        assert "HIGH_RISK_COUNTRY" in result.matched_rules
        assert any("IR" in r for r in result.reasons)

    def test_high_risk_country_north_korea(self, high_risk_countries):
        result = check_country("KP", high_risk_countries)
        assert result.score_delta == 50

    def test_high_risk_country_syria(self, high_risk_countries):
        result = check_country("SY", high_risk_countries)
        assert result.score_delta == 50

    def test_safe_country_us(self, high_risk_countries):
        result = check_country("US", high_risk_countries)
        assert result.score_delta == 0
        assert result.matched_rules == []
        assert result.reasons == []

    def test_safe_country_mexico(self, high_risk_countries):
        result = check_country("MX", high_risk_countries)
        assert result.score_delta == 0

    def test_safe_country_uk(self, high_risk_countries):
        result = check_country("GB", high_risk_countries)
        assert result.score_delta == 0

    def test_case_insensitive_lowercase(self, high_risk_countries):
        result = check_country("ir", high_risk_countries)
        assert result.score_delta == 50

    def test_case_insensitive_mixed(self, high_risk_countries):
        result = check_country("Ir", high_risk_countries)
        assert result.score_delta == 50

    def test_whitespace_stripped(self, high_risk_countries):
        result = check_country("  IR  ", high_risk_countries)
        assert result.score_delta == 50

    def test_empty_country_set(self):
        result = check_country("IR", set())
        assert result.score_delta == 0

    def test_all_high_risk_countries(self, high_risk_countries):
        for code in ["IR", "KP", "SY", "MM", "YE", "LY", "SO", "SS", "AF", "VE"]:
            result = check_country(code, high_risk_countries)
            assert result.score_delta == 50, f"Failed for {code}"
