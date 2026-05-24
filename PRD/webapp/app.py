"""
Flask Web Application for GNAF Database with Freemium Model
Provides API endpoints and web interface for searching suburbs and postcodes
"""
import os

from flask import Flask, jsonify
from flask_login import LoginManager
from flask_mail import Mail
from dotenv import load_dotenv

from blueprints.db import get_db_connection
from blueprints.pages import pages_bp
from blueprints.search import search_bp
from blueprints.schools import schools_bp
from blueprints.australia_schools import aus_schools_bp
from blueprints.hazards import hazards_bp
from blueprints.premium import premium_bp

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Flask-Mail configuration (set these in your .env file)
app.config['MAIL_SERVER']         = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT']           = int(os.getenv('MAIL_PORT', '587'))
app.config['MAIL_USE_TLS']        = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
app.config['MAIL_USERNAME']       = os.getenv('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD']       = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', os.getenv('MAIL_USERNAME', ''))
mail = Mail(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page'


@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    from models import User
    conn = get_db_connection()
    if not conn:
        return None
    user = User.get_by_id(conn, int(user_id))
    conn.close()
    return user


# Register blueprints
app.register_blueprint(pages_bp)
app.register_blueprint(search_bp)
app.register_blueprint(schools_bp)
app.register_blueprint(aus_schools_bp)
app.register_blueprint(hazards_bp)
app.register_blueprint(premium_bp)

from auth import auth_bp
app.register_blueprint(auth_bp)

from payments import payments_bp
app.register_blueprint(payments_bp)




# ============================================
# Error Handlers
# ============================================
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


# ============================================
# Run Application
# ============================================
if __name__ == '__main__':
    # Development server
    app.run(debug=True, host='0.0.0.0', port=5000)
