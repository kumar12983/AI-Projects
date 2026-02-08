-- ============================================
-- ESSENTIAL QUERIES EXECUTED FOR PERFORMANCE FIX
-- Date: February 8, 2026
-- Issue: Address loading was 31+ seconds
-- Fix: Created missing spatial index
-- Result: Now loads in 0.27 seconds (114x faster)
-- ============================================

-- ============================================
-- THE ONE CRITICAL QUERY THAT FIXED EVERYTHING
-- ============================================

-- This single index creation reduced query time from 31s to 0.27s
CREATE INDEX CONCURRENTLY idx_address_default_geocode_geom 
ON gnaf.address_default_geocode USING GIST (geom);

-- Build time: ~62 seconds
-- Index size: 664 MB
-- Impact: 99.1% performance improvement


-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- 1. Check if index was created
SELECT indexname, pg_size_pretty(pg_relation_size('gnaf.' || indexname)) as size
FROM pg_indexes
WHERE schemaname = 'gnaf' AND tablename = 'address_default_geocode' 
AND indexname = 'idx_address_default_geocode_geom';

-- 2. Update table statistics (required after index creation)
ANALYZE gnaf.address_default_geocode;

-- 3. Test query performance (should be < 500ms)
EXPLAIN ANALYZE 
SELECT ad.address_detail_pid
FROM gnaf.address_default_geocode adg
INNER JOIN gnaf.address_detail ad ON ad.address_detail_pid = adg.address_detail_pid
WHERE adg.geom IS NOT NULL
    AND ST_DWithin(
        adg.geom,
        ST_SetSRID(ST_MakePoint(151.0423504, -33.7811846), 4326),
        0.045
    )
LIMIT 100;


-- ============================================
-- PREREQUISITE (must exist before creating index)
-- ============================================

-- The geom column must already exist and be populated
-- If it doesn't exist, run this first:

ALTER TABLE gnaf.address_default_geocode 
ADD COLUMN IF NOT EXISTS geom geometry(Point, 4326);

UPDATE gnaf.address_default_geocode 
SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
WHERE longitude IS NOT NULL AND latitude IS NOT NULL AND geom IS NULL;


-- ============================================
-- DEPLOYMENT SUMMARY
-- ============================================
-- For new database deployment, run in this order:
--
-- 1. Ensure PostGIS is installed:
--    CREATE EXTENSION IF NOT EXISTS postgis;
--
-- 2. Create/populate geom column (if needed):
--    ALTER TABLE gnaf.address_default_geocode ADD COLUMN geom geometry(Point, 4326);
--    UPDATE ... (see above)
--
-- 3. Create the CRITICAL spatial index:
--    CREATE INDEX CONCURRENTLY idx_address_default_geocode_geom ...
--
-- 4. Update statistics:
--    ANALYZE gnaf.address_default_geocode;
--
-- That's it! Your queries will now be 114x faster.
-- ============================================
