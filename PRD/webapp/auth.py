"""
Authentication routes and decorators for freemium access control
"""
from functools import wraps
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from models import User
import psycopg2

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

    # Ensure required tables exist before attempting registration
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'webapp'
              AND table_name IN ('users', 'subscription_tiers')
        """)
        existing_tables = {row[0] for row in cursor.fetchall()}
        cursor.close()

        missing_tables = {'users', 'subscription_tiers'} - existing_tables
        if missing_tables:
            conn.close()
            return jsonify({
                'error': 'Database not initialized',
                'message': 'Missing required tables. Run database_migrations/001_create_users_subscriptions.sql',
                'missing_tables': sorted(list(missing_tables))
            }), 500
    except Exception as e:
        conn.close()
        return jsonify({
            'error': 'Database check failed',
            'message': 'Unable to verify database schema. Please check database connectivity.'
        }), 500
    
    # Check if user already exists
    existing = User.get_by_email(conn, email)
    if existing:
        conn.close()
        return jsonify({'error': 'Email already registered'}), 400
    
    # Create new user
    user_id = User.create_user(conn, email, password, full_name)
    conn.close()
    
    if user_id:
        return jsonify({
            'success': True,
            'message': 'Account created successfully! Please log in.',
            'redirect': '/login'
        })
    else:
        return jsonify({'error': 'Registration failed'}), 500


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
    
    user_data = User.get_by_email(conn, email)
    
    if not user_data or not User.verify_password(user_data['password_hash'], password):
        conn.close()
        return jsonify({'error': 'Invalid email or password'}), 401
    
    # Create User object and log in
    user = User(
        user_data['user_id'],
        user_data['email'],
        user_data['full_name'],
        user_data['tier_id'],
        user_data['tier_name'],
        user_data['searches_per_month'],
        user_data['can_export_data'],
        user_data['can_access_analytics'],
        user_data['can_access_school_catchments'],
        user_data['subscription_status']
    )
    
    # Update last login
    cursor = conn.cursor()
    cursor.execute("UPDATE webapp.users SET last_login = CURRENT_TIMESTAMP WHERE user_id = %s", (user.user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
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
    return redirect(url_for('index'))


@auth_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard showing usage and subscription info"""
    conn = get_db_connection()
    if not conn:
        flash('Database connection error', 'error')
        return redirect(url_for('index'))
    
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

    raw_token = User.set_reset_token(conn, email)
    conn.close()

    # Always return the same success message to prevent email enumeration
    if raw_token:
        reset_url = url_for('auth.reset_password', token=raw_token, _external=True)
        try:
            from app import mail
            msg = Message(
                subject='Reset Your Password – Property Research Database',
                recipients=[email],
                html=f'''
<p>Hi,</p>
<p>We received a request to reset the password for your account.</p>
<p><a href="{reset_url}" style="background:#1e3a8a;color:#fff;padding:10px 20px;
   border-radius:5px;text-decoration:none;font-weight:600;">Reset Password</a></p>
<p>Or copy this link into your browser:<br>
   <a href="{reset_url}">{reset_url}</a></p>
<p>This link expires in <strong>1 hour</strong>. If you did not request this,
   you can safely ignore this email — your password will not be changed.</p>
<p>— Property Research Database</p>
''',
            )
            mail.send(msg)
        except Exception as exc:
            # Log but don't expose internal errors to the client
            print(f"[forgot_password] email send error: {exc}")

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
