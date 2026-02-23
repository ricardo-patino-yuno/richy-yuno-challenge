"""Tests for the screening engine orchestrator."""

from tests.conftest import make_request


class TestScreeningEngine:
    def test_clean_transaction_approved(self, engine):
        req = make_request()
        resp = engine.screen(req)
        assert resp.decision == "APPROVED"
        assert resp.risk_score == 0
        assert resp.reasons == []
        assert resp.matched_rules == []
        assert resp.transaction_id  # UUID generated

    def test_sanctions_denied(self, engine):
        req = make_request(sender="Mohammad Ahmad")
        resp = engine.screen(req)
        assert resp.decision == "DENIED"
        assert resp.risk_score == 100
        assert "SANCTIONS_MATCH" in resp.matched_rules

    def test_sanctions_fuzzy_denied(self, engine):
        req = make_request(sender="Muhammed Ahmad")
        resp = engine.screen(req)
        assert resp.decision == "DENIED"

    def test_recipient_sanctions_denied(self, engine):
        req = make_request(recipient="Ali Hassan")
        resp = engine.screen(req)
        assert resp.decision == "DENIED"

    def test_high_risk_country_review(self, engine):
        req = make_request(country="IR")
        resp = engine.screen(req)
        assert resp.decision == "REVIEW"
        assert resp.risk_score == 50
        assert "HIGH_RISK_COUNTRY" in resp.matched_rules

    def test_large_amount_review(self, engine):
        req = make_request(amount=2500.0)
        resp = engine.screen(req)
        assert resp.decision == "REVIEW"
        assert "LARGE_AMOUNT" in resp.matched_rules

    def test_velocity_review(self, engine):
        """6th transaction from same sender in 1 hour triggers REVIEW."""
        for i in range(5):
            engine.screen(make_request(
                sender="SpeedySender",
                amount=100 + i * 37,  # vary amounts to avoid structuring
                timestamp=f"2026-02-22T12:0{i}:00Z",
            ))
        resp = engine.screen(make_request(
            sender="SpeedySender",
            amount=330.0,
            timestamp="2026-02-22T12:30:00Z",
        ))
        assert resp.decision == "REVIEW"
        assert "VELOCITY_EXCEEDED" in resp.matched_rules

    def test_structuring_review(self, engine):
        """3 similar amounts from same sender in 30 min triggers REVIEW."""
        engine.screen(make_request(sender="Splitter", amount=500.0, timestamp="2026-02-22T16:00:00Z"))
        engine.screen(make_request(sender="Splitter", amount=490.0, timestamp="2026-02-22T16:05:00Z"))
        resp = engine.screen(make_request(sender="Splitter", amount=510.0, timestamp="2026-02-22T16:10:00Z"))
        assert resp.decision == "REVIEW"
        assert "STRUCTURING_DETECTED" in resp.matched_rules

    def test_combined_country_and_amount(self, engine):
        req = make_request(country="IR", amount=3000.0)
        resp = engine.screen(req)
        assert resp.decision == "REVIEW"
        assert resp.risk_score == 100  # 50 + 50, capped at 100
        assert "HIGH_RISK_COUNTRY" in resp.matched_rules
        assert "LARGE_AMOUNT" in resp.matched_rules

    def test_transaction_stored_after_screening(self, engine, store):
        req = make_request(sender="Tracker")
        engine.screen(req)
        stored = store.get_by_sender("Tracker")
        assert len(stored) == 1
        assert stored[0].sender_name == "Tracker"

    def test_audit_entry_created(self, engine, store):
        req = make_request(sender="Audited")
        resp = engine.screen(req)
        audit = store.get_audit_log(transaction_id=resp.transaction_id)
        assert len(audit) == 1
        assert audit[0].decision == resp.decision
        assert audit[0].risk_score == resp.risk_score

    def test_deterministic_same_input_same_output(self, engine):
        """Same input should produce same decision (sans transaction_id)."""
        req1 = make_request(sender="Deterministic", timestamp="2026-02-22T10:00:00Z")
        req2 = make_request(sender="Deterministic", timestamp="2026-02-22T10:00:00Z")
        resp1 = engine.screen(req1)
        # Note: resp2 will have a second txn in history, so velocity count differs
        # Use a fresh engine for true determinism test
        from app.models import RulesConfig
        from app.screening.engine import ScreeningEngine
        from app.storage.memory import MemoryStore
        fresh_engine = ScreeningEngine(
            sanctions_list=engine.sanctions_list,
            high_risk_countries=engine.high_risk_countries,
            store=MemoryStore(),
            config=RulesConfig(),
        )
        resp2 = fresh_engine.screen(req2)
        assert resp1.decision == resp2.decision
        assert resp1.risk_score == resp2.risk_score
        assert resp1.reasons == resp2.reasons

    def test_unique_transaction_ids(self, engine):
        resp1 = engine.screen(make_request(timestamp="2026-02-22T10:00:00Z"))
        resp2 = engine.screen(make_request(timestamp="2026-02-22T10:01:00Z"))
        assert resp1.transaction_id != resp2.transaction_id

    def test_sanctions_overrides_other_flags(self, engine):
        """Even with country+amount flags, sanctions = DENIED not REVIEW."""
        req = make_request(sender="Mohammad Ahmad", country="IR", amount=5000.0)
        resp = engine.screen(req)
        assert resp.decision == "DENIED"
        assert "SANCTIONS_MATCH" in resp.matched_rules
