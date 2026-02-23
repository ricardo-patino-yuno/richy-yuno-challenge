# Plan A: Python + FastAPI (Updated)

## Stack

- **Language**: Python 3.12
- **Framework**: FastAPI
- **Fuzzy Matching**: `thefuzz` (Levenshtein) + manual string normalization
- **Storage**: In-memory (Python dicts + lists)
- **Validation**: Pydantic v2 models
- **Test Data**: JSON files loaded at startup

---

## Project Structure

```
yuno-challenge/
├── app/
│   ├── main.py              # FastAPI app, startup event (load data), route mounting
│   ├── models.py             # Pydantic request/response models
│   ├── screening/
│   │   ├── engine.py         # Core screening orchestrator (runs all rules, aggregates)
│   │   ├── rules/
│   │   │   ├── sanctions.py      # Sanctions matching (fuzzy + exact, checks BOTH sender & recipient)
│   │   │   ├── country_risk.py   # High-risk country check
│   │   │   ├── velocity.py       # Transaction velocity check (>5 txns/hour)
│   │   │   ├── amount.py         # Large amount check (>$2,000 USD)
│   │   │   └── structuring.py    # Structuring pattern detection (similar amounts in short window)
│   │   └── scorer.py        # Risk score aggregation + decision logic (deterministic)
│   ├── storage/
│   │   └── memory.py         # In-memory transaction store (keyed by sender_name as customer ID)
│   └── routes/
│       ├── screening.py      # POST /api/screening, POST /api/screening/batch
│       ├── transactions.py   # GET /api/transactions/{customer_id}
│       ├── rules.py          # GET/PUT /api/rules (stretch B)
│       └── audit.py          # GET /api/audit (stretch C)
├── data/
│   ├── sanctions_list.json       # 25-30 sanctioned names + orgs (with spelling variants)
│   ├── high_risk_countries.json  # 10 country codes
│   ├── rules_config.json         # Configurable thresholds (stretch B)
│   └── test_transactions.json    # 120+ test transactions (24+ hour span, 20+ customer IDs)
├── demo.sh                   # curl-based demo script showing full responses with reasoning
├── requirements.txt
└── README.md                 # Setup, testing, architecture decisions, API examples
```

---

## Pydantic Models

### Request

```python
class TransactionRequest(BaseModel):
    sender_name: str
    recipient_name: str
    amount: float
    currency: str           # e.g. "USD", "BRL", "NGN"
    destination_country: str  # ISO country code
    timestamp: datetime
```

### Response

```python
class ScreeningResponse(BaseModel):
    decision: Literal["APPROVED", "DENIED", "REVIEW"]
    risk_score: int          # 0-100
    reasons: list[str]       # Human-readable explanations
    matched_rules: list[str] # e.g. ["SANCTIONS_MATCH", "HIGH_RISK_COUNTRY"]
```

### Internal

```python
class RuleResult(BaseModel):
    score_delta: int
    reasons: list[str]
    matched_rules: list[str]
```

**Note**: The spec uses "sender name" as the customer identifier. Test data will use sender_name as the customer ID for velocity/structuring lookups (20+ unique sender names).

---

## Implementation Order

### Phase 1: Scaffold + Data Files (10 min)
1. Create project structure, `requirements.txt`, basic `main.py`
2. Create `data/sanctions_list.json` — 25-30 entries:
   - Individuals with spelling variations: "Mohammad Ahmad" / "Mohammed Ahmed" / "Muhammad Ahmad"
   - Organization names: e.g., "Al-Rashid Trading Company"
   - Mix of first/last name orderings
3. Create `data/high_risk_countries.json` — 10 codes: IR, KP, SY, MM, YE, LY, SO, SS, AF, VE
4. Define Pydantic models in `models.py`
5. Basic FastAPI app with `GET /health`

### Phase 2: Core Screening Engine (25 min)
Build each rule as a function returning `RuleResult`:

