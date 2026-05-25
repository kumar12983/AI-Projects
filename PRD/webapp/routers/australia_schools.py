"""
Australia-wide school API routes.
All routes require a valid JWT Bearer token.
"""
from fastapi import APIRouter, Depends, HTTPException, Query

from dependencies import get_current_user_id, get_db
from schemas import AusSchoolAutocompleteQuery, SchoolAddressFilterQuery
from services import australia_schools_service

router = APIRouter(tags=["australia_schools"])


@router.get("/api/autocomplete/australia-schools")
def autocomplete_australia_schools(
    params: AusSchoolAutocompleteQuery = Depends(),
    _uid:   int = Depends(get_current_user_id),
    conn=Depends(get_db),
):
    return australia_schools_service.autocomplete_australia_schools(
        conn,
        query=params.q,
        state=params.state or "",
    )


@router.get("/api/australia-school/{acara_sml_id}/info")
def get_australia_school_info(
    acara_sml_id: str,          # string — some IDs are non-numeric
    _uid: int = Depends(get_current_user_id),
    conn=Depends(get_db),
):
    info = australia_schools_service.get_australia_school_info(conn, acara_sml_id)
    if info is None:
        raise HTTPException(status_code=404, detail="School not found")
    return info


@router.get("/api/australia-school/{acara_sml_id}/addresses")
def get_australia_school_addresses(
    acara_sml_id: int,
    params: SchoolAddressFilterQuery = Depends(),
    _uid:   int = Depends(get_current_user_id),
    conn=Depends(get_db),
):
    result = australia_schools_service.get_australia_school_addresses(
        conn,
        acara_sml_id=acara_sml_id,
        street_number=params.street_number or "",
        street=params.street or "",
        suburb=params.suburb or "",
        postcode=params.postcode or "",
        state=params.state or "",
        limit=params.limit or 100,
        offset=params.offset or 0,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="School not found")
    if isinstance(result, dict) and result.get("no_coordinates"):
        return {"message": "School location coordinates not available"}
    return result


@router.get("/api/australia-school/{acara_sml_id}/autocomplete/streets")
def autocomplete_australia_school_streets(
    acara_sml_id: int,
    q:    str = Query(..., min_length=1),
    _uid: int = Depends(get_current_user_id),
    conn=Depends(get_db),
):
    return australia_schools_service.autocomplete_australia_school_streets(
        conn, acara_sml_id, q
    )


@router.get("/api/australia-school/{acara_sml_id}/autocomplete/suburbs")
def autocomplete_australia_school_suburbs(
    acara_sml_id: int,
    q:    str = Query(..., min_length=1),
    _uid: int = Depends(get_current_user_id),
    conn=Depends(get_db),
):
    return australia_schools_service.autocomplete_australia_school_suburbs(
        conn, acara_sml_id, q
    )


@router.get("/api/australia-school/{acara_sml_id}/autocomplete/postcodes")
def autocomplete_australia_school_postcodes(
    acara_sml_id: int,
    q:    str = Query(..., min_length=1),
    _uid: int = Depends(get_current_user_id),
    conn=Depends(get_db),
):
    return australia_schools_service.autocomplete_australia_school_postcodes(
        conn, acara_sml_id, q
    )
