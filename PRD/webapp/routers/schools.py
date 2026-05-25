"""
NSW/VIC school catchment API routes.
All routes require a valid JWT Bearer token.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from dependencies import get_current_user_id, get_db
from schemas import SchoolAutocompleteQuery, SchoolAddressFilterQuery
from services import school_service

router = APIRouter(tags=["schools"])


@router.get("/api/autocomplete/schools")
def autocomplete_schools(
    params: SchoolAutocompleteQuery = Depends(),
    _uid:   int = Depends(get_current_user_id),
    conn=Depends(get_db),
):
    results = school_service.autocomplete_schools(
        conn,
        query=params.q,
        school_type=params.type or "",
        state=params.state or "NSW",
    )
    return results


@router.get("/api/school/{school_id}/autocomplete/streets")
def autocomplete_school_streets(
    school_id: int,
    q:    str = Query(..., min_length=1),
    _uid: int = Depends(get_current_user_id),
    conn=Depends(get_db),
):
    return school_service.autocomplete_school_streets(conn, school_id, q)


@router.get("/api/school/{school_id}/autocomplete/suburbs")
def autocomplete_school_suburbs(
    school_id: int,
    q:    str = Query(..., min_length=1),
    _uid: int = Depends(get_current_user_id),
    conn=Depends(get_db),
):
    return school_service.autocomplete_school_suburbs(conn, school_id, q)


@router.get("/api/school/{school_id}/autocomplete/postcodes")
def autocomplete_school_postcodes(
    school_id: int,
    q:    str = Query(..., min_length=1),
    _uid: int = Depends(get_current_user_id),
    conn=Depends(get_db),
):
    return school_service.autocomplete_school_postcodes(conn, school_id, q)


@router.get("/api/school/{school_id}/info")
def get_school_info(
    school_id: int,
    _uid: int = Depends(get_current_user_id),
    conn=Depends(get_db),
):
    info = school_service.get_school_info(conn, school_id)
    if info is None:
        raise HTTPException(status_code=404, detail="School not found")
    return info


@router.get("/api/school/{school_id}/addresses")
def get_school_addresses(
    school_id:     int,
    params:        SchoolAddressFilterQuery = Depends(),
    _uid:          int = Depends(get_current_user_id),
    conn=Depends(get_db),
):
    result = school_service.get_school_addresses(
        conn,
        school_id=school_id,
        street_number=params.street_number or "",
        street=params.street or "",
        suburb=params.suburb or "",
        postcode=params.postcode or "",
        state=params.state or "",
        limit=params.limit or 500,
        offset=params.offset or 0,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="School not found")
    return result


@router.get("/api/school/{school_id}/boundary")
def get_school_boundary(
    school_id: int,
    _uid: int = Depends(get_current_user_id),
    conn=Depends(get_db),
):
    boundary = school_service.get_school_boundary(conn, school_id)
    if boundary is None:
        raise HTTPException(status_code=404, detail="School boundary not found")
    return boundary
