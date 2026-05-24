"""
Premium feature API routes (export and analytics).
Blueprints are intentionally thin: validate → call service → return JSON.
"""
from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required

from .db import get_db_connection
from services import premium_service
from decorators import jwt_required_premium

premium_bp = Blueprint('premium', __name__)


@premium_bp.route('/api/export/suburbs', methods=['GET'])
@jwt_required_premium
def export_suburbs():
    state = request.args.get('state', '').strip()
    conn  = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        csv_content = premium_service.export_suburbs_csv(conn, state)
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=suburbs_{state or "all"}.csv'}
        )
    except Exception as e:
        return jsonify({'error': f'Export failed: {str(e)}'}), 500
    finally:
        conn.close()


@premium_bp.route('/api/premium/analytics', methods=['GET'])
@jwt_required_premium
def premium_analytics():
    suburb   = request.args.get('suburb',   '').strip()
    postcode = request.args.get('postcode', '').strip()
    if not suburb and not postcode:
        return jsonify({'error': 'suburb or postcode parameter required'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        return jsonify(premium_service.get_premium_analytics(conn, suburb, postcode))
    except Exception as e:
        return jsonify({'error': f'Analytics failed: {str(e)}'}), 500
    finally:
        conn.close()
