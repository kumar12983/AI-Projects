-- ============================================
-- GNAF PostGIS Geospatial Setup
-- ============================================
-- This script sets up PostGIS extensions and adds geospatial capabilities
-- to your GNAF (Geocoded National Address File) database
-- ============================================

-- ============================================
-- Step 1: Enable PostGIS Extension
-- ============================================
-- IMPORTANT: PostGIS must be installed on your PostgreSQL server FIRST!
-- 
-- To install PostGIS on Windows:
-- 1. Use Stack Builder (comes with PostgreSQL installer)
--    - Open "Stack Builder" from Start menu
--    - Select your PostgreSQL version
--    - Under "Spatial Extensions", select PostGIS Bundle
--    - Follow the installation wizard
-- 
-- 2. OR Download from: https://postgis.net/windows_downloads/
--    - Download the appropriate version for your PostgreSQL
--    - Run the installer
-- 
-- After installation, restart PostgreSQL service and run this script.
-- Run this as a superuser on your gnaf_db database

-- Try to create PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Optional: topology extension (comment out if not needed)
-- CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Verify PostGIS installation
SELECT PostGIS_Version();

-- If you get an error, PostGIS is not installed. See instructions above.

-- ============================================
-- Step 2: Add Geometry Columns to Existing Tables
-- ============================================

SET search_path TO gnaf, public;

-- Add geometry column to ADDRESS_DEFAULT_GEOCODE table
-- This table contains the primary geocoded coordinates for each address
ALTER TABLE address_default_geocode 
ADD COLUMN IF NOT EXISTS geom geometry(Point, 4326);

COMMENT ON COLUMN address_default_geocode.geom IS 'Point geometry in WGS84 (SRID 4326) coordinate system';

-- Add geometry column to ADDRESS_SITE_GEOCODE table
-- This table contains site-level geocodes
ALTER TABLE address_site_geocode 
ADD COLUMN IF NOT EXISTS geom geometry(Point, 4326);

COMMENT ON COLUMN address_site_geocode.geom IS 'Point geometry in WGS84 (SRID 4326) coordinate system';

-- If you have custom tables (from setup_gnaf_database.sql):
-- Add to postcodes table
ALTER TABLE IF EXISTS postcodes 
ADD COLUMN IF NOT EXISTS geom geometry(Point, 4326);

-- Add to addresses table
ALTER TABLE IF EXISTS addresses 
ADD COLUMN IF NOT EXISTS geom geometry(Point, 4326);

-- ============================================
-- Step 3: Populate Geometry Columns from Lat/Long
-- ============================================

-- Update ADDRESS_DEFAULT_GEOCODE geometry
UPDATE address_default_geocode 
SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
WHERE longitude IS NOT NULL 
  AND latitude IS NOT NULL
  AND geom IS NULL;

-- Update ADDRESS_SITE_GEOCODE geometry
UPDATE address_site_geocode 
SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
WHERE longitude IS NOT NULL 
  AND latitude IS NOT NULL
  AND geom IS NULL;

-- Update custom postcodes table (if exists)
UPDATE postcodes 
SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
WHERE longitude IS NOT NULL 
  AND latitude IS NOT NULL
  AND geom IS NULL
  AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'gnaf' AND table_name = 'postcodes');

-- Update custom addresses table (if exists)
UPDATE addresses 
SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
WHERE longitude IS NOT NULL 
  AND latitude IS NOT NULL
  AND geom IS NULL
  AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'gnaf' AND table_name = 'addresses');

-- ============================================
-- Step 4: Create Spatial Indexes
-- ============================================
-- Spatial indexes dramatically improve query performance

-- Index on ADDRESS_DEFAULT_GEOCODE
DROP INDEX IF EXISTS idx_address_default_geocode_geom;
CREATE INDEX idx_address_default_geocode_geom 
ON address_default_geocode USING GIST(geom);

-- Index on ADDRESS_SITE_GEOCODE
DROP INDEX IF EXISTS idx_address_site_geocode_geom 
ON address_site_geocode USING GIST(geom);

-- Index on custom tables (if they exist)
DROP INDEX IF EXISTS idx_postcodes_geom;
CREATE INDEX IF NOT EXISTS idx_postcodes_geom 
ON postcodes USING GIST(geom);

DROP INDEX IF EXISTS idx_addresses_geom;
CREATE INDEX IF NOT EXISTS idx_addresses_geom 
ON addresses USING GIST(geom);

-- ============================================
-- Step 5: Verify Setup
-- ============================================

-- Check geometry column registration
SELECT f_table_schema, f_table_name, f_geometry_column, srid, type
FROM geometry_columns
WHERE f_table_schema = 'gnaf';

-- Count geocoded addresses
SELECT 
    'ADDRESS_DEFAULT_GEOCODE' as table_name,
    COUNT(*) as total_records,
    COUNT(geom) as geocoded_records,
    ROUND(100.0 * COUNT(geom) / COUNT(*), 2) as percent_geocoded
