
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.db import first as db_first
from app.core.db import rows as db_rows
from app.core.security import CurrentUser, get_current_user
from app.core.supabase_client import require_supabase
from app.schemas import Profile, ProfileUpdate, SearchHistoryEntry

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("", response_model=Profile)
async def get_profile(user: CurrentUser = Depends(get_current_user)):
    """The signed-in user's profile row, created on first sign-up by a
    database trigger."""
    sb = require_supabase()
    res = sb.table("profiles").select("*").eq("id", user.id).limit(1).execute()
    existing_profile = db_first(res)
    if existing_profile is None:
        # Defensive: the trigger should have made this, but a user created
        # before the migration ran would not have one.
        created = (
            sb.table("profiles")
            .insert(
                {
                    "id": user.id,
                    "username": (user.email or user.id).split("@")[0],
                    "display_name": (user.email or user.id).split("@")[0],
                }
            )
            .execute()
        )
        created_profile = db_first(created)
        if created_profile is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create a profile",
            )
        return created_profile
    return existing_profile


@router.patch("", response_model=Profile)
async def update_profile(
    payload: ProfileUpdate, user: CurrentUser = Depends(get_current_user)
):
    sb = require_supabase()
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Nothing to update"
        )
    res = sb.table("profiles").update(updates).eq("id", user.id).execute()
    existing_profile = db_first(res)
    if existing_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    return res.data[0]


@router.get("/history", response_model=list[SearchHistoryEntry])
async def search_history(
    limit: int = Query(20, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
):
    """Recent searches, newest first."""
    sb = require_supabase()
    res = (
        sb.table("search_history")
        .select("*")
        .eq("user_id", user.id)
        .order("searched_at", desc=True)
        .limit(limit)
        .execute()
    )
    return db_rows(res)


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
async def clear_history(user: CurrentUser = Depends(get_current_user)):
    sb = require_supabase()
    sb.table("search_history").delete().eq("user_id", user.id).execute()
    return None
