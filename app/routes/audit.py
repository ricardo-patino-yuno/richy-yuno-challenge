"""Audit log endpoint for compliance review."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Query, Request

from app.models import AuditEntry
from app.storage.memory import MemoryStore

router = APIRouter(prefix="/api")


def _get_store(request: Request) -> MemoryStore:
    """Retrieve the memory store from application state."""
    return request.app.state.store


@router.get("/audit", response_model=List[AuditEntry])
async def get_audit_log(
    request: Request,
    transaction_id: Optional[str] = Query(default=None),
    from_date: Optional[datetime] = Query(default=None),
    to_date: Optional[datetime] = Query(default=None),
) -> List[AuditEntry]:
    """Retrieve audit log entries with optional filters.

    Filters:
      - transaction_id: exact match on a specific transaction
      - from_date: entries with timestamp >= this value
      - to_date: entries with timestamp <= this value
    """
    store = _get_store(request)
    return store.get_audit_log(
        transaction_id=transaction_id,
        since=from_date,
        until=to_date,
    )
