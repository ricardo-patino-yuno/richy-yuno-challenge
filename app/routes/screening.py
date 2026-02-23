"""Screening endpoints for single and batch transaction processing."""

from collections import Counter

from fastapi import APIRouter, Request

from app.models import (
    BatchRequest,
    BatchResponse,
    BatchSummary,
    ScreeningResponse,
    TransactionRequest,
)
from app.screening.engine import ScreeningEngine

router = APIRouter(prefix="/api")


def _get_engine(request: Request) -> ScreeningEngine:
    """Retrieve the screening engine from application state."""
    return request.app.state.engine


@router.post("/screening", response_model=ScreeningResponse)
async def screen_transaction(
    transaction: TransactionRequest,
    request: Request,
) -> ScreeningResponse:
    """Screen a single transaction against all compliance rules."""
    engine = _get_engine(request)
    return engine.screen(transaction)


@router.post("/screening/batch", response_model=BatchResponse)
async def screen_batch(
    batch: BatchRequest,
    request: Request,
) -> BatchResponse:
    """Screen a batch of transactions and return aggregate summary.

    Each transaction is screened independently. The summary includes
    counts per decision category and the top 5 most common risk factors.
    """
    engine = _get_engine(request)

    results: list[ScreeningResponse] = []
    for tx in batch.transactions:
        result = engine.screen(tx)
        results.append(result)

    # Count decisions
    approved = sum(1 for r in results if r.decision == "APPROVED")
    denied = sum(1 for r in results if r.decision == "DENIED")
    review = sum(1 for r in results if r.decision == "REVIEW")

    # Find the top 5 most common matched rules across all results
    all_rules: list[str] = []
    for r in results:
        all_rules.extend(r.matched_rules)
    rule_counts = Counter(all_rules)
    common_risk_factors = [rule for rule, _ in rule_counts.most_common(5)]

    summary = BatchSummary(
        total=len(results),
        approved=approved,
        denied=denied,
        review=review,
        common_risk_factors=common_risk_factors,
    )

    return BatchResponse(results=results, summary=summary)
