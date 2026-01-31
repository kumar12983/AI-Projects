"""
Load NSW School Catchment Shapefiles into PostgreSQL/PostGIS
This script loads primary, secondary, and future school catchment data into the GNAF database
"""

import geopandas as gpd
import psycopg2
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('webapp/.env')

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'gnaf_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'admin')

# Database connection string for SQLAlchemy
connection_string = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

def enable_postgis():
    """Enable PostGIS extension if not already enabled"""
    print("Enabling PostGIS extension...")
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    conn.autocommit = True
    cursor = conn.cursor()
    
    try:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        print("✓ PostGIS extension enabled")
    except Exception as e:
        print(f"⚠ PostGIS may already be enabled: {e}")
    
    cursor.close()
    conn.close()

def load_shapefile(shapefile_path, table_name, schema='public'):
    """Load a shapefile into PostgreSQL"""
    print(f"\nLoading {shapefile_path}...")
    
    # Read shapefile with geopandas
    gdf = gpd.read_file(shapefile_path)
    
    # Print info about the shapefile
    print(f"  Records: {len(gdf)}")
    print(f"  Columns: {', '.join(gdf.columns)}")
    print(f"  CRS: {gdf.crs}")
    
    # Convert to WGS84 if needed (EPSG:4326) to match GNAF coordinates
    if gdf.crs != 'EPSG:4326':
        print(f"  Converting from {gdf.crs} to EPSG:4326 (WGS84)...")
        gdf = gdf.to_crs('EPSG:4326')
    
    # Load into PostgreSQL
    engine = create_engine(connection_string)
    print(f"  Writing to database table: {schema}.{table_name}...")
    
    gdf.to_postgis(
        name=table_name,
        con=engine,
        schema=schema,
        if_exists='replace',
        index=True
    )
    
    print(f"✓ Loaded {len(gdf)} records to {schema}.{table_name}")
    
    # Create spatial index
    print(f"  Creating spatial index...")
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor = conn.cursor()
    cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_geom ON {schema}.{table_name} USING GIST (geometry);")
    conn.commit()
    cursor.close()
    conn.close()
    print(f"✓ Spatial index created")
    
    return gdf

def main():
    print("=" * 60)
    print("NSW School Catchment Data Loader")
    print("=" * 60)
    
    # Check if geopandas is installed
    try:
        import geopandas
        print("✓ GeoPandas is installed")
    except ImportError:
        print("✗ GeoPandas is not installed")
        print("\nPlease install required packages:")
        print("  pip install geopandas psycopg2-binary sqlalchemy")
        return
    
    # Enable PostGIS
    enable_postgis()
    
    # Define shapefiles to load
    shapefiles = {
        'nsw_school_catchments/catchments_primary.shp': 'school_catchments_primary',
        'nsw_school_catchments/catchments_secondary.shp': 'school_catchments_secondary',
        'nsw_school_catchments/catchments_future.shp': 'school_catchments_future'
    }
    
    # Load each shapefile
    for shapefile, table_name in shapefiles.items():
        try:
            load_shapefile(shapefile, table_name, schema='public')
        except Exception as e:
            print(f"✗ Error loading {shapefile}: {e}")
    
    print("\n" + "=" * 60)
    print("Loading Complete!")
    print("=" * 60)
    
    # Print summary queries
    print("\nYou can now query school catchments with SQL:")
    print("\n-- Find which primary school catchment an address is in:")
    print("SELECT sc.* ")
    print("FROM school_catchments_primary sc")
    print("WHERE ST_Contains(sc.geometry, ST_SetSRID(ST_MakePoint(151.2093, -33.8688), 4326));")
    
    print("\n-- Find all addresses in a specific school catchment:")
    print("SELECT ad.*, adg.latitude, adg.longitude, sc.school_code, sc.school_name")
    print("FROM gnaf.address_detail ad")
    print("JOIN gnaf.address_default_geocode adg ON ad.address_detail_pid = adg.address_detail_pid")
    print("JOIN school_catchments_primary sc ON ST_Contains(sc.geometry, ST_SetSRID(ST_MakePoint(adg.longitude, adg.latitude), 4326))")
    print("WHERE ad.date_retired IS NULL")
    print("LIMIT 10;")

if __name__ == '__main__':
    main()
