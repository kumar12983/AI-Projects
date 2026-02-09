"""
Import School Location 2025 data and update school_profile_2025 with coordinates
1. Create gnaf.school_location table
2. Prompt for Excel file location (with default)
3. Import data from Excel
4. Update school_profile_2025 with latitude and longitude
"""
import pandas as pd
import psycopg2
from psycopg2 import sql
from pathlib import Path
import sys
import os
from dotenv import load_dotenv


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


def create_school_location_table(conn):
    """Create the school_location table in gnaf schema"""
    create_table_sql = """
    DROP TABLE IF EXISTS gnaf.school_location CASCADE;
    
    CREATE TABLE gnaf.school_location (
        -- Identifiers
        calendar_year INT NOT NULL,
        acara_sml_id INT NOT NULL PRIMARY KEY,
        location_age_id NUMERIC,
        school_age_id NUMERIC,
        rolled_school_id INT,
        
        -- School Information
        school_name VARCHAR(255) NOT NULL,
        suburb VARCHAR(100) NOT NULL,
        state VARCHAR(10) NOT NULL,
        postcode INT NOT NULL,
        school_sector VARCHAR(100),
        school_type VARCHAR(100),
        special_school INT,
        campus_type VARCHAR(100),
        
        -- Geographic Coordinates
        latitude NUMERIC(10, 7),
        longitude NUMERIC(10, 7),
        
        -- ABS Geographic Areas
        abs_remoteness_area INT,
        abs_remoteness_area_name VARCHAR(100),
        meshblock BIGINT,
        statistical_area_1 BIGINT,
        statistical_area_2 BIGINT,
        statistical_area_2_name VARCHAR(255),
        statistical_area_3 BIGINT,
        statistical_area_3_name VARCHAR(255),
        statistical_area_4 BIGINT,
        statistical_area_4_name VARCHAR(255),
        
        -- Government Areas
        local_government_area BIGINT,
        local_government_area_name VARCHAR(255),
        state_electoral_division BIGINT,
        state_electoral_division_name VARCHAR(255),
        commonwealth_electoral_division BIGINT,
        commonwealth_electoral_division_name VARCHAR(255)
    );
    
    -- Create index on acara_sml_id for faster lookups
    CREATE INDEX idx_school_location_acara_sml_id ON gnaf.school_location(acara_sml_id);
    
    -- Create spatial index on coordinates
    CREATE INDEX idx_school_location_coords ON gnaf.school_location(latitude, longitude);
    
    COMMENT ON TABLE gnaf.school_location IS 'School location data with geographic coordinates and statistical areas';
    COMMENT ON COLUMN gnaf.school_location.acara_sml_id IS 'Unique ID allocated to a school by ACARA (Primary Key)';
    COMMENT ON COLUMN gnaf.school_location.latitude IS 'Geographic latitude coordinate';
    COMMENT ON COLUMN gnaf.school_location.longitude IS 'Geographic longitude coordinate';
    """
    
    try:
        cursor = conn.cursor()
        cursor.execute(create_table_sql)
        conn.commit()
        cursor.close()
        print("✓ Created gnaf.school_location table with indexes")
        return True
    except psycopg2.Error as e:
        print(f"✗ Error creating table: {e}")
        conn.rollback()
        return False


