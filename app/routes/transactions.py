"""Transaction history lookup endpoint."""

from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Request

from app.models import StoredTransaction
from app.storage.memory import MemoryStore

router = APIRouter(prefix="/api")


def _get_store(request: Request) -> MemoryStore:
    """Retrieve the memory store from application state."""
    return request.app.state.store


@router.get("/transactions/{customer_id}", response_model=List[StoredTransaction])
async def get_customer_transactions(
    customer_id: str,
    request: Request,
    hours: int = 24,
) -> List[StoredTransaction]:
    """Get transactions for a customer (by sender name) within the last N hours.

    The customer_id path parameter is used as the sender name for lookup.
    URL-encoded names are automatically decoded by FastAPI.
    """
    store = _get_store(request)
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    return store.get_by_sender(customer_id, since=since)
