"""
Drop the redundant idx_address_geocode_point index to save 664 MB
All queries have been updated to use the geom column instead
"""
import psycopg2
import os
import time
from dotenv import load_dotenv

load_dotenv()

c = psycopg2.connect(
    host=os.getenv('DB_HOST', 'localhost'), 
    database=os.getenv('DB_NAME', 'gnaf_db'), 
    user=os.getenv('DB_USER', 'postgres'), 
    password=os.getenv('DB_PASSWORD', ''), 
    port=int(os.getenv('DB_PORT', '5432'))
)

# Need autocommit for DROP INDEX CONCURRENTLY
c.set_session(autocommit=True)
cur = c.cursor()

print("=" * 100)
print("DROPPING REDUNDANT SPATIAL INDEX")
print("=" * 100)

# Check current size before dropping
cur.execute("""
    SELECT pg_size_pretty(pg_relation_size('gnaf.idx_address_geocode_point')) as size
""")
size_result = cur.fetchone()
old_size = size_result[0] if size_result else "Unknown"

print(f"\nCurrent idx_address_geocode_point size: {old_size}")
print("\nThis index is redundant because:")
print("  1. We have idx_address_default_geocode_geom on the geom column")
print("  2. All queries have been updated to use geom instead of computed expressions")
print("  3. The geom column index is faster")
print("\nDropping the index will:")
print(f"  ✓ Free up {old_size} of disk space")
print("  ✓ Reduce index maintenance overhead during INSERT/UPDATE operations")
print("  ✓ Simplify query optimization")

print("\n" + "-" * 100)
input("Press ENTER to proceed with dropping the index, or Ctrl+C to cancel...")
print("-" * 100)

print("\nDropping idx_address_geocode_point...")
print("Using CONCURRENTLY to avoid locking the table...")

start = time.time()

try:
    cur.execute('DROP INDEX CONCURRENTLY IF EXISTS gnaf.idx_address_geocode_point')
    elapsed = time.time() - start
    print(f"\n✓ Index dropped successfully in {elapsed:.1f} seconds")
    print(f"✓ Freed up {old_size} of disk space")
    
except Exception as e:
    print(f"\n✗ Error dropping index: {e}")
    print("The index may not exist or there may be a permission issue.")

# Verify the index is gone
print("\n" + "=" * 100)
print("VERIFICATION")
print("=" * 100)

cur.execute("""
    SELECT indexname, pg_size_pretty(pg_relation_size(schemaname||'.'||indexname)) as size
    FROM pg_indexes
    WHERE schemaname = 'gnaf'
    AND tablename = 'address_default_geocode'
    AND (indexname LIKE '%geom%' OR indexname LIKE '%point%')
    ORDER BY indexname
""")

remaining = cur.fetchall()
print(f"\nRemaining spatial indexes on address_default_geocode:")
if remaining:
    for idx in remaining:
        print(f"  ✓ {idx[0]}: {idx[1]}")
else:
    print("  (none - unexpected!)")

# Check total space used by all indexes on the table
cur.execute("""
    SELECT 
        pg_size_pretty(SUM(pg_relation_size(schemaname||'.'||indexname))) as total_index_size
    FROM pg_indexes
    WHERE schemaname = 'gnaf'
    AND tablename = 'address_default_geocode'
""")

total = cur.fetchone()
if total:
    print(f"\nTotal index size for address_default_geocode: {total[0]}")

c.close()

print("\n" + "=" * 100)
print("INDEX CLEANUP COMPLETE")
print("=" * 100)
print("\nThe database is now optimized with no redundant spatial indexes!")
