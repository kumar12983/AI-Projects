"""
NSW school catchment API routes.
"""
import traceback

from flask import Blueprint, request, jsonify
from flask_login import login_required
from psycopg2.extras import RealDictCursor

from .db import get_db_connection, is_coordinate_like

schools_bp = Blueprint('schools', __name__)


@schools_bp.route('/api/autocomplete/schools', methods=['GET'])
@login_required
def autocomplete_schools():
    """
    Autocomplete school names with smart ranking
    Prioritizes exact matches, then starts-with, then contains
    Example: /api/autocomplete/schools?q=Hornsby NPS&type=PRIMARY
    """
    query = str(request.args.get('q', '')).strip()
    school_type = str(request.args.get('type', '')).strip()
    state = str(request.args.get('state', 'NSW')).strip()

    if not query or len(query) < 3:
        return jsonify([])

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        type_filter = ""
        type_param = None
        if school_type and school_type.upper() != 'ALL':
            type_filter = "AND school_type = %s"
            type_param = school_type.upper()

        exact_query = """
            SELECT 
                school_id,
                school_name,
                school_type,
                state,
                0 as rank_order
            FROM gnaf.school_catchments
            WHERE state = %s
            AND UPPER(school_name) = UPPER(%s) {type_filter}
        """.format(type_filter=type_filter)

        params = [state, query]
        if type_param:
            params.append(type_param)

        cursor.execute(exact_query, params)
        exact_results = cursor.fetchall()

        if not exact_results:
            prefix_query = """
                SELECT 
                    school_id,
                    school_name,
                    school_type,
                    state,
                    1 as rank_order
                FROM gnaf.school_catchments
                WHERE state = %s
                AND UPPER(school_name) LIKE UPPER(%s) || '%%' {type_filter}
                ORDER BY school_name
                LIMIT 20
            """.format(type_filter=type_filter)

            params = [state, query]
            if type_param:
                params.append(type_param)

            cursor.execute(prefix_query, params)
            exact_results = cursor.fetchall()

        if not exact_results:
            substring_query = """
                SELECT 
                    school_id,
                    school_name,
                    school_type,
                    state,
                    2 as rank_order
                FROM gnaf.school_catchments
                WHERE state = %s
                AND UPPER(school_name) LIKE '%%' || UPPER(%s) || '%%' {type_filter}
                ORDER BY school_name
                LIMIT 20
            """.format(type_filter=type_filter)

            params = [state, query]
            if type_param:
                params.append(type_param)

            cursor.execute(substring_query, params)
            exact_results = cursor.fetchall()

        output_results = []
        for row in exact_results:
            output_results.append({
                'school_id': row['school_id'],
                'school_name': row['school_name'],
                'school_type': row['school_type'],
                'state': row['state']
            })

        cursor.close()
        conn.close()

        return jsonify(output_results)

    except Exception as e:
        if conn:
            conn.close()
        print(f"Error in autocomplete_schools: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


@schools_bp.route('/api/school/<school_id>/autocomplete/streets', methods=['GET'])
@login_required
def autocomplete_school_streets(school_id):
    """
    Autocomplete street names filtered by school catchment area
    Example: /api/school/2060/autocomplete/streets?q=George
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
            SELECT DISTINCT 
                scs.street_name,
                st.name as street_type
            FROM public.school_catchment_streets scs
            LEFT JOIN gnaf.street_type_aut st ON scs.street_type_code = st.code
            WHERE scs.school_id = %s
            AND UPPER(scs.street_name) LIKE UPPER(%s)
            ORDER BY scs.street_name
            LIMIT 20
        """, (school_id, str(query) + '%'))

        results = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify(results)

    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


@schools_bp.route('/api/school/<school_id>/autocomplete/suburbs', methods=['GET'])
@login_required
def autocomplete_school_suburbs(school_id):
    """
    Autocomplete suburb names filtered by school catchment area
    Example: /api/school/2060/autocomplete/suburbs?q=Syd
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
            SELECT DISTINCT 
                scs.locality_name as suburb,
                scs.postcode
            FROM public.school_catchment_streets scs
            WHERE scs.school_id = %s
            AND UPPER(scs.locality_name) LIKE UPPER(%s)
            ORDER BY scs.locality_name
            LIMIT 20
        """, (school_id, str(query) + '%'))

        results = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify(results)

    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


