"""
Premium-only API routes (CSV export and analytics).
Requires an active premium subscription — enforced by get_premium_user.
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from dependencies import get_premium_user, get_db
from services import premium_service

router = APIRouter(tags=["premium"])


@router.get("/api/export/suburbs")
def export_suburbs_csv(
    state: str = Query(""),
    user=Depends(get_premium_user),
    conn=Depends(get_db),
):
    csv_data = premium_service.export_suburbs_csv(conn, state=state)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=suburbs.csv"},
    )


@router.get("/api/premium/analytics")
def get_premium_analytics(
    suburb:   str = Query(""),
    postcode: str = Query(""),
    user=Depends(get_premium_user),
    conn=Depends(get_db),
):
    return premium_service.get_premium_analytics(conn, suburb=suburb, postcode=postcode)
