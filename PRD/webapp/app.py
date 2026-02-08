"""
Flask Web Application for GNAF Database with Freemium Model
Provides API endpoints and web interface for searching suburbs and postcodes
"""
from flask import Flask, render_template, request, jsonify
from flask_login import LoginManager, login_required, current_user
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page'

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'gnaf_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
    'port': int(os.getenv('DB_PORT', '5432'))
}


def get_db_connection():
    """Create and return a database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None


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


# Register authentication blueprint
from auth import auth_bp
app.register_blueprint(auth_bp)

# Register payments blueprint
from payments import payments_bp
app.register_blueprint(payments_bp)

# Setup school profile search routes
from school_profile_search import setup_school_profile_routes
setup_school_profile_routes(app, DB_CONFIG)


# ============================================
# Web Pages
# ============================================

@app.route('/')
def index():
    """Main landing page"""
    return render_template('index.html')


@app.route('/search')
def search_page():
    """Search page"""
    return render_template('search.html')


@app.route('/school-search')
@login_required
def school_search_page():
    """School catchment search page"""
    return render_template('school_search.html')


@app.route('/australia-school-search')
@login_required
def australia_school_search_page():
    """Australia-wide school search page with 5km zones"""
    return render_template('australia_school_search.html')


@app.route('/address-lookup')
def address_lookup_page():
    """Address lookup page"""
    return render_template('address_lookup.html')


@app.route('/test-autocomplete')
def test_autocomplete():
    """Test page for autocomplete functionality"""
    return render_template('test_autocomplete.html')


@app.route('/school-rankings')
@login_required
def school_rankings_page():
    """School rankings and information page"""
    return render_template('school_rankings.html')


# ============================================
# API Endpoints
# ============================================

@app.route('/api/search/suburbs', methods=['GET'])
def search_suburbs_by_postcode():
    """
    Search suburbs by postcode
    Example: /api/search/suburbs?postcode=2000
    """
    postcode = request.args.get('postcode', '').strip()
    
    if not postcode:
        return jsonify({'error': 'Postcode parameter is required'}), 400
    
    if not postcode.isdigit() or len(postcode) != 4:
        return jsonify({'error': 'Invalid postcode format. Must be 4 digits'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Query suburb_postcode table by postcode
        cursor.execute("""
            SELECT DISTINCT 
                locality_name as suburb,
                postcode,
                state_name as state,
                0 as address_count
            FROM gnaf.suburb_postcode
            WHERE postcode = %s
            ORDER BY locality_name
        """, (postcode,))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            'postcode': postcode,
            'count': len(results),
            'suburbs': results
        })
        
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


@app.route('/api/search/postcodes', methods=['GET'])
def search_postcodes_by_suburb():
    """
    Search postcodes by suburb name
    Example: /api/search/postcodes?suburb=Sydney
    """
    suburb = request.args.get('suburb', '').strip()
    
    if not suburb:
        return jsonify({'error': 'Suburb parameter is required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Search for suburbs (case-insensitive, partial match)
        cursor.execute("""
            SELECT DISTINCT 
                locality_name as suburb,
                postcode,
                state_name as state,
                0 as address_count
            FROM gnaf.suburb_postcode
            WHERE UPPER(locality_name) LIKE UPPER(%s)
            ORDER BY locality_name, postcode
            LIMIT 50
        """, (f'%{suburb}%',))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            'search_term': suburb,
            'count': len(results),
            'results': results
        })
        
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


@app.route('/api/autocomplete/suburbs', methods=['GET'])
def autocomplete_suburbs():
    """
    Autocomplete suburb names
    Example: /api/autocomplete/suburbs?q=Syd
    """
    query = request.args.get('q', '').strip()
    
    if not query or len(query) < 2:
        return jsonify([])
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT DISTINCT 
                locality_name as suburb,
                postcode,
                state_name as state
            FROM gnaf.suburb_postcode
            WHERE UPPER(locality_name) LIKE UPPER(%s)
            ORDER BY locality_name
            LIMIT 20
        """, (f'{query}%',))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(results)
        
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


