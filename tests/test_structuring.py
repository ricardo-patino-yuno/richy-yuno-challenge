"""Tests for the structuring detection rule."""

from app.screening.rules.structuring import check_structuring
from tests.conftest import make_stored


class TestCheckStructuring:
    def test_no_history_no_flag(self, store):
        """Single transaction cannot be structuring."""
        from datetime import datetime, timezone
        ts = datetime(2026, 2, 22, 16, 10, tzinfo=timezone.utc)
        result = check_structuring("Sender", 500.0, store, ts)
        assert result.score_delta == 0

    def test_two_similar_not_enough(self, store):
        """2 similar amounts (1 stored + 1 current) < min_count=3."""
        from datetime import datetime, timezone
        store.add(make_stored(sender="Sender", amount=500.0, timestamp="2026-02-22T16:00:00Z", tx_id="tx-1"))
        ts = datetime(2026, 2, 22, 16, 10, tzinfo=timezone.utc)
        result = check_structuring("Sender", 490.0, store, ts)
        assert result.score_delta == 0

    def test_three_similar_triggers(self, store):
        """3 similar amounts (2 stored + 1 current) = min_count=3."""
        from datetime import datetime, timezone
        store.add(make_stored(sender="Sender", amount=500.0, timestamp="2026-02-22T16:00:00Z", tx_id="tx-1"))
        store.add(make_stored(sender="Sender", amount=490.0, timestamp="2026-02-22T16:05:00Z", tx_id="tx-2"))
        ts = datetime(2026, 2, 22, 16, 10, tzinfo=timezone.utc)
        result = check_structuring("Sender", 510.0, store, ts)
        assert result.score_delta == 50
        assert "STRUCTURING_DETECTED" in result.matched_rules

    def test_five_similar_triggers(self, store):
        """Classic structuring: 5 x ~$500 in 25 minutes."""
        from datetime import datetime, timezone
        amounts_ts = [
            (490.0, "2026-02-22T16:00:00Z"),
            (500.0, "2026-02-22T16:06:00Z"),
            (510.0, "2026-02-22T16:12:00Z"),
            (495.0, "2026-02-22T16:19:00Z"),
        ]
        for i, (amt, ts_str) in enumerate(amounts_ts):
            store.add(make_stored(sender="Diego", amount=amt, timestamp=ts_str, tx_id=f"tx-{i}"))
        ts = datetime(2026, 2, 22, 16, 25, tzinfo=timezone.utc)
        result = check_structuring("Diego", 505.0, store, ts)
        assert result.score_delta == 50
        assert any("5 transactions" in r for r in result.reasons)

    def test_dissimilar_amounts_no_flag(self, store):
        """Amounts that vary by more than 20% should not cluster."""
        from datetime import datetime, timezone
        store.add(make_stored(sender="Sender", amount=100.0, timestamp="2026-02-22T16:00:00Z", tx_id="tx-1"))
        store.add(make_stored(sender="Sender", amount=500.0, timestamp="2026-02-22T16:05:00Z", tx_id="tx-2"))
        ts = datetime(2026, 2, 22, 16, 10, tzinfo=timezone.utc)
        result = check_structuring("Sender", 900.0, store, ts)
        assert result.score_delta == 0

    def test_outside_window_not_counted(self, store):
        """Transactions older than 30 minutes should be excluded."""
        from datetime import datetime, timezone
        store.add(make_stored(sender="Sender", amount=500.0, timestamp="2026-02-22T15:00:00Z", tx_id="tx-1"))
        store.add(make_stored(sender="Sender", amount=490.0, timestamp="2026-02-22T15:05:00Z", tx_id="tx-2"))
        ts = datetime(2026, 2, 22, 16, 10, tzinfo=timezone.utc)
        result = check_structuring("Sender", 510.0, store, ts)
        assert result.score_delta == 0

    def test_different_sender_not_counted(self, store):
        """Only the target sender's transactions should be checked."""
        from datetime import datetime, timezone
        store.add(make_stored(sender="Other", amount=500.0, timestamp="2026-02-22T16:00:00Z", tx_id="tx-1"))
        store.add(make_stored(sender="Other", amount=490.0, timestamp="2026-02-22T16:05:00Z", tx_id="tx-2"))
        ts = datetime(2026, 2, 22, 16, 10, tzinfo=timezone.utc)
        result = check_structuring("Target", 510.0, store, ts)
        assert result.score_delta == 0

    def test_custom_min_count(self, store):
        """With min_count=2, two similar amounts should trigger."""
        from datetime import datetime, timezone
        store.add(make_stored(sender="Sender", amount=500.0, timestamp="2026-02-22T16:00:00Z", tx_id="tx-1"))
        ts = datetime(2026, 2, 22, 16, 10, tzinfo=timezone.utc)
        result = check_structuring("Sender", 490.0, store, ts, min_count=2)
        assert result.score_delta == 50

    def test_custom_variance(self, store):
        """With variance=0.05 (5%), $500 and $600 should NOT cluster."""
        from datetime import datetime, timezone
        store.add(make_stored(sender="Sender", amount=500.0, timestamp="2026-02-22T16:00:00Z", tx_id="tx-1"))
        store.add(make_stored(sender="Sender", amount=600.0, timestamp="2026-02-22T16:05:00Z", tx_id="tx-2"))
        ts = datetime(2026, 2, 22, 16, 10, tzinfo=timezone.utc)
        result = check_structuring("Sender", 550.0, store, ts, amount_variance=0.05)
        assert result.score_delta == 0

    def test_amounts_at_boundary_of_20_percent(self, store):
        """$500 and $400 differ by 20% of $500 — should be on the boundary."""
        from datetime import datetime, timezone
        store.add(make_stored(sender="Sender", amount=500.0, timestamp="2026-02-22T16:00:00Z", tx_id="tx-1"))
        store.add(make_stored(sender="Sender", amount=400.0, timestamp="2026-02-22T16:05:00Z", tx_id="tx-2"))
        ts = datetime(2026, 2, 22, 16, 10, tzinfo=timezone.utc)
        result = check_structuring("Sender", 480.0, store, ts)
        # 400 is within 20% of 480 (384-576), 500 is within 20% of 480 (384-576)
        # All three cluster around 480: 400, 480, 500 — all within ±20% of 480
        assert result.score_delta == 50

    def test_reason_includes_amount_and_count(self, store):
        from datetime import datetime, timezone
        store.add(make_stored(sender="S", amount=500.0, timestamp="2026-02-22T16:00:00Z", tx_id="tx-1"))
        store.add(make_stored(sender="S", amount=490.0, timestamp="2026-02-22T16:05:00Z", tx_id="tx-2"))
        ts = datetime(2026, 2, 22, 16, 10, tzinfo=timezone.utc)
        result = check_structuring("S", 510.0, store, ts)
        assert any("3 transactions" in r for r in result.reasons)
        assert any("$" in r for r in result.reasons)
