-- ============================================
-- CRITICAL PERFORMANCE OPTIMIZATION INDEXES
-- ============================================
-- These indexes were created during the Australia School Search performance optimization
-- Date: February 8, 2026
-- Issue: Address loading was taking 31+ seconds
-- Solution: Create missing GIST spatial index on geom column
-- Result: Performance improved from 31s to 0.27s (114x faster, 99.1% improvement)
--
-- IMPORTANT: Run these queries when setting up a new database deployment
-- ============================================

SET search_path TO gnaf, public;

-- ============================================
-- Step 1: Verify PostGIS Extension Exists
-- ============================================
-- The geom column must already exist (created by gnaf_geospatial_setup.sql)
-- This script only creates the missing spatial index

SELECT 
    column_name, 
    data_type,
    udt_name
FROM information_schema.columns
WHERE table_schema = 'gnaf'
AND table_name = 'address_default_geocode'
AND column_name = 'geom';

-- Expected output: geom | USER-DEFINED | geometry

-- ============================================
-- Step 2: Create CRITICAL Spatial Index on geom Column
-- ============================================
-- This index is ESSENTIAL for fast spatial queries
-- Without it, queries take 31+ seconds
-- With it, queries take < 0.3 seconds
--
-- Build time: ~60-90 seconds for 16.7 million rows
-- Index size: ~664 MB
-- Type: GIST (Generalized Search Tree for spatial data)

-- Use CONCURRENTLY to avoid locking the table during creation
-- Note: CONCURRENTLY requires autocommit mode (cannot be run in a transaction)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_address_default_geocode_geom 
ON gnaf.address_default_geocode USING GIST (geom);

-- ============================================
-- Step 3: Verify Index Creation
-- ============================================

-- Check if index was created successfully
SELECT 
    indexname,
    indexdef,
    pg_size_pretty(pg_relation_size('gnaf.' || indexname)) as index_size
FROM pg_indexes
WHERE schemaname = 'gnaf'
AND tablename = 'address_default_geocode'
AND indexname = 'idx_address_default_geocode_geom';

-- Expected output:
-- indexname: idx_address_default_geocode_geom
-- indexdef: CREATE INDEX idx_address_default_geocode_geom ON gnaf.address_default_geocode USING gist (geom)
-- index_size: ~664 MB

-- ============================================
-- Step 4: Analyze Table for Query Planner
-- ============================================
-- Update statistics so PostgreSQL can use the new index effectively
ANALYZE gnaf.address_default_geocode;

-- ============================================
-- Step 5: Test Query Performance
-- ============================================
-- Test query should now use the spatial index and be very fast

EXPLAIN (ANALYZE, BUFFERS) 
SELECT 
    ad.address_detail_pid,
    adg.latitude,
    adg.longitude,
    ROUND(
        (ST_Distance(
            adg.geom::geography,
            ST_SetSRID(ST_MakePoint(151.0423504, -33.7811846), 4326)::geography
        ) / 1000.0)::numeric,
        2
    ) as distance_km
FROM gnaf.address_default_geocode adg
INNER JOIN gnaf.address_detail ad ON ad.address_detail_pid = adg.address_detail_pid
WHERE adg.geom IS NOT NULL
    AND ST_DWithin(
        adg.geom,
        ST_SetSRID(ST_MakePoint(151.0423504, -33.7811846), 4326),
        0.045  -- approximately 5km in degrees
    )
ORDER BY adg.geom <-> ST_SetSRID(ST_MakePoint(151.0423504, -33.7811846), 4326)
LIMIT 100;

-- Look for "Index Scan using idx_address_default_geocode_geom" in the output
-- Execution time should be < 500ms

-- ============================================
-- Step 6: OPTIONAL - Remove Redundant Index (Save 664 MB)
-- ============================================
-- If idx_address_geocode_point exists, it's redundant
-- It indexes a computed expression: ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
-- Our new idx_address_default_geocode_geom is faster and serves the same purpose
--
-- CAUTION: Only drop if ALL queries have been updated to use geom column
-- Check which index is being used first:

SELECT 
    indexname,
    pg_size_pretty(pg_relation_size('gnaf.' || indexname)) as size
