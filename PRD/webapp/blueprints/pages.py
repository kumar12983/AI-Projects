"""
Page (template-rendering) routes.
"""
from flask import Blueprint, render_template
from flask_login import login_required

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/')
def index():
    return render_template('index.html')


@pages_bp.route('/search')
def search_page():
    return render_template('search.html')


@pages_bp.route('/school-search')
@login_required
def school_search_page():
    return render_template('school_search.html')


@pages_bp.route('/australia-school-search')
@login_required
def australia_school_search_page():
    return render_template('australia_school_search.html')


@pages_bp.route('/address-lookup')
def address_lookup_page():
    return render_template('address_lookup.html')


@pages_bp.route('/test-autocomplete')
def test_autocomplete():
    return render_template('test_autocomplete.html')


@pages_bp.route('/school-rankings')
@login_required
def school_rankings_page():
    return render_template('school_rankings.html')
