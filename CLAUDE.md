# CLAUDE.md

## Project Overview

Remessas Global Payment Screening API — a real-time transaction screening service for cross-border remittances. Built with Python 3.12 + FastAPI.

## Quick Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Run pytest suite (129 tests)
pytest

# Run bash integration tests (15 tests)
bash test_integration.sh

# Run demo (12 scenarios)
bash demo.sh
```

## Architecture

- **Framework**: FastAPI with Pydantic v2 for validation
- **Storage**: In-memory (dicts + lists in `app/storage/memory.py`)
- **Screening pipeline**: 5 independent rules in `app/screening/rules/`, orchestrated by `app/screening/engine.py`, scored by `app/screening/scorer.py`

## Key Files

- `app/main.py` — FastAPI app entry point, loads data files at startup
- `app/models.py` — All Pydantic models (request, response, config, audit)
- `app/screening/engine.py` — Core orchestrator, runs all 5 rules
- `app/screening/rules/` — One file per rule (sanctions, country, velocity, amount, structuring)
- `app/screening/scorer.py` — Score aggregation and decision logic
- `app/storage/memory.py` — In-memory store keyed by sender name
- `app/routes/` — FastAPI routers (screening, transactions, rules, audit)
- `data/` — JSON reference data (sanctions list, countries, rules config, test transactions)
- `tests/` — pytest suite (129 tests across 8 files)
- `docs/` — Project documentation (research, plans, comparison, AI session report)

## Decision Logic

- Sanctions match → **DENIED** (score=100, overrides everything)
- Score >= 50 → **REVIEW** (any single non-sanctions flag triggers this)
- Score < 50 → **APPROVED**
- Each non-sanctions rule contributes score_delta=50 (country, amount, velocity, structuring)

## Conventions

- Rule functions return `RuleResult(score_delta, reasons, matched_rules)`
- Sender name is used as customer identifier (normalized: lowercase, stripped)
- All timestamps are ISO 8601 with UTC timezone
- Fuzzy matching threshold: 85 (uses thefuzz ratio + token_sort_ratio)
