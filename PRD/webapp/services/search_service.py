"""
Search service — all SQL for suburb/postcode/street/address search.
Each function accepts a live psycopg2 connection and returns plain Python
dicts/lists so blueprints stay free of SQL.
"""
import re

from psycopg2.extras import RealDictCursor

from db_utils import _STREET_TYPE_TO_CODE


# ---------------------------------------------------------------------------
# Suburb / postcode lookups
# ---------------------------------------------------------------------------

def search_suburbs_by_postcode(conn, postcode: str) -> list:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT DISTINCT
                locality_name AS suburb,
                postcode,
                state_name    AS state,
                0             AS address_count
            FROM gnaf.suburb_postcode
            WHERE postcode = %s
            ORDER BY locality_name
            """,
            (postcode,),
        )
        return cur.fetchall()


def search_postcodes_by_suburb(conn, suburb: str) -> list:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT DISTINCT
                locality_name AS suburb,
                postcode,
                state_name    AS state,
                0             AS address_count
            FROM gnaf.suburb_postcode
            WHERE UPPER(locality_name) LIKE UPPER(%s)
            ORDER BY locality_name, postcode
            LIMIT 50
            """,
            ('%' + suburb + '%',),
        )
        return cur.fetchall()


def autocomplete_suburbs(conn, query: str) -> list:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT DISTINCT
                locality_name AS suburb,
                postcode,
                state_name    AS state
            FROM gnaf.suburb_postcode
            WHERE UPPER(locality_name) LIKE UPPER(%s)
            ORDER BY locality_name
            LIMIT 20
            """,
            (query + '%',),
        )
        return cur.fetchall()


def autocomplete_streets(conn, query: str) -> list:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT DISTINCT
                sl.street_name,
                st.name AS street_type
            FROM gnaf.street_locality sl
            LEFT JOIN gnaf.street_type_aut st ON sl.street_type_code = st.code
            WHERE sl.date_retired IS NULL
              AND UPPER(sl.street_name) LIKE UPPER(%s)
            ORDER BY sl.street_name
            LIMIT 20
            """,
            (query + '%',),
        )
        return cur.fetchall()


def autocomplete_full_address(conn, query: str, state: str = '') -> list:
    """
    Full-address autocomplete using gnaf.address_full_text.
    Requires at least one text anchor token (>=3 chars) or a state filter.
    """
    tokens = query.upper().split()
    where_parts = []
    exec_params: list = []
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
        return []

    state_filter = ''
    if state:
        state_filter = 'AND state = %s'
        exec_params.append(state)
        has_text_anchor = True

    if not has_text_anchor:
        return []

    sql = f"""
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
        WHERE {' AND '.join(where_parts)}
        {state_filter}
        ORDER BY full_address
        LIMIT 15
    """

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, exec_params)
        return [dict(r) for r in cur.fetchall()]


