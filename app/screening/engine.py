"""Core screening orchestrator.

Executes all 5 compliance rules in order of severity:
  1. Sanctions (instant DENIED if matched)
  2. Country risk
  3. Velocity
  4. Amount
  5. Structuring

Then aggregates results and stores the transaction for future
velocity/structuring lookups.
"""

import uuid

from app.models import (
    AuditEntry,
    RulesConfig,
    ScreeningResponse,
    StoredTransaction,
    TransactionRequest,
)
from app.screening.rules.amount import check_amount
from app.screening.rules.country_risk import check_country
from app.screening.rules.sanctions import check_sanctions
from app.screening.rules.structuring import check_structuring
from app.screening.rules.velocity import check_velocity
from app.screening.scorer import aggregate_results
from app.storage.memory import MemoryStore


class ScreeningEngine:
    """Orchestrates transaction screening through all compliance rules."""

    def __init__(
        self,
        sanctions_list: list[str],
        high_risk_countries: set[str],
        store: MemoryStore,
        config: RulesConfig,
    ) -> None:
        self.sanctions_list = sanctions_list
        self.high_risk_countries = high_risk_countries
        self.store = store
        self.config = config

    def screen(self, request: TransactionRequest) -> ScreeningResponse:
        """Screen a single transaction through all compliance rules.

        Runs each rule in order, aggregates the results into a final
        decision, persists the transaction, and returns the response.
        """
        transaction_id = str(uuid.uuid4())

        # Execute rules in order of severity
        rule_results = [
            # 1. Sanctions -- highest severity, instant denial
            check_sanctions(
                sender_name=request.sender_name,
                recipient_name=request.recipient_name,
                sanctions_list=self.sanctions_list,
                threshold=self.config.fuzzy_match_threshold,
            ),
            # 2. Country risk -- elevated risk for high-risk jurisdictions
            check_country(
                destination_country=request.destination_country,
                high_risk_countries=self.high_risk_countries,
            ),
            # 3. Velocity -- unusual transaction frequency
            check_velocity(
                sender_name=request.sender_name,
                store=self.store,
                timestamp=request.timestamp,
                threshold=self.config.velocity_threshold,
                window_minutes=self.config.velocity_window_minutes,
            ),
            # 4. Amount -- large transaction flag
            check_amount(
                amount=request.amount,
                threshold=self.config.amount_threshold,
            ),
            # 5. Structuring -- split-transaction detection
            check_structuring(
                sender_name=request.sender_name,
                amount=request.amount,
                store=self.store,
                timestamp=request.timestamp,
                window_minutes=self.config.structuring_window_minutes,
                min_count=self.config.structuring_min_count,
                amount_variance=self.config.structuring_amount_variance,
            ),
        ]

        # Aggregate all rule results into a final decision
        risk_score, decision, reasons, matched_rules = aggregate_results(
            rule_results
        )

        # Persist the transaction for future velocity/structuring lookups
        stored_tx = StoredTransaction(
            transaction_id=transaction_id,
            sender_name=request.sender_name,
            recipient_name=request.recipient_name,
            amount=request.amount,
            currency=request.currency,
            destination_country=request.destination_country,
            timestamp=request.timestamp,
            decision=decision,
            risk_score=risk_score,
        )
        self.store.add(stored_tx)

        # Record a full audit trail entry
        audit_entry = AuditEntry(
            transaction_id=transaction_id,
            timestamp=request.timestamp,
            request=request,
            decision=decision,
            risk_score=risk_score,
            reasons=reasons,
            matched_rules=matched_rules,
        )
        self.store.add_audit(audit_entry)

        return ScreeningResponse(
            transaction_id=transaction_id,
            decision=decision,
            risk_score=risk_score,
            reasons=reasons,
            matched_rules=matched_rules,
        )
