"""Remessas Global Payment Screening API.

A real-time transaction screening service for cross-border remittances.
Screens transactions against sanctions lists, high-risk countries,
velocity thresholds, amount limits, and structuring patterns.

Run with:
    python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

import json
from pathlib import Path
from typing import Dict, List, Set

from fastapi import FastAPI

from app.models import RulesConfig
from app.routes import audit, rules, screening, transactions
from app.screening.engine import ScreeningEngine
from app.storage.memory import MemoryStore

# Resolve the data/ directory relative to this file so the server works
# regardless of which directory uvicorn is launched from.
DATA_DIR = Path(__file__).parent.parent / "data"

app = FastAPI(
    title="Remessas Global Payment Screening API",
    description=(
        "Real-time transaction screening for cross-border remittances. "
        "Checks sanctions lists, high-risk countries, velocity limits, "
        "large amounts, and structuring patterns."
    ),
    version="1.0.0",
)


@app.on_event("startup")
async def startup() -> None:
    """Load reference data and initialize the screening engine."""

    # Load the sanctions list (list of sanctioned entity names)
    with open(DATA_DIR / "sanctions_list.json", "r") as f:
        sanctions_list: List[str] = json.load(f)

    # Load high-risk country codes (ISO 3166-1 alpha-2)
    with open(DATA_DIR / "high_risk_countries.json", "r") as f:
        high_risk_countries: Set[str] = set(json.load(f))

    # Load tunable rule thresholds (or use defaults)
    rules_config_path = DATA_DIR / "rules_config.json"
    if rules_config_path.exists():
        with open(rules_config_path, "r") as f:
            config = RulesConfig(**json.load(f))
    else:
        config = RulesConfig()

    # Initialize the in-memory store and screening engine
    store = MemoryStore()
    engine = ScreeningEngine(
        sanctions_list=sanctions_list,
        high_risk_countries=high_risk_countries,
        store=store,
        config=config,
    )

    # Attach to app state for dependency injection in routes
    app.state.engine = engine
    app.state.store = store
    app.state.config = config


# Mount all API routers
app.include_router(screening.router)
app.include_router(transactions.router)
app.include_router(rules.router)
app.include_router(audit.router)


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Simple health check endpoint."""
    return {"status": "healthy"}
