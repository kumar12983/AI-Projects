#!/usr/bin/env python3
"""
Load Victoria School Zone Data into gnaf.school_catchments

This script loads Victoria school catchment data from GeoJSON files into the
PostgreSQL database, harmonizing with the existing NSW data structure.

Usage:
    python load_victoria_catchments.py [--dry-run] [--backup]

Options:
    --dry-run    Show what would be loaded without actually loading
    --backup     Create backup of school_catchments table before loading

Author: GitHub Copilot
Date: February 10, 2026
"""

import geopandas as gpd
from sqlalchemy import create_engine
import psycopg2
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment (try both paths)
load_dotenv(Path(__file__).parent.parent / 'webapp' / '.env')
load_dotenv()  # Also try .env in current directory

# Database configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'gnaf_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')

connection_string = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

# Victoria data location
VIC_DATA_DIR = Path(r'C:\Users\kumar\Documents\workspace\dv371_DataVic_School_Zones_2024')

# File mappings with metadata
VIC_FILES = {
    'Primary_Integrated_2024.geojson': {
        'school_type': 'PRIMARY',
        'description': 'Primary schools (Prep-Year 6)',
        'priority': 1
    },
    'Secondary_Integrated_Year7_2024.geojson': {
        'school_type': 'SECONDARY',
        'description': 'Secondary schools - Year 7 catchments',
        'priority': 2
    },
    'Secondary_Integrated_Year8_2024.geojson': {
        'school_type': 'SECONDARY',
        'description': 'Secondary schools - Year 8 catchments',
        'priority': 3
    },
    'Secondary_Integrated_Year9_2024.geojson': {
        'school_type': 'SECONDARY',
        'description': 'Secondary schools - Year 9 catchments',
        'priority': 4
    },
    'Secondary_Integrated_Year10_2024.geojson': {
        'school_type': 'SECONDARY',
        'description': 'Secondary schools - Year 10 catchments',
        'priority': 5
    },
    'Secondary_Integrated_Year11_2024.geojson': {
        'school_type': 'SECONDARY',
        'description': 'Secondary schools - Year 11 catchments',
        'priority': 6
    },
    'Secondary_Integrated_Year12_2024.geojson': {
        'school_type': 'SECONDARY',
        'description': 'Secondary schools - Year 12 catchments',
        'priority': 7
    },
    'Standalone_juniorsec_2024.geojson': {
        'school_type': 'JUNIOR_SECONDARY',
        'description': 'Standalone junior secondary schools',
        'priority': 8
    },
    'Standalone_seniorsec_2024.geojson': {
        'school_type': 'SENIOR_SECONDARY',
        'description': 'Standalone senior secondary schools',
        'priority': 9
    },
    'Standalone_singlesex_2024.geojson': {
        'school_type': 'SINGLE_SEX',
        'description': 'Single-sex schools',
        'priority': 10
    }
}


def map_year_levels(year_level_code):
    """
    Map Victoria year level codes to NSW-style year flags
    
    Args:
        year_level_code: Victoria year level code ('P6', '7', '8', etc.)
    
    Returns:
        dict: Year flags compatible with NSW schema
    """
    year_flags = {f'year{i}': 'N' for i in range(1, 13)}
    year_flags['kindergart'] = 'N'
    
    if not year_level_code:
        return year_flags
    
    year_level_code = str(year_level_code).strip()
    
    if year_level_code == 'P6':
        # Primary integrated: Prep (Kindergarten) to Year 6
        year_flags['kindergart'] = 'Y'
        for i in range(1, 7):
            year_flags[f'year{i}'] = 'Y'
    
    elif year_level_code.isdigit():
        # Specific year level (7-12)
        year_num = int(year_level_code)
        if 7 <= year_num <= 12:
            year_flags[f'year{year_num}'] = 'Y'
    
    return year_flags


