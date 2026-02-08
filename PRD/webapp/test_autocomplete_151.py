"""
Test what happens when we search for '151' in street autocomplete
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    database=os.getenv('DB_NAME', 'gnaf_db'),
    user=os.getenv('DB_USER', 'postgres'),
    password=os.getenv('DB_PASSWORD', ''),
    port=int(os.getenv('DB_PORT', '5432'))
)

cur = conn.cursor(cursor_factory=RealDictCursor)

# Simulate the autocomplete query for school 41319 with query '151'
school_lat = -33.7811846
school_lng = 151.0423504
lat_offset = 0.045
lng_offset = 0.045
query = '151'

print(f"\n=== Testing Street Autocomplete ===")
print(f"School: 41319 (lat: {school_lat}, lng: {school_lng})")
print(f"Search query: '{query}'")
print(f"Bounding box: lat {school_lat-lat_offset} to {school_lat+lat_offset}")
print(f"              lng {school_lng-lng_offset} to {school_lng+lng_offset}\n")

cur.execute("""
    SELECT DISTINCT 
        sl.street_name,
        st.name as street_type,
        COUNT(*) OVER (PARTITION BY sl.street_name) as occurrence_count
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
      query + '%'))

results = cur.fetchall()

print(f"Results ({len(results)} streets starting with '{query}'):\n")
for r in results:
    street_full = f"{r['street_name']} {r['street_type']}" if r['street_type'] else r['street_name']
    print(f"  {street_full:50s} ({r['occurrence_count']} addresses)")

cur.close()
conn.close()
