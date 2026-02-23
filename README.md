# Remessas Global Payment Screening API

A real-time transaction screening service for cross-border remittances. Built as a compliance-first API that checks every transaction against sanctions lists, high-risk jurisdictions, velocity limits, large-amount thresholds, and structuring patterns before allowing it to proceed.

Cross-border remittance corridors (e.g., US to Latin America) require robust compliance screening to satisfy AML/CFT regulations. This API provides an instant APPROVED / REVIEW / DENIED decision for each transaction, with full audit trails for compliance officers.

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then visit **http://localhost:8000/docs** for the interactive Swagger UI.

---

## Architecture Decisions

### Why Python + FastAPI

Python offers the fastest prototyping speed for a REST API of this scope. FastAPI was chosen specifically because:

- **Pydantic v2** provides strict request/response validation with zero boilerplate. Every field type, range, and format is enforced automatically.
- **Auto-generated OpenAPI docs** mean the Swagger UI at `/docs` is always in sync with the code -- no separate spec file to maintain.
- **Async-ready** with uvicorn, though the screening logic is CPU-bound and runs synchronously by design (deterministic, no I/O waits).

### Why In-Memory Storage

For a prototype/demo, in-memory storage is the right tradeoff:

- **Zero external dependencies** -- no database to install, configure, or migrate.
- **Instant startup** -- the server is ready in under a second.
- **Simple data model** -- transactions are stored in a dict keyed by normalized sender name, giving O(1) lookups for velocity and structuring checks.

Data is lost on restart, which is acceptable for a screening prototype. A production system would swap `MemoryStore` for a PostgreSQL or Redis-backed implementation behind the same interface.

### Rule Pipeline Design

Each of the 5 compliance rules is an independent function that accepts specific inputs and returns a `RuleResult`:

```python
class RuleResult(BaseModel):
    score_delta: int        # Points to add to cumulative risk score
    reasons: list[str]      # Human-readable explanation
    matched_rules: list[str] # Machine-readable rule tags
```

The screening engine runs all 5 rules in severity order, then the scorer aggregates results:

1. **Sanctions** (score_delta=100, instant DENIED)
2. **Country risk** (score_delta=50)
3. **Velocity** (score_delta=50)
4. **Amount** (score_delta=50)
5. **Structuring** (score_delta=50)

This design makes rules easy to add, remove, or modify independently. Adding a 6th rule means writing one function and adding one line to the engine. No rule knows about any other rule.

### Fuzzy Matching Strategy

The sanctions rule uses the `thefuzz` library with two complementary strategies:

- **`fuzz.ratio()`** -- character-level similarity, catches typos and transliteration variants ("Mohammad" vs "Mohammed").
- **`fuzz.token_sort_ratio()`** -- sorts tokens before comparing, catches name reorderings ("Ahmad Mohammad" vs "Mohammad Ahmad").

The higher of the two scores is used. A threshold of **85** balances sensitivity (catching real variants) against false positives (not flagging "Maria" for "Nadia").

### Score Thresholds and Decision Logic

| Rule | score_delta | Effect |
|------|-------------|--------|
| Sanctions match | 100 | Always DENIED (overrides score) |
| High-risk country | 50 | REVIEW (any single flag >= 50) |
| Large amount | 50 | REVIEW |
| Velocity exceeded | 50 | REVIEW |
| Structuring detected | 50 | REVIEW |

Decision logic:
- If `SANCTIONS_MATCH` is in matched_rules: **DENIED** (regardless of score)
- If cumulative score >= 50: **REVIEW**
- Otherwise: **APPROVED**

