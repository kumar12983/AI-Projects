"""
JWT-based decorators for API access control.
HTML routes (auth.py) still use Flask-Login / session-based decorators.
"""
from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity


def get_db_connection():
    from app import get_db_connection as _get_db
    return _get_db()


def jwt_required_premium(f):
    """Require a valid JWT AND a Premium subscription."""
    @wraps(f)
    def decorated(*args, **kwargs):
        verify_jwt_in_request()
        from services import user_service
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        try:
            user_id = get_jwt_identity()
            user = user_service.get_user_by_id(conn, user_id)
        finally:
            conn.close()

        if user is None:
            return jsonify({'error': 'User not found'}), 401
        if not user.is_premium():
            return jsonify({
                'error': 'Premium subscription required',
                'message': 'Upgrade to Premium for unlimited access',
                'upgrade_url': '/pricing',
            }), 403
        return f(*args, **kwargs)
    return decorated


def jwt_track_usage(search_type):
    """Require a valid JWT, enforce rate limit, and track usage."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            verify_jwt_in_request()
            from services import user_service
            conn = get_db_connection()
            if not conn:
                return jsonify({'error': 'Database connection failed'}), 500

            try:
                user_id = get_jwt_identity()
                user = user_service.get_user_by_id(conn, user_id)
                if user is None:
                    return jsonify({'error': 'User not found'}), 401

                if not user.has_searches_remaining(conn):
                    return jsonify({
                        'error': 'Monthly search limit reached',
                        'message': f'You have used all {user.searches_per_month} searches this month.',
                        'upgrade_url': '/pricing',
                        'searches_limit': user.searches_per_month,
                    }), 429

                response = f(*args, **kwargs)

                search_query = (
                    request.args.get('q')
                    or request.args.get('suburb')
                    or request.args.get('postcode', '')
                )
                status_code = response[1] if isinstance(response, tuple) else 200
                user.track_usage(
                    conn,
                    request.endpoint,
                    search_type,
                    search_query,
                    status_code,
                    request.remote_addr,
                )
                return response
            finally:
                conn.close()

        return decorated
    return decorator