1. **`check_sanctions(sender_name, recipient_name, sanctions_list)`**
   - Check **BOTH** sender and recipient names (spec requirement)
   - Normalize: lowercase, strip whitespace, remove special characters
   - Use `thefuzz.fuzz.ratio()` with threshold 85 for fuzzy matching
   - Also use `fuzz.token_sort_ratio()` to handle name reordering ("Ahmad Mohammad" vs "Mohammad Ahmad")
   - Match → score_delta = 100, matched_rule = "SANCTIONS_MATCH"

2. **`check_country(destination_country, high_risk_set)`**
   - Simple `set` lookup on ISO code
   - Match → score_delta = 20, matched_rule = "HIGH_RISK_COUNTRY"

3. **`check_velocity(sender_name, store, timestamp)`**
   - Count sender's transactions in last 60 minutes from store
   - If count > 5 → score_delta = 30, matched_rule = "VELOCITY_EXCEEDED"

4. **`check_amount(amount)`**
   - If amount > 2000 → score_delta = 15, matched_rule = "LARGE_AMOUNT"

5. **`check_structuring(sender_name, amount, store, timestamp)`**
   - Look at sender's transactions in last 30 minutes
   - If 3+ transactions with amounts within 20% of each other → structuring detected
   - score_delta = 35, matched_rule = "STRUCTURING_DETECTED"
   - Context: catches attempts to stay under reporting thresholds (e.g., 5 x $500 instead of $2,500)

6. **Build `engine.py` orchestrator:**
   - Run sanctions check first — if match, immediately return DENIED (score=100)
   - Run remaining checks, accumulate score_delta values
   - Decision logic (deterministic):
     - Sanctions match → **DENIED** (score near 100)
     - Total score >= 50 → **REVIEW**
     - Total score < 50 → **APPROVED**
   - Aggregate all reasons and matched_rules from triggered checks
   - Ensure output is deterministic: same input + same history = same output

7. Wire to `POST /api/screening` route
8. After screening, store the transaction in memory for future lookups

### Phase 3: Historical Storage + Query Endpoint (15 min)
1. `MemoryStore` class:
   - `dict[str, list[StoredTransaction]]` keyed by normalized sender_name
   - Methods: `add(tx)`, `get_by_sender(name, since: datetime)`, `get_all(since, until)`
   - `StoredTransaction` includes all request fields + the screening decision + transaction_id (UUID)
2. Every screened transaction gets stored **after** screening
3. `GET /api/transactions/{customer_id}?hours=24` — returns transaction history
   - Default: last 24 hours
   - Supports `hours` query parameter to adjust window
4. Velocity and structuring checks read from this store

### Phase 4: Test Data (10 min)
Generate `data/test_transactions.json` with 120+ transactions:

| Category | Count | Details |
|----------|-------|---------|
| Clean/APPROVED | ~50 | Normal amounts ($50-$500), safe countries, unique senders |
| Sanctions DENIED | ~8 | Sender or recipient matches sanctioned names (exact + fuzzy variants) |
| Velocity REVIEW | ~15 | 3 customers with 6+ transactions clustered within 1 hour |
| Structuring REVIEW | ~15 | 3 customers with 4-5 x ~$500 in 30 min windows |
| High-risk country REVIEW | ~12 | Transactions to IR, KP, SY, etc. |
| Large amount REVIEW | ~10 | Amounts $2,100-$5,000 |
| Overlapping flags | ~10 | High-risk country + large amount, velocity + structuring, etc. |

Requirements met:
- 20+ unique sender names (customer IDs)
- Amounts: $50-$5,000 range
- Timestamps spanning 24+ hours
- Explicit DENIED, REVIEW, APPROVED examples
- Structuring patterns: e.g., sender "Carlos Mendez" sends $500, $490, $510, $495, $505 in 30 minutes

### Phase 5: Stretch Goals — All Three (15 min)

**A. Batch Screening (5 min)**
- `POST /api/screening/batch` accepts `list[TransactionRequest]` (10-1000 items)
- Returns:
  ```python
  class BatchResponse(BaseModel):
      results: list[ScreeningResponse]
      summary: BatchSummary

  class BatchSummary(BaseModel):
      total: int
      approved: int
      denied: int
      review: int
      common_risk_factors: list[str]  # Most frequently triggered rules
  ```

