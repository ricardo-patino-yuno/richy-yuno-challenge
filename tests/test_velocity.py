"""Tests for the transaction velocity rule."""

from app.screening.rules.velocity import check_velocity
from tests.conftest import make_stored


class TestCheckVelocity:
    def test_no_history_no_flag(self, store):
        """First transaction from a sender should not trigger velocity."""
        from datetime import datetime, timezone
        ts = datetime(2026, 2, 22, 12, 0, tzinfo=timezone.utc)
        result = check_velocity("New Sender", store, ts)
        # count = 0 + 1 (current) = 1, threshold = 5
        assert result.score_delta == 0
        assert result.matched_rules == []

    def test_under_threshold(self, store):
        """4 stored + 1 current = 5, which is NOT > 5."""
        from datetime import datetime, timezone
        for i in range(4):
            store.add(make_stored(
                sender="Test User",
                timestamp=f"2026-02-22T12:0{i}:00Z",
                tx_id=f"tx-{i}",
            ))
        ts = datetime(2026, 2, 22, 12, 30, tzinfo=timezone.utc)
        result = check_velocity("Test User", store, ts)
        assert result.score_delta == 0

    def test_at_threshold_triggers(self, store):
        """5 stored + 1 current = 6, which IS > 5."""
        from datetime import datetime, timezone
        for i in range(5):
            store.add(make_stored(
                sender="Test User",
                timestamp=f"2026-02-22T12:{i:02d}:00Z",
                tx_id=f"tx-{i}",
            ))
        ts = datetime(2026, 2, 22, 12, 30, tzinfo=timezone.utc)
        result = check_velocity("Test User", store, ts)
        assert result.score_delta == 50
        assert "VELOCITY_EXCEEDED" in result.matched_rules
        assert any("6 transactions" in r for r in result.reasons)

    def test_well_over_threshold(self, store):
        """10 stored + 1 current = 11."""
        from datetime import datetime, timezone
        for i in range(10):
            store.add(make_stored(
                sender="Busy Sender",
                timestamp=f"2026-02-22T12:{i:02d}:00Z",
                tx_id=f"tx-{i}",
            ))
        ts = datetime(2026, 2, 22, 12, 30, tzinfo=timezone.utc)
        result = check_velocity("Busy Sender", store, ts)
        assert result.score_delta == 50
        assert any("11 transactions" in r for r in result.reasons)

    def test_outside_window_not_counted(self, store):
        """Transactions older than 60 minutes should not count."""
        from datetime import datetime, timezone
        for i in range(6):
            store.add(make_stored(
                sender="Old Sender",
                timestamp=f"2026-02-22T10:0{i}:00Z",  # 2 hours before
                tx_id=f"tx-{i}",
            ))
        ts = datetime(2026, 2, 22, 12, 0, tzinfo=timezone.utc)
        result = check_velocity("Old Sender", store, ts)
        assert result.score_delta == 0

    def test_different_sender_not_counted(self, store):
        """Transactions from other senders should not affect velocity."""
        from datetime import datetime, timezone
        for i in range(6):
            store.add(make_stored(
                sender="Other Person",
                timestamp=f"2026-02-22T12:0{i}:00Z",
                tx_id=f"tx-{i}",
            ))
        ts = datetime(2026, 2, 22, 12, 30, tzinfo=timezone.utc)
        result = check_velocity("Target Sender", store, ts)
        assert result.score_delta == 0

    def test_custom_threshold(self, store):
        """Custom threshold of 2: 2 stored + 1 current = 3 > 2."""
        from datetime import datetime, timezone
        for i in range(2):
            store.add(make_stored(
                sender="Test",
                timestamp=f"2026-02-22T12:0{i}:00Z",
                tx_id=f"tx-{i}",
            ))
        ts = datetime(2026, 2, 22, 12, 30, tzinfo=timezone.utc)
        result = check_velocity("Test", store, ts, threshold=2)
        assert result.score_delta == 50

    def test_custom_window(self, store):
        """Custom window of 10 minutes — older txns excluded."""
        from datetime import datetime, timezone
        for i in range(6):
            store.add(make_stored(
                sender="Test",
                timestamp=f"2026-02-22T12:0{i}:00Z",
                tx_id=f"tx-{i}",
            ))
        ts = datetime(2026, 2, 22, 12, 30, tzinfo=timezone.utc)
        result = check_velocity("Test", store, ts, window_minutes=10)
        # All 6 txns are 20+ minutes old, outside 10-min window
        assert result.score_delta == 0

    def test_case_insensitive_sender(self, store):
        """Sender lookup should be case-insensitive."""
        from datetime import datetime, timezone
        for i in range(5):
            store.add(make_stored(
                sender="John Smith",
                timestamp=f"2026-02-22T12:0{i}:00Z",
                tx_id=f"tx-{i}",
            ))
        ts = datetime(2026, 2, 22, 12, 30, tzinfo=timezone.utc)
        result = check_velocity("john smith", store, ts)
        assert result.score_delta == 50
