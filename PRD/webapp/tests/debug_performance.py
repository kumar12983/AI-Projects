"""
Debug script to analyze the performance of the addresses endpoint
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
import time

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'gnaf_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
    'port': int(os.getenv('DB_PORT', '5432'))
}

def check_indexes():
    """Check what indexes exist on key tables"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    print("=" * 80)
    print("CHECKING SPATIAL INDEXES")
    print("=" * 80)
    
    cur.execute("""
        SELECT indexname, tablename, indexdef
        FROM pg_indexes
        WHERE schemaname = 'gnaf'
        AND (indexname LIKE '%geom%' OR indexname LIKE '%geocode%')
        ORDER BY tablename, indexname
    """)
    
    indexes = cur.fetchall()
    if indexes:
        for idx in indexes:
            print(f"\n{idx['tablename']}.{idx['indexname']}:")
            print(f"  {idx['indexdef']}")
    else:
        print("⚠ NO SPATIAL INDEXES FOUND!")
    
    print("\n" + "=" * 80)
    print("CHECKING REGULAR INDEXES ON KEY COLUMNS")
    print("=" * 80)
    
    cur.execute("""
        SELECT indexname, tablename
        FROM pg_indexes
        WHERE schemaname = 'gnaf'
        AND tablename IN ('address_detail', 'address_default_geocode')
        ORDER BY tablename, indexname
    """)
    
    indexes = cur.fetchall()
    for idx in indexes:
        print(f"  {idx['tablename']}.{idx['indexname']}")
    
    cur.close()
    conn.close()

def test_query_performance():
    """Test the actual query performance"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    print("\n" + "=" * 80)
    print("TESTING QUERY PERFORMANCE FOR SCHOOL 41811")
    print("=" * 80)
    
    # Get school location
    cur.execute("""
        SELECT latitude, longitude, geom_5km_buffer
        FROM gnaf.school_geometry
        WHERE acara_sml_id = 41811
        LIMIT 1
    """)
    school = cur.fetchone()
    
    if not school:
        print("❌ School 41811 not found!")
        cur.close()
        conn.close()
        return
    
    school_lat = float(school['latitude'])
    school_lng = float(school['longitude'])
    
    print(f"\nSchool location: {school_lat}, {school_lng}")
    
    # Test 1: Current query with ST_DWithin on geography (SLOW)
    print("\n--- Test 1: Current query with ST_DWithin on geography ---")
    query1 = """
        WITH school_point AS (
            SELECT ST_SetSRID(ST_MakePoint(%s, %s), 4326) as geom
        )
        SELECT COUNT(DISTINCT ad.address_detail_pid) as total
        FROM gnaf.address_detail ad
        CROSS JOIN school_point sp
        INNER JOIN gnaf.address_default_geocode adg
            ON ad.address_detail_pid = adg.address_detail_pid
        WHERE adg.latitude IS NOT NULL 
            AND adg.longitude IS NOT NULL
            AND ST_DWithin(
                sp.geom::geography,
                ST_SetSRID(ST_MakePoint(adg.longitude, adg.latitude), 4326)::geography,
                5000
            )
    """
    
    start = time.time()
    cur.execute(query1, (school_lng, school_lat))
    result = cur.fetchone()
    elapsed = time.time() - start
    
    print(f"Result: {result['total']:,} addresses")
    print(f"Time: {elapsed:.2f} seconds")
    
    # Test 2: Using geometry column directly if it exists
    print("\n--- Test 2: Testing with geometry column (if exists) ---")
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'gnaf'
        AND table_name = 'address_default_geocode'
        AND column_name = 'geom'
    """)
    
    has_geom = cur.fetchone()
    
    if has_geom:
        print("✓ Geometry column exists")
        
        query2 = """
            SELECT COUNT(DISTINCT ad.address_detail_pid) as total
            FROM gnaf.address_detail ad
            INNER JOIN gnaf.address_default_geocode adg
                ON ad.address_detail_pid = adg.address_detail_pid
            WHERE adg.geom IS NOT NULL
                AND ST_DWithin(
                    adg.geom::geography,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                    5000
                )
        """
        
        start = time.time()
        cur.execute(query2, (school_lng, school_lat))
        result = cur.fetchone()
        elapsed = time.time() - start
        
        print(f"Result: {result['total']:,} addresses")
        print(f"Time: {elapsed:.2f} seconds")
    else:
        print("⚠ No geometry column found on address_default_geocode")
    
    # Test 3: Using existing buffer from school_geometry
    print("\n--- Test 3: Using pre-computed 5km buffer from school_geometry ---")
    if school['geom_5km_buffer']:
        
        query3 = """
            SELECT COUNT(DISTINCT ad.address_detail_pid) as total
            FROM gnaf.address_detail ad
            INNER JOIN gnaf.address_default_geocode adg
                ON ad.address_detail_pid = adg.address_detail_pid
            WHERE adg.latitude IS NOT NULL
                AND adg.longitude IS NOT NULL
                AND ST_DWithin(
                    ST_GeomFromText(%s, 4326),
                    ST_SetSRID(ST_MakePoint(adg.longitude, adg.latitude), 4326),
                    0
                )
        """
        
        start = time.time()
        cur.execute(query3, (school['geom_5km_buffer'],))
        result = cur.fetchone()
        elapsed = time.time() - start
        
        print(f"Result: {result['total']:,} addresses")
        print(f"Time: {elapsed:.2f} seconds")
    else:
        print("⚠ No 5km buffer found for this school")
    
    cur.close()
    conn.close()

def analyze_query_plan():
    """Analyze the query execution plan"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    print("\n" + "=" * 80)
    print("QUERY EXECUTION PLAN")
    print("=" * 80)
    
    cur.execute("""
        SELECT latitude, longitude
        FROM gnaf.school_geometry
        WHERE acara_sml_id = 41811
        LIMIT 1
    """)
    school = cur.fetchone()
    
    if not school:
        print("❌ School 41811 not found!")
        cur.close()
        conn.close()
        return
    
    school_lat, school_lng = school
    
    query = """
        WITH school_point AS (
            SELECT ST_SetSRID(ST_MakePoint(%s, %s), 4326) as geom
        )
        SELECT ad.address_detail_pid
        FROM gnaf.address_detail ad
        CROSS JOIN school_point sp
        INNER JOIN gnaf.address_default_geocode adg
            ON ad.address_detail_pid = adg.address_detail_pid
        WHERE adg.latitude IS NOT NULL 
            AND adg.longitude IS NOT NULL
            AND ST_DWithin(
                sp.geom::geography,
                ST_SetSRID(ST_MakePoint(adg.longitude, adg.latitude), 4326)::geography,
                5000
            )
        LIMIT 100
    """
    
    cur.execute("EXPLAIN ANALYZE " + query, (school_lng, school_lat))
    
    print("\n")
    for row in cur.fetchall():
        print(row[0])
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_indexes()
    test_query_performance()
    analyze_query_plan()
