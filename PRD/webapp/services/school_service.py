"""
NSW school catchment service — all SQL extracted from blueprints/schools.py.
"""
import json
import traceback

from psycopg2.extras import RealDictCursor


def autocomplete_schools(conn, query: str, school_type: str = '', state: str = 'NSW') -> list:
    """3-tier ranking: exact → prefix → contains."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        type_filter = ''
        type_param  = None
        if school_type and school_type.upper() != 'ALL':
            type_filter = 'AND school_type = %s'
            type_param  = school_type.upper()

        def _run(template, rank):
            params = [state, query]
            if type_param:
                params.append(type_param)
            cur.execute(template.format(type_filter=type_filter), params)
            return cur.fetchall()

        exact_sql = """
            SELECT school_id, school_name, school_type, state, 0 AS rank_order
            FROM gnaf.school_catchments
            WHERE state = %s AND UPPER(school_name) = UPPER(%s) {type_filter}
        """
        results = _run(exact_sql, 0)
        if not results:
            prefix_sql = """
                SELECT school_id, school_name, school_type, state, 1 AS rank_order
                FROM gnaf.school_catchments
                WHERE state = %s AND UPPER(school_name) LIKE UPPER(%s) || '%%' {type_filter}
                ORDER BY school_name LIMIT 20
            """
            results = _run(prefix_sql, 1)
        if not results:
            substr_sql = """
                SELECT school_id, school_name, school_type, state, 2 AS rank_order
                FROM gnaf.school_catchments
                WHERE state = %s AND UPPER(school_name) LIKE '%%' || UPPER(%s) || '%%' {type_filter}
                ORDER BY school_name LIMIT 20
            """
            results = _run(substr_sql, 2)

    return [
        {'school_id': r['school_id'], 'school_name': r['school_name'],
         'school_type': r['school_type'], 'state': r['state']}
        for r in results
    ]


def autocomplete_school_streets(conn, school_id, query: str) -> list:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT DISTINCT scs.street_name, st.name AS street_type
            FROM public.school_catchment_streets scs
            LEFT JOIN gnaf.street_type_aut st ON scs.street_type_code = st.code
            WHERE scs.school_id = %s AND UPPER(scs.street_name) LIKE UPPER(%s)
            ORDER BY scs.street_name LIMIT 20
            """,
            (school_id, query + '%'),
        )
        return cur.fetchall()


def autocomplete_school_suburbs(conn, school_id, query: str) -> list:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT DISTINCT scs.locality_name AS suburb, scs.postcode
            FROM public.school_catchment_streets scs
            WHERE scs.school_id = %s AND UPPER(scs.locality_name) LIKE UPPER(%s)
            ORDER BY scs.locality_name LIMIT 20
            """,
            (school_id, query + '%'),
        )
        return cur.fetchall()


def autocomplete_school_postcodes(conn, school_id, query: str) -> list:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT DISTINCT scs.postcode, scs.locality_name AS suburb
            FROM public.school_catchment_streets scs
            WHERE scs.school_id = %s AND scs.postcode LIKE %s
            ORDER BY scs.postcode LIMIT 20
            """,
            (school_id, query + '%'),
        )
        return cur.fetchall()


