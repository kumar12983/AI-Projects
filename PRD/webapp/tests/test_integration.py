"""
Integration tests for Flask blueprint endpoints.

Tests the HTTP layer using Flask's test client with the database
connection mocked out. Covers:
  - Valid inputs → correct status code and response shape
  - Invalid/missing inputs → 400 / 422 validation errors
  - Auth-protected routes → 401/302 when unauthenticated
"""
import json
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# App fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    """Create the Flask app configured for testing."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    # Provide minimal env so app.py does not blow up without a real .env
    os.environ.setdefault("SECRET_KEY", "test-secret")
    os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")
    os.environ.setdefault("DB_HOST", "localhost")
    os.environ.setdefault("DB_NAME", "gnaf_db")
    os.environ.setdefault("DB_USER", "postgres")
    os.environ.setdefault("DB_PASSWORD", "")
    os.environ.setdefault("MAIL_USERNAME", "test@example.com")
    os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_dummy")
    os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_dummy")

    from app import app as flask_app
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def jwt_token(app):
    """Return a valid JWT access token for a dummy user (id=1)."""
    with app.app_context():
        from flask_jwt_extended import create_access_token
        # flask-jwt-extended 4.7+ requires identity to be a string.
        return create_access_token(identity="1")


@pytest.fixture
def auth_headers(jwt_token):
    """Authorization header dict for protected API requests."""
    return {'Authorization': f'Bearer {jwt_token}'}


# ---------------------------------------------------------------------------
# Shared DB mock helper
# ---------------------------------------------------------------------------

def make_cursor_mock(rows):
    """Return a mock cursor whose fetchall() returns *rows*."""
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    cursor.fetchone.return_value = rows[0] if rows else None
    # Services use `with conn.cursor(...) as cur:` — ensure __enter__ returns this
    # same cursor so fetchall/fetchone return the configured values.
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    return cursor


def make_conn_mock(rows=None):
    """Return a (conn_mock, cursor_mock) pair pre-wired for get_db_connection."""
    cursor = make_cursor_mock(rows or [])
    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


# ===========================================================================
# /api/search/suburbs
# ===========================================================================

class TestSearchSuburbs:
    ENDPOINT = "/api/search/suburbs"

    def test_valid_postcode_returns_200(self, client):
        conn, cursor = make_conn_mock([
            {"suburb": "SYDNEY", "postcode": "2000", "state": "New South Wales", "address_count": 0}
        ])
        with patch("blueprints.search.get_db_connection", return_value=conn):
            resp = client.get(f"{self.ENDPOINT}?postcode=2000")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["postcode"] == "2000"
        assert isinstance(data["suburbs"], list)

    def test_missing_postcode_returns_422(self, client):
        resp = client.get(self.ENDPOINT)
        assert resp.status_code == 422

    def test_non_numeric_postcode_returns_422(self, client):
        resp = client.get(f"{self.ENDPOINT}?postcode=ABCD")
        assert resp.status_code == 422

    def test_too_short_postcode_returns_422(self, client):
        resp = client.get(f"{self.ENDPOINT}?postcode=200")
        assert resp.status_code == 422

    def test_five_digit_postcode_returns_422(self, client):
        resp = client.get(f"{self.ENDPOINT}?postcode=20001")
        assert resp.status_code == 422

    def test_db_failure_returns_500(self, client):
        with patch("blueprints.search.get_db_connection", return_value=None):
            resp = client.get(f"{self.ENDPOINT}?postcode=2000")
        assert resp.status_code == 500


# ===========================================================================
# /api/search/postcodes
# ===========================================================================

class TestSearchPostcodes:
    ENDPOINT = "/api/search/postcodes"

    def test_valid_suburb_returns_200(self, client):
        conn, _ = make_conn_mock([
            {"suburb": "SYDNEY", "postcode": "2000", "state": "New South Wales", "address_count": 0}
        ])
        with patch("blueprints.search.get_db_connection", return_value=conn):
            resp = client.get(f"{self.ENDPOINT}?suburb=Sydney")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "results" in data

    def test_missing_suburb_returns_422(self, client):
        resp = client.get(self.ENDPOINT)
        assert resp.status_code == 422

    def test_empty_suburb_returns_422(self, client):
        resp = client.get(f"{self.ENDPOINT}?suburb=")
        assert resp.status_code == 422


