"""
JWT authentication endpoints.
These are the API-facing login / refresh / logout routes.
HTML login/register flows remain in auth.py (session-based).
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
)

api_auth_bp = Blueprint('api_auth', __name__, url_prefix='/api/auth')


def get_db_connection():
    from app import get_db_connection as _get_db
    return _get_db()


@api_auth_bp.route('/login', methods=['POST'])
def api_login():
    """
    Authenticate with email/password, return JWT access + refresh tokens.

    Body (JSON):
        email    str
        password str

    Returns:
        200  { access_token, refresh_token }
        400  missing fields
        401  invalid credentials
    """
    data = request.get_json(silent=True) or {}
    email    = (data.get('email')    or '').strip().lower()
    password = data.get('password')  or ''

    if not email or not password:
        return jsonify({'error': 'email and password are required'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        from services import user_service
        user = user_service.authenticate_user(conn, email, password)
    finally:
        conn.close()

    if user is None:
        return jsonify({'error': 'Invalid email or password'}), 401

    # flask-jwt-extended 4.7+ requires identity to be a string.
    access_token  = create_access_token(identity=str(user.user_id))
    refresh_token = create_refresh_token(identity=str(user.user_id))

    return jsonify({'access_token': access_token, 'refresh_token': refresh_token}), 200


@api_auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def api_refresh():
    """
    Issue a new access token using a valid refresh token.

    Header:
        Authorization: Bearer <refresh_token>

    Returns:
        200  { access_token }
    """
    user_id = get_jwt_identity()
    access_token = create_access_token(identity=user_id)
    return jsonify({'access_token': access_token}), 200


@api_auth_bp.route('/logout', methods=['DELETE'])
@jwt_required()
def api_logout():
    """
    Stateless logout — client should discard tokens.

    Returns:
        200  { message }
    """
    return jsonify({'message': 'Logged out. Discard your tokens.'}), 200
