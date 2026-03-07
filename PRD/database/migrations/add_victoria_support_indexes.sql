-- ============================================================================
-- Victoria School Catchments - Concurrent Index Creation
-- ============================================================================
-- Run this AFTER add_victoria_support_PRODUCTION.sql completes
-- These indexes are created CONCURRENTLY for zero-downtime
--
-- IMPORTANT: 
-- - Cannot run inside a transaction
-- - Run during low-traffic period if possible
-- - Monitor progress with pg_stat_progress_create_index
-- ============================================================================

-- Enable extension if not already enabled
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================================
-- Create indexes CONCURRENTLY (won't block reads/writes)
-- ============================================================================

-- State index (if not already created by main migration)
DROP INDEX IF EXISTS gnaf.idx_school_catchments_state;
CREATE INDEX CONCURRENTLY idx_school_catchments_state 
ON gnaf.school_catchments (state);

-- Entity code index (partial, for Victoria data)
DROP INDEX IF EXISTS gnaf.idx_school_catchments_entity_code;
CREATE INDEX CONCURRENTLY idx_school_catchments_entity_code 
ON gnaf.school_catchments (entity_code) 
WHERE entity_code IS NOT NULL;

-- Centroid index (for distance calculations)
DROP INDEX IF EXISTS gnaf.idx_school_catchments_centroid;
CREATE INDEX CONCURRENTLY idx_school_catchments_centroid 
ON gnaf.school_catchments (centroid_lat, centroid_lng);

-- Boundary year index
DROP INDEX IF EXISTS gnaf.idx_school_catchments_boundary_year;
CREATE INDEX CONCURRENTLY idx_school_catchments_boundary_year 
ON gnaf.school_catchments (boundary_year);

-- Composite index for common queries
DROP INDEX IF EXISTS gnaf.idx_school_catchments_state_type;
CREATE INDEX CONCURRENTLY idx_school_catchments_state_type 
ON gnaf.school_catchments (state, school_type);

-- Full-text search on school names
DROP INDEX IF EXISTS gnaf.idx_school_catchments_name_trgm;
CREATE INDEX CONCURRENTLY idx_school_catchments_name_trgm 
ON gnaf.school_catchments 
USING GIN (school_name gin_trgm_ops);

-- Spatial index (most critical for performance)
-- This might already exist, but recreate to ensure proper coverage
DROP INDEX IF EXISTS gnaf.idx_school_catchments_geom;
CREATE INDEX CONCURRENTLY idx_school_catchments_geom 
ON gnaf.school_catchments 
USING GIST (geometry);

-- ============================================================================
-- Verify indexes created successfully
-- ============================================================================

SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
FROM pg_indexes
WHERE schemaname = 'gnaf'
AND tablename = 'school_catchments'
ORDER BY indexname;

-- ============================================================================
-- Monitor index creation progress (run in separate session)
-- ============================================================================

/*
SELECT 
    phase,
    blocks_total,
    blocks_done,
    tuples_total,
    tuples_done,
    ROUND((blocks_done::numeric / NULLIF(blocks_total, 0)) * 100, 2) as pct_complete
FROM pg_stat_progress_create_index;
*/

-- ============================================================================
-- Analyze table after index creation
-- ============================================================================

ANALYZE gnaf.school_catchments;

\echo 'Concurrent index creation complete!'