FROM pg_indexes
WHERE schemaname = 'gnaf'
AND tablename = 'address_default_geocode'
AND indexname = 'idx_address_geocode_point';

-- If it exists and you've verified all queries use geom column, drop it:
-- DROP INDEX CONCURRENTLY IF EXISTS gnaf.idx_address_geocode_point;

-- ============================================
-- Step 7: Create Indexes on Related Tables (if not already created)
-- ============================================

-- These indexes support the address query joins
-- Most should already exist, but verify:

-- Address detail indexes
CREATE INDEX IF NOT EXISTS idx_address_detail_active 
ON gnaf.address_detail(address_detail_pid) 
WHERE date_retired IS NULL;

CREATE INDEX IF NOT EXISTS idx_address_street_locality_pid 
ON gnaf.address_detail(street_locality_pid);

CREATE INDEX IF NOT EXISTS idx_address_locality_pid 
ON gnaf.address_detail(locality_pid);

-- Address geocode PID index (for joins)
CREATE INDEX IF NOT EXISTS idx_address_geocode_pid 
ON gnaf.address_default_geocode(address_detail_pid);

-- School geometry indexes (for school lookups)
CREATE INDEX IF NOT EXISTS idx_school_geom_acara_sml_id 
ON gnaf.school_geometry(acara_sml_id);

CREATE INDEX IF NOT EXISTS idx_school_geom_5km_buffer 
ON gnaf.school_geometry USING GIST(geom_5km_buffer);

-- Analyze all tables after index creation
ANALYZE gnaf.address_detail;
ANALYZE gnaf.address_default_geocode;
ANALYZE gnaf.school_geometry;

-- ============================================
-- Deployment Verification Checklist
-- ============================================
-- Run these queries to verify the deployment is optimized:

-- 1. Check geom column exists and has data
SELECT 
    COUNT(*) as total_rows,
    COUNT(geom) as rows_with_geom,
    ROUND(100.0 * COUNT(geom) / COUNT(*), 2) as percent_complete
FROM gnaf.address_default_geocode;
-- Expected: ~16.7M rows with ~100% complete

-- 2. List all spatial indexes
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(schemaname||'.'||indexname)) as size
FROM pg_indexes
WHERE schemaname = 'gnaf'
AND (indexname LIKE '%geom%' OR indexdef LIKE '%GIST%')
ORDER BY tablename, indexname;

-- 3. Test query performance on a sample school
DO $$
DECLARE
    start_time timestamp;
    end_time timestamp;
    elapsed_ms numeric;
    row_count integer;
BEGIN
    start_time := clock_timestamp();
    
    SELECT COUNT(*) INTO row_count
    FROM gnaf.address_default_geocode adg
    INNER JOIN gnaf.address_detail ad ON ad.address_detail_pid = adg.address_detail_pid
    WHERE adg.geom IS NOT NULL
        AND ST_DWithin(
            adg.geom,
            ST_SetSRID(ST_MakePoint(151.0423504, -33.7811846), 4326),
            0.045
        )
    LIMIT 100;
    
    end_time := clock_timestamp();
    elapsed_ms := EXTRACT(MILLISECONDS FROM (end_time - start_time));
    
    RAISE NOTICE 'Query returned % rows in % ms', row_count, elapsed_ms;
    
    IF elapsed_ms < 500 THEN
        RAISE NOTICE '✓ EXCELLENT: Query performance is optimal';
    ELSIF elapsed_ms < 2000 THEN
        RAISE NOTICE '✓ GOOD: Query performance is acceptable';
    ELSE
        RAISE NOTICE '⚠ WARNING: Query is slower than expected. Check if spatial index exists.';
    END IF;
END $$;

-- ============================================
-- SUMMARY
-- ============================================
-- Critical index created:
--   - idx_address_default_geocode_geom (GIST on geom column)
--
-- Performance improvement:
--   - Before: 31+ seconds
--   - After: 0.27 seconds
--   - Speedup: 114x faster (99.1% improvement)
--
-- Disk space:
--   - Index size: ~664 MB
--   - Optional savings: Drop idx_address_geocode_point (664 MB)
--
-- Maintenance:
--   - Run ANALYZE periodically for optimal query planning
--   - Monitor index bloat and rebuild if needed
--   - Vacuum tables regularly
-- ============================================