def import_school_location_data(conn, excel_file):
    """Import school location data from Excel to PostgreSQL"""
    
    # Check if file exists
    excel_path = Path(excel_file)
    if not excel_path.exists():
        print(f"✗ File not found: {excel_file}")
        return 0
    
    print(f"\n📂 Loading data from: {excel_file}")
    
    # Read Excel file
    try:
        df = pd.read_excel(excel_file, sheet_name='SchoolLocations 2025')
        print(f"✓ Read {len(df)} rows from Excel")
    except Exception as e:
        print(f"✗ Error reading Excel file: {e}")
        return 0
    
    # Rename columns to match database schema (lowercase with underscores)
    column_mapping = {
        'Calendar Year': 'calendar_year',
        'ACARA SML ID': 'acara_sml_id',
        'Location AGE ID': 'location_age_id',
        'School AGE ID': 'school_age_id',
        'Rolled School ID': 'rolled_school_id',
        'School Name': 'school_name',
        'Suburb': 'suburb',
        'State': 'state',
        'Postcode': 'postcode',
        'School Sector': 'school_sector',
        'School Type': 'school_type',
        'Special school': 'special_school',
        'Campus Type': 'campus_type',
        'Latitude': 'latitude',
        'Longitude': 'longitude',
        'ABS Remoteness Area': 'abs_remoteness_area',
        'ABS Remoteness Area Name': 'abs_remoteness_area_name',
        'Meshblock': 'meshblock',
        'Statistical Area 1': 'statistical_area_1',
        'Statistical Area 2': 'statistical_area_2',
        'Statistical Area 2 Name': 'statistical_area_2_name',
        'Statistical Area 3': 'statistical_area_3',
        'Statistical Area 3 Name': 'statistical_area_3_name',
        'Statistical Area 4': 'statistical_area_4',
        'Statistical Area 4 Name': 'statistical_area_4_name',
        'Local Government Area': 'local_government_area',
        'Local Government Area Name': 'local_government_area_name',
        'State Electoral Division': 'state_electoral_division',
        'State Electoral Division Name': 'state_electoral_division_name',
        'Commonwealth Electoral Division': 'commonwealth_electoral_division',
        'Commonwealth Electoral Division Name': 'commonwealth_electoral_division_name'
    }
    
    df = df.rename(columns=column_mapping)
    
    # Replace NaN with None for proper NULL handling
    df = df.where(pd.notnull(df), None)
    
    # Prepare insert statement
    columns = list(column_mapping.values())
    placeholders = ', '.join(['%s'] * len(columns))
    column_names = ', '.join(columns)
    
    insert_sql = f"""
        INSERT INTO gnaf.school_location ({column_names})
        VALUES ({placeholders})
        ON CONFLICT (acara_sml_id) DO UPDATE SET
            calendar_year = EXCLUDED.calendar_year,
            location_age_id = EXCLUDED.location_age_id,
            school_age_id = EXCLUDED.school_age_id,
            rolled_school_id = EXCLUDED.rolled_school_id,
            school_name = EXCLUDED.school_name,
            suburb = EXCLUDED.suburb,
            state = EXCLUDED.state,
            postcode = EXCLUDED.postcode,
            school_sector = EXCLUDED.school_sector,
            school_type = EXCLUDED.school_type,
            special_school = EXCLUDED.special_school,
            campus_type = EXCLUDED.campus_type,
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            abs_remoteness_area = EXCLUDED.abs_remoteness_area,
            abs_remoteness_area_name = EXCLUDED.abs_remoteness_area_name,
            meshblock = EXCLUDED.meshblock,
            statistical_area_1 = EXCLUDED.statistical_area_1,
            statistical_area_2 = EXCLUDED.statistical_area_2,
            statistical_area_2_name = EXCLUDED.statistical_area_2_name,
            statistical_area_3 = EXCLUDED.statistical_area_3,
            statistical_area_3_name = EXCLUDED.statistical_area_3_name,
            statistical_area_4 = EXCLUDED.statistical_area_4,
            statistical_area_4_name = EXCLUDED.statistical_area_4_name,
            local_government_area = EXCLUDED.local_government_area,
            local_government_area_name = EXCLUDED.local_government_area_name,
            state_electoral_division = EXCLUDED.state_electoral_division,
            state_electoral_division_name = EXCLUDED.state_electoral_division_name,
            commonwealth_electoral_division = EXCLUDED.commonwealth_electoral_division,
            commonwealth_electoral_division_name = EXCLUDED.commonwealth_electoral_division_name
    """
    
    # Insert data in batches
    cursor = conn.cursor()
    batch_size = 1000
    inserted_count = 0
    
    try:
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i + batch_size]
            values = [tuple(row) for row in batch[columns].values]
            cursor.executemany(insert_sql, values)
            inserted_count += len(batch)
            if inserted_count % 1000 == 0:
                print(f"  ⏳ Processed {inserted_count}/{len(df)} rows...")
        
        conn.commit()
        print(f"✓ Successfully imported {inserted_count} rows into gnaf.school_location")
        cursor.close()
        return inserted_count
        
    except psycopg2.Error as e:
        print(f"✗ Error inserting data: {e}")
        conn.rollback()
        cursor.close()
        return 0