@app.route('/api/autocomplete/streets', methods=['GET'])
def autocomplete_streets():
    """
    Autocomplete street names
    Example: /api/autocomplete/streets?q=George
    """
    query = request.args.get('q', '').strip()
    
    if not query or len(query) < 2:
        return jsonify([])
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT DISTINCT 
                sl.street_name,
                st.name as street_type
            FROM gnaf.street_locality sl
            LEFT JOIN gnaf.street_type_aut st ON sl.street_type_code = st.code
            WHERE sl.date_retired IS NULL
            AND UPPER(sl.street_name) LIKE UPPER(%s)
            ORDER BY sl.street_name
            LIMIT 20
        """, (f'{query}%',))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(results)
        
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


@app.route('/api/school/<school_id>/autocomplete/streets', methods=['GET'])
@login_required
def autocomplete_school_streets(school_id):
    """
    Autocomplete street names filtered by school catchment area
    Example: /api/school/2060/autocomplete/streets?q=George
    """
    query = request.args.get('q', '').strip()
    
    if not query or len(query) < 2:
        return jsonify([])
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT DISTINCT 
                scs.street_name,
                st.name as street_type
            FROM public.school_catchment_streets scs
            LEFT JOIN gnaf.street_type_aut st ON scs.street_type_code = st.code
            WHERE scs.school_id = %s
            AND UPPER(scs.street_name) LIKE UPPER(%s)
            ORDER BY scs.street_name
            LIMIT 20
        """, (school_id, f'{query}%'))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(results)
        
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


@app.route('/api/school/<school_id>/autocomplete/suburbs', methods=['GET'])
@login_required
def autocomplete_school_suburbs(school_id):
    """
    Autocomplete suburb names filtered by school catchment area
    Example: /api/school/2060/autocomplete/suburbs?q=Syd
    """
    query = request.args.get('q', '').strip()
    
    if not query or len(query) < 2:
        return jsonify([])
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT DISTINCT 
                scs.locality_name as suburb,
                scs.postcode
            FROM public.school_catchment_streets scs
            WHERE scs.school_id = %s
            AND UPPER(scs.locality_name) LIKE UPPER(%s)
            ORDER BY scs.locality_name
            LIMIT 20
        """, (school_id, f'{query}%'))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(results)
        
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


@app.route('/api/school/<school_id>/autocomplete/postcodes', methods=['GET'])
@login_required
def autocomplete_school_postcodes(school_id):
    """
    Autocomplete postcodes filtered by school catchment area
    Example: /api/school/2060/autocomplete/postcodes?q=20
    """
    query = request.args.get('q', '').strip()
    
    if not query or len(query) < 1:
        return jsonify([])
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT DISTINCT 
                scs.postcode,
                scs.locality_name as suburb
            FROM public.school_catchment_streets scs
            WHERE scs.school_id = %s
            AND scs.postcode LIKE %s
            ORDER BY scs.postcode
            LIMIT 20
        """, (school_id, f'{query}%'))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(results)
        
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


@app.route('/api/address/search', methods=['GET'])
def search_address():
    """
    Search for addresses by street name or locality
    Example: /api/address/search?street=George&suburb=Sydney&street_number=283
    """
    street_number = request.args.get('street_number', '').strip()
    street = request.args.get('street', '').strip()
    suburb = request.args.get('suburb', '').strip()
    postcode = request.args.get('postcode', '').strip()
    state = request.args.get('state', '').strip()
    limit = int(request.args.get('limit', 50))
    
    if not street and not suburb and not postcode and not state:
        return jsonify({'error': 'At least one search parameter required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Build dynamic query with DISTINCT ON to eliminate duplicates
        query = """
            SELECT DISTINCT ON (ad.address_detail_pid)
                ad.address_detail_pid,
                ad.building_name,
                ad.number_first,
                ad.number_first_suffix,
                ad.number_last,
                ad.number_last_suffix,
                ad.flat_number,
                ad.confidence,
                ft.name as flat_type,
                CONCAT_WS(' ',
                    ft.name, ad.flat_number,
                    CONCAT(ad.number_first, COALESCE(ad.number_first_suffix, '')),
                    CASE WHEN ad.number_last IS NOT NULL THEN CONCAT('-', ad.number_last, COALESCE(ad.number_last_suffix, '')) END
                ) as street_number,
                sl.street_name,
                st.name as street_type,
                l.locality_name as suburb,
                s.state_abbreviation as state,
                ad.postcode,
                adg.latitude,
                adg.longitude,
                adg.geocode_type_code
            FROM gnaf.address_detail ad
            LEFT JOIN gnaf.flat_type_aut ft ON ad.flat_type_code = ft.code
            LEFT JOIN gnaf.street_locality sl ON ad.street_locality_pid = sl.street_locality_pid
            LEFT JOIN gnaf.street_type_aut st ON sl.street_type_code = st.code
            LEFT JOIN gnaf.locality l ON ad.locality_pid = l.locality_pid
            LEFT JOIN gnaf.state s ON l.state_pid = s.state_pid
            LEFT JOIN gnaf.address_default_geocode adg ON ad.address_detail_pid = adg.address_detail_pid
            WHERE ad.date_retired IS NULL
        """
        
        params = []
        
        if street_number:
            query += " AND CAST(ad.number_first AS TEXT) LIKE %s"
            params.append(f'%{street_number}%')
        
        if street:
            query += " AND UPPER(sl.street_name) LIKE UPPER(%s)"
            params.append(f'%{street}%')
        
        if suburb:
            query += " AND UPPER(l.locality_name) LIKE UPPER(%s)"
            params.append(f'%{suburb}%')
        
        if postcode:
            query += " AND ad.postcode = %s"
            params.append(postcode)
        
        if state:
            query += " AND s.state_abbreviation = %s"
            params.append(state)
        
        query += " ORDER BY ad.address_detail_pid, l.locality_name, sl.street_name, ad.number_first LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            'count': len(results),
            'addresses': results
        })
        
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