Multiple non-sanctions flags stack (e.g., high-risk country + large amount = score 100, still REVIEW not DENIED because there is no sanctions match).

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/screening` | Screen a single transaction |
| `POST` | `/api/screening/batch` | Batch screen 10-1000 transactions |
| `GET` | `/api/transactions/{customer_id}` | Query transaction history by sender name |
| `GET` | `/api/rules` | Get current screening rules config |
| `PUT` | `/api/rules` | Update screening rules dynamically |
| `GET` | `/api/audit` | Query audit trail with optional filters |

### GET /health

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

```json
{
    "status": "healthy"
}
```

### POST /api/screening

Screen a single transaction against all compliance rules.

**Request:**

```bash
curl -s -X POST http://localhost:8000/api/screening \
  -H "Content-Type: application/json" \
  -d '{
    "sender_name": "Maria Garcia",
    "recipient_name": "Rosa Delgado",
    "amount": 150.00,
    "currency": "USD",
    "destination_country": "MX",
    "timestamp": "2026-02-22T08:15:00Z"
  }' | python3 -m json.tool
```

**APPROVED response** (clean transaction):

```json
{
    "transaction_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "decision": "APPROVED",
    "risk_score": 0,
    "reasons": [],
    "matched_rules": []
}
```

**DENIED response** (sanctions match):

```bash
curl -s -X POST http://localhost:8000/api/screening \
  -H "Content-Type: application/json" \
  -d '{
    "sender_name": "Mohammad Ahmad",
    "recipient_name": "Layla Khoury",
    "amount": 350.00,
    "currency": "USD",
    "destination_country": "US",
    "timestamp": "2026-02-22T10:15:00Z"
  }' | python3 -m json.tool
```

```json
{
    "transaction_id": "f9e8d7c6-b5a4-3210-fedc-ba9876543210",
    "decision": "DENIED",
    "risk_score": 100,
    "reasons": [
        "Sender 'Mohammad Ahmad' matches sanctioned entity 'Mohammad Ahmad' (similarity: 100%)"
    ],
    "matched_rules": [
        "SANCTIONS_MATCH"
    ]
}
```

**REVIEW response** (high-risk country):

```bash
curl -s -X POST http://localhost:8000/api/screening \
  -H "Content-Type: application/json" \
  -d '{
    "sender_name": "Nora Fischer",
    "recipient_name": "Darius Tehrani",
    "amount": 250.00,
    "currency": "USD",
    "destination_country": "IR",
    "timestamp": "2026-02-22T09:15:00Z"
  }' | python3 -m json.tool
```

```json
{
    "transaction_id": "11223344-5566-7788-99aa-bbccddeeff00",
    "decision": "REVIEW",
    "risk_score": 50,
    "reasons": [
        "Destination country 'IR' is a high-risk jurisdiction"
    ],
    "matched_rules": [
        "HIGH_RISK_COUNTRY"
    ]
}
```

### POST /api/screening/batch

Screen multiple transactions in one request. Returns individual results plus an aggregate summary.

**Request:**

```bash
curl -s -X POST http://localhost:8000/api/screening/batch \
  -H "Content-Type: application/json" \
  -d '{
    "transactions": [
      {"sender_name":"Clean Person","recipient_name":"Other","amount":100,"currency":"USD","destination_country":"US","timestamp":"2026-02-22T10:00:00Z"},
      {"sender_name":"Omar Farooq","recipient_name":"Test","amount":200,"currency":"USD","destination_country":"US","timestamp":"2026-02-22T10:00:00Z"},
      {"sender_name":"Safe Person","recipient_name":"Friend","amount":300,"currency":"USD","destination_country":"IR","timestamp":"2026-02-22T10:00:00Z"}
    ]
  }' | python3 -m json.tool
