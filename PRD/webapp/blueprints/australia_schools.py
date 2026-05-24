"""
Australia-wide school (5 km radius) API routes.
Blueprints are intentionally thin: validate → call service → return JSON.
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required

from .db import get_db_connection, is_coordinate_like
from .validators import AusSchoolAutocompleteQuery, validate_query_params
from services import australia_schools_service

aus_schools_bp = Blueprint('aus_schools', __name__)


@aus_schools_bp.route('/api/autocomplete/australia-schools', methods=['GET'])
@login_required
def autocomplete_australia_schools():
    validated, err = validate_query_params(AusSchoolAutocompleteQuery, request.args)
    if err:
        return err
    if not validated.q or len(validated.q) < 3:
        return jsonify([])
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        return jsonify(australia_schools_service.autocomplete_australia_schools(
            conn, validated.q, validated.state or ''))
    except Exception as e:
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500
    finally:
        conn.close()


@aus_schools_bp.route('/api/australia-school/<string:acara_sml_id>/info', methods=['GET'])
@login_required
def get_australia_school_info(acara_sml_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        result = australia_schools_service.get_australia_school_info(conn, acara_sml_id)
        if result is None:
            return jsonify({'error': 'School not found'}), 404
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500
    finally:
        conn.close()


@aus_schools_bp.route('/api/australia-school/<int:acara_sml_id>/addresses', methods=['GET'])
@login_required
def get_australia_school_addresses(acara_sml_id):
    limit  = request.args.get('limit',  '100')
    offset = request.args.get('offset', '0')
    street_number = request.args.get('street_number', '').strip()
    street        = request.args.get('street',        '').strip()
    suburb        = request.args.get('suburb',        '').strip()
    postcode      = request.args.get('postcode',      '').strip()
    state         = request.args.get('state',         '').strip()

    if street and is_coordinate_like(street):
        return jsonify({'error': 'Invalid street name: looks like a coordinate value'}), 400
    if suburb and is_coordinate_like(suburb):
        return jsonify({'error': 'Invalid suburb name: looks like a coordinate value'}), 400

    try:
        limit  = int(limit)
        offset = int(offset)
    except Exception:
        limit  = 100
        offset = 0

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        result = australia_schools_service.get_australia_school_addresses(
            conn, acara_sml_id,
            street_number=street_number, street=street,
            suburb=suburb, postcode=postcode, state=state,
            limit=limit, offset=offset,
        )
        if result is None:
            return jsonify({'error': 'School not found'}), 404
        if result.get('no_coordinates'):
            return jsonify({'error': 'School coordinates not available. Unable to search addresses within 5km radius.'}), 200
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500
    finally:
        conn.close()


@aus_schools_bp.route('/api/australia-school/<int:acara_sml_id>/autocomplete/streets', methods=['GET'])
@login_required
def autocomplete_australia_school_streets(acara_sml_id):
    query = str(request.args.get('q', '')).strip()
    if not query or len(query) < 2 or is_coordinate_like(query):
        return jsonify([])
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        return jsonify(australia_schools_service.autocomplete_australia_school_streets(
            conn, acara_sml_id, query))
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@aus_schools_bp.route('/api/australia-school/<int:acara_sml_id>/autocomplete/suburbs', methods=['GET'])
@login_required
def autocomplete_australia_school_suburbs(acara_sml_id):
    query = str(request.args.get('q', '')).strip()
    if not query or len(query) < 2:
        return jsonify([])
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        return jsonify(australia_schools_service.autocomplete_australia_school_suburbs(
            conn, acara_sml_id, query))
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@aus_schools_bp.route('/api/australia-school/<int:acara_sml_id>/autocomplete/postcodes', methods=['GET'])
@login_required
def autocomplete_australia_school_postcodes(acara_sml_id):
    query = str(request.args.get('q', '')).strip()
    if not query or len(query) < 2:
        return jsonify([])
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        return jsonify(australia_schools_service.autocomplete_australia_school_postcodes(
            conn, acara_sml_id, query))
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