**B. Configurable Rules (5 min)**
- Load thresholds from `data/rules_config.json` at startup:
  ```json
  {
    "velocity_threshold": 5,
    "velocity_window_minutes": 60,
    "amount_threshold": 2000,
    "structuring_window_minutes": 30,
    "structuring_min_count": 3,
    "structuring_amount_variance": 0.20,
    "fuzzy_match_threshold": 85
  }
  ```
- `GET /api/rules` — returns current config
- `PUT /api/rules` — updates config (no restart needed)
- Demo: change `amount_threshold` from 2000 to 1000, show a $1,500 transaction going from APPROVED to REVIEW

**C. Audit Trail (5 min)**
- Every screening decision logged to in-memory list:
  ```python
  class AuditEntry(BaseModel):
      transaction_id: str  # UUID
      timestamp: datetime
      request: TransactionRequest
      decision: str
      risk_score: int
      reasons: list[str]
      matched_rules: list[str]
  ```
- `GET /api/audit?from=&to=&transaction_id=` — query by time range or specific transaction

### Phase 6: Documentation + Demo (10 min)

**README.md must include (per spec):**
1. **Setup instructions** — how to install dependencies and run the service
2. **API usage examples** — example curl requests and responses for each endpoint
3. **Architecture decisions** — why Python/FastAPI, why in-memory, how rules are structured
4. **How to test** — how to load test data and verify all decision types

