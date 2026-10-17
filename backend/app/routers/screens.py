
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.db import first as db_first
from app.core.db import rows as db_rows
from app.core.security import CurrentUser, get_current_user
from app.core.supabase_client import require_supabase
from app.schemas import (
    SavedScreen,
    SavedScreenCreate,
    ScreenRunRequest,
    ScreenRunResponse,
)
from app.services import screener

router = APIRouter(prefix="/api/screens", tags=["screens"])


@router.get("/metrics")
async def list_metrics():
    """The metrics a screen may filter on, for building the criteria UI."""
    return {
        "metrics": [
            {"key": key, "label": meta["label"], "unit": meta["unit"]}
            for key, meta in screener.METRICS.items()
        ],
        "operators": [
            {"key": "gt", "label": "greater than"},
            {"key": "gte", "label": "at least"},
            {"key": "lt", "label": "less than"},
            {"key": "lte", "label": "at most"},
            {"key": "eq", "label": "equals"},
            {"key": "between", "label": "between"},
        ],
        "universe_size": screener.universe_size(),
        "coverage": screener.coverage(),
    }


@router.get("/presets")
async def list_presets():
    """Built-in screens: growth, value, dividend, quality."""
    return {
        "presets": [
            {"key": key, **preset} for key, preset in screener.PRESET_SCREENS.items()
        ]
    }


@router.post("/presets/{key}/run", response_model=ScreenRunResponse)
async def run_preset(key: str, limit: int = 25):
    preset = screener.PRESET_SCREENS.get(key)
    if preset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No preset named '{key}'"
        )
    return await screener.run_screen(preset["criteria"], limit=limit)


@router.post("/run", response_model=ScreenRunResponse)
async def run_custom(payload: ScreenRunRequest):
    """Run an ad-hoc set of criteria without saving it."""
    if not payload.criteria:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Add at least one criterion to run a screen.",
        )
    criteria = [c.model_dump() for c in payload.criteria]
    return await screener.run_screen(
        criteria, symbols=payload.symbols, limit=payload.limit
    )


# ----------------------------- saved screens ------------------------------
@router.get("/saved", response_model=list[SavedScreen])
async def list_saved(user: CurrentUser = Depends(get_current_user)):
    sb = require_supabase()
    res = (
        sb.table("saved_screens")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .execute()
    )
    return db_rows(res)


@router.post("/saved", response_model=SavedScreen, status_code=status.HTTP_201_CREATED)
async def create_saved(
    payload: SavedScreenCreate, user: CurrentUser = Depends(get_current_user)
):
    sb = require_supabase()
    res = (
        sb.table("saved_screens")
        .insert(
            {
                "user_id": user.id,
                "name": payload.name,
                "description": payload.description,
                "criteria": [c.model_dump() for c in payload.criteria],
                "is_public": payload.is_public,
            }
        )
        .execute()
    )
    created = db_first(res)
    if created is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save the screen",
        )
    return created


@router.post("/saved/{screen_id}/run", response_model=ScreenRunResponse)
async def run_saved(
    screen_id: str, limit: int = 25, user: CurrentUser = Depends(get_current_user)
):
    sb = require_supabase()
    res = (
        sb.table("saved_screens")
        .select("*")
        .eq("id", screen_id)
        .eq("user_id", user.id)
        .limit(1)
        .execute()
    )
    row = db_first(res)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Screen not found"
        )
    criteria = row.get("criteria")
    return await screener.run_screen(
        criteria if isinstance(criteria, list) else [], limit=limit
    )


@router.delete("/saved/{screen_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved(screen_id: str, user: CurrentUser = Depends(get_current_user)):
    sb = require_supabase()
    sb.table("saved_screens").delete().eq("id", screen_id).eq(
        "user_id", user.id
    ).execute()
    return None
