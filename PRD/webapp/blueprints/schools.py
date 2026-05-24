"""
NSW school catchment API routes.
Blueprints are intentionally thin: validate → call service → return JSON.
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required

from .db import get_db_connection, is_coordinate_like
from .validators import SchoolAutocompleteQuery, validate_query_params
from services import school_service

schools_bp = Blueprint('schools', __name__)

@schools_bp.route('/api/autocomplete/schools', methods=['GET'])
@login_required
def autocomplete_schools():
    validated, err = validate_query_params(SchoolAutocompleteQuery, request.args)
    if err:
        return err
    if not validated.q or len(validated.q) < 3:
        return jsonify([])
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        return jsonify(school_service.autocomplete_schools(
            conn, validated.q, validated.type or '', validated.state))
    except Exception as e:
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500
    finally:
        conn.close()


@schools_bp.route('/api/school/<school_id>/autocomplete/streets', methods=['GET'])
@login_required
def autocomplete_school_streets(school_id):
    query = str(request.args.get('q', '')).strip()
    if not query or len(query) < 2:
        return jsonify([])
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        return jsonify(school_service.autocomplete_school_streets(conn, school_id, query))
    except Exception as e:
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500
    finally:
        conn.close()


@schools_bp.route('/api/school/<school_id>/autocomplete/suburbs', methods=['GET'])
@login_required
def autocomplete_school_suburbs(school_id):
    query = str(request.args.get('q', '')).strip()
    if not query or len(query) < 2:
        return jsonify([])
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        return jsonify(school_service.autocomplete_school_suburbs(conn, school_id, query))
    except Exception as e:
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500
    finally:
        conn.close()


@schools_bp.route('/api/school/<school_id>/autocomplete/postcodes', methods=['GET'])
@login_required
def autocomplete_school_postcodes(school_id):
    query = str(request.args.get('q', '')).strip()
    if not query or len(query) < 1:
        return jsonify([])
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        return jsonify(school_service.autocomplete_school_postcodes(conn, school_id, query))
    except Exception as e:
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500
    finally:
        conn.close()


@schools_bp.route('/api/school/<int:school_id>/info', methods=['GET'])
@login_required
def get_school_info(school_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        result = school_service.get_school_info(conn, school_id)
        if result is None:
            return jsonify({'error': 'School not found'}), 404
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500
    finally:
        conn.close()


@schools_bp.route('/api/school/<school_id>/addresses', methods=['GET'])
@login_required
def get_school_addresses(school_id):
    limit  = request.args.get('limit',  '500')
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
        limit  = 500
        offset = 0

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        result = school_service.get_school_addresses(
            conn, school_id,
            street_number=street_number, street=street,
            suburb=suburb, postcode=postcode, state=state,
            limit=limit, offset=offset,
        )
        if result is None:
            return jsonify({'error': 'School not found'}), 404
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500
    finally:
        conn.close()


@schools_bp.route('/api/school/<school_id>/boundary', methods=['GET'])
@login_required
def get_school_boundary(school_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        result = school_service.get_school_boundary(conn, school_id)
        if result is None:
            return jsonify({'error': 'School boundary not found'}), 404
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500
    finally:
        conn.close()