def ensure_schema_updated(conn):
    """
    Ensure the school_catchments table has all required columns for Victoria data
    
    Args:
        conn: psycopg2 connection
    """
    print("\n" + "=" * 70)
    print("Checking/Updating Database Schema")
    print("=" * 70)
    
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'gnaf' 
            AND table_name = 'school_catchments'
        );
    """)
    
    table_exists = cursor.fetchone()[0]
    
    if not table_exists:
        print("✗ Table gnaf.school_catchments does not exist!")
        print("  Please create the table first using the schema in VICTORIA_SCHOOL_ZONE_DATA_MODEL.md")
        cursor.close()
        return False
    
    print("✓ Table gnaf.school_catchments exists")
    
    # Check for Victoria-specific columns
    required_columns = {
        'state': 'VARCHAR(3)',
        'campus_name': 'VARCHAR(255)',
        'entity_code': 'INTEGER',
        'year_level_code': 'VARCHAR(10)',
        'boundary_year': 'INTEGER',
        'centroid_lat': 'DOUBLE PRECISION',
        'centroid_lng': 'DOUBLE PRECISION',
        'data_source': 'VARCHAR(50)'
    }
    
    missing_columns = []
    
    for col_name, col_type in required_columns.items():
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_schema = 'gnaf' 
                AND table_name = 'school_catchments'
                AND column_name = %s
            );
        """, (col_name,))
        
        if not cursor.fetchone()[0]:
            missing_columns.append((col_name, col_type))
    
    if missing_columns:
        print(f"\n⚠ Missing {len(missing_columns)} required columns:")
        for col_name, col_type in missing_columns:
            print(f"  - {col_name} ({col_type})")
        
        print("\nWould you like to add these columns? (y/n): ", end='')
        response = input().strip().lower()
        
        if response == 'y':
            print("\nAdding missing columns...")
            for col_name, col_type in missing_columns:
                try:
                    cursor.execute(f"""
                        ALTER TABLE gnaf.school_catchments 
                        ADD COLUMN IF NOT EXISTS {col_name} {col_type};
                    """)
                    print(f"  ✓ Added column: {col_name}")
                except Exception as e:
                    print(f"  ✗ Error adding {col_name}: {e}")
                    cursor.close()
                    return False
            
            conn.commit()
            print("✓ Schema updated successfully")
        else:
            print("✗ Schema update cancelled. Please add columns manually.")
            cursor.close()
            return False
    else:
        print("✓ All required columns exist")
    
    cursor.close()
    return True


