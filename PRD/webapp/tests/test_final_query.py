"""
Test the FINAL optimized query with the new GIST spatial index
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

def test_final_optimized_query():
    """Test the final optimized query with spatial index"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    acara_sml_id = 41811
    cur.execute("""
        SELECT latitude, longitude
        FROM gnaf.school_geometry
        WHERE acara_sml_id = %s
        LIMIT 1
    """, (acara_sml_id,))
    
    school = cur.fetchone()
    school_lat = float(school['latitude'])
    school_lng = float(school['longitude'])
    
    print("=" * 80)
    print(f"TESTING FINAL OPTIMIZED QUERY FOR SCHOOL {acara_sml_id}")
    print(f"School location: {school_lat}, {school_lng}")
    print("=" * 80)
    
    limit = 100
    offset = 0
    
    # Final optimized query using geom column with GIST index
    query = """
        SELECT
            ad.address_detail_pid as gnaf_id,
            COALESCE(ad.number_first_prefix || '', '') ||
            COALESCE(ad.number_first::text || '', '') ||
            COALESCE(ad.number_first_suffix || ' ', ' ') ||
            COALESCE(sl.street_name || ' ', '') ||
            COALESCE(st.name || ', ', ', ') ||
            COALESCE(l.locality_name || ' ', ' ') ||
            COALESCE(s.state_abbreviation || ' ', ' ') ||
            COALESCE(ad.postcode || '', '') AS full_address,
            ad.number_first,
            ad.number_first_suffix,
            ad.number_last,
            ad.number_last_suffix,
            ad.flat_number,
            ft.name as flat_type,
            sl.street_name,
            st.name as street_type,
            l.locality_name,
            s.state_abbreviation,
            ad.postcode,
            ad.confidence,
            adg.latitude,
            adg.longitude,
            adg.geocode_type_code,
            ROUND(
                (ST_Distance(
                    adg.geom::geography,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                ) / 1000.0)::numeric,
                2
            ) as distance_km
        FROM gnaf.address_default_geocode adg
        INNER JOIN gnaf.address_detail ad
            ON ad.address_detail_pid = adg.address_detail_pid
        LEFT JOIN gnaf.flat_type_aut ft
            ON ad.flat_type_code = ft.code
        LEFT JOIN gnaf.street_locality sl
            ON ad.street_locality_pid = sl.street_locality_pid
        LEFT JOIN gnaf.street_type_aut st
            ON sl.street_type_code = st.code
        LEFT JOIN gnaf.locality l
            ON ad.locality_pid = l.locality_pid
        LEFT JOIN gnaf.state s
            ON l.state_pid = s.state_pid
        WHERE adg.geom IS NOT NULL
            AND ST_DWithin(
                adg.geom,
                ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                0.045
            )
        ORDER BY 
            adg.geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
        LIMIT %s OFFSET %s
    """
    
    query_params = [
        school_lng, school_lat,  # for distance calculation
        school_lng, school_lat,  # for ST_DWithin
        school_lng, school_lat,  # for KNN ordering
        limit, offset
    ]
    
    print("\n--- Running FINAL optimized query (with GIST index) ---")
    start = time.time()
    cur.execute(query, query_params)
    addresses = cur.fetchall()
    elapsed = time.time() - start
    
    # Filter to exact 5km
    filtered = [addr for addr in addresses if addr['distance_km'] <= 5.0]
    
    print(f"✓ Query executed in {elapsed:.2f} seconds")
    print(f"✓ Retrieved {len(addresses)} addresses")
    print(f"✓ {len(filtered)} addresses within exact 5km")
    
    if filtered:
        print(f"\nFirst 5 addresses:")
        for i, addr in enumerate(filtered[:5], 1):
            print(f"  {i}. {addr['full_address']}")
            print(f"     Distance: {addr['distance_km']} km")
    
    # Test count query
    print("\n--- Testing count query ---")
    count_query = """
        SELECT COUNT(DISTINCT ad.address_detail_pid) as total
        FROM gnaf.address_default_geocode adg
        INNER JOIN gnaf.address_detail ad
            ON ad.address_detail_pid = adg.address_detail_pid
        WHERE adg.geom IS NOT NULL
            AND ST_DWithin(
                adg.geom,
                ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                0.045
            )
    """
    
    count_params = [school_lng, school_lat]
    
    start = time.time()
    cur.execute(count_query, count_params)
    result = cur.fetchone()
    count_elapsed = time.time() - start
    
    print(f"✓ Count query executed in {count_elapsed:.2f} seconds")
    print(f"✓ Total addresses in 5km zone: {result['total']:,}")
    
    cur.close()
    conn.close()
    
    print("\n" + "=" * 80)
    print("PERFORMANCE COMPARISON")
    print("=" * 80)
    print(f"OLD QUERY (no spatial index):  ~31.00 seconds")
    print(f"OPTIMIZED (before index):      ~6.64 seconds")
    print(f"FINAL (with GIST index):       ~{elapsed:.2f} seconds")
    print(f"\nSPEEDUP: {31/elapsed:.1f}x faster than original!")
    print(f"IMPROVEMENT: {((31-elapsed)/31)*100:.1f}% faster")
    
    if elapsed < 2.0:
        print("\n✓ EXCELLENT! Query is now under 2 seconds!")
    elif elapsed < 5.0:
        print("\n✓ GOOD! Query performance is acceptable.")
    else:
        print("\n⚠ Still slower than ideal, but much improved.")

if __name__ == "__main__":
    test_final_optimized_query()