@schools_bp.route('/api/school/<school_id>/autocomplete/postcodes', methods=['GET'])
@login_required
def autocomplete_school_postcodes(school_id):
    """
    Autocomplete postcodes filtered by school catchment area
    Example: /api/school/2060/autocomplete/postcodes?q=20
    """
    query = str(request.args.get('q', '')).strip()

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
        """, (school_id, str(query) + '%'))

        results = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify(results)

    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


@schools_bp.route('/api/school/<int:school_id>/info', methods=['GET'])
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

        cursor.execute("""
            SELECT DISTINCT
                s.school_id,
                s.school_name,
                s.school_type,
                s.state,
                s.campus_name,
                s.centroid_lat,
                s.centroid_lng,
                COALESCE(pf.latitude, s.school_lat, s.centroid_lat) as school_latitude,
                COALESCE(pf.longitude, s.school_lng, s.centroid_lng) as school_longitude
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

        cursor.execute("""
            SELECT COUNT(*) as address_count
            FROM gnaf.school_catchments
            WHERE school_id::text = %s
        """, (str(school_id),))

        stats = cursor.fetchone()
        print(f"[DEBUG] stats: {stats}")

        vic_year_codes = None
        if catchment_info.get('state') == 'VIC':
            cursor.execute("""
                SELECT ARRAY_AGG(DISTINCT year_level_code ORDER BY year_level_code) as codes
                FROM gnaf.school_catchments
                WHERE school_id::text = %s
                  AND year_level_code IS NOT NULL
                  AND TRIM(year_level_code) != ''
            """, (str(school_id),))
            vic_yr = cursor.fetchone()
            if vic_yr and vic_yr['codes']:
                vic_year_codes = vic_yr['codes']

        cursor.close()
        conn.close()

        year_levels = []
        if year_data:
            if year_data.get('kg') == 'Y':
                year_levels.append('K')
            for i in range(1, 13):
                yr_key = f'yr_{i:02d}'
                if year_data.get(yr_key) == 'Y':
                    year_levels.append(str(i))

        vic_year_level_display = None
        if not year_levels and vic_year_codes:
            has_p6 = 'P6' in vic_year_codes
            numeric = sorted([int(c) for c in vic_year_codes if c != 'P6' and c.isdigit()])
            parts = []
            if has_p6:
                parts.append('Prep - Year 6')
            if numeric:
                parts.append('Year ' + ', '.join(str(n) for n in numeric))
            vic_year_level_display = ' / '.join(parts)
            year_levels = [vic_year_level_display] if vic_year_level_display else []

        print(f"[DEBUG] year_levels: {year_levels}")

        result = {
            'school_id': str(catchment_info['school_id']),
            'school_name': catchment_info['school_name'],
            'school_type': catchment_info['school_type'],
            'state': catchment_info.get('state'),
            'campus_name': catchment_info.get('campus_name'),
            'year_level_code': vic_year_level_display,
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
                'state': catchment_info.get('state') or (lookup_info['state'] if lookup_info else None),
                'postcode': lookup_info['postcode'] if lookup_info else None
            } if (catchment_info.get('school_latitude') and catchment_info.get('school_longitude')) else None
        }

        print(f"[DEBUG] Returning result: {result}")
        return jsonify(result)

    except Exception as e:
        if conn:
            conn.close()
        print(f"[ERROR] Error in get_school_info for school_id={school_id}: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


@schools_bp.route('/api/school/<school_id>/addresses', methods=['GET'])
@login_required
def get_school_addresses(school_id):
    """
    Get addresses within a school catchment with optional search filters
    Example: /api/school/2060/addresses?limit=500&offset=0&street=Burdett&suburb=Hornsby
    """
    limit = request.args.get('limit', '500')
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
        limit = 500
        offset = 0

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

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
                    agc.geom::geography,
                    sp.geom::geography
                ) / 1000.0 AS numeric), 2) as distance_km,
                TO_CHAR(gvl.purchase_price, 'FM$999,999,999') AS last_sold_price,
                TO_CHAR(gvl.contract_date,  'FMDD Month YYYY') AS last_sale_date
            FROM gnaf.address_detail ad
            JOIN gnaf.address_default_geocode agc ON ad.address_detail_pid = agc.address_detail_pid
            JOIN gnaf.street_locality sl ON ad.street_locality_pid = sl.street_locality_pid
            JOIN gnaf.locality l ON sl.locality_pid = l.locality_pid
            JOIN gnaf.state s ON l.state_pid = s.state_pid
            LEFT JOIN gnaf.street_type_aut st ON sl.street_type_code = st.code
            LEFT JOIN gnaf.flat_type_aut ft ON ad.flat_type_code = ft.code
            LEFT JOIN public.gnaf_vg_sale_link gvl ON gvl.address_detail_pid = ad.address_detail_pid
            CROSS JOIN school_catchment sc
            CROSS JOIN school_point sp
            WHERE ad.date_retired IS NULL
            AND agc.date_retired IS NULL
            AND agc.geom IS NOT NULL
            AND sl.date_retired IS NULL
            AND l.date_retired IS NULL
            AND ST_Contains(sc.geometry, agc.geom)
            {additional_where}
            ORDER BY ad.address_detail_pid, l.locality_name, sl.street_name, ad.number_first
            LIMIT %s OFFSET %s
        """

        query_params = [school_id, school_lng, school_lat] + filter_params + [limit, offset]

        cursor.execute(query, query_params)
        addresses = cursor.fetchall()

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
            AND agc.geom IS NOT NULL
            AND ST_Contains(sc.geometry, agc.geom)
            {additional_where}
        """

        count_params = [school_id] + filter_params
        cursor.execute(count_query, count_params)
        total_count = cursor.fetchone()['total']

        cursor.close()
        conn.close()

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


@schools_bp.route('/api/school/<school_id>/boundary', methods=['GET'])
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

        cursor.execute("""
            SELECT 
                ST_AsGeoJSON(ST_Union(geometry)) as geojson,
                MAX(school_name) as school_name,
                MAX(school_type) as school_type
            FROM gnaf.school_catchments
            WHERE school_id = %s
            GROUP BY school_id
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
