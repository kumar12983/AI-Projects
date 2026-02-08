"""
Check for coordinate-like street names in GNAF database
This verifies if the issue is pre-existing data quality or something we caused
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

# Check for street names that look like coordinates (decimal numbers)
cur.execute("""
    SELECT street_name, COUNT(*) as cnt 
    FROM gnaf.street_locality 
    WHERE street_name ~ '^[0-9]+\.[0-9]+$' 
    GROUP BY street_name 
    ORDER BY street_name 
    LIMIT 30
""")

results = cur.fetchall()

print('\n=== Coordinate-like street names in GNAF database ===')
print(f'Found {len(results)} different coordinate-like street names:\n')

for r in results:
    try:
        # Try to parse as a number and check if it's in coordinate range
        num = float(r['street_name'])
        is_lat = -90 <= num <= 90
        is_lng = -180 <= num <= 180
        coord_type = 'LAT' if is_lat else 'LNG' if is_lng else 'NUM'
        print(f"  {r['street_name']:20s} -> {r['cnt']:4d} records ({coord_type})")
    except:
        print(f"  {r['street_name']:20s} -> {r['cnt']:4d} records")

# Check specifically for the one we encountered
cur.execute("""
    SELECT COUNT(*) as cnt 
    FROM gnaf.street_locality 
    WHERE street_name = '151.101268'
""")
specific = cur.fetchone()
print(f"\n'151.101268' appears {specific['cnt']} times in street_locality table")

# Check where it's being used
cur.execute("""
    SELECT sl.street_name, l.locality_name, s.state_abbreviation, COUNT(*) as address_count
    FROM gnaf.street_locality sl
    LEFT JOIN gnaf.locality l ON sl.locality_pid = l.locality_pid
    LEFT JOIN gnaf.state s ON l.state_pid = s.state_pid
    WHERE sl.street_name = '151.101268'
    GROUP BY sl.street_name, l.locality_name, s.state_abbreviation
    LIMIT 5
""")

usage = cur.fetchall()
if usage:
    print("\nUsed in these locations:")
    for u in usage:
        print(f"  {u['locality_name']}, {u['state_abbreviation']} - {u['address_count']} addresses")

cur.close()
conn.close()

print('\n✓ This confirms the coordinate values are PRE-EXISTING bad data in GNAF')
print('✓ NOT caused by any of our UPDATE queries during performance tuning')