def get_school_info(conn, school_id) -> dict | None:
    """Return rich school info dict, or None if not found."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT DISTINCT
                s.school_id, s.school_name, s.school_type, s.state, s.campus_name,
                s.centroid_lat, s.centroid_lng,
                COALESCE(pf.latitude,  s.school_lat, s.centroid_lat) AS school_latitude,
                COALESCE(pf.longitude, s.school_lng, s.centroid_lng) AS school_longitude
            FROM gnaf.school_catchments s
            LEFT JOIN gnaf.school_type_lookup pf ON pf.school_id = s.school_id
            WHERE s.school_id::text = %s
            LIMIT 1
            """,
            (str(school_id),),
        )
        catchment_info = cur.fetchone()
        if not catchment_info:
            return None

        cur.execute(
            """
            SELECT school_id, catchment_school_name, school_sector, school_type,
                   icsea, icsea_percentile, school_url, acara_url, naplan_url,
                   suburb, state, postcode
            FROM gnaf.school_type_lookup
            WHERE school_id::text = %s AND catchment_school_name = %s
            LIMIT 1
            """,
            (str(school_id), catchment_info['school_name']),
        )
        lookup_info = cur.fetchone()

        cur.execute(
            """
            SELECT
                CAST("KINDERGART" AS TEXT) AS kg,
                CAST("YEAR1"  AS TEXT) AS yr_01, CAST("YEAR2"  AS TEXT) AS yr_02,
                CAST("YEAR3"  AS TEXT) AS yr_03, CAST("YEAR4"  AS TEXT) AS yr_04,
                CAST("YEAR5"  AS TEXT) AS yr_05, CAST("YEAR6"  AS TEXT) AS yr_06,
                CAST("YEAR7"  AS TEXT) AS yr_07, CAST("YEAR8"  AS TEXT) AS yr_08,
                CAST("YEAR9"  AS TEXT) AS yr_09, CAST("YEAR10" AS TEXT) AS yr_10,
                CAST("YEAR11" AS TEXT) AS yr_11, CAST("YEAR12" AS TEXT) AS yr_12
            FROM public.school_catchments_primary   WHERE "USE_ID"::text = %s
            UNION ALL
            SELECT
                CAST("KINDERGART" AS TEXT) AS kg,
                CAST("YEAR1"  AS TEXT) AS yr_01, CAST("YEAR2"  AS TEXT) AS yr_02,
                CAST("YEAR3"  AS TEXT) AS yr_03, CAST("YEAR4"  AS TEXT) AS yr_04,
                CAST("YEAR5"  AS TEXT) AS yr_05, CAST("YEAR6"  AS TEXT) AS yr_06,
                CAST("YEAR7"  AS TEXT) AS yr_07, CAST("YEAR8"  AS TEXT) AS yr_08,
                CAST("YEAR9"  AS TEXT) AS yr_09, CAST("YEAR10" AS TEXT) AS yr_10,
                CAST("YEAR11" AS TEXT) AS yr_11, CAST("YEAR12" AS TEXT) AS yr_12
            FROM public.school_catchments_secondary WHERE "USE_ID"::text = %s
            UNION ALL
            SELECT
                CAST("KINDERGART" AS TEXT) AS kg,
                CAST("YEAR1"  AS TEXT) AS yr_01, CAST("YEAR2"  AS TEXT) AS yr_02,
                CAST("YEAR3"  AS TEXT) AS yr_03, CAST("YEAR4"  AS TEXT) AS yr_04,
                CAST("YEAR5"  AS TEXT) AS yr_05, CAST("YEAR6"  AS TEXT) AS yr_06,
                CAST("YEAR7"  AS TEXT) AS yr_07, CAST("YEAR8"  AS TEXT) AS yr_08,
                CAST("YEAR9"  AS TEXT) AS yr_09, CAST("YEAR10" AS TEXT) AS yr_10,
                CAST("YEAR11" AS TEXT) AS yr_11, CAST("YEAR12" AS TEXT) AS yr_12
            FROM public.school_catchments_future    WHERE "USE_ID"::text = %s
            LIMIT 1
            """,
            (str(school_id), str(school_id), str(school_id)),
        )
        year_data = cur.fetchone()

        cur.execute(
            "SELECT COUNT(*) AS address_count FROM gnaf.school_catchments WHERE school_id::text = %s",
            (str(school_id),),
        )
        stats = cur.fetchone()

        vic_year_codes = None
        if catchment_info.get('state') == 'VIC':
            cur.execute(
                """
                SELECT ARRAY_AGG(DISTINCT year_level_code ORDER BY year_level_code) AS codes
                FROM gnaf.school_catchments
                WHERE school_id::text = %s
                  AND year_level_code IS NOT NULL
                  AND TRIM(year_level_code) != ''
                """,
                (str(school_id),),
            )
            vic_yr = cur.fetchone()
            if vic_yr and vic_yr['codes']:
                vic_year_codes = vic_yr['codes']

    # Build year_levels list
    year_levels: list[str] = []
    if year_data:
        if year_data.get('kg') == 'Y':
            year_levels.append('K')
        for i in range(1, 13):
            if year_data.get(f'yr_{i:02d}') == 'Y':
                year_levels.append(str(i))

    vic_year_level_display = None
    if not year_levels and vic_year_codes:
        has_p6  = 'P6' in vic_year_codes
        numeric = sorted([int(c) for c in vic_year_codes if c != 'P6' and c.isdigit()])
        parts   = []
        if has_p6:
            parts.append('Prep - Year 6')
        if numeric:
            parts.append('Year ' + ', '.join(str(n) for n in numeric))
        vic_year_level_display = ' / '.join(parts)
        year_levels = [vic_year_level_display] if vic_year_level_display else []

    return {
        'school_id':        str(catchment_info['school_id']),
        'school_name':      catchment_info['school_name'],
        'school_type':      catchment_info['school_type'],
        'state':            catchment_info.get('state'),
        'campus_name':      catchment_info.get('campus_name'),
        'year_level_code':  vic_year_level_display,
        'school_sector':    lookup_info['school_sector']  if lookup_info else None,
        'school_type_name': lookup_info['school_type']    if lookup_info else None,
        'school_url':       lookup_info['school_url']     if lookup_info else None,
        'acara_url':        lookup_info['acara_url']      if lookup_info else None,
        'naplan_url':       lookup_info['naplan_url']     if lookup_info else None,
        'priority':         None,
        'year_levels':      ', '.join(year_levels) if year_levels else 'N/A',
        'address_count':    stats['address_count'] if stats else 0,
        'icsea':            lookup_info['icsea']            if lookup_info else None,
        'icsea_percentile': lookup_info['icsea_percentile'] if lookup_info else None,
        'location': {
            'suburb':  lookup_info['suburb']  if lookup_info else None,
            'state':   lookup_info['state']   if lookup_info else None,
            'postcode': lookup_info['postcode'] if lookup_info else None,
        } if lookup_info else None,
        'school_location': {
            'latitude':  catchment_info.get('school_latitude'),
            'longitude': catchment_info.get('school_longitude'),
            'suburb':    lookup_info['suburb']  if lookup_info else None,
            'state':     catchment_info.get('state') or (lookup_info['state'] if lookup_info else None),
            'postcode':  lookup_info['postcode'] if lookup_info else None,
        } if (catchment_info.get('school_latitude') and catchment_info.get('school_longitude')) else None,
    }


