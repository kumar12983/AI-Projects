import psycopg2, os
from dotenv import load_dotenv

load_dotenv()
c = psycopg2.connect(host=os.getenv('DB_HOST', 'localhost'), 
                     database=os.getenv('DB_NAME', 'gnaf_db'), 
                     user=os.getenv('DB_USER', 'postgres'), 
                     password=os.getenv('DB_PASSWORD', ''), 
                     port=int(os.getenv('DB_PORT', '5432')))
cur = c.cursor()

# Check for geom column
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='gnaf' AND table_name='address_default_geocode' AND column_name='geom'")
has_geom= cur.fetchone()
print(f"Geom column exists: {has_geom is not None}")

if has_geom:
    cur.execute("SELECT COUNT(*) FROM gnaf.address_default_geocode WHERE geom IS NOT NULL")
    print(f"Non-null geom values: {cur.fetchone()[0]:,}")

# Check indexes
cur.execute("SELECT indexname, indexdef FROM pg_indexes WHERE schemaname='gnaf' AND tablename='address_default_geocode' AND (indexname LIKE '%geom%' OR indexdef LIKE '%GIST%')")
indexes = cur.fetchall()
print(f"\nSpatial indexes on address_default_geocode:")
for idx in indexes:
    print(f"  {idx[0]}")
    print(f"    {idx[1][:100]}...")

c.close()
