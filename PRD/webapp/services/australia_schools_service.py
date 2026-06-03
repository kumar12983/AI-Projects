"""
Australia-wide school (5 km radius) service — all SQL from blueprints/australia_schools.py.
"""
import json
import traceback

from psycopg2.extras import RealDictCursor

from db_utils import is_coordinate_like, _STREET_TYPE_TO_CODE


def autocomplete_australia_schools(conn, query: str, state: str = '') -> list:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        state_filter = 'AND state = %s' if state else ''
        params       = [query, query, query, query]
        if state:
            params.append(state)

        cur.execute(
            f"""
            SELECT
                acara_sml_id, school_name, state, school_sector,
                CASE
                    WHEN UPPER(school_name) LIKE UPPER(%s) || '%%' THEN 1
                    WHEN search_vector @@ plainto_tsquery('english', %s) THEN 2
                    ELSE 3
                END AS rank
            FROM gnaf.school_geometry
            WHERE (UPPER(school_name) LIKE '%%' || UPPER(%s) || '%%'
                   OR search_vector @@ plainto_tsquery('english', %s))
            {state_filter}
            ORDER BY rank, school_name
            LIMIT 20
            """,
            params,
        )
        return [
            {'acara_sml_id': r['acara_sml_id'], 'school_name': r['school_name'],
             'state': r['state'], 'school_type': r['school_sector']}
            for r in cur.fetchall()
        ]


