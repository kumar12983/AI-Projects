"""
Search, autocomplete, address, statistics, and hazard API routes.
"""
import re

from flask import Blueprint, request, jsonify
from flask_login import login_required
from psycopg2.extras import RealDictCursor

from .db import get_db_connection, is_coordinate_like, _STREET_TYPE_TO_CODE
from .validators import (
    AddressSearchQuery,
    AutocompleteQuery,
    CoordinateQuery,
    FullAddressAutocompleteQuery,
    PostcodeQuery,
    SuburbQuery,
    validate_query_params,
)

search_bp = Blueprint('search', __name__)


@search_bp.route('/api/search/suburbs', methods=['GET'])
def search_suburbs_by_postcode():
    """
    Search suburbs by postcode
    Example: /api/search/suburbs?postcode=2000
    """
    validated, err = validate_query_params(PostcodeQuery, request.args)
    if err:
        return err
    postcode = validated.postcode

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

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


@search_bp.route('/api/search/postcodes', methods=['GET'])
def search_postcodes_by_suburb():
    """
    Search postcodes by suburb name
    Example: /api/search/postcodes?suburb=Sydney
    """
    validated, err = validate_query_params(SuburbQuery, request.args)
    if err:
        return err
    suburb = validated.suburb

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

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
        """, ('%' + str(suburb) + '%',))

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


@search_bp.route('/api/autocomplete/suburbs', methods=['GET'])
def autocomplete_suburbs():
    """
    Autocomplete suburb names
    Example: /api/autocomplete/suburbs?q=Syd
    """
    validated, err = validate_query_params(AutocompleteQuery, request.args)
    if err:
        return err
    query = validated.q

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
        """, (str(query) + '%',))

        results = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify(results)

    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


@search_bp.route('/api/autocomplete/streets', methods=['GET'])
def autocomplete_streets():
    """
    Autocomplete street names
    Example: /api/autocomplete/streets?q=George
    """
    validated, err = validate_query_params(AutocompleteQuery, request.args)
    if err:
        return err
    query = validated.q

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
        """, (str(query) + '%',))

        results = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify(results)

    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


@search_bp.route('/api/autocomplete/full-address', methods=['GET'])
def autocomplete_full_address():
    """
    Full-address autocomplete using gnaf.address_full_text materialised view.

    Token rules:
    - Pure number  (e.g. "68"):   number_first = 68  (exact, avoids "68" matching "5688")
    - Number+suffix (e.g. "68A"): number_first = 68 AND number_first_suffix = 'A'
    - Text >= 3 chars:             ILIKE uses GIN trigram index (the speed anchor)
    - Short non-numeric (< 3):     skipped — no trigrams, seq-scan, noisy (RD, ST, AV)

    Performance: the GIN trigram index handles text tokens and narrows the result;
    number_first = X filters the small residual set with no extra overhead.
    At least one text token >= 3 chars (or state) is required to avoid full seq-scan.
    """
    validated, err = validate_query_params(FullAddressAutocompleteQuery, request.args)
    if err:
        return err
    query = validated.q
    state = validated.state or ''

    if not query or len(query) < 4:
        return jsonify([])

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        tokens = query.upper().split()
        where_parts = []
        exec_params = []
        has_text_anchor = False

        for token in tokens:
            pure_num   = re.match(r'^\d+$', token)
            num_suffix = re.match(r'^(\d+)([A-Z]+)$', token)

            if pure_num:
                where_parts.append("number_first = %s")
                exec_params.append(int(token))
            elif num_suffix:
                where_parts.append(
                    "(number_first = %s AND UPPER(COALESCE(number_first_suffix, '')) = %s)"
                )
                exec_params.extend([int(num_suffix.group(1)), num_suffix.group(2)])
            elif len(token) >= 3:
                where_parts.append("full_address LIKE %s")
                exec_params.append('%' + token + '%')
                has_text_anchor = True

        if not where_parts:
            return jsonify([])

        state_filter = "AND state = %s" if state else ""
        if state:
            exec_params.append(state)
            has_text_anchor = True

        if not has_text_anchor:
            return jsonify([])

        search_query = f"""
            SELECT
                address_detail_pid,
                full_address,
                building_name,
                number_first,
                number_first_suffix,
                number_last,
                number_last_suffix,
                flat_type,
                flat_number,
                street_name,
                street_type,
                suburb,
                state,
                postcode,
                latitude,
                longitude
            FROM gnaf.address_full_text
            WHERE {" AND ".join(where_parts)}
            {state_filter}
            ORDER BY full_address
            LIMIT 15
        """

        cursor.execute(search_query, exec_params)
        results = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify([dict(r) for r in results])

    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


@search_bp.route('/api/address/search', methods=['GET'])
def search_address():
    """
    Search for addresses by street name or locality
    Example: /api/address/search?street=George&suburb=Sydney&street_number=283
    """
    validated, err = validate_query_params(AddressSearchQuery, request.args)
    if err:
        return err
    street_number = validated.street_number or ''
    street = validated.street or ''
    suburb = validated.suburb or ''
    postcode = validated.postcode or ''
    state = validated.state or ''
    limit = validated.limit

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

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
                adg.geocode_type_code,
                TO_CHAR(gvl.purchase_price, 'FM$999,999,999') AS last_sold_price,
                TO_CHAR(gvl.contract_date,  'FMDD Month YYYY') AS last_sale_date
            FROM gnaf.address_detail ad
            LEFT JOIN gnaf.flat_type_aut ft ON ad.flat_type_code = ft.code
            LEFT JOIN gnaf.street_locality sl ON ad.street_locality_pid = sl.street_locality_pid
            LEFT JOIN gnaf.street_type_aut st ON sl.street_type_code = st.code
            LEFT JOIN gnaf.locality l ON ad.locality_pid = l.locality_pid
            LEFT JOIN gnaf.state s ON l.state_pid = s.state_pid
            LEFT JOIN gnaf.address_default_geocode adg ON ad.address_detail_pid = adg.address_detail_pid
            LEFT JOIN public.gnaf_vg_sale_link gvl ON gvl.address_detail_pid = ad.address_detail_pid
            WHERE ad.date_retired IS NULL
        """

        params = []

        if street_number:
            _sn_match = re.match(r'^(\d+)([A-Za-z]*)$', street_number.strip())
            if _sn_match:
                _sn_num    = int(_sn_match.group(1))
                _sn_suffix = _sn_match.group(2).upper()
                if _sn_suffix:
                    query += " AND ad.number_first = %s AND UPPER(COALESCE(ad.number_first_suffix, '')) = %s"
                    params.extend([_sn_num, _sn_suffix])
                else:
                    query += " AND ad.number_first = %s"
                    params.append(_sn_num)
            else:
                query += " AND CAST(ad.number_first AS TEXT) LIKE %s"
                params.append('%' + str(street_number) + '%')

        if street:
            _parts = street.upper().split()
            _last = _parts[-1] if _parts else ''
            _gnaf_type = _STREET_TYPE_TO_CODE.get(_last)
            if _gnaf_type and len(_parts) > 1:
                _name_part = ' '.join(_parts[:-1])
                query += " AND UPPER(sl.street_name) LIKE UPPER(%s) AND UPPER(sl.street_type_code) = %s"
                params.extend(['%' + _name_part + '%', _gnaf_type])
            else:
                query += " AND UPPER(sl.street_name) LIKE UPPER(%s)"
                params.append('%' + str(street) + '%')

        if suburb:
            query += " AND UPPER(l.locality_name) LIKE UPPER(%s)"
            params.append('%' + str(suburb) + '%')

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


