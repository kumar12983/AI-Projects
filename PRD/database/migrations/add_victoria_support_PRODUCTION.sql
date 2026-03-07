-- ============================================================================
-- Victoria School Catchments - Schema Migration (PRODUCTION VERSION)
-- ============================================================================
-- This script updates the gnaf.school_catchments table to support both NSW
-- and Victoria school catchment data while maintaining backward compatibility.
--
-- PRODUCTION DEPLOYMENT NOTES:
-- 1. Run during maintenance window (estimated 5-10 minutes for 5,000 records)
-- 2. External backup recommended BEFORE running this script
-- 3. Test on staging environment first
-- 4. Monitor disk space (backup table requires same space as original)
-- 5. Have rollback plan ready (see bottom of file)
--
-- Author: GitHub Copilot
-- Date: February 10, 2026
-- Version: 1.1 (Production)
-- ============================================================================

-- ============================================================================
-- PRE-FLIGHT CHECKS
-- ============================================================================

DO $$
DECLARE
    table_exists BOOLEAN;
    row_count INTEGER;
    disk_space TEXT;
BEGIN
    -- Check if table exists
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'gnaf' AND table_name = 'school_catchments'
    ) INTO table_exists;
    
    IF NOT table_exists THEN
        RAISE EXCEPTION 'Table gnaf.school_catchments does not exist. Aborting migration.';
    END IF;
    
    -- Check row count
    SELECT COUNT(*) INTO row_count FROM gnaf.school_catchments;
    
    RAISE NOTICE '========================================================';
    RAISE NOTICE 'PRE-FLIGHT CHECKS';
    RAISE NOTICE '========================================================';
    RAISE NOTICE 'Table exists: YES';
    RAISE NOTICE 'Current row count: %', row_count;
    RAISE NOTICE 'Estimated migration time: % minutes', ROUND((row_count / 1000.0) * 2);
    RAISE NOTICE '========================================================';
    
    -- Warn if production data
    IF row_count > 1000 THEN
        RAISE NOTICE 'WARNING: Large dataset detected. Ensure you have:';
        RAISE NOTICE '  1. Created external backup via pg_dump';
        RAISE NOTICE '  2. Tested migration on staging environment';
        RAISE NOTICE '  3. Scheduled maintenance window';
        RAISE NOTICE '  4. Informed stakeholders of potential downtime';
        RAISE NOTICE '';
        RAISE NOTICE 'The migration will begin in 5 seconds...';
        RAISE NOTICE 'Press Ctrl+C to cancel if not ready.';
        PERFORM pg_sleep(5);
    END IF;
END $$;

-- ============================================================================
-- Start transaction
-- ============================================================================
BEGIN;

-- Lock table to prevent writes during migration (recommended for production)
-- LOCK TABLE gnaf.school_catchments IN ACCESS EXCLUSIVE MODE;
-- Note: Uncomment above line if you need to prevent concurrent writes
-- This will block all reads/writes until migration completes

-- ============================================================================
-- Step 1: Create internal backup (for quick rollback)
-- ============================================================================

DO $$
DECLARE
    backup_table_name TEXT;
    record_count INTEGER;
    table_size TEXT;