def update_school_profile_coordinates(conn):
    """Update school_profile_2025 with latitude and longitude from school_location"""
    
    update_sql = """
    -- First, add latitude and longitude columns if they don't exist
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_schema = 'gnaf' 
                      AND table_name = 'school_profile_2025' 
                      AND column_name = 'latitude') THEN
            ALTER TABLE gnaf.school_profile_2025 ADD COLUMN latitude NUMERIC(10, 7);
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_schema = 'gnaf' 
                      AND table_name = 'school_profile_2025' 
                      AND column_name = 'longitude') THEN
            ALTER TABLE gnaf.school_profile_2025 ADD COLUMN longitude NUMERIC(10, 7);
        END IF;
    END $$;
    
    -- Update coordinates from school_location
    UPDATE gnaf.school_profile_2025 AS sp
    SET 
        latitude = sl.latitude,
        longitude = sl.longitude
    FROM gnaf.school_location AS sl
    WHERE sp.acara_sml_id = sl.acara_sml_id;
    
    -- Return count of updated rows
    SELECT COUNT(*) 
    FROM gnaf.school_profile_2025 
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL;
    """
    
    try:
        cursor = conn.cursor()
        cursor.execute(update_sql)
        conn.commit()
        
        # Get count of updated rows
        updated_count = cursor.fetchone()[0]
        
        cursor.close()
        print(f"✓ Updated {updated_count} schools in school_profile_2025 with coordinates")
        return updated_count
        
    except psycopg2.Error as e:
        print(f"✗ Error updating school_profile_2025: {e}")
        conn.rollback()
        return 0


def main():
    """Main execution function"""
    print("="*70)
    print("School Location Import and Update Tool")
    print("="*70)
    
    # Load environment variables
    load_dotenv()
    
    # Database connection parameters
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'gnaf_db')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', '')
    
    # Default file location
    default_file = r'C:\Users\kumar\Documents\workspace\school profile\School Location 2025.xlsx'
    
    # Prompt for file location
    print("\n📁 Excel File Location")
    print(f"Default: {default_file}")
    user_input = input("Enter file path (or press Enter for default): ").strip()
    
    excel_file = user_input if user_input else default_file
    
    # Validate file exists
    if not Path(excel_file).exists():
        print(f"\n✗ File not found: {excel_file}")
        print("Please check the file path and try again.")
        sys.exit(1)
    
    print(f"\n✓ Using file: {excel_file}")
    
    # Connect to database
    print("\n🔌 Connecting to database...")
    conn = connect_to_db(db_host, int(db_port), db_name, db_user, db_password)
    
    try:
        # Step 1: Create table
        print("\n📋 Step 1: Creating gnaf.school_location table...")
        if not create_school_location_table(conn):
            print("Failed to create table. Exiting.")
            sys.exit(1)
        
        # Step 2: Import data
        print("\n📥 Step 2: Importing data from Excel...")
        imported_count = import_school_location_data(conn, excel_file)
        if imported_count == 0:
            print("Failed to import data. Exiting.")
            sys.exit(1)
        
        # Step 3: Update school_profile_2025
        print("\n🔄 Step 3: Updating school_profile_2025 with coordinates...")
        updated_count = update_school_profile_coordinates(conn)
        
        # Summary
        print("\n" + "="*70)
        print("✅ IMPORT COMPLETE")
        print("="*70)
        print(f"  • Schools imported to school_location: {imported_count}")
        print(f"  • Schools updated in school_profile_2025: {updated_count}")
        print("="*70)
        
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close connection
        conn.close()
        print("\n🔌 Database connection closed")


if __name__ == "__main__":
    main()