def get_school_addresses(conn, school_id, street_number: str = '', street: str = '',
                         suburb: str = '', postcode: str = '', state: str = '',
                         limit: int = 500, offset: int = 0) -> dict:
    """Return paginated addresses within a school catchment."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT COALESCE(pf.latitude,  s.school_lat) AS school_lat,
                   COALESCE(pf.longitude, s.school_lng) AS school_lng
            FROM gnaf.school_catchments s
            LEFT JOIN gnaf.school_type_lookup pf ON pf.school_id = s.school_id
            WHERE s.school_id = %s LIMIT 1
            """,
            (school_id,),
        )
        school_location = cur.fetchone()
        if not school_location:
            return None  # caller should 404

        school_lat = school_location['school_lat']
        school_lng = school_location['school_lng']

        filter_conditions: list[str] = []
        filter_params:     list      = []

        if street_number:
            filter_conditions.append("ad.number_first::text ILIKE %s")
            filter_params.append('%' + street_number + '%')
        if street:
            filter_conditions.append("sl.street_name ILIKE %s")
            filter_params.append('%' + street + '%')
        if suburb:
            filter_conditions.append("l.locality_name ILIKE %s")
            filter_params.append('%' + suburb + '%')
        if postcode:
            filter_conditions.append("ad.postcode = %s")
            filter_params.append(postcode)
        if state:
            filter_conditions.append("s.state_abbreviation ILIKE %s")
            filter_params.append(state)

        additional_where = ('AND ' + ' AND '.join(filter_conditions)) if filter_conditions else ''

        query = f"""
            WITH school_catchment AS (
                SELECT geometry FROM gnaf.school_catchments WHERE school_id = %s
            ),
            school_point AS (
                SELECT ST_SetSRID(ST_MakePoint(%s, %s), 4326) AS geom
            )
            SELECT DISTINCT ON (ad.address_detail_pid)
                ad.address_detail_pid AS gnaf_id,
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
                COALESCE(st.name || ' ', '')         AS full_address,
                ad.number_first, ad.number_first_suffix,
                ad.number_last,  ad.number_last_suffix,
                COALESCE(ad.flat_number::text, '') AS flat_number,
                sl.street_name, st.name AS street_type,
                l.locality_name AS suburb, ad.postcode,
                s.state_abbreviation AS state,
                agc.latitude, agc.longitude, agc.geocode_type_code,
                ad.confidence,
                ROUND(CAST(ST_Distance(
                    agc.geom::geography, sp.geom::geography
                ) / 1000.0 AS numeric), 2) AS distance_km,
                TO_CHAR(gvl.purchase_price, 'FM$999,999,999') AS last_sold_price,
                TO_CHAR(gvl.contract_date,  'FMDD Month YYYY') AS last_sale_date
            FROM gnaf.address_detail ad
            JOIN gnaf.address_default_geocode agc ON ad.address_detail_pid = agc.address_detail_pid
            JOIN gnaf.street_locality sl           ON ad.street_locality_pid = sl.street_locality_pid
            JOIN gnaf.locality l                   ON sl.locality_pid = l.locality_pid
            JOIN gnaf.state s                      ON l.state_pid = s.state_pid
            LEFT JOIN gnaf.street_type_aut st      ON sl.street_type_code = st.code
            LEFT JOIN gnaf.flat_type_aut ft        ON ad.flat_type_code = ft.code
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
        cur.execute(query, [school_id, school_lng, school_lat] + filter_params + [limit, offset])
        addresses = cur.fetchall()

        count_sql = f"""
            WITH school_catchment AS (
                SELECT geometry FROM gnaf.school_catchments WHERE school_id = %s
            )
            SELECT COUNT(DISTINCT ad.address_detail_pid) AS total
            FROM gnaf.address_detail ad
            JOIN gnaf.address_default_geocode agc ON ad.address_detail_pid = agc.address_detail_pid
            JOIN gnaf.street_locality sl           ON ad.street_locality_pid = sl.street_locality_pid
            JOIN gnaf.locality l                   ON sl.locality_pid = l.locality_pid
            JOIN gnaf.state s                      ON l.state_pid = s.state_pid
            LEFT JOIN gnaf.street_type_aut st      ON sl.street_type_code = st.code
            CROSS JOIN school_catchment sc
            WHERE ad.date_retired IS NULL
              AND agc.date_retired IS NULL
              AND agc.geom IS NOT NULL
              AND ST_Contains(sc.geometry, agc.geom)
            {additional_where}
        """
        cur.execute(count_sql, [school_id] + filter_params)
        total_count = cur.fetchone()['total']

    return {
        'addresses':      addresses,
        'total_count':    total_count,
        'showing_count':  len(addresses),
        'offset':         offset,
        'limit':          limit,
        'has_more':       (offset + len(addresses)) < total_count,
        'school_location': {'latitude': school_lat, 'longitude': school_lng},
    }


def get_school_boundary(conn, school_id) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT ST_AsGeoJSON(ST_Union(geometry)) AS geojson,
                   MAX(school_name) AS school_name,
                   MAX(school_type) AS school_type
            FROM gnaf.school_catchments
            WHERE school_id = %s
            GROUP BY school_id
            """,
            (school_id,),
        )
        result = cur.fetchone()
    if not result:
        return None
    return {
        'geojson':     json.loads(result['geojson']),
        'school_name': result['school_name'],
        'school_type': result['school_type'],
    }
