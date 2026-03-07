"""Fix geometry SRID for school_catchments table"""
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
    
    print("Fixing geometry SRID...")
    
    # Drop dependent views first
    print("  Dropping dependent views...")
    cursor.execute("DROP VIEW IF EXISTS gnaf.vic_school_catchments CASCADE;")
    cursor.execute("DROP VIEW IF EXISTS gnaf.nsw_school_catchments CASCADE;")
    cursor.execute("DROP VIEW IF EXISTS gnaf.school_catchments_summary CASCADE;")
    
    # Update SRID to 4326
    print("  Updating geometry SRID to 4326...")
    cursor.execute("SELECT UpdateGeometrySRID('gnaf', 'school_catchments', 'geometry', 4326);")
    
    # Recreate views
    print("  Recreating views...")
    
    # Victoria view
    cursor.execute("""
        CREATE OR REPLACE VIEW gnaf.vic_school_catchments AS
        SELECT 
            catchment_id,
            school_id,
            entity_code,
            school_name,
            campus_name,
            school_type,
            year_level_code,
            boundary_year,
            kindergart, year1, year2, year3, year4, year5, year6,
            year7, year8, year9, year10, year11, year12,
            geometry,
            centroid_lat,
            centroid_lng,
            data_source,
            created_at,
            updated_at
        FROM gnaf.school_catchments
        WHERE state = 'VIC';
    """)
    
    # NSW view
    cursor.execute("""
        CREATE OR REPLACE VIEW gnaf.nsw_school_catchments AS
        SELECT 
            catchment_id,
            school_id,
            use_id,
            school_name,
            school_type,
            add_date,
            kindergart, year1, year2, year3, year4, year5, year6,
            year7, year8, year9, year10, year11, year12,
            priority,
            geometry,
            centroid_lat,
            centroid_lng,
            data_source,
            created_at,
            updated_at
        FROM gnaf.school_catchments
        WHERE state = 'NSW';
    """)
    
    # Summary view
    cursor.execute("""
        CREATE OR REPLACE VIEW gnaf.school_catchments_summary AS
        SELECT 
            state,
            school_type,
            boundary_year,
            COUNT(*) as catchment_count,
            COUNT(DISTINCT school_id) as unique_schools,
            COUNT(DISTINCT CASE WHEN kindergart = 'Y' THEN school_id END) as kindergarten_schools,
            COUNT(DISTINCT CASE WHEN year7 = 'Y' THEN school_id END) as year7_schools,
            COUNT(DISTINCT CASE WHEN year12 = 'Y' THEN school_id END) as year12_schools
        FROM gnaf.school_catchments
        GROUP BY state, school_type, boundary_year
        ORDER BY state, school_type;
    """)
    
    # Verify
    cursor.execute("SELECT Find_SRID('gnaf', 'school_catchments', 'geometry') as current_srid;")
    result = cursor.fetchone()
    print(f"✓ Current SRID: {result[0]}")
    
    conn.commit()
    print("✓ Geometry SRID fixed successfully!")
    print("✓ Views recreated successfully!")
    
except Exception as e:
    print(f"✗ Error: {e}")
    if conn:
        conn.rollback()
finally:
    if cursor:
        cursor.close()
    if conn:
        conn.close()