```

**Response** (truncated for brevity):

```json
{
    "results": [ ... ],
    "summary": {
        "total": 3,
        "approved": 1,
        "denied": 1,
        "review": 1,
        "common_risk_factors": ["SANCTIONS_MATCH", "HIGH_RISK_COUNTRY"]
    }
}
```

### GET /api/transactions/{customer_id}

Retrieve transaction history for a sender. The `customer_id` path parameter is the sender name (URL-encoded).

**Request:**

```bash
curl -s "http://localhost:8000/api/transactions/Maria%20Garcia?hours=24" | python3 -m json.tool
```

**Response:**

```json
[
    {
        "transaction_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "sender_name": "Maria Garcia",
        "recipient_name": "Rosa Delgado",
        "amount": 150.0,
        "currency": "USD",
        "destination_country": "MX",
        "timestamp": "2026-02-22T08:15:00Z",
        "decision": "APPROVED",
        "risk_score": 0
    }
]
```

### GET /api/rules

Return the current screening rules configuration.

**Request:**

```bash
curl -s http://localhost:8000/api/rules | python3 -m json.tool
```

**Response:**

```json
{
    "velocity_threshold": 5,
    "velocity_window_minutes": 60,
    "amount_threshold": 2000.0,
    "structuring_window_minutes": 30,
    "structuring_min_count": 3,
    "structuring_amount_variance": 0.2,
    "fuzzy_match_threshold": 85
}
```

### PUT /api/rules

Update the screening rules. Changes take effect immediately for all subsequent screenings.

**Request:**

```bash
curl -s -X PUT http://localhost:8000/api/rules \
  -H "Content-Type: application/json" \
  -d '{
    "velocity_threshold": 5,
    "velocity_window_minutes": 60,
    "amount_threshold": 1000,
    "structuring_window_minutes": 30,
    "structuring_min_count": 3,
    "structuring_amount_variance": 0.20,
    "fuzzy_match_threshold": 85
  }' | python3 -m json.tool
```

**Response:** Returns the updated configuration (same shape as GET /api/rules).

### GET /api/audit

Query the audit trail. Supports optional filters via query parameters.

| Parameter | Type | Description |
|-----------|------|-------------|
| `transaction_id` | string | Filter by specific transaction ID |
| `from_date` | ISO datetime | Entries with timestamp >= this value |
| `to_date` | ISO datetime | Entries with timestamp <= this value |

**Request:**

```bash
curl -s "http://localhost:8000/api/audit?from_date=2026-02-22T00:00:00Z&to_date=2026-02-22T23:59:59Z" | python3 -m json.tool
```

**Response:**

```json
[
    {
        "transaction_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "timestamp": "2026-02-22T08:15:00Z",
        "request": {
            "sender_name": "Maria Garcia",
            "recipient_name": "Rosa Delgado",
            "amount": 150.0,
            "currency": "USD",
            "destination_country": "MX",
            "timestamp": "2026-02-22T08:15:00Z"
        },
        "decision": "APPROVED",
        "risk_score": 0,
        "reasons": [],
        "matched_rules": []
    }
]
```

---

## Test Data

The `data/` directory contains three reference files loaded at startup:

| File | Contents |
|------|----------|
| `data/sanctions_list.json` | 29 fictional sanctioned names, including spelling variants (e.g., "Mohammad Ahmad" / "Mohammed Ahmed" / "Muhammad Ahmad") for fuzzy matching testing |
| `data/high_risk_countries.json` | 10 high-risk jurisdiction ISO codes: IR, KP, SY, MM, YE, LY, SO, SS, AF, VE |
| `data/rules_config.json` | Default thresholds for all 5 rules (velocity=5/hr, amount=$2000, structuring=3 txns in 30 min, fuzzy=85%) |
| `data/test_transactions.json` | 125 test transactions covering all decision types (APPROVED, DENIED, REVIEW) across all rule categories |

---

## How to Test

1. **Start the server:**
   ```bash
   python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

2. **Run the demo script** (shows all decision types with formatted output):
   ```bash
   bash demo.sh
   ```

3. **Run the pytest suite** (129 unit + integration tests):
   ```bash
   pytest
   ```

4. **Run the bash integration tests** (15 automated pass/fail checks):
   ```bash
   bash test_integration.sh
   ```

5. **Use the Swagger UI** for interactive exploration:
   Open http://localhost:8000/docs in your browser.

---

## Stretch Goals Implemented

