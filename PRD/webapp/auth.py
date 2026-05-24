"""
Authentication routes and decorators for freemium access control
"""
from functools import wraps
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from models import User
from services import user_service

auth_bp = Blueprint('auth', __name__)


def get_db_connection():
    """Import from app.py - will be set during initialization"""
    from app import get_db_connection as _get_db
    return _get_db()


def premium_required(f):
    """Decorator to require premium subscription"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_premium():
            return jsonify({
                'error': 'Premium subscription required',
                'message': 'Upgrade to Premium for unlimited access',
                'upgrade_url': '/pricing'
            }), 403
        return f(*args, **kwargs)
    return decorated_function


def track_api_usage(search_type):
    """Decorator to track API usage and enforce rate limits"""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            conn = get_db_connection()
            if not conn:
                return jsonify({'error': 'Database connection failed'}), 500
            
            # Check if user has searches remaining
            if not current_user.has_searches_remaining(conn):
                remaining = current_user.searches_per_month - current_user.get_monthly_usage(conn)
                conn.close()
                return jsonify({
                    'error': 'Monthly search limit reached',
                    'message': f'You have used all {current_user.searches_per_month} searches this month.',
                    'upgrade_url': '/pricing',
                    'searches_used': current_user.get_monthly_usage(conn),
                    'searches_limit': current_user.searches_per_month
                }), 429
            
            # Execute the actual endpoint
            response = f(*args, **kwargs)
            
            # Track usage
            search_query = request.args.get('q') or request.args.get('suburb') or request.args.get('postcode', '')
            status_code = response[1] if isinstance(response, tuple) else 200
            
            current_user.track_usage(
                conn, 
                request.endpoint, 
                search_type,
                search_query,
                status_code,
                request.remote_addr
            )
            
            conn.close()
            return response
        
        return decorated_function
    return decorator


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page"""
    if request.method == 'GET':
        return render_template('auth.html')
    
    # POST request
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    full_name = request.form.get('full_name', '').strip()
    
    if not email or not password or not full_name:
        return jsonify({'error': 'All fields are required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        user_id = user_service.register_user(conn, email, password, full_name)
    except Exception as e:
        conn.close()
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500
    finally:
        conn.close()

    if user_id is None:
        return jsonify({'error': 'Email already registered'}), 400

    return jsonify({
        'success': True,
        'message': 'Account created successfully! Please log in.',
        'redirect': '/login'
    })


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if request.method == 'GET':
        return render_template('auth.html')
    
    # POST request
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        user = user_service.authenticate_user(conn, email, password)
    except Exception as e:
        conn.close()
        return jsonify({'error': f'Login failed: {str(e)}'}), 500
    finally:
        conn.close()

    if not user:
        return jsonify({'error': 'Invalid email or password'}), 401

    login_user(user, remember=True)
    return jsonify({
        'success': True,
        'message': 'Logged in successfully',
        'redirect': '/dashboard'
    })


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout current user"""
    logout_user()
    flash('Logged out successfully', 'success')
    return redirect(url_for('pages.index'))


@auth_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard showing usage and subscription info"""
    conn = get_db_connection()
    if not conn:
        flash('Database connection error', 'error')
        return redirect(url_for('pages.index'))
    
    usage_count = current_user.get_monthly_usage(conn)
    conn.close()
    
    return render_template('dashboard.html', 
                         user=current_user,
                         usage_count=usage_count)


@auth_bp.route('/pricing')
def pricing():
    """Pricing page showing Free vs Premium tiers"""
    return render_template('pricing.html')


# ---------------------------------------------------------------------------
# Password reset flow
# ---------------------------------------------------------------------------

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Request a password-reset link via email."""
    email = request.form.get('email', '').strip().lower()
    if not email:
        return jsonify({'error': 'Email address is required'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    def _build_reset_url(token):
        return url_for('auth.reset_password', token=token, _external=True)

    from app import mail as _mail
    user_service.request_password_reset(conn, email, _mail, _build_reset_url)
    conn.close()

    return jsonify({
        'success': True,
        'message': 'If that email is registered you will receive a reset link shortly. '
                   'Please also check your spam folder.',
    })


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Render or process the reset-password form."""
    if request.method == 'GET':
        conn = get_db_connection()
        if not conn:
            return render_template(
                'reset_password.html',
                error='Database connection failed. Please try again later.',
                token=None,
            )
        user = User.get_by_reset_token(conn, token)
        conn.close()
        if not user:
            return render_template(
                'reset_password.html',
                error='This password-reset link is invalid or has expired. '
                      'Please request a new one.',
                token=None,
            )
        return render_template('reset_password.html', token=token, error=None)

    # POST – apply the new password
    password         = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not password or len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    if password != confirm_password:
        return jsonify({'error': 'Passwords do not match'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    user = User.get_by_reset_token(conn, token)
    if not user:
        conn.close()
        return jsonify({
            'error': 'This reset link is invalid or has expired. '
                     'Please request a new one.'
        }), 400

    User.update_password(conn, user['user_id'], password)
    conn.close()

    return jsonify({
        'success': True,
        'message': 'Password reset successfully. You can now log in with your new password.',
        'redirect': '/login',
    })
