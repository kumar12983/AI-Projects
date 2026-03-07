"""Verify Victoria data loaded successfully"""
import psycopg2
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv(Path(__file__).parent.parent / 'webapp' / '.env')
load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'gnaf_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
    'port': int(os.getenv('DB_PORT', '5432'))
}

conn = None
cursor = None

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("=" * 70)
    print("Victoria Data Verification")
    print("=" * 70)
    
    # Query: Count by state and school type
    print("\nRecords by state and school type:")
    cursor.execute("""
        SELECT state, school_type, COUNT(*) as count
        FROM gnaf.school_catchments
        GROUP BY state, school_type
        ORDER BY state, school_type;
    """)
    
    results = cursor.fetchall()
    for row in results:
        print(f"  {row[0]:3s} | {row[1]:20s} | {row[2]:5d} catchments")
    
    # Total counts
    print("\nTotal counts by state:")
    cursor.execute("""
        SELECT state, COUNT(*) as count
        FROM gnaf.school_catchments
        GROUP BY state
        ORDER BY state;
    """)
    
    results = cursor.fetchall()
    for row in results:
        print(f"  {row[0]:3s}: {row[1]:,} catchments")
    
    # Sample Victoria records
    print("\nSample Victoria primary schools:")
    cursor.execute("""
        SELECT school_name, campus_name, year_level_code, 
               ROUND((ST_Area(geometry::geography) / 1000000)::numeric, 2) as area_km2
        FROM gnaf.school_catchments
        WHERE state = 'VIC' AND school_type = 'PRIMARY'
        LIMIT 5;
    """)
    
    results = cursor.fetchall()
    for row in results:
        print(f"  {row[0]}")
        print(f"    Campus: {row[1]}")
        print(f"    Year Level: {row[2]}, Area: {row[3]} km²")
    
    # Sample Victoria secondary schools
    print("\nSample Victoria secondary schools (Year 7):")
    cursor.execute("""
        SELECT school_name, campus_name, year_level_code,
               ROUND((ST_Area(geometry::geography) / 1000000)::numeric, 2) as area_km2
        FROM gnaf.school_catchments
        WHERE state = 'VIC' AND school_type = 'SECONDARY' AND year_level_code = '7'
        LIMIT 5;
    """)
    
    results = cursor.fetchall()
    for row in results:
        print(f"  {row[0]}")
        print(f"    Campus: {row[1]}")
        print(f"    Year Level: {row[2]}, Area: {row[3]} km²")
    
    # Test spatial query - Melbourne CBD
    print("\nSchools serving Melbourne CBD (144.9631°E, -37.8136°S):")
    cursor.execute("""
        SELECT school_name, school_type, year_level_code
        FROM gnaf.school_catchments
        WHERE state = 'VIC'
        AND ST_Contains(geometry, ST_SetSRID(ST_MakePoint(144.9631, -37.8136), 4326))
        ORDER BY school_type, school_name;
    """)
    
    results = cursor.fetchall()
    if results:
        for row in results:
            print(f"  {row[0]} ({row[1]}) - Year Level: {row[2]}")
    else:
        print("  No schools found for this location")
    
    print("\n" + "=" * 70)
    print("✓ Verification complete!")
    print("=" * 70)
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if cursor:
        cursor.close()
    if conn:
        conn.close()
