"""Shared fixtures for the test suite."""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.models import RulesConfig, TransactionRequest, StoredTransaction
from app.storage.memory import MemoryStore
from app.screening.engine import ScreeningEngine


SANCTIONS_LIST = [
    "Mohammad Ahmad",
    "Mohammed Ahmed",
    "Muhammad Ahmad",
    "Viktor Petrov",
    "Victor Petroff",
    "Ali Hassan",
    "Ali Hasan",
    "Al-Rashid Trading Company",
    "Golden Phoenix Import Export",
]

HIGH_RISK_COUNTRIES = {"IR", "KP", "SY", "MM", "YE", "LY", "SO", "SS", "AF", "VE"}


@pytest.fixture
def sanctions_list():
    return SANCTIONS_LIST[:]


@pytest.fixture
def high_risk_countries():
    return HIGH_RISK_COUNTRIES.copy()


@pytest.fixture
def config():
    return RulesConfig()


@pytest.fixture
def store():
    return MemoryStore()


@pytest.fixture
def engine(sanctions_list, high_risk_countries, store, config):
    return ScreeningEngine(
        sanctions_list=sanctions_list,
        high_risk_countries=high_risk_countries,
        store=store,
        config=config,
    )


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def make_request(
    sender="Maria Garcia",
    recipient="Rosa Delgado",
    amount=150.0,
    currency="USD",
    country="MX",
    timestamp="2026-02-22T10:00:00Z",
) -> TransactionRequest:
    return TransactionRequest(
        sender_name=sender,
        recipient_name=recipient,
        amount=amount,
        currency=currency,
        destination_country=country,
        timestamp=datetime.fromisoformat(timestamp.replace("Z", "+00:00")),
    )


def make_stored(
    sender="Maria Garcia",
    amount=150.0,
    timestamp="2026-02-22T10:00:00Z",
    tx_id="test-id",
) -> StoredTransaction:
    return StoredTransaction(
        transaction_id=tx_id,
        sender_name=sender,
        recipient_name="Someone",
        amount=amount,
        currency="USD",
        destination_country="US",
        timestamp=datetime.fromisoformat(timestamp.replace("Z", "+00:00")),
        decision="APPROVED",
        risk_score=0,
    )