def get_australia_school_info(conn, acara_sml_id) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                sg.acara_sml_id, sg.school_name, sg.state, sg.school_sector,
                pf.latitude, pf.longitude, sg.school_id, sg.has_catchment,
                ST_AsGeoJSON(ST_Transform(sg.geom_5km_buffer, 4326)) AS geom_5km_buffer_json,
                pf.year_range, pf.school_type, pf.school_url,
                lk.acara_url AS school_profile_url, lk.naplan_url,
                pf.icsea, pf.icsea_percentile
            FROM gnaf.school_geometry sg
            LEFT JOIN gnaf.school_profile_2025 pf ON sg.acara_sml_id = pf.acara_sml_id
            LEFT JOIN gnaf.school_type_lookup  lk ON sg.acara_sml_id = lk.acara_sml_id
            WHERE sg.acara_sml_id = %s
            LIMIT 1
            """,
            (acara_sml_id,),
        )
        school = cur.fetchone()
        if not school:
            return None

        vic_catchment_id = None
        if school['has_catchment'] != 'Y' and school['state'] == 'VIC':
            cur.execute(
                """
                SELECT school_id FROM gnaf.school_catchments
                WHERE state = 'VIC' AND LOWER(TRIM(school_name)) = LOWER(TRIM(%s))
                LIMIT 1
                """,
                (school['school_name'],),
            )
            row = cur.fetchone()
            if row:
                vic_catchment_id = row['school_id']

    geom_5km_buffer = None
    if school['geom_5km_buffer_json']:
        geometry        = json.loads(school['geom_5km_buffer_json'])
        geom_5km_buffer = {'type': 'Feature', 'geometry': geometry, 'properties': {}}

    acara_url  = school['school_profile_url'] or (
        f"https://myschool.edu.au/school/{school['acara_sml_id']}" if school['acara_sml_id'] else None
    )
    naplan_url = school['naplan_url'] or (
        f"https://myschool.edu.au/school/{school['acara_sml_id']}/naplan/results"
        if school['acara_sml_id'] else None
    )

    return {
        'acara_sml_id':     school['acara_sml_id'],
        'school_name':      school['school_name'],
        'state':            school['state'],
        'sector':           school['school_sector'],
        'latitude':         float(school['latitude'])  if school['latitude']  else None,
        'longitude':        float(school['longitude']) if school['longitude'] else None,
        'school_id':        vic_catchment_id if vic_catchment_id else school['school_id'],
        'has_catchment':    'Y' if (school['has_catchment'] == 'Y' or vic_catchment_id) else school['has_catchment'],
        'buffer_geojson':   geom_5km_buffer,
        'year_range':       school['year_range'],
        'school_type':      school['school_type'],
        'school_url':       school['school_url'],
        'acara_url':        acara_url,
        'naplan_url':       naplan_url,
        'icsea':            school['icsea'],
        'icsea_percentile': school['icsea_percentile'],
    }


def get_australia_school_addresses(conn, acara_sml_id: int,
                                   street_number: str = '', street: str = '',
                                   suburb: str = '', postcode: str = '', state: str = '',
                                   limit: int = 100, offset: int = 0) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT latitude, longitude FROM gnaf.school_profile_2025 WHERE acara_sml_id = %s LIMIT 1",
            (acara_sml_id,),
        )
        loc = cur.fetchone()
        if not loc:
            return None  # caller should 404
        if loc['latitude'] is None or loc['longitude'] is None:
            return {'no_coordinates': True}  # caller returns 200 with message

        school_lat = float(loc['latitude'])
        school_lng = float(loc['longitude'])

        filter_conditions: list[str] = []
        filter_params:     list      = []

        if street_number:
            filter_conditions.append("ad.number_first::text ILIKE %s")
            filter_params.append('%' + street_number + '%')
        if street:
            _parts  = street.upper().split()
            _last   = _parts[-1] if _parts else ''
            _gnaf_t = _STREET_TYPE_TO_CODE.get(_last)
            if _gnaf_t and len(_parts) > 1:
                _name_part = ' '.join(_parts[:-1])
                filter_conditions.append("UPPER(sl.street_name) LIKE UPPER(%s) AND UPPER(sl.street_type_code) = %s")
                filter_params.extend(['%' + _name_part + '%', _gnaf_t])
            else:
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
            SELECT
                ad.address_detail_pid,
                COALESCE(ad.number_first_prefix  || '', '') ||
                COALESCE(ad.number_first::text   || '', '') ||
                COALESCE(ad.number_first_suffix  || ' ', ' ') ||
                COALESCE(sl.street_name          || ' ', '') ||
                COALESCE(st.name                 || ', ', ', ') ||
                COALESCE(l.locality_name         || ' ', ' ') ||
                COALESCE(s.state_abbreviation    || ' ', ' ') ||
                COALESCE(ad.postcode             || '', '')   AS full_address,
                ad.number_first, ad.number_first_suffix,
                ad.number_last,  ad.number_last_suffix,
                ad.flat_number,  ft.name AS flat_type,
                sl.street_name,  st.name AS street_type,
                l.locality_name, s.state_abbreviation,
                ad.postcode, ad.confidence,
                adg.latitude, adg.longitude, adg.geocode_type_code,
                ROUND(
                    (ST_Distance(
                        adg.geom::geography,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                    ) / 1000.0)::numeric,
                    2
                ) AS distance_km,
                TO_CHAR(gvl.purchase_price, 'FM$999,999,999') AS last_sold_price,
                TO_CHAR(gvl.contract_date,  'FMDD Month YYYY') AS last_sale_date
            FROM gnaf.address_default_geocode adg
            INNER JOIN gnaf.address_detail ad  ON ad.address_detail_pid   = adg.address_detail_pid
            LEFT  JOIN gnaf.flat_type_aut ft   ON ad.flat_type_code        = ft.code
            LEFT  JOIN gnaf.street_locality sl ON ad.street_locality_pid   = sl.street_locality_pid
            LEFT  JOIN gnaf.street_type_aut st ON sl.street_type_code      = st.code
            LEFT  JOIN gnaf.locality l         ON ad.locality_pid          = l.locality_pid
            LEFT  JOIN gnaf.state s            ON l.state_pid              = s.state_pid
            LEFT  JOIN public.gnaf_vg_sale_link gvl ON gvl.address_detail_pid = ad.address_detail_pid
            WHERE adg.geom IS NOT NULL
              AND ST_DWithin(
                  adg.geom,
                  ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                  0.045
              )
            {additional_where}
            ORDER BY adg.geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
            LIMIT %s OFFSET %s
        """
        query_params = [school_lng, school_lat, school_lng, school_lat] + filter_params + \
                       [school_lng, school_lat, limit, offset]
        cur.execute(query, query_params)
        addresses = cur.fetchall()

        filtered = sorted(
            [a for a in addresses if a['distance_km'] <= 5.0],
            key=lambda x: x['distance_km'],
        )

        count_sql = f"""
            SELECT COUNT(DISTINCT ad.address_detail_pid) AS total
            FROM gnaf.address_default_geocode adg
            INNER JOIN gnaf.address_detail ad  ON ad.address_detail_pid = adg.address_detail_pid
            LEFT  JOIN gnaf.street_locality sl ON ad.street_locality_pid = sl.street_locality_pid
            LEFT  JOIN gnaf.locality l         ON ad.locality_pid = l.locality_pid
            LEFT  JOIN gnaf.state s            ON l.state_pid = s.state_pid
            WHERE adg.geom IS NOT NULL
              AND ST_DWithin(adg.geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326), 0.045)
            {additional_where}
        """
        cur.execute(count_sql, [school_lng, school_lat] + filter_params)
        total = (cur.fetchone() or {}).get('total', len(filtered))

    return {
        'addresses':   [dict(a) for a in filtered],
        'total_count': total,
        'limit':       limit,
        'offset':      offset,
    }