def search_address(conn, street_number: str = '', street: str = '',
                   suburb: str = '', postcode: str = '', state: str = '',
                   limit: int = 100) -> list:
    """Multi-filter address search with property sale data."""
    sql = """
        SELECT DISTINCT ON (ad.address_detail_pid)
            ad.address_detail_pid,
            ad.building_name,
            ad.number_first,
            ad.number_first_suffix,
            ad.number_last,
            ad.number_last_suffix,
            ad.flat_number,
            ad.confidence,
            ft.name AS flat_type,
            CONCAT_WS(' ',
                ft.name, ad.flat_number,
                CONCAT(ad.number_first, COALESCE(ad.number_first_suffix, '')),
                CASE WHEN ad.number_last IS NOT NULL
                     THEN CONCAT('-', ad.number_last, COALESCE(ad.number_last_suffix, ''))
                END
            ) AS street_number,
            sl.street_name,
            st.name AS street_type,
            l.locality_name AS suburb,
            s.state_abbreviation AS state,
            ad.postcode,
            adg.latitude,
            adg.longitude,
            adg.geocode_type_code,
            TO_CHAR(gvl.purchase_price, 'FM$999,999,999') AS last_sold_price,
            TO_CHAR(gvl.contract_date,  'FMDD Month YYYY') AS last_sale_date
        FROM gnaf.address_detail ad
        LEFT JOIN gnaf.flat_type_aut ft       ON ad.flat_type_code = ft.code
        LEFT JOIN gnaf.street_locality sl     ON ad.street_locality_pid = sl.street_locality_pid
        LEFT JOIN gnaf.street_type_aut st     ON sl.street_type_code = st.code
        LEFT JOIN gnaf.locality l             ON ad.locality_pid = l.locality_pid
        LEFT JOIN gnaf.state s                ON l.state_pid = s.state_pid
        LEFT JOIN gnaf.address_default_geocode adg ON ad.address_detail_pid = adg.address_detail_pid
        LEFT JOIN public.gnaf_vg_sale_link gvl ON gvl.address_detail_pid = ad.address_detail_pid
        WHERE ad.date_retired IS NULL
    """
    params: list = []

    if street_number:
        m = re.match(r'^(\d+)([A-Za-z]*)$', street_number.strip())
        if m:
            num    = int(m.group(1))
            suffix = m.group(2).upper()
            if suffix:
                sql += " AND ad.number_first = %s AND UPPER(COALESCE(ad.number_first_suffix, '')) = %s"
                params.extend([num, suffix])
            else:
                sql += " AND ad.number_first = %s"
                params.append(num)
        else:
            sql += " AND CAST(ad.number_first AS TEXT) LIKE %s"
            params.append('%' + street_number + '%')

    if street:
        parts  = street.upper().split()
        last   = parts[-1] if parts else ''
        gnaf_t = _STREET_TYPE_TO_CODE.get(last)
        if gnaf_t and len(parts) > 1:
            name_part = ' '.join(parts[:-1])
            sql += " AND UPPER(sl.street_name) LIKE UPPER(%s) AND UPPER(sl.street_type_code) = %s"
            params.extend(['%' + name_part + '%', gnaf_t])
        else:
            sql += " AND UPPER(sl.street_name) LIKE UPPER(%s)"
            params.append('%' + street + '%')

    if suburb:
        sql += " AND UPPER(l.locality_name) LIKE UPPER(%s)"
        params.append('%' + suburb + '%')

    if postcode:
        sql += " AND ad.postcode = %s"
        params.append(postcode)

    if state:
        sql += " AND s.state_abbreviation = %s"
        params.append(state)

    sql += " ORDER BY ad.address_detail_pid, l.locality_name, sl.street_name, ad.number_first LIMIT %s"
    params.append(limit)

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_schools_for_address(conn, lat: float, lng: float, state: str = 'NSW') -> list:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
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
            """,
            (state, lng, lat),
        )
        return cur.fetchall()


def get_statistics(conn) -> dict:
    stats: dict = {}
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM gnaf.stats_summary")
        summary = cur.fetchone()
        if summary:
            stats['total_localities'] = summary['total_localities']
            stats['total_addresses']  = summary['total_addresses']
            stats['total_streets']    = summary['total_streets']
            stats['last_refreshed']   = (
                summary['last_refreshed'].isoformat() if summary.get('last_refreshed') else None
            )
        else:
            stats.update({'total_localities': 0, 'total_addresses': 0, 'total_streets': 0})

        cur.execute("SELECT * FROM gnaf.stats_by_state ORDER BY state_abbreviation")
        stats['localities_by_state'] = cur.fetchall()

    return stats


def get_suburbs_by_state(conn, state: str) -> list:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT DISTINCT
                locality_name AS suburb,
                postcode,
                state_name    AS state
            FROM gnaf.suburb_postcode
            WHERE state_name = %s
            ORDER BY locality_name, postcode
            """,
            (state,),
        )
        return cur.fetchall()
