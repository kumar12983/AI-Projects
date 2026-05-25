"""
FastAPI-compatible re-export of Pydantic validator models.
Underlying model logic lives in blueprints/validators.py (unchanged).
Used with Depends() in FastAPI routers for automatic query-param validation.

Note: blueprints/validators.py imports `from flask import jsonify` for the
validate_query_params() helper (Flask-only).  That import is harmless here
because Flask is installed in the same venv.  Only the Pydantic model classes
are used by FastAPI — validate_query_params() is never called in router code.
"""
from blueprints.validators import (          # noqa: F401  (re-exported)
    PostcodeQuery,
    SuburbQuery,
    AutocompleteQuery,
    FullAddressAutocompleteQuery,
    AddressSearchQuery,
    CoordinateQuery,
    StateQuery,
    SchoolAutocompleteQuery,
    SchoolAddressFilterQuery,
    AusSchoolAutocompleteQuery,
    HazardQuery,
    VALID_AU_STATES,
)
from pydantic import BaseModel, field_validator


class LoginRequest(BaseModel):
    """Request body for POST /api/auth/login."""
    email:    str
    password: str

    @field_validator("email")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            raise ValueError("email is required")
        return v

    @field_validator("password")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("password is required")
        return v