@app.route('/api/address/schools', methods=['GET'])
@login_required
def get_schools_for_address():
    """
    Get schools that contain a given address (lat/lng) in their catchment
    Example: /api/address/schools?lat=-33.8688&lng=151.2093
    """
    try:
        lat = float(request.args.get('lat', ''))
        lng = float(request.args.get('lng', ''))
    except (TypeError, ValueError):
        return jsonify({'error': 'Valid lat and lng parameters required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT DISTINCT
                school_id,
                school_name,
                school_type
            FROM gnaf.school_catchments
            WHERE ST_Contains(
                geometry,
                ST_SetSRID(ST_MakePoint(%s, %s), 4326)
            )
            ORDER BY school_type, school_name
        """
        
        cursor.execute(query, (lng, lat))
        schools = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            'count': len(schools),
            'schools': schools
        })
        
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


@app.route('/api/stats', methods=['GET'])
def get_statistics():
    """
    Get database statistics
    Example: /api/stats
    """
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get various statistics from materialized view
        stats = {}
        
        # Get pre-calculated statistics from materialized view
        cursor.execute("SELECT * FROM gnaf.stats_summary")
        summary = cursor.fetchone()
        
        if summary:
            stats['total_localities'] = summary['total_localities']
            stats['total_addresses'] = summary['total_addresses']
            stats['total_streets'] = summary['total_streets']
            stats['last_refreshed'] = summary['last_refreshed'].isoformat() if summary.get('last_refreshed') else None
        else:
            # Fallback if materialized view doesn't exist
            stats['total_localities'] = 0
            stats['total_addresses'] = 0
            stats['total_streets'] = 0
        
        # Get state breakdown from materialized view
        cursor.execute("SELECT * FROM gnaf.stats_by_state ORDER BY state_abbreviation")
        stats['localities_by_state'] = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify(stats)
        
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


@app.route('/api/suburbs/by-state', methods=['GET'])
def get_suburbs_by_state():
    """
    Get all suburbs and postcodes for a specific state
    Example: /api/suburbs/by-state?state=NEW SOUTH WALES
    """
    state = request.args.get('state', '').strip()
    
    if not state:
        return jsonify({'error': 'State parameter is required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT DISTINCT 
                locality_name as suburb,
                postcode,
                state_name as state
            FROM gnaf.suburb_postcode
            WHERE state_name = %s
            ORDER BY locality_name, postcode
        """, (state,))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            'state': state,
            'count': len(results),
            'suburbs': results
        })
        
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


# ============================================
# Error Handlers
# ============================================
# School Catchment API Endpoints
# ============================================

