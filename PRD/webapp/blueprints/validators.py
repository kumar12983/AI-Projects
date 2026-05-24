"""
Pydantic input validation models for Flask blueprint endpoints.

Usage in a route:
    validated, err = validate_query_params(PostcodeQuery, request.args)
    if err:
        return err
    # use validated.postcode
"""
from typing import Optional, Tuple, Any

from flask import jsonify
from pydantic import BaseModel, field_validator, model_validator, ValidationError

VALID_AU_STATES = {'NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'NT', 'ACT'}


def validate_query_params(
    model_class: type,
    args: Any,
) -> Tuple[Optional[BaseModel], Optional[tuple]]:
    """
    Validate Flask request.args against a Pydantic model.

    Returns:
        (validated_model, None)        on success
        (None, (response, status_code)) on validation failure
    """
    try:
        return model_class(**dict(args)), None
    except ValidationError as exc:
        errors = [
            {"field": str(e["loc"][0]) if e["loc"] else "__root__", "message": e["msg"]}
            for e in exc.errors()
        ]
        return None, (jsonify({"error": "Invalid parameters", "details": errors}), 422)
    except (TypeError, ValueError) as exc:
        return None, (jsonify({"error": str(exc)}), 400)


# ---------------------------------------------------------------------------
# Search blueprint validators
# ---------------------------------------------------------------------------

class PostcodeQuery(BaseModel):
    postcode: str

    @field_validator("postcode")
    @classmethod
    def must_be_4_digits(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Postcode is required")
        if not v.isdigit() or len(v) != 4:
            raise ValueError("Postcode must be exactly 4 digits")
        return v


class SuburbQuery(BaseModel):
    suburb: str

    @field_validator("suburb")
    @classmethod
    def not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Suburb is required")
        return v


class AutocompleteQuery(BaseModel):
    """Generic short-text autocomplete (minimum 2 chars enforced in route)."""
    q: str = ""

    @field_validator("q")
    @classmethod
    def strip_q(cls, v: str) -> str:
        return v.strip()


class FullAddressAutocompleteQuery(BaseModel):
    """Full-address autocomplete (minimum 4 chars enforced in route)."""
    q: str = ""
    state: Optional[str] = None

    @field_validator("q")
    @classmethod
    def strip_q(cls, v: str) -> str:
        return v.strip()

    @field_validator("state")
    @classmethod
    def valid_state(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().upper()
            if v and v not in VALID_AU_STATES:
                raise ValueError(f"State must be one of {sorted(VALID_AU_STATES)}")
            return v or None
        return None


class AddressSearchQuery(BaseModel):
    street_number: Optional[str] = None
    street: Optional[str] = None
    suburb: Optional[str] = None
    postcode: Optional[str] = None
    state: Optional[str] = None
    limit: int = 50

    @field_validator("limit", mode="before")
    @classmethod
    def clamp_limit(cls, v: Any) -> int:
        try:
            v = int(v)
        except (TypeError, ValueError):
            raise ValueError("limit must be an integer")
        return max(1, min(v, 200))

    @field_validator("postcode")
    @classmethod
    def valid_postcode(cls, v: Optional[str]) -> Optional[str]:
        if v:
            v = v.strip()
            if not v.isdigit() or len(v) != 4:
                raise ValueError("Postcode must be exactly 4 digits")
        return v or None

    @field_validator("state")
    @classmethod
    def valid_state(cls, v: Optional[str]) -> Optional[str]:
        if v:
            v = v.strip().upper()
            if v not in VALID_AU_STATES:
                raise ValueError(f"State must be one of {sorted(VALID_AU_STATES)}")
        return v or None

    @model_validator(mode="after")
    def at_least_one_param(self) -> "AddressSearchQuery":
        if not any([self.street, self.suburb, self.postcode, self.state]):
            raise ValueError("At least one search parameter required")
        return self


class CoordinateQuery(BaseModel):
    lat: float
    lng: float

    @field_validator("lat", mode="before")
    @classmethod
    def parse_lat(cls, v: Any) -> float:
        try:
            v = float(v)
        except (TypeError, ValueError):
            raise ValueError("lat must be a number")
        if not (-90.0 <= v <= 90.0):
            raise ValueError("lat must be between -90 and 90")
        return v

    @field_validator("lng", mode="before")
    @classmethod
    def parse_lng(cls, v: Any) -> float:
        try:
            v = float(v)
        except (TypeError, ValueError):
            raise ValueError("lng must be a number")
        if not (-180.0 <= v <= 180.0):
            raise ValueError("lng must be between -180 and 180")
        return v


class StateQuery(BaseModel):
    state: str

    @field_validator("state")
    @classmethod
    def valid_state(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("State is required")
        if v not in VALID_AU_STATES:
            raise ValueError(f"State must be one of {sorted(VALID_AU_STATES)}")
        return v


# ---------------------------------------------------------------------------
# Schools blueprint validators
# ---------------------------------------------------------------------------

class SchoolAutocompleteQuery(BaseModel):
    q: str = ""
    type: Optional[str] = None
    state: str = "NSW"

    @field_validator("q")
    @classmethod
    def strip_q(cls, v: str) -> str:
        return v.strip()

    @field_validator("state")
    @classmethod
    def valid_state(cls, v: str) -> str:
        v = v.strip().upper()
        if v and v not in VALID_AU_STATES:
            raise ValueError(f"State must be one of {sorted(VALID_AU_STATES)}")
        return v or "NSW"


class SchoolAddressFilterQuery(BaseModel):
    street: Optional[str] = None
    suburb: Optional[str] = None
    limit: int = 100
    offset: int = 0

    @field_validator("limit", mode="before")
    @classmethod
    def clamp_limit(cls, v: Any) -> int:
        try:
            v = int(v)
        except (TypeError, ValueError):
            raise ValueError("limit must be an integer")
        return max(1, min(v, 500))

    @field_validator("offset", mode="before")
    @classmethod
    def non_negative_offset(cls, v: Any) -> int:
        try:
            v = int(v)
        except (TypeError, ValueError):
            raise ValueError("offset must be an integer")
        if v < 0:
            raise ValueError("Offset must be >= 0")
        return v


# ---------------------------------------------------------------------------
# Australia-wide schools blueprint validators
# ---------------------------------------------------------------------------

class AusSchoolAutocompleteQuery(BaseModel):
    q: str = ""
    state: Optional[str] = None

    @field_validator("q")
    @classmethod
    def strip_q(cls, v: str) -> str:
        return v.strip()

    @field_validator("state")
    @classmethod
    def valid_state(cls, v: Optional[str]) -> Optional[str]:
        if v:
            v = v.strip().upper()
            if v not in VALID_AU_STATES:
                raise ValueError(f"State must be one of {sorted(VALID_AU_STATES)}")
        return v or None


# ---------------------------------------------------------------------------
# Hazards blueprint validators
# ---------------------------------------------------------------------------

class HazardQuery(BaseModel):
    lat: float
    lng: float

    @field_validator("lat", mode="before")
    @classmethod
    def parse_lat(cls, v: Any) -> float:
        try:
            v = float(v)
        except (TypeError, ValueError):
            raise ValueError("lat must be a number")
        if not (-90.0 <= v <= 90.0):
            raise ValueError("lat must be between -90 and 90")
        return v

    @field_validator("lng", mode="before")
    @classmethod
    def parse_lng(cls, v: Any) -> float:
        try:
            v = float(v)
        except (TypeError, ValueError):
            raise ValueError("lng must be a number")
        if not (-180.0 <= v <= 180.0):
            raise ValueError("lng must be between -180 and 180")
        return v
