"""
Australia-wide school (5 km radius) API routes.
"""
import json
import traceback

from flask import Blueprint, request, jsonify
from flask_login import login_required
from psycopg2.extras import RealDictCursor

from .db import get_db_connection, is_coordinate_like
from .validators import AusSchoolAutocompleteQuery, validate_query_params

aus_schools_bp = Blueprint('aus_schools', __name__)


@aus_schools_bp.route('/api/autocomplete/australia-schools', methods=['GET'])
@login_required
def autocomplete_australia_schools():
    """
    Autocomplete Australian school names using TSvector search
    Supports state filtering
    Example: /api/autocomplete/australia-schools?q=Hornsby&state=NSW
    """
    validated, err = validate_query_params(AusSchoolAutocompleteQuery, request.args)
    if err:
        return err
    query = validated.q
    state = validated.state or ''

    if not query or len(query) < 3:
        return jsonify([])

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        state_filter = ""
        params = [query, query, query, query]
        if state:
            state_filter = "AND state = %s"
            params.append(state)

        search_query = f"""
            SELECT 
                acara_sml_id,
                school_name,
                state,
                school_sector,
                CASE 
                    WHEN UPPER(school_name) LIKE UPPER(%s) || '%%' THEN 1
                    WHEN search_vector @@ plainto_tsquery('english', %s) THEN 2
                    ELSE 3
                END as rank
            FROM gnaf.school_geometry
            WHERE (UPPER(school_name) LIKE '%%' || UPPER(%s) || '%%'
                   OR search_vector @@ plainto_tsquery('english', %s))
            {state_filter}
            ORDER BY rank, school_name
            LIMIT 20
        """

        cursor.execute(search_query, params)
        results = cursor.fetchall()

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
        traceback.print_exc()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