def backup_table(conn):
    """
    Create a backup of the school_catchments table
    
    Args:
        conn: psycopg2 connection
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_table_name = f'school_catchments_backup_{timestamp}'
    
    print(f"\nCreating backup: gnaf.{backup_table_name}")
    
    cursor = conn.cursor()
    
    try:
        cursor.execute(f"""
            CREATE TABLE gnaf.{backup_table_name} AS 
            SELECT * FROM gnaf.school_catchments;
        """)
        conn.commit()
        
        cursor.execute(f"SELECT COUNT(*) FROM gnaf.{backup_table_name};")
        count = cursor.fetchone()[0]
        
        print(f"✓ Backup created: {count} records")
        print(f"  Table: gnaf.{backup_table_name}")
        
        cursor.close()
        return True
    
    except Exception as e:
        print(f"✗ Backup failed: {e}")
        cursor.close()
        return False


def delete_existing_vic_data(engine):
    """
    Delete existing Victoria data from the table
    
    Args:
        engine: SQLAlchemy engine
    """
    print("\nChecking for existing Victoria data...")
    
    conn = engine.raw_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM gnaf.school_catchments WHERE state = 'VIC';")
    existing_count = cursor.fetchone()[0]
    
    if existing_count > 0:
        print(f"  Found {existing_count} existing Victoria records")
        print("  Deleting existing Victoria data...")
        
        cursor.execute("DELETE FROM gnaf.school_catchments WHERE state = 'VIC';")
        conn.commit()
        
        print(f"  ✓ Deleted {existing_count} records")
    else:
        print("  No existing Victoria data found")
    
    cursor.close()
    conn.close()


def load_victoria_file(file_path, school_type, engine, dry_run=False):
    """
    Load a single Victoria GeoJSON file
    
    Args:
        file_path: Path to GeoJSON file
        school_type: School type classification
        engine: SQLAlchemy engine
        dry_run: If True, just validate without loading
    
    Returns:
        int: Number of records loaded
    """
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Processing: {file_path.name}")
    print(f"  School Type: {school_type}")
    
    # Read GeoJSON
    try:
        gdf = gpd.read_file(file_path)
    except Exception as e:
        print(f"  ✗ Error reading file: {e}")
        return 0
    
    print(f"  Records: {len(gdf)}")
    print(f"  Columns: {', '.join(gdf.columns)}")
    
    # Validate required columns
    required_cols = {'ENTITY_CODE', 'School_Name', 'Campus_Name', 'geometry'}
    missing_cols = required_cols - set(gdf.columns)
    
    if missing_cols:
        print(f"  ✗ Missing required columns: {missing_cols}")
        return 0
    
    # Convert CRS if needed
    if gdf.crs and gdf.crs != 'EPSG:4326':
        print(f"  Converting CRS from {gdf.crs} to EPSG:4326...")
        gdf = gdf.to_crs('EPSG:4326')
    
    # Validate geometries
    invalid_geoms = ~gdf.geometry.is_valid
    if invalid_geoms.any():
        print(f"  ⚠ Found {invalid_geoms.sum()} invalid geometries - attempting to fix...")
        gdf.loc[invalid_geoms, 'geometry'] = gdf.loc[invalid_geoms, 'geometry'].buffer(0)
    
    # Transform data
    transformed_records = []
    
    for idx, row in gdf.iterrows():
        try:
            # Map year levels
            year_flags = map_year_levels(row.get('Year_Level'))
            
            # Calculate centroid
            centroid = row['geometry'].centroid
            
            # Build record
            record = {
                'school_id': str(row['ENTITY_CODE']),
                'school_name': row['School_Name'],
                'campus_name': row['Campus_Name'],
                'school_type': school_type,
                'state': 'VIC',
                'boundary_year': int(row.get('Boundary_Year', 2024)),
                **year_flags,
                'year_level_code': str(row.get('Year_Level', '')),
                'entity_code': int(row['ENTITY_CODE']),
                'use_id': None,
                'add_date': None,
                'priority': None,
                'geometry': row['geometry'],
                'centroid_lat': centroid.y,
                'centroid_lng': centroid.x,
                'data_source': 'DATAVIC'
            }
            
            transformed_records.append(record)
        
        except Exception as e:
            print(f"  ⚠ Error processing record {idx}: {e}")
            continue
    
    print(f"  Transformed: {len(transformed_records)} records")
    
    if dry_run:
        print(f"  [DRY RUN] Would load {len(transformed_records)} records")
        
        # Show sample
        if transformed_records:
            print("\n  Sample record:")
            sample = transformed_records[0]
            for k, v in list(sample.items())[:10]:
                if k != 'geometry':
                    print(f"    {k}: {v}")
        
        return len(transformed_records)
    
    # Create GeoDataFrame
    gdf_transformed = gpd.GeoDataFrame(transformed_records, crs='EPSG:4326')
    
    # Load to database
    print(f"  Writing to database...")
    
    try:
        gdf_transformed.to_postgis(
            'school_catchments',
            engine,
            schema='gnaf',
            if_exists='append',
            index=False
        )
        
        print(f"  ✓ Loaded {len(gdf_transformed)} records")
        return len(gdf_transformed)
    
    except Exception as e:
        print(f"  ✗ Database error: {e}")
        import traceback
        traceback.print_exc()
        return 0


def validate_loaded_data(engine):
    """
    Validate the loaded Victoria data
    
    Args:
        engine: SQLAlchemy engine
    """
    print("\n" + "=" * 70)
    print("Data Validation")
    print("=" * 70)
    
    conn = engine.raw_connection()
    cursor = conn.cursor()
    
    # Count by state
    cursor.execute("""
        SELECT state, COUNT(*) as count
        FROM gnaf.school_catchments
        GROUP BY state
        ORDER BY state;
    """)
    
    print("\nRecords by state:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]:,} catchments")
    
    # Count by school type (VIC only)
    cursor.execute("""
        SELECT school_type, COUNT(*) as count
        FROM gnaf.school_catchments
        WHERE state = 'VIC'
        GROUP BY school_type
        ORDER BY school_type;
    """)
    
    print("\nVictoria catchments by type:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]:,} catchments")
    
    # Check for invalid geometries
    cursor.execute("""
        SELECT COUNT(*) 
        FROM gnaf.school_catchments 
        WHERE state = 'VIC' 
        AND NOT ST_IsValid(geometry);
    """)
    
    invalid_count = cursor.fetchone()[0]
    if invalid_count > 0:
        print(f"\n⚠ Warning: {invalid_count} invalid geometries found")
    else:
        print("\n✓ All geometries are valid")
    
    # Check for missing centroids
    cursor.execute("""
        SELECT COUNT(*) 
        FROM gnaf.school_catchments 
        WHERE state = 'VIC' 
        AND (centroid_lat IS NULL OR centroid_lng IS NULL);
    """)
    
    missing_centroids = cursor.fetchone()[0]
    if missing_centroids > 0:
        print(f"⚠ Warning: {missing_centroids} records missing centroids")
    else:
        print("✓ All records have centroids")
    
    cursor.close()
    conn.close()


def main():
    """Main execution function"""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description='Load Victoria School Zone Data into PostgreSQL'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate files without loading to database'
    )
    parser.add_argument(
        '--backup',
        action='store_true',
        help='Create backup of existing data before loading'
    )
    
    args = parser.parse_args()
    
    # Banner
    print("=" * 70)
    print("Victoria School Zone Data Loader")
    if args.dry_run:
        print("[DRY RUN MODE - No data will be modified]")
    print("=" * 70)
    
    # Check data directory
    if not VIC_DATA_DIR.exists():
        print(f"\n✗ Data directory not found: {VIC_DATA_DIR}")
        print("  Please update VIC_DATA_DIR in the script")
        return 1
    
    print(f"\nData directory: {VIC_DATA_DIR}")
    
    # Create engine
    try:
        engine = create_engine(connection_string)
        conn = engine.raw_connection()
        print("✓ Database connection established")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return 1
    
    # Ensure schema is updated
    if not args.dry_run:
        if not ensure_schema_updated(conn):
            return 1
    
    # Create backup if requested
    if args.backup and not args.dry_run:
        if not backup_table(conn):
            print("⚠ Backup failed, continue anyway? (y/n): ", end='')
            if input().strip().lower() != 'y':
                return 1
    
    conn.close()
    
    # Delete existing Victoria data (unless dry run)
    if not args.dry_run:
        delete_existing_vic_data(engine)
    
    # Load each file
    total_loaded = 0
    files_loaded = 0
    
    # Sort files by priority
    sorted_files = sorted(
        VIC_FILES.items(),
        key=lambda x: x[1]['priority']
    )
    
    for filename, config in sorted_files:
        file_path = VIC_DATA_DIR / filename
        
        if not file_path.exists():
            print(f"\n⚠ File not found: {filename}")
            continue
        
        try:
            count = load_victoria_file(
                file_path,
                config['school_type'],
                engine,
                dry_run=args.dry_run
            )
            
            if count > 0:
                total_loaded += count
                files_loaded += 1
        
        except Exception as e:
            print(f"\n✗ Error loading {filename}: {e}")
            import traceback
            traceback.print_exc()
    
    # Validation
    if not args.dry_run and total_loaded > 0:
        validate_loaded_data(engine)
    
    # Summary
    print("\n" + "=" * 70)
    if args.dry_run:
        print("DRY RUN COMPLETE")
        print(f"  Files processed: {files_loaded}")
        print(f"  Records that would be loaded: {total_loaded:,}")
        print("\nRun without --dry-run to load data")
    else:
        print("MIGRATION COMPLETE")
        print(f"  Files loaded: {files_loaded}")
        print(f"  Total records loaded: {total_loaded:,}")
        print("\n✓ Victoria school catchment data successfully loaded!")
    print("=" * 70)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
