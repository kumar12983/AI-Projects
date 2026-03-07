#!/usr/bin/env python3
"""
Test what happens when a school has multiple catchment geometries

Example: Richmond High School (VIC) has separate catchments for Year 7, 8, 9, 10, 11, 12
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'gnaf_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')


def test_multiple_geometries():
    """Test what happens with schools that have multiple catchment boundaries"""
    
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD
    )
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    print("=" * 80)
    print("Testing Multiple Geometries Per School")
    print("=" * 80)
    
    # Find schools with multiple geometries
    print("\n1. Schools with multiple catchment boundaries:")
    print("-" * 80)
    
    cursor.execute("""
        SELECT 
            school_id,
            school_name,
            state,
            COUNT(*) as geometry_count,
            STRING_AGG(DISTINCT school_type, ', ') as types,
            STRING_AGG(DISTINCT year_level_code, ', ' ORDER BY year_level_code) as year_levels
        FROM gnaf.school_catchments
        GROUP BY school_id, school_name, state
        HAVING COUNT(*) > 1
        ORDER BY COUNT(*) DESC
        LIMIT 10
    """)
    
    multi_schools = cursor.fetchall()
    
    for school in multi_schools:
        print(f"\n  School: {school['school_name']} ({school['state']})")
        print(f"    ID: {school['school_id']}")
        print(f"    Geometries: {school['geometry_count']}")
        print(f"    Types: {school['types']}")
        print(f"    Year Levels: {school['year_levels']}")
    
    if not multi_schools:
        print("\n  No schools with multiple geometries found")
        return
    
    # Test what happens with the boundary query (uses LIMIT 1)
    test_school = multi_schools[0]
    school_id = test_school['school_id']
    
    print("\n" + "=" * 80)
    print(f"2. Testing Boundary Query for: {test_school['school_name']}")
    print("=" * 80)
    
    # Simulate app.py boundary query (with LIMIT 1)
    cursor.execute("""
        SELECT 
            ST_AsGeoJSON(geometry) as geojson,
            school_name,
            school_type,
            year_level_code,
            catchment_id
        FROM gnaf.school_catchments
        WHERE school_id = %s
        LIMIT 1
    """, (school_id,))
    
    boundary = cursor.fetchone()
    print(f"\n  Query with LIMIT 1 returns:")
    print(f"    Catchment ID: {boundary['catchment_id']}")
    print(f"    Type: {boundary['school_type']}")
    print(f"    Year Level: {boundary['year_level_code']}")
    print(f"    ⚠️  Only ONE geometry returned (may miss other year levels!)")
    
    # Show what's missing
    print(f"\n  ALL geometries for this school:")
    cursor.execute("""
        SELECT catchment_id, school_type, year_level_code,
               ROUND((ST_Area(geometry::geography) / 1000000)::numeric, 2) as area_km2
        FROM gnaf.school_catchments
        WHERE school_id = %s
        ORDER BY year_level_code
    """, (school_id,))
    
    all_boundaries = cursor.fetchall()
    for b in all_boundaries:
        print(f"    - {b['school_type']}, Year {b['year_level_code']}, "
              f"Catchment ID: {b['catchment_id']}, Area: {b['area_km2']} km²")
    
    # Test address lookup query
    print("\n" + "=" * 80)
    print("3. Testing Address Lookup Query (CTE without LIMIT)")
    print("=" * 80)
    
    # This simulates the CTE in get_school_addresses
    cursor.execute("""
        WITH school_catchment AS (
            SELECT geometry FROM gnaf.school_catchments WHERE school_id = %s
        )
        SELECT COUNT(*) as geometry_count FROM school_catchment
    """, (school_id,))
    
    cte_result = cursor.fetchone()
    print(f"\n  CTE returns {cte_result['geometry_count']} geometry rows")
    
    if cte_result['geometry_count'] > 1:
        print(f"  ⚠️  WARNING: ST_Contains will be checked against EACH geometry!")
        print(f"     An address could match multiple catchments for the same school")
        print(f"     causing duplicate addresses in results")
    
    # Test with a real address
    print("\n" + "=" * 80)
    print("4. Testing Address Search with Multiple Geometries")
    print("=" * 80)
    
    # Get an address in this school's catchment
    cursor.execute("""
        SELECT DISTINCT
            ad.address_detail_pid,
            CONCAT_WS(' ',
                ad.number_first,
                sl.street_name,
                l.locality_name
            ) as address,
            COUNT(*) OVER (PARTITION BY ad.address_detail_pid) as match_count
        FROM gnaf.address_detail ad
        JOIN gnaf.address_default_geocode agc ON ad.address_detail_pid = agc.address_detail_pid
        JOIN gnaf.street_locality sl ON ad.street_locality_pid = sl.street_locality_pid
        JOIN gnaf.locality l ON ad.locality_pid = l.locality_pid
        CROSS JOIN gnaf.school_catchments sc
        WHERE sc.school_id = %s
        AND ad.date_retired IS NULL
        AND agc.geom IS NOT NULL
        AND ST_Contains(sc.geometry, agc.geom)
        LIMIT 5
    """, (school_id,))
    
    test_addresses = cursor.fetchall()
    
    if test_addresses:
        print(f"\n  Sample addresses in catchment:")
        for addr in test_addresses:
            print(f"    {addr['address']}")
            if addr['match_count'] > 1:
                print(f"      ⚠️  Matches {addr['match_count']} catchment boundaries (DUPLICATE!)")
    else:
        print("\n  No addresses found in catchment")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("""
  When a school has multiple geometries (e.g., different year levels):
  
  1. Boundary Query (/api/school/<id>/boundary):
     - Uses LIMIT 1 → Returns only ONE geometry
     - May miss other year level catchments
     - PROBLEM: Incomplete boundary display
  
  2. Address Query (/api/school/<id>/addresses):
     - CTE returns ALL geometries for school_id
     - ST_Contains checks against EACH geometry
     - PROBLEM: Same address may appear MULTIPLE times (once per matching geometry)
  
  3. Materialized View (public.school_catchment_addresses):
     - CROSS JOIN with all geometries
     - One address can match multiple geometries
     - Uses DISTINCT ON (address_detail_pid, school_id)
     - SOLUTION: Deduplicates at the (address, school) level
     
  RECOMMENDATION:
  - For boundary queries: Use ST_Union to merge all geometries
  - For address queries: Add DISTINCT ON or only select one geometry per school
    """)


if __name__ == '__main__':
    test_multiple_geometries()
