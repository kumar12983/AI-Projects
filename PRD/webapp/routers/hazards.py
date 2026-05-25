"""
Hazard data API routes.
"""
from fastapi import APIRouter, Depends, HTTPException

from dependencies import get_current_user_id
from schemas import HazardQuery

router = APIRouter(tags=["hazards"])


@router.get("/api/hazards")
def get_hazards(
    params: HazardQuery = Depends(),
    _uid:   int = Depends(get_current_user_id),   # auth guard
):
    try:
        from services.hazard_service import get_hazards as _get_hazards
    except ImportError:
        raise HTTPException(status_code=500, detail="Hazard API module not available")
    return _get_hazards(params.lat, params.lng)