# ===========================================================================
# /api/autocomplete/suburbs
# ===========================================================================

class TestAutocompleteSuburbs:
    ENDPOINT = "/api/autocomplete/suburbs"

    def test_valid_query_returns_200(self, client):
        conn, _ = make_conn_mock([{"suburb": "SYDNEY", "postcode": "2000", "state": "NSW"}])
        with patch("blueprints.search.get_db_connection", return_value=conn):
            resp = client.get(f"{self.ENDPOINT}?q=Syd")
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)

    def test_too_short_query_returns_empty_list(self, client):
        resp = client.get(f"{self.ENDPOINT}?q=S")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_empty_query_returns_empty_list(self, client):
        resp = client.get(self.ENDPOINT)
        assert resp.status_code == 200
        assert resp.get_json() == []


# ===========================================================================
# /api/autocomplete/streets
# ===========================================================================

class TestAutocompleteStreets:
    ENDPOINT = "/api/autocomplete/streets"

    def test_valid_query_returns_200(self, client):
        conn, _ = make_conn_mock([{"street_name": "GEORGE", "street_type": "Street"}])
        with patch("blueprints.search.get_db_connection", return_value=conn):
            resp = client.get(f"{self.ENDPOINT}?q=George")
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)

    def test_single_char_returns_empty_list(self, client):
        resp = client.get(f"{self.ENDPOINT}?q=G")
        assert resp.status_code == 200
        assert resp.get_json() == []


# ===========================================================================
# /api/autocomplete/full-address
# ===========================================================================

class TestAutocompleteFullAddress:
    ENDPOINT = "/api/autocomplete/full-address"

    def test_valid_query_returns_200(self, client):
        conn, _ = make_conn_mock([{
            "address_detail_pid": "pid1", "full_address": "68 BINGARA RD, BELROSE NSW 2085",
            "building_name": None, "number_first": 68, "number_first_suffix": None,
            "number_last": None, "number_last_suffix": None, "flat_type": None,
            "flat_number": None, "street_name": "BINGARA", "street_type": "Road",
            "suburb": "BELROSE", "state": "NSW", "postcode": "2085",
            "latitude": -33.7, "longitude": 151.2
        }])
        with patch("blueprints.search.get_db_connection", return_value=conn):
            resp = client.get(f"{self.ENDPOINT}?q=68+Bingara")
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)

    def test_too_short_returns_empty_list(self, client):
        resp = client.get(f"{self.ENDPOINT}?q=68")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_invalid_state_returns_422(self, client):
        resp = client.get(f"{self.ENDPOINT}?q=George+St&state=INVALID")
        assert resp.status_code == 422

    def test_valid_state_filter_accepted(self, client):
        conn, _ = make_conn_mock([])
        with patch("blueprints.search.get_db_connection", return_value=conn):
            resp = client.get(f"{self.ENDPOINT}?q=George+St&state=NSW")
        assert resp.status_code == 200


# ===========================================================================
# /api/address/search
# ===========================================================================

class TestAddressSearch:
    ENDPOINT = "/api/address/search"

    def test_valid_street_returns_200(self, client):
        conn, _ = make_conn_mock([{
            "address_detail_pid": "p1", "building_name": None, "number_first": 1,
            "number_first_suffix": None, "number_last": None, "number_last_suffix": None,
            "flat_number": None, "confidence": 2, "flat_type": None,
            "street_number": "1", "street_name": "GEORGE", "street_type": "Street",
            "suburb": "SYDNEY", "state": "NSW", "postcode": "2000",
            "latitude": -33.8, "longitude": 151.2, "geocode_type_code": "PROPERTY",
            "last_sold_price": None, "last_sale_date": None
        }])
        with patch("blueprints.search.get_db_connection", return_value=conn):
            resp = client.get(f"{self.ENDPOINT}?street=George&suburb=Sydney")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "addresses" in data

    def test_no_params_returns_422(self, client):
        resp = client.get(self.ENDPOINT)
        assert resp.status_code == 422

    def test_invalid_postcode_returns_422(self, client):
        resp = client.get(f"{self.ENDPOINT}?street=George&postcode=200X")
        assert resp.status_code == 422

    def test_invalid_state_returns_422(self, client):
        resp = client.get(f"{self.ENDPOINT}?street=George&state=ZZ")
        assert resp.status_code == 422

    def test_limit_is_clamped(self, client):
        """limit > 200 is clamped to 200 — no error returned."""
        conn, _ = make_conn_mock([])
        with patch("blueprints.search.get_db_connection", return_value=conn):
            resp = client.get(f"{self.ENDPOINT}?state=NSW&limit=9999")
        assert resp.status_code == 200