FROM address_default_geocode
UNION ALL
SELECT 
    'ADDRESS_SITE_GEOCODE' as table_name,
    COUNT(*) as total_records,
    COUNT(geom) as geocoded_records,
    ROUND(100.0 * COUNT(geom) / COUNT(*), 2) as percent_geocoded
FROM address_site_geocode;

-- ============================================
-- Step 6: Create Helper Functions
-- ============================================

-- Function to get distance between two addresses
CREATE OR REPLACE FUNCTION gnaf.get_distance_between_addresses(
    pid1 VARCHAR,
    pid2 VARCHAR
)
RETURNS NUMERIC AS $$
DECLARE
    distance_meters NUMERIC;
BEGIN
    SELECT ST_Distance(
        a1.geom::geography,
        a2.geom::geography
    ) INTO distance_meters
    FROM address_default_geocode a1
    CROSS JOIN address_default_geocode a2
    WHERE a1.address_detail_pid = pid1
      AND a2.address_detail_pid = pid2
      AND a1.geom IS NOT NULL
      AND a2.geom IS NOT NULL;
    
    RETURN distance_meters;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION gnaf.get_distance_between_addresses IS 
'Calculate distance in meters between two addresses using their PIDs';

-- Function to find addresses within radius
CREATE OR REPLACE FUNCTION gnaf.find_addresses_within_radius(
    center_lat NUMERIC,
    center_lon NUMERIC,
    radius_meters NUMERIC
)
RETURNS TABLE(
    address_detail_pid VARCHAR,
    distance_meters NUMERIC,
    latitude NUMERIC,
    longitude NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        adg.address_detail_pid,
        ST_Distance(
            geom::geography,
            ST_SetSRID(ST_MakePoint(center_lon, center_lat), 4326)::geography
        ) as distance_meters,
        adg.latitude,
        adg.longitude
    FROM address_default_geocode adg
    WHERE geom IS NOT NULL
      AND ST_DWithin(
          geom::geography,
          ST_SetSRID(ST_MakePoint(center_lon, center_lat), 4326)::geography,
          radius_meters
      )
    ORDER BY geom <-> ST_SetSRID(ST_MakePoint(center_lon, center_lat), 4326);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION gnaf.find_addresses_within_radius IS 
'Find all addresses within specified radius (meters) of a point';

-- ============================================
-- Step 7: Create Materialized View for Quick Access
-- ============================================

-- Materialized view combining address details with geometry
DROP MATERIALIZED VIEW IF EXISTS gnaf.mv_addresses_geocoded CASCADE;

CREATE MATERIALIZED VIEW gnaf.mv_addresses_geocoded AS
SELECT 
    ad.address_detail_pid,
    ad.building_name,
    ad.flat_number,
    ad.number_first,
    ad.number_last,
    sl.street_name,
    st.name as street_type,
    l.locality_name,
    s.state_abbreviation,
    ad.postcode,
    adg.latitude,
    adg.longitude,
    adg.geom,
    adg.geocode_type_code,
    
    -- Full address string
    CONCAT_WS(', ',
        NULLIF(TRIM(CONCAT_WS(' ', ft.name, ad.flat_number)), ''),
        TRIM(CONCAT_WS(' ',
            ad.number_first,
            CASE WHEN ad.number_last IS NOT NULL THEN CONCAT('-', ad.number_last) END,
            sl.street_name,
            st.name
        )),
        l.locality_name,
        CONCAT(s.state_abbreviation, ' ', ad.postcode)
    ) AS full_address
    
FROM address_detail ad
INNER JOIN address_default_geocode adg ON ad.address_detail_pid = adg.address_detail_pid
LEFT JOIN flat_type_aut ft ON ad.flat_type_code = ft.code
LEFT JOIN street_locality sl ON ad.street_locality_pid = sl.street_locality_pid
LEFT JOIN street_type_aut st ON sl.street_type_code = st.code
LEFT JOIN locality l ON ad.locality_pid = l.locality_pid
LEFT JOIN state s ON l.state_pid = s.state_pid
WHERE adg.geom IS NOT NULL
  AND adg.date_retired IS NULL;

-- Create indexes on the materialized view
CREATE INDEX idx_mv_addresses_geocoded_geom 
ON gnaf.mv_addresses_geocoded USING GIST(geom);

CREATE INDEX idx_mv_addresses_geocoded_pid 
ON gnaf.mv_addresses_geocoded(address_detail_pid);

CREATE INDEX idx_mv_addresses_geocoded_suburb 
ON gnaf.mv_addresses_geocoded(locality_name);

CREATE INDEX idx_mv_addresses_geocoded_postcode 
ON gnaf.mv_addresses_geocoded(postcode);

CREATE INDEX idx_mv_addresses_geocoded_state 
ON gnaf.mv_addresses_geocoded(state_abbreviation);

COMMENT ON MATERIALIZED VIEW gnaf.mv_addresses_geocoded IS 
'Materialized view of all geocoded addresses with full address details';

-- Refresh the materialized view (run this after data updates)
-- REFRESH MATERIALIZED VIEW gnaf.mv_addresses_geocoded;

-- ============================================
-- Setup Complete!
-- ============================================
-- Run the queries in gnaf_geospatial_queries.sql to test your setup
