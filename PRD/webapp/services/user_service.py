"""
User service — registration, authentication, and password-reset logic.
All functions accept a live psycopg2 connection.
"""
from models import User


def register_user(conn, email: str, password: str, full_name: str) -> int | None:
    """Create a new user. Returns user_id on success, None on failure."""
    existing = User.get_by_email(conn, email)
    if existing:
        return None  # caller should return 400

    return User.create_user(conn, email, password, full_name)


def authenticate_user(conn, email: str, password: str) -> User | None:
    """Verify credentials. Returns a User instance on success, None otherwise."""
    user_data = User.get_by_email(conn, email)
    if not user_data or not User.verify_password(user_data['password_hash'], password):
        return None

    # Update last_login
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE webapp.users SET last_login = CURRENT_TIMESTAMP WHERE user_id = %s",
        (user_data['user_id'],),
    )
    conn.commit()
    cursor.close()

    return User(
        user_data['user_id'],
        user_data['email'],
        user_data['full_name'],
        user_data['tier_id'],
        user_data['tier_name'],
        user_data['searches_per_month'],
        user_data['can_export_data'],
        user_data['can_access_analytics'],
        user_data['can_access_school_catchments'],
        user_data['subscription_status'],
    )


def get_user_by_id(conn, user_id: int) -> User | None:
    return User.get_by_id(conn, user_id)


def request_password_reset(conn, email: str, mail_instance, reset_url_builder) -> bool:
    """
    Generate a reset token and e-mail the link.
    *reset_url_builder* is a callable that accepts the raw token and returns a URL string.
    Returns True if a token was generated (account exists), False otherwise.
    """
    raw_token = User.set_reset_token(conn, email)
    if not raw_token:
        return False

    reset_url = reset_url_builder(raw_token)
    try:
        from flask_mail import Message
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
        mail_instance.send(msg)
    except Exception as exc:
        print(f"[user_service.request_password_reset] email send error: {exc}")

    return True


def complete_password_reset(conn, token: str, new_password: str) -> bool:
    """
    Validate the token and update the password.
    Returns True on success, False if the token is invalid/expired.
    """
    user = User.get_by_reset_token(conn, token)
    if not user:
        return False
    User.update_password(conn, user['user_id'], new_password)
    return True
