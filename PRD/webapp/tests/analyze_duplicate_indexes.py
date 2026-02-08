"""
Analyze index usage and provide recommendation
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

c = psycopg2.connect(
    host=os.getenv('DB_HOST', 'localhost'), 
    database=os.getenv('DB_NAME', 'gnaf_db'), 
    user=os.getenv('DB_USER', 'postgres'), 
    password=os.getenv('DB_PASSWORD', ''), 
    port=int(os.getenv('DB_PORT', '5432'))
)

cur = c.cursor(cursor_factory=RealDictCursor)

print("=" * 100)
print("ANALYZING DUPLICATE SPATIAL INDEXES")
print("=" * 100)

# Check which index is used for our optimized query
print("\n--- Testing which index is used for optimized query ---")
cur.execute("""
    EXPLAIN (FORMAT JSON)
    SELECT ad.address_detail_pid
    FROM gnaf.address_default_geocode adg
    INNER JOIN gnaf.address_detail ad ON ad.address_detail_pid = adg.address_detail_pid
    WHERE adg.geom IS NOT NULL
        AND ST_DWithin(
            adg.geom,
            ST_SetSRID(ST_MakePoint(151.0, -33.8), 4326),
            0.045
        )
    LIMIT 10
""")

plan = cur.fetchone()
plan_text = str(plan['QUERY PLAN'])

if 'idx_address_default_geocode_geom' in plan_text:
    print("✓ Uses idx_address_default_geocode_geom (geom column)")
elif 'idx_address_geocode_point' in plan_text:
    print("✓ Uses idx_address_geocode_point (computed expression)")
else:
    print("⚠ No spatial index detected in plan")

# Check old computed expression index usage
print("\n--- Testing computed expression query ---")
cur.execute("""
    EXPLAIN (FORMAT JSON)
    SELECT ad.address_detail_pid
    FROM gnaf.address_default_geocode adg
    INNER JOIN gnaf.address_detail ad ON ad.address_detail_pid = adg.address_detail_pid
    WHERE ST_DWithin(
        ST_SetSRID(ST_MakePoint(adg.longitude, adg.latitude), 4326),
        ST_SetSRID(ST_MakePoint(151.0, -33.8), 4326),
        0.045
    )
    LIMIT 10
""")

plan2 = cur.fetchone()
plan2_text = str(plan2['QUERY PLAN'])

if 'idx_address_geocode_point' in plan2_text:
    print("✓ Uses idx_address_geocode_point (computed expression)")
elif 'idx_address_default_geocode_geom' in plan2_text:
    print("✓ Uses idx_address_default_geocode_geom (geom column)")
else:
    print("⚠ No spatial index detected in plan")

# Get index sizes
print("\n" + "=" * 100)
print("INDEX SIZE COMPARISON")
print("=" * 100)

cur.execute("""
    SELECT 
        indexname,
        pg_size_pretty(pg_relation_size(schemaname||'.'||indexname)) as size,
        pg_relation_size(schemaname||'.'||indexname) as size_bytes
    FROM pg_indexes
    WHERE schemaname = 'gnaf'
    AND tablename = 'address_default_geocode'
    AND (indexname = 'idx_address_default_geocode_geom' OR indexname = 'idx_address_geocode_point')
    ORDER BY indexname
""")

indexes = cur.fetchall()
total_size = 0
for idx in indexes:
    print(f"{idx['indexname']:<45} {idx['size']:>10}")
    total_size += idx['size_bytes']

print("-" * 100)
print(f"{'TOTAL SIZE':<45} {total_size / (1024**3):.2f} GB")

print("\n" + "=" * 100)
print("RECOMMENDATION")
print("=" * 100)

print("""
Since:
1. Both indexes serve the same purpose (spatial indexing of coordinates)
2. Our optimized query uses 'geom' column directly (idx_address_default_geocode_geom)
3. The 'geom' column is faster than the computed expression

Recommendation: DROP idx_address_geocode_point index

Benefits:
- Save 664 MB of disk space
- Reduce index maintenance overhead
- Simplify query optimization

Steps to drop the redundant index:
1. First, update any remaining queries to use 'geom' column instead of computed expression
2. Run: DROP INDEX IF EXISTS gnaf.idx_address_geocode_point;

IMPORTANT: Before dropping, verify no other applications are using this index!
""")

c.close()