@search_bp.route('/api/address/schools', methods=['GET'])
@login_required
def get_schools_for_address():
    """
    Get schools that contain a given address (lat/lng) in their catchment
    Example: /api/address/schools?lat=-33.8688&lng=151.2093&state=VIC
    """
    validated, err = validate_query_params(CoordinateQuery, request.args)
    if err:
        return err
    lat = validated.lat
    lng = validated.lng
    state = str(request.args.get('state', 'NSW')).strip()

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT DISTINCT
                school_id,
                school_name,
                campus_name,
                school_type,
                state,
                year_level_code
            FROM gnaf.school_catchments
            WHERE state = %s
            AND ST_Contains(
                geometry,
                ST_SetSRID(ST_MakePoint(%s, %s), 4326)
            )
            ORDER BY school_type, school_name
        """

        cursor.execute(query, (state, lng, lat))
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


@search_bp.route('/api/stats', methods=['GET'])
def get_statistics():
    """Get general database statistics"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        stats = {}

        cursor.execute("SELECT * FROM gnaf.stats_summary")
        summary = cursor.fetchone()

        if summary:
            stats['total_localities'] = summary['total_localities']
            stats['total_addresses'] = summary['total_addresses']
            stats['total_streets'] = summary['total_streets']
            stats['last_refreshed'] = summary['last_refreshed'].isoformat() if summary.get('last_refreshed') else None
        else:
            stats['total_localities'] = 0
            stats['total_addresses'] = 0
            stats['total_streets'] = 0

        cursor.execute("SELECT * FROM gnaf.stats_by_state ORDER BY state_abbreviation")
        stats['localities_by_state'] = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(stats)

    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500


@search_bp.route('/api/suburbs/by-state', methods=['GET'])
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