@aus_schools_bp.route('/api/australia-school/<string:acara_sml_id>/info', methods=['GET'])
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

        cursor.execute("""
            SELECT 
                sg.acara_sml_id,
                sg.school_name,
                sg.state,
                sg.school_sector,
                pf.latitude,
                pf.longitude,
                sg.school_id,
                sg.has_catchment,
                ST_AsGeoJSON(ST_Transform(sg.geom_5km_buffer, 4326)) as geom_5km_buffer_json,
                pf.year_range,
                pf.school_type,
                pf.school_url,
                lk.acara_url as school_profile_url,
                lk.naplan_url,
                pf.icsea,
                pf.icsea_percentile
            FROM gnaf.school_geometry sg
            LEFT JOIN gnaf.school_profile_2025 pf ON sg.acara_sml_id = pf.acara_sml_id
            LEFT JOIN gnaf.school_type_lookup lk ON sg.acara_sml_id = lk.acara_sml_id
            WHERE sg.acara_sml_id = %s
            LIMIT 1
        """, (acara_sml_id,))

        school = cursor.fetchone()

        if not school:
            cursor.close()
            conn.close()
            return jsonify({'error': 'School not found'}), 404

        vic_catchment_id = None
        if school['has_catchment'] != 'Y' and school['state'] == 'VIC':
            cursor.execute("""
                SELECT school_id
                FROM gnaf.school_catchments
                WHERE state = 'VIC'
                  AND LOWER(TRIM(school_name)) = LOWER(TRIM(%s))
                LIMIT 1
            """, (school['school_name'],))
            vic_row = cursor.fetchone()
            if vic_row:
                vic_catchment_id = vic_row['school_id']

        geom_5km_buffer = None
        if school['geom_5km_buffer_json']:
            geometry = json.loads(school['geom_5km_buffer_json'])
            geom_5km_buffer = {
                "type": "Feature",
                "geometry": geometry,
                "properties": {}
            }
            print(f"Geometry type: {geometry.get('type', 'unknown')}")
            print(f"Geometry has coordinates: {bool(geometry.get('coordinates'))}")
        else:
            print(f"No geom_5km_buffer_json for school {school['acara_sml_id']}")

        acara_url = school['school_profile_url'] or (
            f"https://myschool.edu.au/school/{school['acara_sml_id']}" if school['acara_sml_id'] else None
        )
        naplan_url = school['naplan_url'] or (
            f"https://myschool.edu.au/school/{school['acara_sml_id']}/naplan/results" if school['acara_sml_id'] else None
        )

        effective_school_id = vic_catchment_id if vic_catchment_id else school['school_id']
        effective_has_catchment = 'Y' if (school['has_catchment'] == 'Y' or vic_catchment_id) else school['has_catchment']

        response_data = {
            'acara_sml_id': school['acara_sml_id'],
            'school_name': school['school_name'],
            'state': school['state'],
            'school_sector': school['school_sector'],
            'latitude': float(school['latitude']) if school['latitude'] else None,
            'longitude': float(school['longitude']) if school['longitude'] else None,
            'school_id': effective_school_id,
            'has_catchment': effective_has_catchment,
            'geom_5km_buffer': geom_5km_buffer,
            'year_levels': school['year_range'],
            'school_type': school['school_type'],
            'school_type_full': school['school_type'],
            'school_url': school['school_url'],
            'school_profile_url': acara_url,
            'naplan_url': naplan_url,
            'icsea_score': school['icsea'],
            'icsea_percentile': school['icsea_percentile']
        }

        cursor.close()
        conn.close()

        return jsonify(response_data)

    except Exception as e:
        if conn:
            conn.close()
        print(f"Error in get_australia_school_info: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


@aus_schools_bp.route('/api/australia-school/<int:acara_sml_id>/addresses', methods=['GET'])
@login_required
def get_australia_school_addresses(acara_sml_id):
    """
    Get addresses within 5km of a school with optional search filters
    OPTIMIZED: Uses spatial indexes and efficient geometry queries for fast response
    Example: /api/australia-school/41319/addresses?limit=200&street=George&suburb=Sydney
    """
    limit = request.args.get('limit', '100')
    offset = request.args.get('offset', '0')

    street_number = request.args.get('street_number', '').strip()
    street = request.args.get('street', '').strip()
    suburb = request.args.get('suburb', '').strip()
    postcode = request.args.get('postcode', '').strip()
    state = request.args.get('state', '').strip()

    if street and is_coordinate_like(street):
        return jsonify({'error': 'Invalid street name: looks like a coordinate value'}), 400

    if suburb and is_coordinate_like(suburb):
        return jsonify({'error': 'Invalid suburb name: looks like a coordinate value'}), 400

    try:
        limit = int(limit)
        offset = int(offset)
    except Exception:
        limit = 100
        offset = 0

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT 
                latitude,
                longitude
            FROM gnaf.school_profile_2025
            WHERE acara_sml_id = %s
            LIMIT 1
        """, (acara_sml_id,))

        school_location = cursor.fetchone()
        if not school_location:
            cursor.close()
            conn.close()
            return jsonify({'error': 'School not found'}), 404

        if school_location['latitude'] is None or school_location['longitude'] is None:
            cursor.close()
            conn.close()
            return jsonify({'error': 'School coordinates not available for this location. Unable to search addresses within 5km radius.'}), 200

        school_lat = float(school_location['latitude'])
        school_lng = float(school_location['longitude'])

        filter_conditions = []
        filter_params = []

        if street_number:
            filter_conditions.append("ad.number_first::text ILIKE %s")
            filter_params.append('%' + str(street_number) + '%')

        if street:
            filter_conditions.append("sl.street_name ILIKE %s")
            filter_params.append('%' + str(street) + '%')

        if suburb:
            filter_conditions.append("l.locality_name ILIKE %s")
            filter_params.append('%' + str(suburb) + '%')

        if postcode:
            filter_conditions.append("ad.postcode = %s")
            filter_params.append(postcode)

        if state:
            filter_conditions.append("s.state_abbreviation ILIKE %s")
            filter_params.append(state)

        additional_where = ""
        if filter_conditions:
            additional_where = "AND " + " AND ".join(filter_conditions)

        query = f"""
            SELECT
                ad.address_detail_pid as gnaf_id,
                COALESCE(ad.number_first_prefix || '', '') ||
                COALESCE(ad.number_first::text || '', '') ||
                COALESCE(ad.number_first_suffix || ' ', ' ') ||
                COALESCE(sl.street_name || ' ', '') ||
                COALESCE(st.name || ', ', ', ') ||
                COALESCE(l.locality_name || ' ', ' ') ||
                COALESCE(s.state_abbreviation || ' ', ' ') ||
                COALESCE(ad.postcode || '', '') AS full_address,
                ad.number_first,
                ad.number_first_suffix,
                ad.number_last,
                ad.number_last_suffix,
                ad.flat_number,
                ft.name as flat_type,
                sl.street_name,
                st.name as street_type,
                l.locality_name,
                s.state_abbreviation,
                ad.postcode,
                ad.confidence,
                adg.latitude,
                adg.longitude,
                adg.geocode_type_code,
                ROUND(
                    (ST_Distance(
                        adg.geom::geography,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                    ) / 1000.0)::numeric,
                    2
                ) as distance_km,
                TO_CHAR(gvl.purchase_price, 'FM$999,999,999') AS last_sold_price,
                TO_CHAR(gvl.contract_date,  'FMDD Month YYYY') AS last_sale_date
            FROM gnaf.address_default_geocode adg
            INNER JOIN gnaf.address_detail ad
                ON ad.address_detail_pid = adg.address_detail_pid
            LEFT JOIN gnaf.flat_type_aut ft
                ON ad.flat_type_code = ft.code
            LEFT JOIN gnaf.street_locality sl
                ON ad.street_locality_pid = sl.street_locality_pid
            LEFT JOIN gnaf.street_type_aut st
                ON sl.street_type_code = st.code
            LEFT JOIN gnaf.locality l
                ON ad.locality_pid = l.locality_pid
            LEFT JOIN gnaf.state s
                ON l.state_pid = s.state_pid
            LEFT JOIN public.gnaf_vg_sale_link gvl ON gvl.address_detail_pid = ad.address_detail_pid
            WHERE adg.geom IS NOT NULL
                AND ST_DWithin(
                    adg.geom,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                    0.045
                )
                {additional_where}
            ORDER BY 
                adg.geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
            LIMIT %s OFFSET %s
        """

        query_params = [
            school_lng, school_lat,
            school_lng, school_lat,
        ] + filter_params + [
            school_lng, school_lat,
            limit, offset
        ]

        cursor.execute(query, query_params)
        addresses = cursor.fetchall()

        filtered_addresses = [addr for addr in addresses if addr['distance_km'] <= 5.0]
        sorted_addresses = sorted(filtered_addresses, key=lambda x: x['distance_km'])

        count_query = f"""
            SELECT COUNT(DISTINCT ad.address_detail_pid) as total
            FROM gnaf.address_default_geocode adg
            INNER JOIN gnaf.address_detail ad
                ON ad.address_detail_pid = adg.address_detail_pid
            LEFT JOIN gnaf.street_locality sl
                ON ad.street_locality_pid = sl.street_locality_pid
            LEFT JOIN gnaf.locality l
                ON ad.locality_pid = l.locality_pid
            LEFT JOIN gnaf.state s
                ON l.state_pid = s.state_pid
            WHERE adg.geom IS NOT NULL
                AND ST_DWithin(
                    adg.geom,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                    0.045
                )
                {additional_where}
        """

        count_params = [school_lng, school_lat] + filter_params
        cursor.execute(count_query, count_params)
        total_result = cursor.fetchone()
        total_addresses = total_result['total'] if total_result else len(sorted_addresses)

        cursor.close()
        conn.close()

        return jsonify({
            'addresses': [dict(addr) for addr in sorted_addresses],
            'total': total_addresses,
            'limit': limit,
            'offset': offset
        })

    except Exception as e:
        if conn:
            conn.close()
        print(f"Error in get_australia_school_addresses: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


@aus_schools_bp.route('/api/australia-school/<int:acara_sml_id>/autocomplete/streets', methods=['GET'])
@login_required
def autocomplete_australia_school_streets(acara_sml_id):
    """
    Autocomplete streets within 5km of a school
    Example: /api/australia-school/41319/autocomplete/streets?q=George
    """
    query = str(request.args.get('q', '')).strip()

    if not query or len(query) < 2:
        return jsonify([])

    if is_coordinate_like(query):
        return jsonify([])

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT latitude, longitude 
            FROM gnaf.school_geometry 
            WHERE acara_sml_id = %s
        """, (acara_sml_id,))
        school = cursor.fetchone()

        if not school:
            return jsonify([])

        if school['latitude'] is None or school['longitude'] is None:
            return jsonify([])

        lat_offset = 0.045
        lng_offset = 0.045
        school_lat = float(school['latitude'])
        school_lng = float(school['longitude'])

        cursor.execute("""
            SELECT DISTINCT 
                sl.street_name,
                st.name as street_type
            FROM gnaf.address_detail ad
            INNER JOIN gnaf.address_default_geocode adg
                ON ad.address_detail_pid = adg.address_detail_pid
            INNER JOIN gnaf.street_locality sl
                ON ad.street_locality_pid = sl.street_locality_pid
            LEFT JOIN gnaf.street_type_aut st
                ON sl.street_type_code = st.code
            WHERE adg.latitude IS NOT NULL 
                AND adg.longitude IS NOT NULL
                AND adg.latitude BETWEEN %s AND %s
                AND adg.longitude BETWEEN %s AND %s
                AND sl.street_name ILIKE %s
            ORDER BY sl.street_name
            LIMIT 20
        """, (school_lat - lat_offset, school_lat + lat_offset,
              school_lng - lng_offset, school_lng + lng_offset,
              str(query) + '%'))

        results = cursor.fetchall()
        cursor.close()
        conn.close()

        filtered_results = [
            r for r in results
            if not is_coordinate_like(r.get('street_name', ''))
        ]

        return jsonify([dict(r) for r in filtered_results])

    except Exception as e:
        if conn:
            conn.close()
        print(f"Error in autocomplete_australia_school_streets: {str(e)}")
        return jsonify({'error': str(e)}), 500