**demo.sh must include (per spec deliverable #5):**
- At least 5-6 curl commands showing:
  1. APPROVED — clean transaction, low risk
  2. DENIED — sanctions match (exact name)
  3. DENIED — sanctions match (fuzzy variant)
  4. REVIEW — high-risk country
  5. REVIEW — large amount
  6. REVIEW — velocity (after sending 6+ transactions)
  7. REVIEW — structuring pattern
- **Each must show the full JSON response** including reasons and matched_rules (not just the decision)

**Source code comments (per spec deliverable #4):**
- Add inline comments explaining key logic, especially:
  - Fuzzy matching algorithm choice and threshold reasoning
  - Structuring detection algorithm
  - Score aggregation and decision thresholds
  - Why sanctions check short-circuits to DENIED

---

## Checklist: Acceptance Criteria Coverage

| # | Criterion | Where it's covered |
|---|-----------|-------------------|
| 1 | POST request → JSON response with decision + risk score + reasons | Phase 2: engine.py + POST /api/screening |
| 2 | Sanctions matching with fuzzy matching for name variations | Phase 2: sanctions.py (thefuzz ratio + token_sort_ratio, both sender & recipient) |
| 3 | High-risk jurisdiction + high amount flagging | Phase 2: country_risk.py + amount.py |
| 4 | Velocity detection (multiple txns from same customer, short time) | Phase 2: velocity.py + Phase 3: memory store |
| 5 | Query historical transactions by customer | Phase 3: GET /api/transactions/{customer_id} |
| 6 | Test data with clear APPROVED, DENIED, REVIEW examples | Phase 4: 120+ transactions with explicit categories |
| 7 | Well-organized code + README with run/test instructions | Phase 6: README + comments in source |

---

## Checklist: Deliverables

| # | Deliverable | File(s) |
|---|-------------|---------|
| 1 | Working backend API service | `app/` directory, run with `uvicorn` |
| 2 | README with setup, testing, architecture decisions | `README.md` |
| 3 | Test data files | `data/sanctions_list.json`, `data/high_risk_countries.json`, `data/test_transactions.json` |
| 4 | Source code with comments explaining key screening logic | All `.py` files, especially `screening/rules/*.py` |
| 5 | Demo script showing APPROVED/DENIED/REVIEW with reasoning | `demo.sh` |

---

## Checklist: Rubric Points

| Criterion | Points | How we score them |
|-----------|--------|-------------------|
| Core Functionality | 25 | Deterministic screening, risk scores 0-100, detailed reasons array, matched_rules |
| Compliance Logic | 25 | All 5 rules implemented: sanctions (fuzzy, both names), country, velocity, amount, structuring |
| Historical Tracking | 15 | In-memory store, query endpoint, feeds into velocity + structuring |
| Code Quality | 10 | Separated concerns (routes/engine/rules/store), meaningful names, Pydantic models |
| Test Data | 10 | 120+ transactions, 20+ customers, 24h span, all edge cases |
| Documentation | 10 | README (setup + testing + architecture) + Swagger auto-docs + demo.sh |
| Stretch Goals | 5 | All 3: batch screening + configurable rules + audit trail |

---

## Dependencies

```
fastapi==0.115.0
uvicorn==0.30.0
thefuzz==0.22.1
python-Levenshtein==0.25.1
pydantic==2.9.0
```

---

## Detailed TODO List

### Legend
- `[P]` = Can be parallelized with other `[P]` tasks in the same phase
- `[S]` = Sequential, must complete before next task starts
- `[Agent:X]` = Assigned to agent X

---

### PHASE 0: Project Scaffold (2 min) `[S — must complete first]`

| # | Task | Agent | Depends On | Output |
|---|------|-------|------------|--------|
| 0.1 | Create directory structure (`app/`, `app/screening/`, `app/screening/rules/`, `app/storage/`, `app/routes/`, `data/`) | Orchestrator | — | Dirs |
| 0.2 | Create `requirements.txt` with pinned dependencies | Orchestrator | — | File |
| 0.3 | Create all `__init__.py` files (empty) for Python packages | Orchestrator | 0.1 | Files |
| 0.4 | `pip install -r requirements.txt` | Orchestrator | 0.2 | Env ready |

---

### PHASE 1: Foundation Layer (8 min) `[P — all independent]`

| # | Task | Agent | Depends On | Output |
|---|------|-------|------------|--------|
| 1.1 | Create `app/models.py` — all Pydantic models: `TransactionRequest`, `ScreeningResponse`, `RuleResult`, `StoredTransaction`, `BatchResponse`, `BatchSummary`, `AuditEntry`, `RulesConfig` | Agent-Code | 0.3 | models.py |
| 1.2 | Create `data/sanctions_list.json` — 25-30 fictional names with spelling variants + organizations | Agent-Data | — | JSON file |
| 1.3 | Create `data/high_risk_countries.json` — 10 country codes with country names | Agent-Data | — | JSON file |
| 1.4 | Create `data/rules_config.json` — all configurable thresholds with defaults | Agent-Data | — | JSON file |

---

### PHASE 2: Storage + Rules (12 min) `[P — groups can run in parallel]`

**Group A: Storage** (depends on 1.1)

| # | Task | Agent | Depends On | Output |
|---|------|-------|------------|--------|
| 2.1 | Create `app/storage/memory.py` — `MemoryStore` class with `add()`, `get_by_sender()`, `get_all()` methods. Thread-safe with proper key normalization. | Agent-Code | 1.1 | memory.py |

**Group B: Screening Rules** (depends on 1.1; each rule is independent of others)

| # | Task | Agent | Depends On | Output |
|---|------|-------|------------|--------|
| 2.2 | Create `app/screening/rules/sanctions.py` — `check_sanctions(sender, recipient, sanctions_list)` using `thefuzz.fuzz.ratio()` + `token_sort_ratio()`. Normalize names. Check BOTH sender & recipient. Threshold 85. Include inline comments explaining fuzzy matching choice. | Agent-Code | 1.1 | sanctions.py |
| 2.3 | Create `app/screening/rules/country_risk.py` — `check_country(country, high_risk_set)`. Set lookup on ISO code. score_delta=20. | Agent-Code | 1.1 | country_risk.py |
| 2.4 | Create `app/screening/rules/velocity.py` — `check_velocity(sender, store, timestamp)`. Count sender's txns in last 60 min. Threshold > 5. score_delta=30. Include comment explaining velocity concept. | Agent-Code | 1.1, 2.1 | velocity.py |
| 2.5 | Create `app/screening/rules/amount.py` — `check_amount(amount)`. Threshold > 2000. score_delta=15. | Agent-Code | 1.1 | amount.py |
| 2.6 | Create `app/screening/rules/structuring.py` — `check_structuring(sender, amount, store, timestamp)`. 30-min window, 3+ txns with amounts within 20% of each other. score_delta=35. Include comment explaining structuring / reporting thresholds. | Agent-Code | 1.1, 2.1 | structuring.py |

---

### PHASE 3: Engine + Routes (12 min) `[S — engine first, then routes]`

| # | Task | Agent | Depends On | Output |
|---|------|-------|------------|--------|
| 3.1 | Create `app/screening/scorer.py` — pure function that takes list of `RuleResult`, aggregates scores (cap at 100), determines decision: sanctions→DENIED, score>=50→REVIEW, else APPROVED. Comment explaining deterministic logic. | Agent-Code | 1.1 | scorer.py |
| 3.2 | Create `app/screening/engine.py` — `ScreeningEngine` class. `screen(request, store, config)` method runs all 5 rules in order, calls scorer, returns `ScreeningResponse`. Also generates `transaction_id` (UUID) and stores the transaction. Comment explaining rule execution order. | Agent-Code | 2.1-2.6, 3.1 | engine.py |
| 3.3 | Create `app/routes/screening.py` — `POST /api/screening` (single transaction), `POST /api/screening/batch` (stretch A: array of 10-1000 txns, returns results + summary). | Agent-Code | 3.2 | screening.py |
| 3.4 | Create `app/routes/transactions.py` — `GET /api/transactions/{customer_id}` with `?hours=24` query param. Returns list of stored transactions. | Agent-Code | 2.1 | transactions.py |
| 3.5 | Create `app/routes/rules.py` — `GET /api/rules` returns current config. `PUT /api/rules` updates thresholds at runtime (stretch B). | Agent-Code | 1.1 | rules.py |
| 3.6 | Create `app/routes/audit.py` — `GET /api/audit` with `?from=`, `?to=`, `?transaction_id=` filters (stretch C). Reads from audit log in store. | Agent-Code | 2.1 | audit.py |
| 3.7 | Create `app/main.py` — FastAPI app, load data files at startup, create MemoryStore + ScreeningEngine instances, mount all routers, `GET /health` endpoint. | Agent-Code | 3.3-3.6 | main.py |

---

### PHASE 4: Test Data (8 min) `[P — can overlap with Phase 3]`

| # | Task | Agent | Depends On | Output |
|---|------|-------|------------|--------|
| 4.1 | Create `data/test_transactions.json` — 120+ transactions. Must reference exact names from `sanctions_list.json` for DENIED cases. Must use country codes from `high_risk_countries.json` for REVIEW cases. 20+ unique senders, $50-$5000, 24h+ timestamp span. Include structuring clusters (5 x ~$500 in 30min), velocity clusters (6+ txns in 1hr), sanctions name variants, high-risk countries, large amounts, overlapping flags, and clean transactions. | Agent-Data | 1.2, 1.3 | JSON file |

---

### PHASE 5: Integration Test (5 min) `[S]`

| # | Task | Agent | Depends On | Output |
|---|------|-------|------------|--------|
| 5.1 | Start the server with `uvicorn app.main:app` | Orchestrator | 3.7 | Running server |
| 5.2 | Send a clean transaction → verify APPROVED with score < 50 | Orchestrator | 5.1 | Pass/Fail |
| 5.3 | Send a sanctioned sender name → verify DENIED with score ~100 | Orchestrator | 5.1 | Pass/Fail |
| 5.4 | Send a fuzzy sanctions variant → verify DENIED | Orchestrator | 5.1 | Pass/Fail |
| 5.5 | Send to a high-risk country → verify REVIEW | Orchestrator | 5.1 | Pass/Fail |
| 5.6 | Send amount > $2000 → verify REVIEW | Orchestrator | 5.1 | Pass/Fail |
| 5.7 | Send 6 transactions from same sender in <1hr → verify last one gets velocity REVIEW | Orchestrator | 5.1 | Pass/Fail |
| 5.8 | Send 4 x ~$500 from same sender in 30min → verify structuring REVIEW | Orchestrator | 5.1 | Pass/Fail |
| 5.9 | Query `GET /api/transactions/{sender}` → verify history returned | Orchestrator | 5.1 | Pass/Fail |
| 5.10 | Test batch endpoint with 5 mixed transactions → verify summary counts | Orchestrator | 5.1 | Pass/Fail |
| 5.11 | Test `GET /api/rules` and `PUT /api/rules` (change threshold, verify effect) | Orchestrator | 5.1 | Pass/Fail |
| 5.12 | Test `GET /api/audit` → verify audit entries exist | Orchestrator | 5.1 | Pass/Fail |

---

### PHASE 6: Documentation + Demo (8 min) `[P]`

| # | Task | Agent | Depends On | Output |
|---|------|-------|------------|--------|
| 6.1 | Create `demo.sh` — 7+ curl commands covering all decision types, each with `jq` formatting to show full JSON response. Include comments explaining what each request tests. Must demonstrate: APPROVED, DENIED (exact), DENIED (fuzzy), REVIEW (country), REVIEW (amount), REVIEW (velocity via multiple sends), REVIEW (structuring via multiple sends). | Agent-Docs | 5.x passed | demo.sh |
| 6.2 | Create `README.md` — sections: Overview, Quick Start (install + run), Architecture Decisions (why FastAPI, why in-memory, rule pipeline design), API Reference (all endpoints with example req/res), Test Data Description (what each category tests), Stretch Goals Implemented, How to Run Demo. | Agent-Docs | 5.x passed | README.md |

---

### PHASE 7: Final Polish (3 min) `[S]`

| # | Task | Agent | Depends On | Output |
|---|------|-------|------------|--------|
| 7.1 | Review all source files for missing inline comments on screening logic | Orchestrator | 6.x | Updated files |
| 7.2 | Run `demo.sh` end-to-end, verify all outputs are correct | Orchestrator | 6.1 | Pass/Fail |
| 7.3 | Final read of README for completeness against spec deliverables | Orchestrator | 6.2 | Pass/Fail |

---

## Agent Orchestration Strategy

### Why Not Fully Parallel?

The codebase is ~500 lines of Python with tight coupling between layers (models → storage → rules → engine → routes → main). Splitting code generation across many agents creates **integration risk** — mismatched imports, inconsistent function signatures, different coding styles. The cost of debugging integration issues would eat the time savings.

### Recommended Agent Architecture: 3 Agents + Orchestrator

```
┌─────────────────────────────────────────────────────┐
│                   ORCHESTRATOR                       │
│  (Main Claude session)                               │
│  - Creates project scaffold (Phase 0)                │
│  - Coordinates agent launches                        │
│  - Runs integration tests (Phase 5)                  │
│  - Final polish (Phase 7)                            │
│  - Fixes any issues found during testing             │
└───────┬──────────────┬──────────────┬───────────────┘
        │              │              │
   ┌────▼────┐   ┌─────▼─────┐  ┌────▼────┐
   │ Agent   │   │  Agent    │  │ Agent   │
   │ Code    │   │  Data     │  │ Docs    │
   │         │   │           │  │         │
   │ Phase 1 │   │ Phase 1   │  │ Phase 6 │
   │ (models)│   │ (3 JSON   │  │ (README │
   │         │   │  files)   │  │  + demo)│
   │ Phase 2 │   │           │  │         │
   │ (store  │   │ Phase 4   │  └─────────┘
   │ + rules)│   │ (test     │
   │         │   │  txns)    │
   │ Phase 3 │   └───────────┘
   │ (engine │
   │ + routes│
   │ + main) │
   └─────────┘
```

### Agent Descriptions

**Orchestrator (Main Session)**
- Owns the project lifecycle
- Creates Phase 0 scaffold (dirs, requirements.txt, __init__.py files, pip install)
- Launches Agent-Code and Agent-Data in parallel for Phase 1
- Waits for Agent-Code to finish Phase 1 (models.py) before Phase 2 can start
- Agent-Data can continue independently since data files don't import Python code
- Launches Agent-Data Phase 4 (test transactions) as soon as Phase 1 data files are done
- Runs all Phase 5 integration tests via curl commands
- Launches Agent-Docs for Phase 6 after tests pass
- Does Phase 7 final polish

**Agent-Code** (single agent, sequential execution)
- Writes ALL Python source files: models → storage → rules → engine → routes → main
- Sequential because each layer imports from the previous one
- Single agent ensures consistent coding style, import paths, and function signatures
- Covers Phases 1.1, 2.1-2.6, 3.1-3.7

**Agent-Data** (can run in parallel with Agent-Code)
- Creates all JSON data files
- Phase 1: sanctions_list.json, high_risk_countries.json, rules_config.json (no dependencies)
- Phase 4: test_transactions.json (depends on Phase 1 data files only — needs to reference same names/countries)
- No Python code knowledge needed — pure data generation

**Agent-Docs** (runs after Phase 5)
- Creates README.md and demo.sh
- Must see the working API to write accurate curl examples and endpoint docs
- Needs to know exact endpoint paths, request/response shapes, and example outputs from Phase 5 test results

### Execution Timeline

```
Time  Orchestrator          Agent-Code              Agent-Data           Agent-Docs
─────┬────────────────────┬───────────────────────┬──────────────────┬──────────────
0:00 │ Phase 0: scaffold  │                       │                  │
0:02 │ ── launch ──────── │ Phase 1.1: models.py  │ Phase 1.2-1.4:   │
     │                    │                       │ sanctions.json   │
     │                    │                       │ countries.json   │
     │                    │                       │ rules_config.json│
0:10 │                    │ Phase 2.1-2.6:        │                  │
     │                    │ memory.py             │ Phase 4.1:       │
     │                    │ sanctions.py          │ test_txns.json   │
     │                    │ country_risk.py       │ (120+ entries)   │
     │                    │ velocity.py           │                  │
     │                    │ amount.py             │                  │
     │                    │ structuring.py        │                  │
0:22 │                    │ Phase 3.1-3.7:        │ ── done ──       │
     │                    │ scorer.py             │                  │
     │                    │ engine.py             │                  │
     │                    │ screening route       │                  │
     │                    │ transactions route    │                  │
     │                    │ rules route           │                  │
     │                    │ audit route           │                  │
     │                    │ main.py               │                  │
0:34 │ Phase 5: test ──── │ ── done ──            │                  │
0:39 │ Fix any issues     │                       │                  │
0:44 │ ── launch ──────── │                       │                  │ Phase 6.1-6.2
     │                    │                       │                  │ demo.sh
     │                    │                       │                  │ README.md
0:52 │ Phase 7: polish    │                       │                  │ ── done ──
0:55 │ ── DONE ──         │                       │                  │
```

**Total estimated time: ~55 minutes** (vs 85 min sequential), leaving 35 min buffer.

### Risk Mitigations for Agent Strategy

| Risk | Mitigation |
|------|-----------|
| Agent-Code produces code that doesn't compile | Orchestrator runs `python -c "from app.main import app"` after Phase 3 to catch import errors before Phase 5 |
| Agent-Data test transactions don't match sanctions names | Agent-Data reads sanctions_list.json first, then generates test_transactions.json referencing those exact names |
| Agent-Docs writes inaccurate curl examples | Agent-Docs runs after Phase 5 and receives actual test results as context |
| Any agent produces inconsistent work | Orchestrator reviews all output at Phase 7 before declaring done |

---

## Key Changes from Original Plan

1. **Sanctions check now verifies BOTH sender and recipient** — original only checked one name
2. **Added `token_sort_ratio`** — handles name reordering (spec example implies this)
3. **All 3 stretch goals included** — audit trail was missing, it's quick to add
4. **`rules_config.json` added to project structure** — was mentioned but not in file tree
5. **Explicit customer ID strategy** — using sender_name as customer identifier (spec says "customer" but input has no customer_id field)
6. **Source code comments requirement** — deliverable #4 explicitly requires comments on screening logic
7. **Demo script must show full responses** — not just decisions, must include reasoning
8. **README must explain architecture decisions** — not just architecture diagram
9. **Transaction stored with UUID** — enables audit trail queries by transaction_id
10. **Deterministic output** — explicitly noted: same input + same history = same output
