"""Rules configuration endpoints for reading and updating thresholds."""

from fastapi import APIRouter, Request

from app.models import RulesConfig

router = APIRouter(prefix="/api")


@router.get("/rules", response_model=RulesConfig)
async def get_rules(request: Request) -> RulesConfig:
    """Return the current screening rules configuration."""
    return request.app.state.config


@router.put("/rules", response_model=RulesConfig)
async def update_rules(
    new_config: RulesConfig,
    request: Request,
) -> RulesConfig:
    """Update the screening rules configuration.

    Updates both the app-level config and the engine's config reference
    so that subsequent screenings use the new thresholds immediately.
    """
    # Update the shared config on app state
    request.app.state.config = new_config
    # Also update the engine's reference so it picks up new thresholds
    request.app.state.engine.config = new_config
    return new_config