@aus_schools_bp.route('/api/australia-school/<int:acara_sml_id>/autocomplete/suburbs', methods=['GET'])
@login_required
def autocomplete_australia_school_suburbs(acara_sml_id):
    """
    Autocomplete suburbs within 5km of a school
    Example: /api/australia-school/41319/autocomplete/suburbs?q=Horn
    """
    query = str(request.args.get('q', '')).strip()

    if not query or len(query) < 2:
        return jsonify([])

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT latitude, longitude 
            FROM gnaf.school_geometry 
            WHERE acara_sml_id = %s
        """, (acara_sml_id,))
        school = cursor.fetchone()

        if not school:
            return jsonify([])

        if school['latitude'] is None or school['longitude'] is None:
            return jsonify([])

        lat_offset = 0.045
        lng_offset = 0.045
        school_lat = float(school['latitude'])
        school_lng = float(school['longitude'])

        cursor.execute("""
            SELECT DISTINCT 
                l.locality_name,
                ad.postcode,
                s.state_abbreviation
            FROM gnaf.address_detail ad
            INNER JOIN gnaf.address_default_geocode adg
                ON ad.address_detail_pid = adg.address_detail_pid
            INNER JOIN gnaf.locality l
                ON ad.locality_pid = l.locality_pid
            LEFT JOIN gnaf.state s
                ON l.state_pid = s.state_pid
            WHERE adg.latitude IS NOT NULL 
                AND adg.longitude IS NOT NULL
                AND adg.latitude BETWEEN %s AND %s
                AND adg.longitude BETWEEN %s AND %s
                AND l.locality_name ILIKE %s
            ORDER BY l.locality_name
            LIMIT 20
        """, (school_lat - lat_offset, school_lat + lat_offset,
              school_lng - lng_offset, school_lng + lng_offset,
              str(query) + '%'))

        results = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify([dict(r) for r in results])

    except Exception as e:
        if conn:
            conn.close()
        print(f"Error in autocomplete_australia_school_suburbs: {str(e)}")
        return jsonify({'error': str(e)}), 500


@aus_schools_bp.route('/api/australia-school/<int:acara_sml_id>/autocomplete/postcodes', methods=['GET'])
@login_required
def autocomplete_australia_school_postcodes(acara_sml_id):
    """
    Autocomplete postcodes within 5km of a school
    Example: /api/australia-school/41319/autocomplete/postcodes?q=20
    """
    query = str(request.args.get('q', '')).strip()

    if not query or len(query) < 2:
        return jsonify([])

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT latitude, longitude 
            FROM gnaf.school_geometry 
            WHERE acara_sml_id = %s
        """, (acara_sml_id,))
        school = cursor.fetchone()

        if not school:
            return jsonify([])

        if school['latitude'] is None or school['longitude'] is None:
            return jsonify([])

        lat_offset = 0.045
        lng_offset = 0.045
        school_lat = float(school['latitude'])
        school_lng = float(school['longitude'])

        cursor.execute("""
            SELECT DISTINCT 
                ad.postcode,
                l.locality_name as suburb
            FROM gnaf.address_detail ad
            INNER JOIN gnaf.address_default_geocode adg
                ON ad.address_detail_pid = adg.address_detail_pid
            LEFT JOIN gnaf.locality l
                ON ad.locality_pid = l.locality_pid
            WHERE adg.latitude IS NOT NULL 
                AND adg.longitude IS NOT NULL
                AND adg.latitude BETWEEN %s AND %s
                AND adg.longitude BETWEEN %s AND %s
                AND ad.postcode ILIKE %s
            ORDER BY ad.postcode
            LIMIT 20
        """, (school_lat - lat_offset, school_lat + lat_offset,
              school_lng - lng_offset, school_lng + lng_offset,
              str(query) + '%'))

        results = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify([dict(r) for r in results])

    except Exception as e:
        if conn:
            conn.close()
        print(f"Error in autocomplete_australia_school_postcodes: {str(e)}")
        return jsonify({'error': str(e)}), 500
