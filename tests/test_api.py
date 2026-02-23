"""Integration tests for the FastAPI endpoints."""

import pytest


class TestHealthEndpoint:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "healthy"}


class TestScreeningEndpoint:
    def _post(self, client, **overrides):
        payload = {
            "sender_name": "Maria Garcia",
            "recipient_name": "Rosa Delgado",
            "amount": 150.0,
            "currency": "USD",
            "destination_country": "MX",
            "timestamp": "2026-02-22T10:00:00Z",
        }
        payload.update(overrides)
        return client.post("/api/screening", json=payload)

    def test_approved(self, client):
        resp = self._post(client)
        assert resp.status_code == 200
        data = resp.json()
        assert data["decision"] == "APPROVED"
        assert data["risk_score"] == 0
        assert "transaction_id" in data

    def test_denied_sanctions_sender(self, client):
        resp = self._post(client, sender_name="Mohammad Ahmad")
        data = resp.json()
        assert data["decision"] == "DENIED"
        assert data["risk_score"] == 100
        assert "SANCTIONS_MATCH" in data["matched_rules"]

    def test_denied_sanctions_recipient(self, client):
        resp = self._post(client, recipient_name="Ali Hassan")
        data = resp.json()
        assert data["decision"] == "DENIED"

    def test_denied_sanctions_fuzzy(self, client):
        resp = self._post(client, sender_name="Muhammed Ahmad")
        data = resp.json()
        assert data["decision"] == "DENIED"

    def test_review_high_risk_country(self, client):
        resp = self._post(client, destination_country="IR")
        data = resp.json()
        assert data["decision"] == "REVIEW"
        assert "HIGH_RISK_COUNTRY" in data["matched_rules"]

    def test_review_large_amount(self, client):
        resp = self._post(client, amount=3000.0)
        data = resp.json()
        assert data["decision"] == "REVIEW"
        assert "LARGE_AMOUNT" in data["matched_rules"]

    def test_review_velocity(self, client):
        for i in range(5):
            self._post(client, sender_name="VelocityAPI", amount=100 + i * 31, timestamp=f"2026-02-23T12:0{i}:00Z")
        resp = self._post(client, sender_name="VelocityAPI", amount=330.0, timestamp="2026-02-23T12:30:00Z")
        data = resp.json()
        assert data["decision"] == "REVIEW"
        assert "VELOCITY_EXCEEDED" in data["matched_rules"]

    def test_review_structuring(self, client):
        self._post(client, sender_name="StructAPI", amount=500.0, timestamp="2026-02-22T16:00:00Z")
        self._post(client, sender_name="StructAPI", amount=490.0, timestamp="2026-02-22T16:05:00Z")
        resp = self._post(client, sender_name="StructAPI", amount=510.0, timestamp="2026-02-22T16:10:00Z")
        data = resp.json()
        assert data["decision"] == "REVIEW"
        assert "STRUCTURING_DETECTED" in data["matched_rules"]

    def test_response_has_reasons(self, client):
        resp = self._post(client, destination_country="KP")
        data = resp.json()
        assert len(data["reasons"]) > 0
        assert "KP" in data["reasons"][0]

    def test_invalid_payload_422(self, client):
        resp = client.post("/api/screening", json={"sender_name": "Only this"})
        assert resp.status_code == 422

    def test_empty_body_422(self, client):
        resp = client.post("/api/screening", json={})
        assert resp.status_code == 422