# ===========================================================================
# /api/address/schools  (login_required — expect redirect when anonymous)
# ===========================================================================

class TestAddressSchools:
    ENDPOINT = "/api/address/schools"

    def test_unauthenticated_returns_401(self, client):
        resp = client.get(f"{self.ENDPOINT}?lat=-33.8688&lng=151.2093")
        assert resp.status_code == 401

    def test_invalid_lat_returns_422(self, client, auth_headers):
        resp = client.get(f"{self.ENDPOINT}?lat=999&lng=151.2", headers=auth_headers)
        assert resp.status_code == 422

    def test_authenticated_with_db_returns_200(self, client, auth_headers):
        conn, _ = make_conn_mock([])
        with patch("blueprints.search.get_db_connection", return_value=conn):
            resp = client.get(
                f"{self.ENDPOINT}?lat=-33.8688&lng=151.2093", headers=auth_headers
            )
        assert resp.status_code == 200


# ===========================================================================
# /api/hazards  (login_required — expect redirect when anonymous)
# ===========================================================================

class TestHazards:
    ENDPOINT = "/api/hazards"

    def test_unauthenticated_returns_401(self, client):
        resp = client.get(f"{self.ENDPOINT}?lat=-33.8&lng=151.2")
        assert resp.status_code == 401

    def test_missing_params_returns_422(self, client, auth_headers):
        resp = client.get(self.ENDPOINT, headers=auth_headers)
        assert resp.status_code == 422


# ===========================================================================
# /api/autocomplete/schools  (login_required)
# ===========================================================================

class TestAutocompleteSchools:
    ENDPOINT = "/api/autocomplete/schools"

    def test_unauthenticated_returns_401(self, client):
        resp = client.get(f"{self.ENDPOINT}?q=Hornsby")
        assert resp.status_code == 401

    def test_invalid_state_returns_422(self, client, auth_headers):
        resp = client.get(f"{self.ENDPOINT}?q=Hornsby&state=BADSTATE", headers=auth_headers)
        assert resp.status_code == 422


# ===========================================================================
# /api/autocomplete/australia-schools  (login_required)
# ===========================================================================

class TestAutocompleteAusSchools:
    ENDPOINT = "/api/autocomplete/australia-schools"

    def test_unauthenticated_returns_401(self, client):
        resp = client.get(f"{self.ENDPOINT}?q=Hornsby")
        assert resp.status_code == 401

    def test_invalid_state_returns_422(self, client, auth_headers):
        resp = client.get(f"{self.ENDPOINT}?q=Hornsby&state=BADSTATE", headers=auth_headers)
        assert resp.status_code == 422


# ===========================================================================
# /api/stats
# ===========================================================================

class TestStats:
    ENDPOINT = "/api/stats"

    def test_returns_200_on_success(self, client):
        conn = MagicMock()
        summary_cursor = MagicMock()
        summary_cursor.fetchone.return_value = {
            "total_localities": 10000,
            "total_addresses": 5000000,
            "total_streets": 200000,
            "last_refreshed": None,
        }
        summary_cursor.fetchall.return_value = []
        # Services use `with conn.cursor(...) as cur:` context manager.
        summary_cursor.__enter__ = MagicMock(return_value=summary_cursor)
        summary_cursor.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = summary_cursor

        with patch("blueprints.search.get_db_connection", return_value=conn):
            resp = client.get(self.ENDPOINT)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "total_addresses" in data

    def test_db_failure_returns_500(self, client):
        with patch("blueprints.search.get_db_connection", return_value=None):
            resp = client.get(self.ENDPOINT)
        assert resp.status_code == 500


# ===========================================================================
# /api/auth  (JWT login / refresh / logout)
# ===========================================================================

