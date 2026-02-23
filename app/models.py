"""Pydantic models for the payment screening API."""

from pydantic import BaseModel
from datetime import datetime
from typing import Literal


class TransactionRequest(BaseModel):
    """Incoming transaction to be screened."""
    sender_name: str
    recipient_name: str
    amount: float
    currency: str
    destination_country: str
    timestamp: datetime


class ScreeningResponse(BaseModel):
    """Result of screening a single transaction."""
    transaction_id: str
    decision: Literal["APPROVED", "DENIED", "REVIEW"]
    risk_score: int  # 0-100 cumulative risk score
    reasons: list[str]
    matched_rules: list[str]


class RuleResult(BaseModel):
    """Output of an individual compliance rule check."""
    score_delta: int  # Points to add to cumulative risk score
    reasons: list[str]
    matched_rules: list[str]


class StoredTransaction(BaseModel):
    """A transaction persisted in the in-memory store for lookups."""
    transaction_id: str
    sender_name: str
    recipient_name: str
    amount: float
    currency: str
    destination_country: str
    timestamp: datetime
    decision: str
    risk_score: int


class BatchRequest(BaseModel):
    """A batch of transactions to screen."""
    transactions: list[TransactionRequest]


class BatchSummary(BaseModel):
    """Aggregate statistics for a batch screening run."""
    total: int
    approved: int
    denied: int
    review: int
    common_risk_factors: list[str]


class BatchResponse(BaseModel):
    """Result of screening a batch of transactions."""
    results: list[ScreeningResponse]
    summary: BatchSummary


class AuditEntry(BaseModel):
    """Full audit trail entry linking request to decision."""
    transaction_id: str
    timestamp: datetime
    request: TransactionRequest
    decision: str
    risk_score: int
    reasons: list[str]
    matched_rules: list[str]


class RulesConfig(BaseModel):
    """Tunable thresholds for all screening rules."""
    velocity_threshold: int = 5
    velocity_window_minutes: int = 60
    amount_threshold: float = 2000
    structuring_window_minutes: int = 30
    structuring_min_count: int = 3
    structuring_amount_variance: float = 0.20
    fuzzy_match_threshold: int = 85
