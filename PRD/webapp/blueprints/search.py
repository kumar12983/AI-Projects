"""
Search, autocomplete, address, and statistics API routes.
Blueprints are intentionally thin: validate → call service → return JSON.
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required

from .db import get_db_connection, is_coordinate_like
from .validators import (
    AddressSearchQuery,
    AutocompleteQuery,
    CoordinateQuery,
    FullAddressAutocompleteQuery,
    PostcodeQuery,
    SuburbQuery,
    validate_query_params,
)
from services import search_service

search_bp = Blueprint('search', __name__)


@search_bp.route('/api/search/suburbs', methods=['GET'])
def search_suburbs_by_postcode():
    validated, err = validate_query_params(PostcodeQuery, request.args)
    if err:
        return err
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        results = search_service.search_suburbs_by_postcode(conn, validated.postcode)
        return jsonify({'postcode': validated.postcode, 'count': len(results), 'suburbs': results})
    except Exception as e:
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500
    finally:
        conn.close()


@search_bp.route('/api/search/postcodes', methods=['GET'])
def search_postcodes_by_suburb():
    validated, err = validate_query_params(SuburbQuery, request.args)
    if err:
        return err
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        results = search_service.search_postcodes_by_suburb(conn, validated.suburb)
        return jsonify({'search_term': validated.suburb, 'count': len(results), 'results': results})
    except Exception as e:
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500
    finally:
        conn.close()


@search_bp.route('/api/autocomplete/suburbs', methods=['GET'])
def autocomplete_suburbs():
    validated, err = validate_query_params(AutocompleteQuery, request.args)
    if err:
        return err
    if not validated.q or len(validated.q) < 2:
        return jsonify([])
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        return jsonify(search_service.autocomplete_suburbs(conn, validated.q))
    except Exception as e:
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500
    finally:
        conn.close()


@search_bp.route('/api/autocomplete/streets', methods=['GET'])
def autocomplete_streets():
    validated, err = validate_query_params(AutocompleteQuery, request.args)
    if err:
        return err
    if not validated.q or len(validated.q) < 2:
        return jsonify([])
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        return jsonify(search_service.autocomplete_streets(conn, validated.q))
    except Exception as e:
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500
    finally:
        conn.close()


@search_bp.route('/api/autocomplete/full-address', methods=['GET'])
def autocomplete_full_address():
    validated, err = validate_query_params(FullAddressAutocompleteQuery, request.args)
    if err:
        return err
    if not validated.q or len(validated.q) < 4:
        return jsonify([])
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        return jsonify(search_service.autocomplete_full_address(
            conn, validated.q, validated.state or ''))
    except Exception as e:
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500
    finally:
        conn.close()


@search_bp.route('/api/address/search', methods=['GET'])
def search_address():
    validated, err = validate_query_params(AddressSearchQuery, request.args)
    if err:
        return err
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        results = search_service.search_address(
            conn,
            street_number=validated.street_number or '',
            street=validated.street or '',
            suburb=validated.suburb or '',
            postcode=validated.postcode or '',
            state=validated.state or '',
            limit=validated.limit,
        )
        return jsonify({'count': len(results), 'addresses': results})
    except Exception as e:
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500
    finally:
        conn.close()


@search_bp.route('/api/address/schools', methods=['GET'])
@login_required
def get_schools_for_address():
    validated, err = validate_query_params(CoordinateQuery, request.args)
    if err:
        return err
    state = str(request.args.get('state', 'NSW')).strip()
    conn  = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        schools = search_service.get_schools_for_address(conn, validated.lat, validated.lng, state)
        return jsonify({'count': len(schools), 'schools': schools})
    except Exception as e:
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500
    finally:
        conn.close()


@search_bp.route('/api/stats', methods=['GET'])
def get_statistics():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        return jsonify(search_service.get_statistics(conn))
    except Exception as e:
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500
    finally:
        conn.close()


@search_bp.route('/api/suburbs/by-state', methods=['GET'])
def get_suburbs_by_state():
    state = request.args.get('state', '').strip()
    if not state:
        return jsonify({'error': 'State parameter is required'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        results = search_service.get_suburbs_by_state(conn, state)
        return jsonify({'state': state, 'count': len(results), 'suburbs': results})
    except Exception as e:
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500
    finally:
        conn.close()
