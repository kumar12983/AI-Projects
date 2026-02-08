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

print("\n" + "=" * 100)
print("INDEXES ON gnaf.address_default_geocode")
print("=" * 100)

# Query 1: Using pg_indexes view (simplest)
cur.execute("""
    SELECT 
        indexname,
        indexdef
    FROM pg_indexes
    WHERE schemaname = 'gnaf'
    AND tablename = 'address_default_geocode'
    ORDER BY indexname
""")

indexes = cur.fetchall()

if indexes:
    for idx in indexes:
        print(f"\nIndex: {idx['indexname']}")
        print(f"Definition: {idx['indexdef']}")
else:
    print("No indexes found")

# Query 2: Get index sizes
print("\n" + "=" * 100)
print("INDEX SIZES")
print("=" * 100)

cur.execute("""
    SELECT 
        indexname,
        pg_size_pretty(pg_relation_size(schemaname||'.'||indexname)) as size
    FROM pg_indexes
    WHERE schemaname = 'gnaf'
    AND tablename = 'address_default_geocode'
    ORDER BY pg_relation_size(schemaname||'.'||indexname) DESC
""")

sizes = cur.fetchall()
for s in sizes:
    print(f"{s['indexname']:<50} {s['size']:>10}")

# Query 3: Get detailed index information
print("\n" + "=" * 100)
print("DETAILED INDEX INFORMATION")
print("=" * 100)

cur.execute("""
    SELECT 
        i.relname as index_name,
        am.amname as index_type,
        pg_size_pretty(pg_relation_size(i.oid)) as index_size,
        idx.indisunique as is_unique,
        idx.indisprimary as is_primary
    FROM pg_class t
    JOIN pg_index idx ON t.oid = idx.indrelid
    JOIN pg_class i ON i.oid = idx.indexrelid
    JOIN pg_am am ON i.relam = am.oid
    JOIN pg_namespace n ON n.oid = t.relnamespace
    WHERE t.relname = 'address_default_geocode'
    AND n.nspname = 'gnaf'
    ORDER BY i.relname
""")

details = cur.fetchall()
print(f"\n{'Index Name':<50} {'Type':<10} {'Size':<10} {'Unique':<8} {'Primary':<8}")
print("-" * 95)
for d in details:
    print(f"{d['index_name']:<50} {d['index_type']:<10} {d['index_size']:<10} {str(d['is_unique']):<8} {str(d['is_primary']):<8}")

c.close()

print("\n" + "=" * 100)
