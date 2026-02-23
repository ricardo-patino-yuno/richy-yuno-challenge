"""In-memory storage for transactions and audit logs.

Uses a dict keyed by normalized sender name for O(1) lookups
during velocity and structuring checks. All data lives in memory
and is lost on restart — suitable for a screening demo/prototype.
"""

from datetime import datetime
from typing import Dict, List, Optional

from app.models import StoredTransaction, AuditEntry


def _normalize_key(name: str) -> str:
    """Normalize a sender name to a consistent dict key (lowercase, stripped)."""
    return name.strip().lower()


class MemoryStore:
    """Thread-safe in-memory store for transactions and audit entries."""

    def __init__(self) -> None:
        # Transactions indexed by normalized sender name for fast lookups
        self._transactions: Dict[str, List[StoredTransaction]] = {}
        # Chronological audit log
        self._audit_log: List[AuditEntry] = []

    def add(self, tx: StoredTransaction) -> None:
        """Store a transaction, indexed by normalized sender name."""
        key = _normalize_key(tx.sender_name)
        if key not in self._transactions:
            self._transactions[key] = []
        self._transactions[key].append(tx)

    def add_audit(self, entry: AuditEntry) -> None:
        """Append an entry to the audit log."""
        self._audit_log.append(entry)

    def get_by_sender(
        self,
        sender_name: str,
        since: Optional[datetime] = None,
    ) -> List[StoredTransaction]:
        """Return transactions for a sender, optionally filtered by timestamp >= since."""
        key = _normalize_key(sender_name)
        txns = self._transactions.get(key, [])
        if since is not None:
            txns = [t for t in txns if t.timestamp >= since]
        return txns

    def get_all(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> List[StoredTransaction]:
        """Return all transactions, optionally filtered by time range."""
        results: List[StoredTransaction] = []
        for txn_list in self._transactions.values():
            for t in txn_list:
                if since is not None and t.timestamp < since:
                    continue
                if until is not None and t.timestamp > until:
                    continue
                results.append(t)
        return results

    def get_audit_log(
        self,
        transaction_id: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> List[AuditEntry]:
        """Return audit entries, optionally filtered by transaction ID and/or time range."""
        results: List[AuditEntry] = []
        for entry in self._audit_log:
            if transaction_id is not None and entry.transaction_id != transaction_id:
                continue
            if since is not None and entry.timestamp < since:
                continue
            if until is not None and entry.timestamp > until:
                continue
            results.append(entry)
        return results
