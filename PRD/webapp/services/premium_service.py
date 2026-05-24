"""
Premium feature service — CSV export and analytics.
"""
import csv
from io import StringIO

from psycopg2.extras import RealDictCursor


def export_suburbs_csv(conn, state: str = '') -> str:
    """Return CSV content as a string."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        sql    = "SELECT DISTINCT locality_name AS suburb, postcode, state_name AS state FROM gnaf.suburb_postcode"
        params: list = []
        if state:
            sql += " WHERE state_name = %s"
            params.append(state)
        sql += " ORDER BY state_name, locality_name, postcode"
        cur.execute(sql, params)
        results = cur.fetchall()

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=['suburb', 'postcode', 'state'])
    writer.writeheader()
    writer.writerows(results)
    return output.getvalue()


def get_premium_analytics(conn, suburb: str = '', postcode: str = '') -> dict:
    analytics = {
        'suburb':          suburb or 'Unknown',
        'postcode':        postcode or 'Unknown',
        'total_addresses': 0,
        'total_streets':   0,
        'premium_feature': True,
    }
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT COUNT(DISTINCT locality_name) AS suburb_count
            FROM gnaf.suburb_postcode
            WHERE (%s = '' OR UPPER(locality_name) = UPPER(%s))
              AND (%s = '' OR postcode = %s)
            """,
            (suburb, suburb, postcode, postcode),
        )
        result = cur.fetchone()
        analytics['matches'] = result['suburb_count'] if result else 0
    return analytics
