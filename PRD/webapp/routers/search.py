"""
Search, autocomplete, address, and statistics API routes.
Routers are intentionally thin: validate (Pydantic/Depends) → call service → return dict.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError as _PydanticValidationError

from db_utils import is_coordinate_like
from dependencies import get_db, get_current_user_id
from schemas import (
    PostcodeQuery,
    SuburbQuery,
    AutocompleteQuery,
    FullAddressAutocompleteQuery,
    AddressSearchQuery,
    CoordinateQuery,
)
from services import search_service

router = APIRouter(tags=["search"])


def _postcode_query(postcode: str = Query(...)) -> PostcodeQuery:
    """Wrapper that converts Pydantic ValidationError → HTTPException(422)."""
    try:
        return PostcodeQuery(postcode=postcode)
    except _PydanticValidationError as exc:
        # Strip non-serialisable 'ctx' (contains raw Exception objects)
        errors = [{k: v for k, v in e.items() if k != "ctx"} for e in exc.errors()]
        raise HTTPException(status_code=422, detail=errors)


@router.get("/api/search/suburbs")
def search_suburbs(params: PostcodeQuery = Depends(_postcode_query), conn=Depends(get_db)):
    results = search_service.search_suburbs_by_postcode(conn, params.postcode)
    return {"postcode": params.postcode, "count": len(results), "suburbs": results}


@router.get("/api/search/postcodes")
def search_postcodes(params: SuburbQuery = Depends(), conn=Depends(get_db)):
    results = search_service.search_postcodes_by_suburb(conn, params.suburb)
    return {"search_term": params.suburb, "count": len(results), "results": results}


@router.get("/api/autocomplete/suburbs")
def autocomplete_suburbs(params: AutocompleteQuery = Depends(), conn=Depends(get_db)):
    if len(params.q) < 2:
        return []
    return search_service.autocomplete_suburbs(conn, params.q)


@router.get("/api/autocomplete/streets")
def autocomplete_streets(params: AutocompleteQuery = Depends(), conn=Depends(get_db)):
    if len(params.q) < 2:
        return []
    return search_service.autocomplete_streets(conn, params.q)


@router.get("/api/autocomplete/full-address")
def autocomplete_full_address(
    params: FullAddressAutocompleteQuery = Depends(),
    conn=Depends(get_db),
):
    if len(params.q) < 4:
        return []
    return search_service.autocomplete_full_address(conn, params.q, params.state or "")


@router.get("/api/address/search")
def address_search(params: AddressSearchQuery = Depends(), conn=Depends(get_db)):
    results = search_service.search_address(
        conn,
        street_number=params.street_number or "",
        street=params.street or "",
        suburb=params.suburb or "",
        postcode=params.postcode or "",
        state=params.state or "",
        limit=params.limit,
    )
    return {"count": len(results), "addresses": results}


@router.get("/api/address/schools")
def get_schools_for_address(
    params: CoordinateQuery = Depends(),
    state:  str = Query("NSW"),
    _uid:   int = Depends(get_current_user_id),   # auth guard — value unused
    conn=Depends(get_db),
):
    schools = search_service.get_schools_for_address(conn, params.lat, params.lng, state)
    return {"count": len(schools), "schools": schools}


@router.get("/api/stats")
def get_stats(conn=Depends(get_db)):
    return search_service.get_statistics(conn)


@router.get("/api/suburbs/by-state")
def suburbs_by_state(
    state: str = Query(..., min_length=1),
    conn=Depends(get_db),
):
    results = search_service.get_suburbs_by_state(conn, state)
    return {"state": state, "count": len(results), "suburbs": results}