BEGIN
    -- Generate backup table name with timestamp
    backup_table_name := 'school_catchments_backup_' || TO_CHAR(NOW(), 'YYYYMMDD_HH24MISS');
    
    -- Check available disk space
    SELECT pg_size_pretty(pg_total_relation_size('gnaf.school_catchments')) INTO table_size;
    
    RAISE NOTICE 'Creating backup table: gnaf.%', backup_table_name;
    RAISE NOTICE 'Original table size: %', table_size;
    
    -- Create backup with all indexes and constraints
    EXECUTE format('CREATE TABLE gnaf.%I (LIKE gnaf.school_catchments INCLUDING ALL)', backup_table_name);
    
    -- Copy data
    EXECUTE format('INSERT INTO gnaf.%I SELECT * FROM gnaf.school_catchments', backup_table_name);
    
    -- Get count
    EXECUTE format('SELECT COUNT(*) FROM gnaf.%I', backup_table_name) INTO record_count;
    
    RAISE NOTICE '✓ BACKUP CREATED: gnaf.%', backup_table_name;
    RAISE NOTICE '✓ Records backed up: %', record_count;
    
    -- Store backup name in a comment for rollback reference
    EXECUTE format('COMMENT ON TABLE gnaf.%I IS ''Migration backup created at %s UTC. Original table: gnaf.school_catchments''', 
                   backup_table_name, TO_CHAR(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS'));
END $$;

-- ============================================================================
-- Step 2: Fix geometry SRID if needed (critical for geopandas loading)
-- ============================================================================

DO $$
DECLARE
    current_srid INTEGER;
BEGIN
    -- Check current SRID
    SELECT Find_SRID('gnaf', 'school_catchments', 'geometry') INTO current_srid;
    
    RAISE NOTICE 'Current geometry SRID: %', current_srid;
    
    -- Only update if SRID is not 4326
    IF current_srid != 4326 THEN
        RAISE NOTICE 'Updating geometry SRID from % to 4326...', current_srid;
        
        -- UpdateGeometrySRID will fail if views depend on geometry column
        -- So we don't create views until later in the migration
        PERFORM UpdateGeometrySRID('gnaf', 'school_catchments', 'geometry', 4326);
        
        RAISE NOTICE '✓ Geometry SRID updated to 4326';
    ELSE
        RAISE NOTICE '✓ Geometry SRID already correct (4326)';
    END IF;
    
EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'Failed to update SRID: %. Continuing migration...', SQLERRM;
    RAISE NOTICE 'You may need to run fix_geometry_srid.py manually before loading Victoria data';
END $$;

-- ============================================================================
-- Step 3: Add new columns (non-blocking, safe for production)
-- ============================================================================

-- Geographic/Administrative columns
ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS state VARCHAR(3);

ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS boundary_year INTEGER;

-- Victoria-specific columns
ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS campus_name VARCHAR(255);

ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS year_level_code VARCHAR(10);

ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS entity_code INTEGER;

-- Computed centroid columns (for performance)
ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS centroid_lat DOUBLE PRECISION;

ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS centroid_lng DOUBLE PRECISION;

-- Data source tracking
ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS data_source VARCHAR(50);

-- Timestamp columns
ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- NSW-specific columns
ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS use_id VARCHAR(50);

ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS add_date VARCHAR(8);

ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS priority VARCHAR(10);

-- Primary key column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'gnaf' 
        AND table_name = 'school_catchments' 
        AND column_name = 'catchment_id'
    ) THEN
        ALTER TABLE gnaf.school_catchments ADD COLUMN catchment_id SERIAL;
        
        BEGIN
            ALTER TABLE gnaf.school_catchments ADD PRIMARY KEY (catchment_id);
        EXCEPTION WHEN others THEN
            CREATE UNIQUE INDEX IF NOT EXISTS idx_catchment_id_unique 
            ON gnaf.school_catchments (catchment_id);
        END;
    END IF;
END $$;

-- Year level columns
ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS kindergart VARCHAR(1);

ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS year1 VARCHAR(1);

ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS year2 VARCHAR(1);

ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS year3 VARCHAR(1);

ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS year4 VARCHAR(1);

ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS year5 VARCHAR(1);

ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS year6 VARCHAR(1);

ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS year7 VARCHAR(1);

ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS year8 VARCHAR(1);

ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS year9 VARCHAR(1);

ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS year10 VARCHAR(1);

ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS year11 VARCHAR(1);

ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS year12 VARCHAR(1);

-- ============================================================================
-- Step 4: Update existing data (batched for large datasets)
-- ============================================================================

-- Set state for existing NSW records (batched to avoid long locks)
DO $$
DECLARE
    batch_size INTEGER := 1000;
    total_updated INTEGER := 0;
    rows_updated INTEGER;
BEGIN
    LOOP
        UPDATE gnaf.school_catchments
        SET state = 'NSW'
        WHERE state IS NULL
        AND catchment_id IN (
            SELECT catchment_id 
            FROM gnaf.school_catchments 
            WHERE state IS NULL 
            LIMIT batch_size
        );
        
        GET DIAGNOSTICS rows_updated = ROW_COUNT;
        total_updated := total_updated + rows_updated;
        
        EXIT WHEN rows_updated = 0;
        
        -- Brief pause between batches to allow other queries
        PERFORM pg_sleep(0.1);
    END LOOP;
    
    RAISE NOTICE '✓ Updated % records with state=NSW', total_updated;
END $$;

-- Set boundary year
UPDATE gnaf.school_catchments
SET boundary_year = 2024
WHERE boundary_year IS NULL;

-- Set data source
UPDATE gnaf.school_catchments
SET data_source = 'NSW_DET'
WHERE data_source IS NULL AND state = 'NSW';

-- Copy school_id to use_id
UPDATE gnaf.school_catchments
SET use_id = school_id
WHERE use_id IS NULL AND state = 'NSW';

-- Calculate centroids (batched)
DO $$
DECLARE
    batch_size INTEGER := 500;
    total_updated INTEGER := 0;
    rows_updated INTEGER;
BEGIN
    LOOP
        UPDATE gnaf.school_catchments
        SET 
            centroid_lat = ST_Y(ST_Centroid(geometry)),
            centroid_lng = ST_X(ST_Centroid(geometry))
        WHERE (centroid_lat IS NULL OR centroid_lng IS NULL)
        AND catchment_id IN (
            SELECT catchment_id 
            FROM gnaf.school_catchments 
            WHERE centroid_lat IS NULL OR centroid_lng IS NULL
            LIMIT batch_size
        );
        
        GET DIAGNOSTICS rows_updated = ROW_COUNT;
        total_updated := total_updated + rows_updated;
        
        EXIT WHEN rows_updated = 0;
        
        PERFORM pg_sleep(0.1);
    END LOOP;
    
    RAISE NOTICE '✓ Calculated centroids for % records', total_updated;
END $$;

-- ============================================================================
-- Step 5: Add constraints (validate data first)
-- ============================================================================

-- Validate data before adding NOT NULL constraints
DO $$
DECLARE
    null_states INTEGER;
    null_years INTEGER;
    null_sources INTEGER;
BEGIN
    SELECT COUNT(*) INTO null_states FROM gnaf.school_catchments WHERE state IS NULL;
    SELECT COUNT(*) INTO null_years FROM gnaf.school_catchments WHERE boundary_year IS NULL;
    SELECT COUNT(*) INTO null_sources FROM gnaf.school_catchments WHERE data_source IS NULL;
    
    IF null_states > 0 OR null_years > 0 OR null_sources > 0 THEN
        RAISE EXCEPTION 'Data validation failed: state=% NULL, boundary_year=% NULL, data_source=% NULL', 
                        null_states, null_years, null_sources;
    END IF;
    
    RAISE NOTICE '✓ Data validation passed';
END $$;

-- State constraint
ALTER TABLE gnaf.school_catchments 
DROP CONSTRAINT IF EXISTS chk_state;

ALTER TABLE gnaf.school_catchments 
ADD CONSTRAINT chk_state 
CHECK (state IN ('NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'NT', 'ACT'));

-- Year level value constraints
ALTER TABLE gnaf.school_catchments 
DROP CONSTRAINT IF EXISTS chk_year_values;

ALTER TABLE gnaf.school_catchments 
ADD CONSTRAINT chk_year_values CHECK (
    kindergart IN ('Y', 'N', NULL) AND
    year1 IN ('Y', 'N', NULL) AND
    year2 IN ('Y', 'N', NULL) AND
    year3 IN ('Y', 'N', NULL) AND
    year4 IN ('Y', 'N', NULL) AND
    year5 IN ('Y', 'N', NULL) AND
    year6 IN ('Y', 'N', NULL) AND
    year7 IN ('Y', 'N', NULL) AND
    year8 IN ('Y', 'N', NULL) AND
    year9 IN ('Y', 'N', NULL) AND
    year10 IN ('Y', 'N', NULL) AND
    year11 IN ('Y', 'N', NULL) AND
    year12 IN ('Y', 'N', NULL)
);

-- NOT NULL constraints
ALTER TABLE gnaf.school_catchments 
ALTER COLUMN state SET NOT NULL;

ALTER TABLE gnaf.school_catchments 
ALTER COLUMN boundary_year SET NOT NULL;

ALTER TABLE gnaf.school_catchments 
ALTER COLUMN data_source SET NOT NULL;

-- ============================================================================
-- Step 6: Create indexes (CONCURRENTLY for zero-downtime)
-- ============================================================================

-- Note: CREATE INDEX CONCURRENTLY cannot run inside a transaction block
-- For production, run these AFTER this migration completes
-- See separate file: add_victoria_support_indexes.sql

-- Drop old indexes first (inside transaction is OK)
DROP INDEX IF EXISTS gnaf.idx_school_catchments_state;
DROP INDEX IF EXISTS gnaf.idx_school_catchments_entity_code;
DROP INDEX IF EXISTS gnaf.idx_school_catchments_centroid;
DROP INDEX IF EXISTS gnaf.idx_school_catchments_boundary_year;
DROP INDEX IF EXISTS gnaf.idx_school_catchments_state_type;
DROP INDEX IF EXISTS gnaf.idx_school_catchments_name_trgm;

-- Create basic indexes (non-concurrent, will lock briefly)
CREATE INDEX idx_school_catchments_state 
ON gnaf.school_catchments (state);

CREATE INDEX idx_school_catchments_entity_code 
ON gnaf.school_catchments (entity_code) 
WHERE entity_code IS NOT NULL;

CREATE INDEX idx_school_catchments_centroid 
ON gnaf.school_catchments (centroid_lat, centroid_lng);

CREATE INDEX idx_school_catchments_boundary_year 
ON gnaf.school_catchments (boundary_year);

CREATE INDEX idx_school_catchments_state_type 
ON gnaf.school_catchments (state, school_type);

-- Full-text search index
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX idx_school_catchments_name_trgm 
ON gnaf.school_catchments 
USING GIN (school_name gin_trgm_ops);

-- ============================================================================
-- Step 7: Create helper views
-- ============================================================================

CREATE OR REPLACE VIEW gnaf.vic_school_catchments AS
SELECT 
    catchment_id, school_id, entity_code, school_name, campus_name,
    school_type, year_level_code, boundary_year,
    kindergart, year1, year2, year3, year4, year5, year6,
    year7, year8, year9, year10, year11, year12,
    geometry, centroid_lat, centroid_lng,
    data_source, created_at, updated_at
FROM gnaf.school_catchments
WHERE state = 'VIC';

CREATE OR REPLACE VIEW gnaf.nsw_school_catchments AS
SELECT 
    catchment_id, school_id, use_id, school_name, school_type, add_date,
    kindergart, year1, year2, year3, year4, year5, year6,
    year7, year8, year9, year10, year11, year12,
    priority, geometry, centroid_lat, centroid_lng,
    data_source, created_at, updated_at
FROM gnaf.school_catchments
WHERE state = 'NSW';

CREATE OR REPLACE VIEW gnaf.school_catchments_summary AS
SELECT 
    state, school_type, boundary_year,
    COUNT(*) as catchment_count,
    COUNT(DISTINCT school_id) as unique_schools,
    COUNT(DISTINCT CASE WHEN kindergart = 'Y' THEN school_id END) as kindergarten_schools,
    COUNT(DISTINCT CASE WHEN year7 = 'Y' THEN school_id END) as year7_schools,
    COUNT(DISTINCT CASE WHEN year12 = 'Y' THEN school_id END) as year12_schools
FROM gnaf.school_catchments
GROUP BY state, school_type, boundary_year
ORDER BY state, school_type;

-- ============================================================================
-- Step 8: Update comments
-- ============================================================================

COMMENT ON TABLE gnaf.school_catchments IS 'Unified school catchment boundaries for NSW, Victoria, and other Australian states. Supports spatial queries to find schools serving specific addresses.';

COMMENT ON COLUMN gnaf.school_catchments.state IS 'Australian state/territory code (NSW, VIC, QLD, etc.)';
COMMENT ON COLUMN gnaf.school_catchments.campus_name IS 'Campus name (Victoria specific)';
COMMENT ON COLUMN gnaf.school_catchments.entity_code IS 'Victoria education department entity code';
COMMENT ON COLUMN gnaf.school_catchments.year_level_code IS 'Victoria year level code (P6, 7-12)';
COMMENT ON COLUMN gnaf.school_catchments.boundary_year IS 'Year of boundary data';
COMMENT ON COLUMN gnaf.school_catchments.centroid_lat IS 'Cached centroid latitude';
COMMENT ON COLUMN gnaf.school_catchments.centroid_lng IS 'Cached centroid longitude';
COMMENT ON COLUMN gnaf.school_catchments.data_source IS 'Data source (NSW_DET, DATAVIC)';

-- ============================================================================
-- Step 9: Analyze table for query planner
-- ============================================================================

ANALYZE gnaf.school_catchments;

-- ============================================================================
-- Step 10: Final validation and summary
-- ============================================================================

DO $$
DECLARE
    total_count INTEGER;
    nsw_count INTEGER;
    vic_count INTEGER;
    validation_errors INTEGER := 0;
    invalid_geoms INTEGER;
    missing_centroids INTEGER;
BEGIN
    -- Count records
    SELECT COUNT(*) INTO total_count FROM gnaf.school_catchments;
    SELECT COUNT(*) INTO nsw_count FROM gnaf.school_catchments WHERE state = 'NSW';
    SELECT COUNT(*) INTO vic_count FROM gnaf.school_catchments WHERE state = 'VIC';
    
    -- Validation checks
    SELECT COUNT(*) INTO invalid_geoms 
    FROM gnaf.school_catchments 
    WHERE NOT ST_IsValid(geometry);
    
    SELECT COUNT(*) INTO missing_centroids 
    FROM gnaf.school_catchments 
    WHERE centroid_lat IS NULL OR centroid_lng IS NULL;
    
    IF invalid_geoms > 0 THEN
        RAISE WARNING 'Found % invalid geometries', invalid_geoms;
        validation_errors := validation_errors + 1;
    END IF;
    
    IF missing_centroids > 0 THEN
        RAISE WARNING 'Found % records with missing centroids', missing_centroids;
        validation_errors := validation_errors + 1;
    END IF;
    
    RAISE NOTICE '';
    RAISE NOTICE '========================================================';
    RAISE NOTICE 'MIGRATION COMPLETE';
    RAISE NOTICE '========================================================';
    RAISE NOTICE 'Total catchments: %', total_count;
    RAISE NOTICE 'NSW catchments: %', nsw_count;
    RAISE NOTICE 'VIC catchments: %', vic_count;
    RAISE NOTICE 'Validation errors: %', validation_errors;
    RAISE NOTICE '';
    RAISE NOTICE 'Schema updates:';
    RAISE NOTICE '  ✓ Added multi-state support columns';
    RAISE NOTICE '  ✓ Updated existing NSW data';
    RAISE NOTICE '  ✓ Created constraints and indexes';
    RAISE NOTICE '  ✓ Created helper views';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '  1. Run add_victoria_support_indexes.sql (CONCURRENTLY)';
    RAISE NOTICE '  2. Load Victoria data: load_victoria_catchments.py';
    RAISE NOTICE '  3. Update application code for multi-state support';
    RAISE NOTICE '  4. Run smoke tests on staging';
    RAISE NOTICE '  5. Deploy to production';
    RAISE NOTICE '========================================================';
    
    IF validation_errors > 0 THEN
        RAISE WARNING 'Migration completed with warnings. Review validation errors above.';
    END IF;
END $$;

-- Commit transaction
COMMIT;

-- ============================================================================
-- POST-MIGRATION MONITORING QUERIES
-- ============================================================================

/*
-- Check table size after migration
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS indexes_size
FROM pg_tables
WHERE schemaname = 'gnaf' AND tablename LIKE 'school_catchments%'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Monitor query performance
SELECT 
    query,
    mean_exec_time,
    calls,
    total_exec_time
FROM pg_stat_statements
WHERE query LIKE '%school_catchments%'
ORDER BY mean_exec_time DESC
LIMIT 10;
*/

-- ============================================================================
-- ROLLBACK PROCEDURE (if migration fails)
-- ============================================================================

/*
-- Step 1: Find the backup table
SELECT tablename 
FROM pg_tables 
WHERE schemaname = 'gnaf' 
AND tablename LIKE 'school_catchments_backup_%'
ORDER BY tablename DESC 
LIMIT 1;

-- Step 2: Restore from backup
BEGIN;

-- Drop current table
DROP TABLE IF EXISTS gnaf.school_catchments CASCADE;

-- Restore from backup (replace YYYYMMDD_HHMMSS with actual backup timestamp)
ALTER TABLE gnaf.school_catchments_backup_YYYYMMDD_HHMMSS 
RENAME TO school_catchments;

-- Verify
SELECT COUNT(*) FROM gnaf.school_catchments;

COMMIT;

-- Step 3: Clean up
-- DROP TABLE gnaf.school_catchments_backup_YYYYMMDD_HHMMSS;
*/