class TestBatchEndpoint:
    def test_batch_mixed(self, client):
        payload = {
            "transactions": [
                {"sender_name": "Clean Person", "recipient_name": "Other", "amount": 100, "currency": "USD", "destination_country": "US", "timestamp": "2026-02-22T10:00:00Z"},
                {"sender_name": "Omar Farooq", "recipient_name": "Test", "amount": 200, "currency": "USD", "destination_country": "US", "timestamp": "2026-02-22T10:00:00Z"},
                {"sender_name": "Safe Person", "recipient_name": "Friend", "amount": 300, "currency": "USD", "destination_country": "IR", "timestamp": "2026-02-22T10:00:00Z"},
            ]
        }
        resp = client.post("/api/screening/batch", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["total"] == 3
        assert data["summary"]["approved"] >= 1
        assert data["summary"]["denied"] >= 1
        assert data["summary"]["review"] >= 1
        assert len(data["results"]) == 3

    def test_batch_all_approved(self, client):
        payload = {
            "transactions": [
                {"sender_name": "A", "recipient_name": "B", "amount": 100, "currency": "USD", "destination_country": "US", "timestamp": "2026-02-22T10:00:00Z"},
                {"sender_name": "C", "recipient_name": "D", "amount": 200, "currency": "USD", "destination_country": "MX", "timestamp": "2026-02-22T11:00:00Z"},
            ]
        }
        resp = client.post("/api/screening/batch", json=payload)
        data = resp.json()
        assert data["summary"]["approved"] == 2
        assert data["summary"]["denied"] == 0
        assert data["summary"]["review"] == 0

    def test_batch_common_risk_factors(self, client):
        payload = {
            "transactions": [
                {"sender_name": "A", "recipient_name": "B", "amount": 100, "currency": "USD", "destination_country": "IR", "timestamp": "2026-02-22T10:00:00Z"},
                {"sender_name": "C", "recipient_name": "D", "amount": 200, "currency": "USD", "destination_country": "KP", "timestamp": "2026-02-22T11:00:00Z"},
            ]
        }
        resp = client.post("/api/screening/batch", json=payload)
        data = resp.json()
        assert "HIGH_RISK_COUNTRY" in data["summary"]["common_risk_factors"]

    def test_batch_empty_list(self, client):
        resp = client.post("/api/screening/batch", json={"transactions": []})
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["total"] == 0


class TestTransactionsEndpoint:
    def test_get_transactions_after_screening(self, client):
        client.post("/api/screening", json={
            "sender_name": "HistoryTest", "recipient_name": "B", "amount": 100,
            "currency": "USD", "destination_country": "US", "timestamp": "2026-02-22T10:00:00Z"
        })
        resp = client.get("/api/transactions/HistoryTest?hours=48")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["sender_name"] == "HistoryTest"

    def test_nonexistent_customer_empty(self, client):
        resp = client.get("/api/transactions/NobodyAtAll?hours=24")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_url_encoded_customer_id(self, client):
        client.post("/api/screening", json={
            "sender_name": "John Smith", "recipient_name": "B", "amount": 100,
            "currency": "USD", "destination_country": "US", "timestamp": "2026-02-22T10:00:00Z"
        })
        resp = client.get("/api/transactions/John%20Smith?hours=48")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


class TestRulesEndpoint:
    def test_get_rules(self, client):
        resp = client.get("/api/rules")
        assert resp.status_code == 200
        data = resp.json()
        assert data["velocity_threshold"] == 5
        assert data["amount_threshold"] == 2000
        assert data["fuzzy_match_threshold"] == 85

    def test_update_rules(self, client):
        new_config = {
            "velocity_threshold": 3,
            "velocity_window_minutes": 30,
            "amount_threshold": 1000,
            "structuring_window_minutes": 15,
            "structuring_min_count": 2,
            "structuring_amount_variance": 0.10,
            "fuzzy_match_threshold": 90,
        }
        resp = client.put("/api/rules", json=new_config)
        assert resp.status_code == 200
        data = resp.json()
        assert data["amount_threshold"] == 1000

    def test_updated_rules_take_effect(self, client):
        # First: $1500 should be APPROVED with default threshold of $2000
        resp = client.post("/api/screening", json={
            "sender_name": "RuleTest", "recipient_name": "B", "amount": 1500,
            "currency": "USD", "destination_country": "US", "timestamp": "2026-02-22T10:00:00Z"
        })
        assert resp.json()["decision"] == "APPROVED"

        # Change threshold to $1000
        client.put("/api/rules", json={
            "velocity_threshold": 5, "velocity_window_minutes": 60,
            "amount_threshold": 1000, "structuring_window_minutes": 30,
            "structuring_min_count": 3, "structuring_amount_variance": 0.20,
            "fuzzy_match_threshold": 85,
        })

        # Now $1500 should trigger REVIEW
        resp = client.post("/api/screening", json={
            "sender_name": "RuleTest2", "recipient_name": "B", "amount": 1500,
            "currency": "USD", "destination_country": "US", "timestamp": "2026-02-22T11:00:00Z"
        })
        assert resp.json()["decision"] == "REVIEW"

        # Restore defaults
        client.put("/api/rules", json={
            "velocity_threshold": 5, "velocity_window_minutes": 60,
            "amount_threshold": 2000, "structuring_window_minutes": 30,
            "structuring_min_count": 3, "structuring_amount_variance": 0.20,
            "fuzzy_match_threshold": 85,
        })


class TestAuditEndpoint:
    def test_audit_populated_after_screening(self, client):
        client.post("/api/screening", json={
            "sender_name": "AuditTest", "recipient_name": "B", "amount": 100,
            "currency": "USD", "destination_country": "US", "timestamp": "2026-02-22T10:00:00Z"
        })
        resp = client.get("/api/audit")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    def test_audit_filter_by_transaction_id(self, client):
        resp = client.post("/api/screening", json={
            "sender_name": "AuditFilter", "recipient_name": "B", "amount": 100,
            "currency": "USD", "destination_country": "US", "timestamp": "2026-02-22T10:00:00Z"
        })
        tx_id = resp.json()["transaction_id"]
        audit_resp = client.get(f"/api/audit?transaction_id={tx_id}")
        data = audit_resp.json()
        assert len(data) == 1
        assert data[0]["transaction_id"] == tx_id

    def test_audit_contains_full_request(self, client):
        client.post("/api/screening", json={
            "sender_name": "FullAudit", "recipient_name": "B", "amount": 100,
            "currency": "USD", "destination_country": "US", "timestamp": "2026-02-22T10:00:00Z"
        })
        resp = client.get("/api/audit")
        entries = [e for e in resp.json() if e["request"]["sender_name"] == "FullAudit"]
        assert len(entries) >= 1
        assert "request" in entries[0]
        assert entries[0]["request"]["sender_name"] == "FullAudit"
        assert "decision" in entries[0]
        assert "risk_score" in entries[0]

    def test_audit_filter_by_date_range(self, client):
        client.post("/api/screening", json={
            "sender_name": "DateTest", "recipient_name": "B", "amount": 100,
            "currency": "USD", "destination_country": "US", "timestamp": "2026-02-22T10:00:00Z"
        })
        resp = client.get("/api/audit?from_date=2026-02-22T00:00:00Z&to_date=2026-02-22T23:59:59Z")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