class TestApiAuth:

    def test_login_missing_fields_returns_400(self, client):
        resp = client.post('/api/auth/login', json={})
        assert resp.status_code == 400

    def test_login_invalid_credentials_returns_401(self, client):
        with patch('services.user_service.authenticate_user', return_value=None), \
             patch('api_auth.get_db_connection', return_value=MagicMock()):
            resp = client.post('/api/auth/login', json={'email': 'a@b.com', 'password': 'wrong'})
        assert resp.status_code == 401

    def test_login_valid_returns_tokens(self, client, app):
        from models import User
        fake_user = MagicMock(spec=User)
        fake_user.user_id = 1
        with patch('services.user_service.authenticate_user', return_value=fake_user), \
             patch('api_auth.get_db_connection', return_value=MagicMock()):
            resp = client.post('/api/auth/login', json={'email': 'a@b.com', 'password': 'correct'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'access_token' in data
        assert 'refresh_token' in data

    def test_refresh_without_token_returns_401(self, client):
        resp = client.post('/api/auth/refresh')
        assert resp.status_code == 401

    def test_logout_without_token_returns_401(self, client):
        resp = client.delete('/api/auth/logout')
        assert resp.status_code == 401

    def test_logout_with_valid_token_returns_200(self, client, auth_headers):
        resp = client.delete('/api/auth/logout', headers=auth_headers)
        assert resp.status_code == 200


# ===========================================================================
# Pydantic validator unit tests (no HTTP layer needed)
# ===========================================================================

class TestValidators:

    def test_postcode_valid(self):
        from blueprints.validators import PostcodeQuery
        m = PostcodeQuery(postcode="2000")
        assert m.postcode == "2000"

    def test_postcode_invalid_letters(self):
        from blueprints.validators import PostcodeQuery
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PostcodeQuery(postcode="ABCD")

    def test_postcode_too_short(self):
        from blueprints.validators import PostcodeQuery
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PostcodeQuery(postcode="200")

    def test_coordinate_out_of_range_lat(self):
        from blueprints.validators import CoordinateQuery
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CoordinateQuery(lat=999, lng=151.0)

    def test_coordinate_out_of_range_lng(self):
        from blueprints.validators import CoordinateQuery
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CoordinateQuery(lat=-33.8, lng=200.0)

    def test_coordinate_valid_sydney(self):
        from blueprints.validators import CoordinateQuery
        m = CoordinateQuery(lat=-33.8688, lng=151.2093)
        assert m.lat == pytest.approx(-33.8688)
        assert m.lng == pytest.approx(151.2093)

    def test_state_invalid(self):
        from blueprints.validators import StateQuery
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            StateQuery(state="XX")

    def test_state_valid_all_abbreviations(self):
        from blueprints.validators import VALID_AU_STATES, StateQuery
        for state in VALID_AU_STATES:
            m = StateQuery(state=state)
            assert m.state == state

    def test_address_search_no_params_raises(self):
        from blueprints.validators import AddressSearchQuery
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            AddressSearchQuery()

    def test_address_search_limit_clamped(self):
        from blueprints.validators import AddressSearchQuery
        m = AddressSearchQuery(state="NSW", limit=9999)
        assert m.limit == 200

    def test_address_search_limit_floor(self):
        from blueprints.validators import AddressSearchQuery
        m = AddressSearchQuery(state="NSW", limit=0)
        assert m.limit == 1

    def test_school_autocomplete_default_state(self):
        from blueprints.validators import SchoolAutocompleteQuery
        m = SchoolAutocompleteQuery(q="Hornsby")
        assert m.state == "NSW"

    def test_school_autocomplete_invalid_state(self):
        from blueprints.validators import SchoolAutocompleteQuery
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            SchoolAutocompleteQuery(q="Hornsby", state="BADSTATE")

    def test_full_address_invalid_state(self):
        from blueprints.validators import FullAddressAutocompleteQuery
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            FullAddressAutocompleteQuery(q="George St", state="INVALID")

    def test_full_address_state_normalised_to_uppercase(self):
        from blueprints.validators import FullAddressAutocompleteQuery
        m = FullAddressAutocompleteQuery(q="George St", state="nsw")
        assert m.state == "NSW"

    def test_validate_query_params_returns_model_on_success(self):
        from blueprints.validators import PostcodeQuery, validate_query_params
        model, err = validate_query_params(PostcodeQuery, {"postcode": "2000"})
        assert err is None
        assert model.postcode == "2000"

    def test_validate_query_params_returns_error_on_failure(self, app):
        from blueprints.validators import PostcodeQuery, validate_query_params
        with app.app_context():
            model, err = validate_query_params(PostcodeQuery, {"postcode": "bad"})
        assert model is None
        assert err is not None