@app.route('/api/autocomplete/schools', methods=['GET'])
@login_required
def autocomplete_schools():
    """
    Autocomplete school names with smart ranking
    Prioritizes exact matches, then starts-with, then contains
    Example: /api/autocomplete/schools?q=Hornsby NPS&type=PRIMARY
    """
    query = request.args.get('q', '').strip()
    school_type = request.args.get('type', '').strip()  # PRIMARY, SECONDARY, FUTURE, or empty for all
    
    if not query or len(query) < 3:
        return jsonify([])
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Build type filter for WHERE clause
        type_filter = ""
        type_param = None
        if school_type and school_type.upper() != 'ALL':
            type_filter = "AND school_type = %s"
            type_param = school_type.upper()
        
        # First, try to find exact or near-exact matches
        exact_query = """
            SELECT 
                school_id,
                school_name,
                school_type,
                0 as rank_order
            FROM gnaf.school_catchments
            WHERE UPPER(school_name) = UPPER(%s) {type_filter}
        """.format(type_filter=type_filter)
        
        params = [query]
        if type_param:
            params.append(type_param)
        
        cursor.execute(exact_query, params)
        exact_results = cursor.fetchall()
        
        # If no exact match, try prefix match (starts with)
        if not exact_results:
            prefix_query = """
                SELECT 
                    school_id,
                    school_name,
                    school_type,
                    1 as rank_order
                FROM gnaf.school_catchments
                WHERE UPPER(school_name) LIKE UPPER(%s) || '%%' {type_filter}
                ORDER BY school_name
                LIMIT 20
            """.format(type_filter=type_filter)
            
            params = [query]
            if type_param:
                params.append(type_param)
            
            cursor.execute(prefix_query, params)
            exact_results = cursor.fetchall()
        
        # If still no results, try substring match
        if not exact_results:
            substring_query = """
                SELECT 
                    school_id,
                    school_name,
                    school_type,
                    2 as rank_order
                FROM gnaf.school_catchments
                WHERE UPPER(school_name) LIKE '%%' || UPPER(%s) || '%%' {type_filter}
                ORDER BY school_name
                LIMIT 20
            """.format(type_filter=type_filter)
            
            params = [query]
            if type_param:
                params.append(type_param)
            
            cursor.execute(substring_query, params)
            exact_results = cursor.fetchall()
        
        # Convert to list of dicts (remove rank_order)
        output_results = []
        for row in exact_results:
            output_results.append({
                'school_id': row['school_id'],
                'school_name': row['school_name'],
                'school_type': row['school_type']
            })
        
        cursor.close()
        conn.close()
        
        return jsonify(output_results)
        
    except Exception as e:
        if conn:
            conn.close()
        print(f"Error in autocomplete_schools: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


@app.route('/api/autocomplete/australia-schools', methods=['GET'])
@login_required
def autocomplete_australia_schools():
    """
    Autocomplete Australian school names using TSvector search
    Supports state filtering
    Example: /api/autocomplete/australia-schools?q=Hornsby&state=NSW
    """
    query = request.args.get('q', '').strip()
    state = request.args.get('state', '').strip()
    
    if not query or len(query) < 3:
        return jsonify([])
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Build state filter
        state_filter = ""
        params = [query]
        if state:
            state_filter = "AND state = %s"
            params.append(state)
        
        # Use TSvector search with optional state filter
        search_query = f"""
            SELECT 
                acara_sml_id,
                school_name,
                state,
                school_sector
            FROM gnaf.school_geometry
            WHERE search_vector @@ plainto_tsquery('english', %s)
            {state_filter}
            ORDER BY school_name
            LIMIT 20
        """
        
        cursor.execute(search_query, params)
        results = cursor.fetchall()
        
        # Convert to list of dicts
        output_results = []
        for row in results:
            output_results.append({
                'acara_sml_id': row['acara_sml_id'],
                'school_name': row['school_name'],
                'state': row['state'],
                'school_sector': row['school_sector']
            })
        
        cursor.close()
        conn.close()
        
        return jsonify(output_results)
        
    except Exception as e:
        if conn:
            conn.close()
        print(f"Error in autocomplete_australia_schools: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


@app.route('/api/australia-school/<string:acara_sml_id>/info', methods=['GET'])
@login_required
def get_australia_school_info(acara_sml_id):
    """
    Get detailed information about an Australian school including 5km buffer geometry
    Uses school_geometry table joined with school_profile_2025
    Example: /api/australia-school/12345/info
    """
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get school info from school_geometry joined with school_profile_2025
        cursor.execute("""
            SELECT 
                sg.acara_sml_id,
                sg.school_name,
                sg.state,
                sg.school_sector,
                sg.latitude,
                sg.longitude,
                sg.school_id,
                sg.has_catchment,
                ST_AsGeoJSON(sg.geom_5km_buffer) as geom_5km_buffer_json,
                pf.year_levels,
                pf.school_type,
                pf.school_url,
                pf.myschool_url as school_profile_url,
                pf.naplan_url,
                pf.icsea_score,
                pf.icsea_percentile
            FROM gnaf.school_geometry sg
            LEFT JOIN school_profile_2025 pf ON sg.acara_sml_id = pf.acara_sml_id
            WHERE sg.acara_sml_id = %s
            LIMIT 1
        """, (acara_sml_id,))
        
        school = cursor.fetchone()
        
        if not school:
            cursor.close()
            conn.close()
            return jsonify({'error': 'School not found'}), 404
        
        # Parse GeoJSON for 5km buffer
        geom_5km_buffer = None
        if school['geom_5km_buffer_json']:
            import json
            geom_5km_buffer = json.loads(school['geom_5km_buffer_json'])
        
        # Prepare response
        response_data = {
            'acara_sml_id': school['acara_sml_id'],
            'school_name': school['school_name'],
            'state': school['state'],
            'school_sector': school['school_sector'],
            'latitude': float(school['latitude']) if school['latitude'] else None,
            'longitude': float(school['longitude']) if school['longitude'] else None,
            'school_id': school['school_id'],
            'has_catchment': school['has_catchment'],
            'geom_5km_buffer': geom_5km_buffer,
            'year_levels': school['year_levels'],
            'school_type': school['school_type'],
            'school_type_full': school['school_type'],
            'school_url': school['school_url'],
            'school_profile_url': school['school_profile_url'],
            'naplan_url': school['naplan_url'],
            'icsea_score': school['icsea_score'],
            'icsea_percentile': school['icsea_percentile']
        }
        
        cursor.close()
        conn.close()
        
        return jsonify(response_data)
        
    except Exception as e:
        if conn:
            conn.close()
        print(f"Error in get_australia_school_info: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


@app.route('/api/school/<int:school_id>/info', methods=['GET'])
@login_required
def get_school_info(school_id):
    """
    Get detailed information about a school including ICSEA data from school_type_lookup
    ICSEA is only shown when school_id AND catchment_school_name match in lookup table
    Example: /api/school/2060/info
    """
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        print(f"[DEBUG] Fetching info for school_id={school_id}")
        
        # Get school info - prioritize school_type_lookup coordinates, fallback to catchments centroid
        cursor.execute("""
            SELECT DISTINCT
                s.school_id,
                s.school_name,
                s.school_type,
                COALESCE(pf.latitude, s.school_lat) as school_latitude,
                COALESCE(pf.longitude, s.school_lng) as school_longitude
            FROM gnaf.school_catchments s
            LEFT JOIN gnaf.school_type_lookup pf ON pf.school_id = s.school_id
            WHERE s.school_id::text = %s
            LIMIT 1
        """, (str(school_id),))
        
        catchment_info = cursor.fetchone()
        print(f"[DEBUG] catchment_info: {catchment_info}")
        
        if not catchment_info:
            cursor.close()
            conn.close()
            return jsonify({'error': 'School not found'}), 404
        
        # Now try to get ICSEA from lookup table with BOTH conditions:
        # 1. school_id must match
        # 2. catchment_school_name must match the catchment name
        print(f"[DEBUG] Querying lookup table with school_id={school_id}, school_name={catchment_info['school_name']}")
        cursor.execute("""
            SELECT 
                school_id,
                catchment_school_name,
                school_sector,
                school_type,
                icsea,
                icsea_percentile,
                school_url,
                acara_url,
                naplan_url,
                suburb,
                state,
                postcode
            FROM gnaf.school_type_lookup
            WHERE school_id::text = %s 
            AND catchment_school_name = %s
            LIMIT 1
        """, (str(school_id), catchment_info['school_name']))
        
        lookup_info = cursor.fetchone()
        print(f"[DEBUG] lookup_info: {lookup_info}")
        
        # Get year levels from original tables
        print(f"[DEBUG] Querying year levels for school_id={school_id}")
        cursor.execute("""
            SELECT 
                CAST("KINDERGART" AS TEXT) as kg,
                CAST("YEAR1" AS TEXT) as yr_01,
                CAST("YEAR2" AS TEXT) as yr_02,
                CAST("YEAR3" AS TEXT) as yr_03,
                CAST("YEAR4" AS TEXT) as yr_04,
                CAST("YEAR5" AS TEXT) as yr_05,
                CAST("YEAR6" AS TEXT) as yr_06,
                CAST("YEAR7" AS TEXT) as yr_07,
                CAST("YEAR8" AS TEXT) as yr_08,
                CAST("YEAR9" AS TEXT) as yr_09,
                CAST("YEAR10" AS TEXT) as yr_10,
                CAST("YEAR11" AS TEXT) as yr_11,
                CAST("YEAR12" AS TEXT) as yr_12
            FROM public.school_catchments_primary
            WHERE "USE_ID"::text = %s
            
            UNION ALL
            
            SELECT 
                CAST("KINDERGART" AS TEXT) as kg,
                CAST("YEAR1" AS TEXT) as yr_01,
                CAST("YEAR2" AS TEXT) as yr_02,
                CAST("YEAR3" AS TEXT) as yr_03,
                CAST("YEAR4" AS TEXT) as yr_04,
                CAST("YEAR5" AS TEXT) as yr_05,
                CAST("YEAR6" AS TEXT) as yr_06,
                CAST("YEAR7" AS TEXT) as yr_07,
                CAST("YEAR8" AS TEXT) as yr_08,
                CAST("YEAR9" AS TEXT) as yr_09,
                CAST("YEAR10" AS TEXT) as yr_10,
                CAST("YEAR11" AS TEXT) as yr_11,
                CAST("YEAR12" AS TEXT) as yr_12
            FROM public.school_catchments_secondary
            WHERE "USE_ID"::text = %s
            
            UNION ALL
            
            SELECT 
                CAST("KINDERGART" AS TEXT) as kg,
                CAST("YEAR1" AS TEXT) as yr_01,
                CAST("YEAR2" AS TEXT) as yr_02,
                CAST("YEAR3" AS TEXT) as yr_03,
                CAST("YEAR4" AS TEXT) as yr_04,
                CAST("YEAR5" AS TEXT) as yr_05,
                CAST("YEAR6" AS TEXT) as yr_06,
                CAST("YEAR7" AS TEXT) as yr_07,
                CAST("YEAR8" AS TEXT) as yr_08,
                CAST("YEAR9" AS TEXT) as yr_09,
                CAST("YEAR10" AS TEXT) as yr_10,
                CAST("YEAR11" AS TEXT) as yr_11,
                CAST("YEAR12" AS TEXT) as yr_12
            FROM public.school_catchments_future
            WHERE "USE_ID"::text = %s
            LIMIT 1
        """, (str(school_id), str(school_id), str(school_id)))
        
        year_data = cursor.fetchone()
        print(f"[DEBUG] year_data: {year_data}")
        
        # Get address count from gnaf.school_catchments
        cursor.execute("""
            SELECT COUNT(*) as address_count
            FROM gnaf.school_catchments
            WHERE school_id::text = %s
        """, (str(school_id),))
        
        stats = cursor.fetchone()
        print(f"[DEBUG] stats: {stats}")
        cursor.close()
        conn.close()
        
        # Build year levels string
        year_levels = []
        if year_data:
            if year_data.get('kg') == 'Y':
                year_levels.append('K')
            for i in range(1, 13):
                yr_key = f'yr_{i:02d}'
                if year_data.get(yr_key) == 'Y':
                    year_levels.append(str(i))
        
        print(f"[DEBUG] year_levels: {year_levels}")
        
        # Build result - ICSEA only if lookup matched BOTH school_id and catchment_school_name
        result = {
            'school_id': str(catchment_info['school_id']),
            'school_name': catchment_info['school_name'],
            'school_type': catchment_info['school_type'],
            'school_sector': lookup_info['school_sector'] if lookup_info else None,
            'school_type_name': lookup_info['school_type'] if lookup_info else None,
            'school_url': lookup_info['school_url'] if lookup_info else None,
            'acara_url': lookup_info['acara_url'] if lookup_info else None,
            'naplan_url': lookup_info['naplan_url'] if lookup_info else None,
            'priority': None,
            'year_levels': ', '.join(year_levels) if year_levels else 'N/A',
            'address_count': stats['address_count'] if stats else 0,
            'icsea': lookup_info['icsea'] if lookup_info else None,
            'icsea_percentile': lookup_info['icsea_percentile'] if lookup_info else None,
            'location': {
                'suburb': lookup_info['suburb'] if lookup_info else None,
                'state': lookup_info['state'] if lookup_info else None,
                'postcode': lookup_info['postcode'] if lookup_info else None
            } if lookup_info else None,
            'school_location': {
                'latitude': catchment_info.get('school_latitude'),
                'longitude': catchment_info.get('school_longitude'),
                'suburb': lookup_info['suburb'] if lookup_info else None,
                'state': lookup_info['state'] if lookup_info else None,
                'postcode': lookup_info['postcode'] if lookup_info else None
            } if (catchment_info.get('school_latitude') and catchment_info.get('school_longitude')) else None
        }
        
        print(f"[DEBUG] Returning result: {result}")
        return jsonify(result)
        
    except Exception as e:
        if conn:
            conn.close()
        print(f"[ERROR] Error in get_school_info for school_id={school_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


@app.route('/api/school/<school_id>/addresses', methods=['GET'])
@login_required
def get_school_addresses(school_id):
    """
    Get addresses within a school catchment with optional search filters
    Example: /api/school/2060/addresses?limit=500&offset=0&street=Burdett&suburb=Hornsby
    """
    limit = request.args.get('limit', '500')
    offset = request.args.get('offset', '0')
    
    # Get optional search filters
    street_number = request.args.get('street_number', '').strip()
    street = request.args.get('street', '').strip()
    suburb = request.args.get('suburb', '').strip()
    postcode = request.args.get('postcode', '').strip()
    state = request.args.get('state', '').strip()
    
    try:
        limit = int(limit)
        offset = int(offset)
    except:
        limit = 500
        offset = 0
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get school location - prioritize school_type_lookup coordinates, fallback to catchments table
        cursor.execute("""
            SELECT 
                COALESCE(pf.latitude, s.school_lat) as school_lat,
                COALESCE(pf.longitude, s.school_lng) as school_lng
            FROM gnaf.school_catchments s
            LEFT JOIN gnaf.school_type_lookup pf ON pf.school_id = s.school_id
            WHERE s.school_id = %s
            LIMIT 1
        """, (school_id,))
        
        school_location = cursor.fetchone()
        if not school_location:
            cursor.close()
            conn.close()
            return jsonify({'error': 'School not found'}), 404
        
        school_lat = school_location['school_lat']
        school_lng = school_location['school_lng']
        
        print(f"[DEBUG] School location for school_id={school_id}:")
        print(f"  school_lat: {school_lat}")
        print(f"  school_lng: {school_lng}")
        
        # Build WHERE clause for optional filters
        filter_conditions = []
        filter_params = []
        
        if street_number:
            filter_conditions.append("ad.number_first::text ILIKE %s")
            filter_params.append(f'%{street_number}%')
        
        if street:
            filter_conditions.append("sl.street_name ILIKE %s")
            filter_params.append(f'%{street}%')
        
        if suburb:
            filter_conditions.append("l.locality_name ILIKE %s")
            filter_params.append(f'%{suburb}%')
        
        if postcode:
            filter_conditions.append("ad.postcode = %s")
            filter_params.append(postcode)
        
        if state:
            filter_conditions.append("s.state_abbreviation ILIKE %s")
            filter_params.append(state)
        
        additional_where = ""
        if filter_conditions:
            additional_where = "AND " + " AND ".join(filter_conditions)
        
        # Get addresses in catchment with DISTINCT ON to eliminate duplicates
        query = f"""
            WITH school_catchment AS (
                SELECT geometry FROM gnaf.school_catchments WHERE school_id = %s
            ),
            school_point AS (
                SELECT ST_SetSRID(ST_MakePoint(%s, %s), 4326) as geom
            )
            SELECT DISTINCT ON (ad.address_detail_pid)
                ad.address_detail_pid as gnaf_id,
                COALESCE(ad.lot_number_prefix || ' ', '') ||
                COALESCE(ad.lot_number || ' ', '') ||
                COALESCE(ad.lot_number_suffix || ' ', '') ||
                COALESCE(ft.name || ' ', '') ||
                COALESCE(ad.flat_number_prefix || '', '') ||
                COALESCE(ad.flat_number::text || '', '') ||
                COALESCE(ad.flat_number_suffix || ' ', '') ||
                COALESCE(ad.level_type_code || ' ', '') ||
                COALESCE(ad.level_number_prefix || '', '') ||
                COALESCE(ad.level_number::text || '', '') ||
                COALESCE(ad.level_number_suffix || ' ', '') ||
                COALESCE(ad.number_first_prefix || '', '') ||
                COALESCE(ad.number_first::text || '', '') ||
                COALESCE(ad.number_first_suffix || '', '') ||
                COALESCE('-' || ad.number_last_prefix || '', '') ||
                COALESCE(ad.number_last::text || '', '') ||
                COALESCE(ad.number_last_suffix || ' ', '') ||
                COALESCE(sl.street_name || ' ', '') ||
                COALESCE(st.name || ' ', '') as full_address,
                ad.number_first,
                ad.number_first_suffix,
                ad.number_last,
                ad.number_last_suffix,
                COALESCE(ad.flat_number::text, '') as flat_number,
                sl.street_name,
                st.name as street_type,
                l.locality_name as suburb,
                ad.postcode,
                s.state_abbreviation as state,
                agc.latitude,
                agc.longitude,
                agc.geocode_type_code,
                ad.confidence,
                ROUND(CAST(ST_Distance(
                    ST_SetSRID(ST_MakePoint(agc.longitude, agc.latitude), 4326)::geography,
                    sp.geom::geography
                ) / 1000.0 AS numeric), 2) as distance_km
            FROM gnaf.address_detail ad
            JOIN gnaf.address_default_geocode agc ON ad.address_detail_pid = agc.address_detail_pid
            JOIN gnaf.street_locality sl ON ad.street_locality_pid = sl.street_locality_pid
            JOIN gnaf.locality l ON sl.locality_pid = l.locality_pid
            JOIN gnaf.state s ON l.state_pid = s.state_pid
            LEFT JOIN gnaf.street_type_aut st ON sl.street_type_code = st.code
            LEFT JOIN gnaf.flat_type_aut ft ON ad.flat_type_code = ft.code
            CROSS JOIN school_catchment sc
            CROSS JOIN school_point sp
            WHERE ad.date_retired IS NULL
            AND agc.date_retired IS NULL
            AND sl.date_retired IS NULL
            AND l.date_retired IS NULL
            AND ST_Contains(sc.geometry, ST_SetSRID(ST_MakePoint(agc.longitude, agc.latitude), 4326))
            {additional_where}
            ORDER BY ad.address_detail_pid, l.locality_name, sl.street_name, ad.number_first
            LIMIT %s OFFSET %s
        """
        
        # Build parameter list
        query_params = [school_id, school_lng, school_lat] + filter_params + [limit, offset]
        
        cursor.execute(query, query_params)
        
        addresses = cursor.fetchall()
        
        # Get total count with same filters
        count_query = f"""
            WITH school_catchment AS (
                SELECT geometry FROM gnaf.school_catchments WHERE school_id = %s
            )
            SELECT COUNT(DISTINCT ad.address_detail_pid) as total
            FROM gnaf.address_detail ad
            JOIN gnaf.address_default_geocode agc ON ad.address_detail_pid = agc.address_detail_pid
            JOIN gnaf.street_locality sl ON ad.street_locality_pid = sl.street_locality_pid
            JOIN gnaf.locality l ON sl.locality_pid = l.locality_pid
            JOIN gnaf.state s ON l.state_pid = s.state_pid
            LEFT JOIN gnaf.street_type_aut st ON sl.street_type_code = st.code
            CROSS JOIN school_catchment sc
            WHERE ad.date_retired IS NULL
            AND agc.date_retired IS NULL
            AND ST_Contains(sc.geometry, ST_SetSRID(ST_MakePoint(agc.longitude, agc.latitude), 4326))
            {additional_where}
        """
        
        count_params = [school_id] + filter_params
        cursor.execute(count_query, count_params)
        total_count = cursor.fetchone()['total']
        
        cursor.close()
        conn.close()
        
        # Debug: Print first address to console
        if addresses:
            first_addr = dict(addresses[0])
            print(f"\n[DEBUG] First address object:")
            print(f"  gnaf_id: {first_addr.get('gnaf_id')}")
            print(f"  latitude: {first_addr.get('latitude')}")
            print(f"  longitude: {first_addr.get('longitude')}")
            print(f"  distance_km: {first_addr.get('distance_km')}")
            print(f"  Full address: {first_addr.get('full_address')}\n")
        
        response = {
            'addresses': addresses,
            'total_count': total_count,
            'showing_count': len(addresses),
            'offset': offset,
            'limit': limit,
            'has_more': (offset + len(addresses)) < total_count,
            'school_location': {
                'latitude': school_lat,
                'longitude': school_lng
            }
        }
        
        print(f"[DEBUG] Returning {len(addresses)} addresses with school_id={school_id}")
        return jsonify(response)
        
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


@app.route('/api/school/<school_id>/boundary', methods=['GET'])
@login_required
def get_school_boundary(school_id):
    """
    Get school catchment boundary as GeoJSON
    Example: /api/school/2060/boundary
    """
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get boundary as GeoJSON
        cursor.execute("""
            SELECT 
                ST_AsGeoJSON(geometry) as geojson,
                school_name,
                school_type
            FROM gnaf.school_catchments
            WHERE school_id = %s
            LIMIT 1
        """, (school_id,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not result:
            return jsonify({'error': 'School boundary not found'}), 404
        
        import json
        return jsonify({
            'geojson': json.loads(result['geojson']),
            'school_name': result['school_name'],
            'school_type': result['school_type']
        })
        
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


# ============================================
# Premium Features (Require Login)
# ============================================

@app.route('/api/export/suburbs', methods=['GET'])
@login_required
def export_suburbs():
    """
    Export suburb data to CSV (Premium feature)
    Example: /api/export/suburbs?state=NSW
    """
    from io import StringIO
    import csv
    
    # Check if user is premium
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
        
        # Create CSV
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=['suburb', 'postcode', 'state'])
        writer.writeheader()
        writer.writerows(results)
        
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=suburbs_{state or "all"}.csv'}
        )
        
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': f'Export failed: {str(e)}'}), 500


@app.route('/api/premium/analytics', methods=['GET'])
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
        
        # Get detailed analytics
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


# ============================================
# Error Handlers
# ============================================
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
