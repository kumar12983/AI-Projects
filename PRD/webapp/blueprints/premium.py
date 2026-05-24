"""
Premium feature API routes (export and analytics).
"""
from flask import Blueprint, request, jsonify, Response
from flask_login import login_required, current_user
from psycopg2.extras import RealDictCursor

from .db import get_db_connection

premium_bp = Blueprint('premium', __name__)


@premium_bp.route('/api/export/suburbs', methods=['GET'])
@login_required
def export_suburbs():
    """
    Export suburb data to CSV (Premium feature)
    Example: /api/export/suburbs?state=NSW
    """
    from io import StringIO
    import csv

    if not current_user.is_premium():
        return jsonify({
            'error': 'Premium subscription required',
            'message': 'Upgrade to Premium to export data',
            'upgrade_url': '/pricing'
        }), 403

    state = request.args.get('state', '').strip()

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT DISTINCT 
                locality_name as suburb,
                postcode,
                state_name as state
            FROM gnaf.suburb_postcode
        """

        params = []
        if state:
            query += " WHERE state_name = %s"
            params.append(state)

        query += " ORDER BY state_name, locality_name, postcode"

        cursor.execute(query, params)
        results = cursor.fetchall()
        cursor.close()
        conn.close()

        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=['suburb', 'postcode', 'state'])
        writer.writeheader()
        writer.writerows(results)

        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=suburbs_{state or "all"}.csv'}
        )

    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': f'Export failed: {str(e)}'}), 500


@premium_bp.route('/api/premium/analytics', methods=['GET'])
@login_required
def premium_analytics():
    """
    Advanced analytics endpoint (Premium feature)
    Example: /api/premium/analytics?suburb=Sydney&postcode=2000
    """
    if not current_user.is_premium():
        return jsonify({
            'error': 'Premium subscription required',
            'message': 'Upgrade to Premium for advanced analytics',
            'upgrade_url': '/pricing'
        }), 403

    suburb = request.args.get('suburb', '').strip()
    postcode = request.args.get('postcode', '').strip()

    if not suburb and not postcode:
        return jsonify({'error': 'suburb or postcode parameter required'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        analytics = {
            'suburb': suburb or 'Unknown',
            'postcode': postcode or 'Unknown',
            'total_addresses': 0,
            'total_streets': 0,
            'premium_feature': True
        }

        cursor.execute("""
            SELECT COUNT(DISTINCT locality_name) as suburb_count
            FROM gnaf.suburb_postcode
            WHERE (%s = '' OR UPPER(locality_name) = UPPER(%s))
            AND (%s = '' OR postcode = %s)
        """, (suburb, suburb, postcode, postcode))

        result = cursor.fetchone()
        analytics['matches'] = result['suburb_count'] if result else 0

        cursor.close()
        conn.close()

        return jsonify(analytics)

    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': f'Analytics failed: {str(e)}'}), 500