- **Batch Screening**: `POST /api/screening/batch` accepts arrays of transactions and returns individual results plus aggregate statistics (counts per decision, top risk factors).
- **Configurable Rules**: `GET/PUT /api/rules` allows modifying all thresholds at runtime -- amount limits, velocity windows, fuzzy match sensitivity, structuring parameters. Changes take effect immediately.
- **Audit Trail**: `GET /api/audit` provides a full compliance audit log with filtering by transaction_id and time range. Each entry links the original request to the final decision, risk score, and matched rules.

---

## Documentation

The [`docs/`](docs/README.md) directory contains the full documentation trail — from initial research through implementation:

| Document | Description |
|----------|-------------|
| [Research](docs/01-research.md) | Deep analysis of the challenge spec |
| [Plan Comparison](docs/02-plan-comparison.md) | Side-by-side comparison of 3 implementation approaches |
| [Plan A: Python + FastAPI](docs/03-plan-a-python-fastapi.md) | Selected plan with detailed TODOs and agent strategy |
| [Plan B: Go + Gin](docs/03-plan-b-go-gin.md) | Alternative plan |
| [Plan C: TypeScript + Express](docs/03-plan-c-typescript-express.md) | Alternative plan |
| [AI Session Report](docs/04-ai-session-report.md) | Full AI-assisted build process breakdown |

---

## Project Structure

```
yuno-challenge/
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI app, startup loader, health endpoint
│   ├── models.py                        # Pydantic models (request, response, config)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── screening.py                 # POST /api/screening, POST /api/screening/batch
│   │   ├── transactions.py              # GET /api/transactions/{customer_id}
│   │   ├── rules.py                     # GET/PUT /api/rules
│   │   └── audit.py                     # GET /api/audit
│   ├── screening/
│   │   ├── __init__.py
│   │   ├── engine.py                    # Orchestrator: runs all rules, aggregates, stores
│   │   ├── scorer.py                    # Score aggregation and decision logic
│   │   └── rules/
│   │       ├── __init__.py
│   │       ├── sanctions.py             # Fuzzy name matching against sanctions list
│   │       ├── country_risk.py          # High-risk jurisdiction check
│   │       ├── velocity.py              # Transaction frequency check (>5/hr)
│   │       ├── amount.py                # Large amount flag (>$2,000)
│   │       └── structuring.py           # Split-transaction pattern detection
│   └── storage/
│       ├── __init__.py
│       └── memory.py                    # In-memory store with sender-keyed indexing
├── data/
│   ├── sanctions_list.json              # 29 sanctioned entity names
│   ├── high_risk_countries.json         # 10 high-risk ISO country codes
│   ├── rules_config.json                # Default rule thresholds
│   └── test_transactions.json           # 125 test transactions
├── tests/                                 # pytest test suite (129 tests)
│   ├── conftest.py                        # Shared fixtures and helpers
│   ├── test_api.py                        # Integration tests (FastAPI TestClient)
│   ├── test_engine.py                     # Screening engine orchestrator tests
│   ├── test_store.py                      # In-memory storage tests
│   ├── test_scorer.py                     # Score aggregation tests
│   ├── test_sanctions.py                  # Sanctions rule tests
│   ├── test_country_risk.py               # Country risk rule tests
│   ├── test_velocity.py                   # Velocity rule tests
│   ├── test_amount.py                     # Amount rule tests
│   └── test_structuring.py               # Structuring rule tests
├── docs/                                  # Project documentation
│   ├── README.md                          # Documentation index
│   ├── 01-research.md                     # Challenge spec analysis
│   ├── 02-plan-comparison.md              # Implementation plan comparison
│   ├── 03-plan-a-python-fastapi.md        # Selected plan (Python + FastAPI)
│   ├── 03-plan-b-go-gin.md               # Alternative plan (Go + Gin)
│   ├── 03-plan-c-typescript-express.md    # Alternative plan (TypeScript + Express)
│   └── 04-ai-session-report.md           # AI-assisted build process report
├── requirements.txt                       # Python dependencies
├── test_integration.sh                    # 15 automated integration tests
└── demo.sh                                # Interactive demo script
```