def autocomplete_australia_school_streets(conn, acara_sml_id: int, query: str) -> list:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT latitude, longitude FROM gnaf.school_geometry WHERE acara_sml_id = %s",
            (acara_sml_id,),
        )
        school = cur.fetchone()
        if not school or school['latitude'] is None or school['longitude'] is None:
            return []

        off = 0.045
        lat, lng = float(school['latitude']), float(school['longitude'])
        cur.execute(
            """
            SELECT DISTINCT sl.street_name, st.name AS street_type
            FROM gnaf.address_detail ad
            INNER JOIN gnaf.address_default_geocode adg ON ad.address_detail_pid = adg.address_detail_pid
            INNER JOIN gnaf.street_locality sl          ON ad.street_locality_pid = sl.street_locality_pid
            LEFT  JOIN gnaf.street_type_aut st          ON sl.street_type_code    = st.code
            WHERE adg.latitude  IS NOT NULL
              AND adg.longitude IS NOT NULL
              AND adg.latitude  BETWEEN %s AND %s
              AND adg.longitude BETWEEN %s AND %s
              AND sl.street_name ILIKE %s
            ORDER BY sl.street_name LIMIT 20
            """,
            (lat - off, lat + off, lng - off, lng + off, query + '%'),
        )
        return [
            dict(r) for r in cur.fetchall()
            if not is_coordinate_like(r.get('street_name', ''))
        ]


def autocomplete_australia_school_suburbs(conn, acara_sml_id: int, query: str) -> list:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT latitude, longitude FROM gnaf.school_geometry WHERE acara_sml_id = %s",
            (acara_sml_id,),
        )
        school = cur.fetchone()
        if not school or school['latitude'] is None or school['longitude'] is None:
            return []

        off = 0.045
        lat, lng = float(school['latitude']), float(school['longitude'])
        cur.execute(
            """
            SELECT DISTINCT l.locality_name, ad.postcode, s.state_abbreviation
            FROM gnaf.address_detail ad
            INNER JOIN gnaf.address_default_geocode adg ON ad.address_detail_pid = adg.address_detail_pid
            INNER JOIN gnaf.locality l                  ON ad.locality_pid        = l.locality_pid
            LEFT  JOIN gnaf.state s                     ON l.state_pid            = s.state_pid
            WHERE adg.latitude  IS NOT NULL
              AND adg.longitude IS NOT NULL
              AND adg.latitude  BETWEEN %s AND %s
              AND adg.longitude BETWEEN %s AND %s
              AND l.locality_name ILIKE %s
            ORDER BY l.locality_name LIMIT 20
            """,
            (lat - off, lat + off, lng - off, lng + off, query + '%'),
        )
        return [
            {'suburb': r['locality_name'], 'postcode': r.get('postcode')}
            for r in cur.fetchall()
        ]


def autocomplete_australia_school_postcodes(conn, acara_sml_id: int, query: str) -> list:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT latitude, longitude FROM gnaf.school_geometry WHERE acara_sml_id = %s",
            (acara_sml_id,),
        )
        school = cur.fetchone()
        if not school or school['latitude'] is None or school['longitude'] is None:
            return []

        off = 0.045
        lat, lng = float(school['latitude']), float(school['longitude'])
        cur.execute(
            """
            SELECT DISTINCT ad.postcode, l.locality_name AS suburb
            FROM gnaf.address_detail ad
            INNER JOIN gnaf.address_default_geocode adg ON ad.address_detail_pid = adg.address_detail_pid
            LEFT  JOIN gnaf.locality l                  ON ad.locality_pid        = l.locality_pid
            WHERE adg.latitude  IS NOT NULL
              AND adg.longitude IS NOT NULL
              AND adg.latitude  BETWEEN %s AND %s
              AND adg.longitude BETWEEN %s AND %s
              AND ad.postcode ILIKE %s
            ORDER BY ad.postcode LIMIT 20
            """,
            (lat - off, lat + off, lng - off, lng + off, query + '%'),
        )
        return [dict(r) for r in cur.fetchall()]
