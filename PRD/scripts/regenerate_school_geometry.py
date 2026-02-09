"""
Regenerate school_geometry table with updated coordinates
This script recreates the school_geometry table from school_profile_2025 
which now has latitude/longitude from school_location
"""
import psycopg2
import os
from dotenv import load_dotenv
import sys


def connect_to_db(host='localhost', port=5432, database='gnaf_db', user='postgres', password=''):
    """Connect to PostgreSQL database"""
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        print(f"✓ Connected to database: {database}")
        return conn
    except psycopg2.Error as e:
        print(f"✗ Error connecting to database: {e}")
        sys.exit(1)


def regenerate_school_geometry(conn):
    """Regenerate school_geometry table with updated coordinates"""
    
    sql_script = """
    SET search_path TO gnaf, public;

    DROP TABLE IF EXISTS gnaf.school_geometry CASCADE;

    CREATE TABLE gnaf.school_geometry AS
    WITH school_geometry AS 
    (
        SELECT 
            pf.acara_sml_id,
            pf.school_name,
            pf.state,
            pf.school_sector,
            pf.longitude,
            pf.latitude,
            -- Create 5km buffer geometry (only if coordinates exist)
            CASE 
                WHEN pf.latitude IS NOT NULL AND pf.longitude IS NOT NULL THEN
                    ST_Buffer(
                        ST_Transform(
                            ST_Point(pf.longitude, pf.latitude, 4326),
                            3857
                        ),
                        5000
                    )::geometry
                ELSE NULL
            END AS geom_5km_buffer,
            lf.school_id,
            cs.geometry AS catchment_zone,
            CASE WHEN cs.geometry IS NOT NULL THEN 'Y' ELSE 'N' END AS has_catchment
        FROM gnaf.school_profile_2025 pf 
        LEFT JOIN gnaf.school_type_lookup lf ON pf.acara_sml_id = lf.acara_sml_id
        LEFT JOIN gnaf.school_catchments cs ON cs.school_id = lf.school_id
    )
    SELECT 
        *,
        CASE WHEN geom_5km_buffer IS NOT NULL THEN 'Y' ELSE 'N' END AS has_geom_buffer
    FROM school_geometry;
    
    -- Add full-text search vector column
    ALTER TABLE gnaf.school_geometry 
    ADD COLUMN search_vector tsvector 
    GENERATED ALWAYS AS (to_tsvector('english', school_name)) STORED;
    
    -- Create indexes
    CREATE INDEX idx_school_geometry_search ON gnaf.school_geometry USING GIN(search_vector);
    CREATE INDEX idx_school_geom_5km_buffer ON gnaf.school_geometry USING GIST(geom_5km_buffer);
    CREATE INDEX idx_school_catchment_zone ON gnaf.school_geometry USING GIST(catchment_zone);
    CREATE INDEX idx_school_geom_acara_sml_id ON gnaf.school_geometry(acara_sml_id);
    CREATE INDEX idx_school_geom_school_id ON gnaf.school_geometry(school_id);
    CREATE INDEX idx_school_geom_state ON gnaf.school_geometry(state);
    CREATE INDEX idx_school_geom_sector ON gnaf.school_geometry(school_sector);
    CREATE INDEX idx_school_geom_coords ON gnaf.school_geometry(latitude, longitude);
    
    -- Add comments
    COMMENT ON TABLE gnaf.school_geometry IS 'School geometry data with 5km buffers and catchment zones - coordinates sourced from school_location table via school_profile_2025';
    COMMENT ON COLUMN gnaf.school_geometry.latitude IS 'Geographic latitude (decimal degrees) - sourced from school_location';
    COMMENT ON COLUMN gnaf.school_geometry.longitude IS 'Geographic longitude (decimal degrees) - sourced from school_location';
    COMMENT ON COLUMN gnaf.school_geometry.geom_5km_buffer IS '5km radius buffer around school location in Web Mercator projection';
    """
    
    try:
        cursor = conn.cursor()
        
        print("\n🔄 Regenerating school_geometry table...")
        cursor.execute(sql_script)
        
        # Get statistics
        cursor.execute("SELECT COUNT(*) FROM gnaf.school_geometry")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM gnaf.school_geometry WHERE latitude IS NOT NULL")
        with_coords = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM gnaf.school_geometry WHERE geom_5km_buffer IS NOT NULL")
        with_buffer = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM gnaf.school_geometry WHERE catchment_zone IS NOT NULL")
        with_catchment = cursor.fetchone()[0]
        
        conn.commit()
        cursor.close()
        
        print("\n" + "="*70)
        print("✅ SCHOOL GEOMETRY TABLE REGENERATED")
        print("="*70)
        print(f"  • Total schools: {total}")
        print(f"  • Schools with coordinates: {with_coords}")
        print(f"  • Schools with 5km buffer: {with_buffer}")
        print(f"  • Schools with catchment zones: {with_catchment}")
        print("="*70)
        
        return True
        
    except psycopg2.Error as e:
        print(f"✗ Error regenerating school_geometry: {e}")
        conn.rollback()
        return False


def main():
    """Main execution function"""
    print("="*70)
    print("Regenerate School Geometry Table")
    print("="*70)
    
    # Load environment variables
    load_dotenv()
    
    # Database connection parameters
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'gnaf_db')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', '')
    
    # Connect to database
    print("\n🔌 Connecting to database...")
    conn = connect_to_db(db_host, int(db_port), db_name, db_user, db_password)
    
    try:
        # Regenerate table
        if not regenerate_school_geometry(conn):
            print("\n✗ Failed to regenerate school_geometry table")
            sys.exit(1)
        
        print("\n✓ Complete! The school_geometry table now has updated coordinates")
        print("  and regenerated 5km buffers from school_location data.\n")
        
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close connection
        conn.close()
        print("🔌 Database connection closed")


if __name__ == "__main__":
    main()
