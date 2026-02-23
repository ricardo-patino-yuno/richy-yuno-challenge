"""Tests for the in-memory storage."""

from datetime import datetime, timezone
from app.models import AuditEntry, TransactionRequest
from app.storage.memory import MemoryStore
from tests.conftest import make_stored


class TestMemoryStoreAdd:
    def test_add_and_retrieve(self, store):
        tx = make_stored(sender="John Smith", tx_id="tx-1")
        store.add(tx)
        results = store.get_by_sender("John Smith")
        assert len(results) == 1
        assert results[0].transaction_id == "tx-1"

    def test_add_multiple_same_sender(self, store):
        store.add(make_stored(sender="John", tx_id="tx-1"))
        store.add(make_stored(sender="John", tx_id="tx-2"))
        store.add(make_stored(sender="John", tx_id="tx-3"))
        assert len(store.get_by_sender("John")) == 3

    def test_different_senders_isolated(self, store):
        store.add(make_stored(sender="Alice", tx_id="tx-1"))
        store.add(make_stored(sender="Bob", tx_id="tx-2"))
        assert len(store.get_by_sender("Alice")) == 1
        assert len(store.get_by_sender("Bob")) == 1

    def test_nonexistent_sender_empty(self, store):
        assert store.get_by_sender("Nobody") == []


class TestMemoryStoreNormalization:
    def test_case_insensitive(self, store):
        store.add(make_stored(sender="John Smith", tx_id="tx-1"))
        assert len(store.get_by_sender("john smith")) == 1
        assert len(store.get_by_sender("JOHN SMITH")) == 1

    def test_whitespace_stripped(self, store):
        store.add(make_stored(sender="John Smith", tx_id="tx-1"))
        assert len(store.get_by_sender("  John Smith  ")) == 1


class TestMemoryStoreTimestampFilter:
    def test_filter_by_since(self, store):
        store.add(make_stored(sender="A", timestamp="2026-02-22T10:00:00Z", tx_id="old"))
        store.add(make_stored(sender="A", timestamp="2026-02-22T14:00:00Z", tx_id="new"))
        since = datetime(2026, 2, 22, 12, 0, tzinfo=timezone.utc)
        results = store.get_by_sender("A", since=since)
        assert len(results) == 1
        assert results[0].transaction_id == "new"

    def test_no_since_returns_all(self, store):
        store.add(make_stored(sender="A", timestamp="2026-02-22T10:00:00Z", tx_id="1"))
        store.add(make_stored(sender="A", timestamp="2026-02-22T14:00:00Z", tx_id="2"))
        assert len(store.get_by_sender("A")) == 2


class TestMemoryStoreGetAll:
    def test_get_all_no_filter(self, store):
        store.add(make_stored(sender="A", tx_id="1"))
        store.add(make_stored(sender="B", tx_id="2"))
        assert len(store.get_all()) == 2

    def test_get_all_with_since(self, store):
        store.add(make_stored(sender="A", timestamp="2026-02-22T10:00:00Z", tx_id="1"))
        store.add(make_stored(sender="A", timestamp="2026-02-22T14:00:00Z", tx_id="2"))
        since = datetime(2026, 2, 22, 12, 0, tzinfo=timezone.utc)
        results = store.get_all(since=since)
        assert len(results) == 1

    def test_get_all_with_until(self, store):
        store.add(make_stored(sender="A", timestamp="2026-02-22T10:00:00Z", tx_id="1"))
        store.add(make_stored(sender="A", timestamp="2026-02-22T14:00:00Z", tx_id="2"))
        until = datetime(2026, 2, 22, 12, 0, tzinfo=timezone.utc)
        results = store.get_all(until=until)
        assert len(results) == 1

    def test_get_all_empty(self, store):
        assert store.get_all() == []


class TestMemoryStoreAudit:
    def _make_audit(self, tx_id="tx-1", ts="2026-02-22T10:00:00Z"):
        return AuditEntry(
            transaction_id=tx_id,
            timestamp=datetime.fromisoformat(ts.replace("Z", "+00:00")),
            request=TransactionRequest(
                sender_name="A", recipient_name="B", amount=100,
                currency="USD", destination_country="US",
                timestamp=datetime.fromisoformat(ts.replace("Z", "+00:00")),
            ),
            decision="APPROVED",
            risk_score=0,
            reasons=[],
            matched_rules=[],
        )

    def test_add_and_get_audit(self, store):
        store.add_audit(self._make_audit("tx-1"))
        store.add_audit(self._make_audit("tx-2"))
        assert len(store.get_audit_log()) == 2

    def test_filter_by_transaction_id(self, store):
        store.add_audit(self._make_audit("tx-1"))
        store.add_audit(self._make_audit("tx-2"))
        results = store.get_audit_log(transaction_id="tx-1")
        assert len(results) == 1
        assert results[0].transaction_id == "tx-1"

    def test_filter_by_since(self, store):
        store.add_audit(self._make_audit("tx-1", "2026-02-22T10:00:00Z"))
        store.add_audit(self._make_audit("tx-2", "2026-02-22T14:00:00Z"))
        since = datetime(2026, 2, 22, 12, 0, tzinfo=timezone.utc)
        results = store.get_audit_log(since=since)
        assert len(results) == 1
        assert results[0].transaction_id == "tx-2"

    def test_filter_by_until(self, store):
        store.add_audit(self._make_audit("tx-1", "2026-02-22T10:00:00Z"))
        store.add_audit(self._make_audit("tx-2", "2026-02-22T14:00:00Z"))
        until = datetime(2026, 2, 22, 12, 0, tzinfo=timezone.utc)
        results = store.get_audit_log(until=until)
        assert len(results) == 1
        assert results[0].transaction_id == "tx-1"

    def test_empty_audit_log(self, store):
        assert store.get_audit_log() == []
