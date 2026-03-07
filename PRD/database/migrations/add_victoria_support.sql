-- ============================================================================
-- Victoria School Catchments - Schema Migration
-- ============================================================================
-- This script updates the gnaf.school_catchments table to support both NSW
-- and Victoria school catchment data while maintaining backward compatibility.
--
-- Author: GitHub Copilot
-- Date: February 10, 2026
-- Version: 1.0
--
-- IMPORTANT: Create a backup before running this migration!
--   pg_dump -h localhost -U postgres -d gnaf_db -t gnaf.school_catchments > backup.sql
-- ============================================================================

-- Start transaction
BEGIN;

-- ============================================================================
-- Step 1: Backup existing data
-- ============================================================================

DO $$
DECLARE
    backup_table_name TEXT;
    record_count INTEGER;
BEGIN
    -- Generate backup table name with timestamp
    backup_table_name := 'school_catchments_backup_' || TO_CHAR(NOW(), 'YYYYMMDD_HH24MISS');
    
    -- Create backup
    EXECUTE format('CREATE TABLE gnaf.%I AS SELECT * FROM gnaf.school_catchments', backup_table_name);
    
    -- Get count
    EXECUTE format('SELECT COUNT(*) FROM gnaf.%I', backup_table_name) INTO record_count;
    
    RAISE NOTICE '========================================================';
    RAISE NOTICE 'BACKUP CREATED: gnaf.%', backup_table_name;
    RAISE NOTICE 'Records backed up: %', record_count;
    RAISE NOTICE '========================================================';
END $$;

-- ============================================================================
-- Step 2: Add new columns for Victoria data support
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

-- NSW-specific columns (if they don't already exist)
ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS use_id VARCHAR(50);

ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS add_date VARCHAR(8);

ALTER TABLE gnaf.school_catchments 
ADD COLUMN IF NOT EXISTS priority VARCHAR(10);

-- Primary key column (if it doesn't exist)
DO $$
BEGIN
    -- Add catchment_id column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'gnaf' 
        AND table_name = 'school_catchments' 
        AND column_name = 'catchment_id'
    ) THEN
        ALTER TABLE gnaf.school_catchments ADD COLUMN catchment_id SERIAL;
        
        -- Try to add primary key constraint
        BEGIN
            ALTER TABLE gnaf.school_catchments ADD PRIMARY KEY (catchment_id);
        EXCEPTION WHEN others THEN
            -- If primary key already exists on another column, create unique index instead
            CREATE UNIQUE INDEX IF NOT EXISTS idx_catchment_id_unique 
            ON gnaf.school_catchments (catchment_id);
        END;
    END IF;
END $$;

-- Year level columns (NSW approach - may already exist from NSW data)
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

-- New columns added successfully

-- ============================================================================
-- Step 3: Update existing NSW data with new column values
-- ============================================================================

-- Set state for all existing NSW records
UPDATE gnaf.school_catchments
SET state = 'NSW'
WHERE state IS NULL;

-- Set boundary year (assuming 2024 for existing data, adjust if needed)
UPDATE gnaf.school_catchments
SET boundary_year = 2024
WHERE boundary_year IS NULL;

-- Set data source for existing records
UPDATE gnaf.school_catchments
SET data_source = 'NSW_DET'
WHERE data_source IS NULL;

-- Copy school_id to use_id for NSW records
UPDATE gnaf.school_catchments
SET use_id = school_id
WHERE use_id IS NULL AND state = 'NSW';

-- Calculate centroids for existing records
UPDATE gnaf.school_catchments
SET 
    centroid_lat = ST_Y(ST_Centroid(geometry)),
    centroid_lng = ST_X(ST_Centroid(geometry))
WHERE centroid_lat IS NULL OR centroid_lng IS NULL;

-- Existing NSW data updated

-- ============================================================================
-- Step 4: Add constraints
-- ============================================================================

-- State constraint
ALTER TABLE gnaf.school_catchments 
DROP CONSTRAINT IF EXISTS chk_state;

ALTER TABLE gnaf.school_catchments 
ADD CONSTRAINT chk_state 
CHECK (state IN ('NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'NT', 'ACT'));

-- Year level value constraints (existing columns)
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

-- NOT NULL constraints for critical columns
ALTER TABLE gnaf.school_catchments 
ALTER COLUMN state SET NOT NULL;

ALTER TABLE gnaf.school_catchments 
ALTER COLUMN boundary_year SET NOT NULL;

ALTER TABLE gnaf.school_catchments 
ALTER COLUMN data_source SET NOT NULL;

-- Constraints added

-- ============================================================================
-- Step 5: Create/Update indexes for performance
-- ============================================================================

-- Drop existing indexes if they exist
DROP INDEX IF EXISTS gnaf.idx_school_catchments_state;
DROP INDEX IF EXISTS gnaf.idx_school_catchments_entity_code;
DROP INDEX IF EXISTS gnaf.idx_school_catchments_centroid;
DROP INDEX IF EXISTS gnaf.idx_school_catchments_boundary_year;
DROP INDEX IF EXISTS gnaf.idx_school_catchments_state_type;
DROP INDEX IF EXISTS gnaf.idx_school_catchments_name_trgm;

-- State index
CREATE INDEX idx_school_catchments_state 
ON gnaf.school_catchments (state);

-- Entity code index (for Victoria data)
CREATE INDEX idx_school_catchments_entity_code 
ON gnaf.school_catchments (entity_code) 
WHERE entity_code IS NOT NULL;

-- Centroid index (for distance queries)
CREATE INDEX idx_school_catchments_centroid 
ON gnaf.school_catchments (centroid_lat, centroid_lng);

-- Boundary year index
CREATE INDEX idx_school_catchments_boundary_year 
ON gnaf.school_catchments (boundary_year);

-- Composite index for common queries
CREATE INDEX idx_school_catchments_state_type 
ON gnaf.school_catchments (state, school_type);

-- Full-text search on school names (requires pg_trgm extension)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX idx_school_catchments_name_trgm 
ON gnaf.school_catchments 
USING GIN (school_name gin_trgm_ops);

-- Indexes created

-- ============================================================================
-- Step 6: Create helper views
-- ============================================================================

-- View for Victoria catchments only
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

-- View for NSW catchments only (backward compatibility)
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

-- Summary view for all catchments
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

-- Helper views created

-- ============================================================================
-- Step 7: Update comments for documentation
-- ============================================================================

COMMENT ON TABLE gnaf.school_catchments IS 'Unified school catchment boundaries for NSW, Victoria, and other Australian states. Supports spatial queries to find schools serving specific addresses.';

COMMENT ON COLUMN gnaf.school_catchments.state IS 'Australian state/territory code (NSW, VIC, QLD, etc.)';
COMMENT ON COLUMN gnaf.school_catchments.campus_name IS 'Campus name (Victoria specific, same as school_name for most)';
COMMENT ON COLUMN gnaf.school_catchments.entity_code IS 'Victoria education department entity code';
COMMENT ON COLUMN gnaf.school_catchments.year_level_code IS 'Victoria year level code (P6 for primary, 7-12 for secondary)';
COMMENT ON COLUMN gnaf.school_catchments.boundary_year IS 'Year of boundary data (2024)';
COMMENT ON COLUMN gnaf.school_catchments.centroid_lat IS 'Cached centroid latitude for distance calculations';
COMMENT ON COLUMN gnaf.school_catchments.centroid_lng IS 'Cached centroid longitude for distance calculations';
COMMENT ON COLUMN gnaf.school_catchments.data_source IS 'Data source (NSW_DET, DATAVIC, etc.)';

-- ============================================================================
-- Step 8: Analyze tables for query optimization
-- ============================================================================

ANALYZE gnaf.school_catchments;

-- ============================================================================
-- Step 9: Display migration summary
-- ============================================================================

DO $$
DECLARE
    total_count INTEGER;
    nsw_count INTEGER;
    vic_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_count FROM gnaf.school_catchments;
    SELECT COUNT(*) INTO nsw_count FROM gnaf.school_catchments WHERE state = 'NSW';
    SELECT COUNT(*) INTO vic_count FROM gnaf.school_catchments WHERE state = 'VIC';
    
    RAISE NOTICE '';
    RAISE NOTICE '========================================================';
    RAISE NOTICE 'MIGRATION COMPLETE';
    RAISE NOTICE '========================================================';
    RAISE NOTICE 'Total catchments: %', total_count;
    RAISE NOTICE 'NSW catchments: %', nsw_count;
    RAISE NOTICE 'VIC catchments: %', vic_count;
    RAISE NOTICE '';
    RAISE NOTICE 'Schema updates:';
    RAISE NOTICE '  - Added state, boundary_year, campus_name columns';
    RAISE NOTICE '  - Added entity_code, year_level_code (Victoria)';
    RAISE NOTICE '  - Added centroid_lat, centroid_lng (cached)';
    RAISE NOTICE '  - Added data_source, timestamps';
    RAISE NOTICE '  - Created indexes for performance';
    RAISE NOTICE '  - Created helper views';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '  1. Run load_victoria_catchments.py to import VIC data';
    RAISE NOTICE '  2. Update application queries to filter by state';
    RAISE NOTICE '  3. Test spatial queries with both NSW and VIC data';
    RAISE NOTICE '========================================================';
END $$;

-- Commit transaction
COMMIT;

-- ============================================================================
-- Verification queries (run separately after migration)
-- ============================================================================

/*
-- Check schema
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'gnaf' 
AND table_name = 'school_catchments'
ORDER BY ordinal_position;

-- Check indexes
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'gnaf'
AND tablename = 'school_catchments';

-- Check constraints
SELECT 
    conname,
    pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'gnaf.school_catchments'::regclass;

-- Check data by state
SELECT 
    state,
    school_type,
    COUNT(*) as count
FROM gnaf.school_catchments
GROUP BY state, school_type
ORDER BY state, school_type;

-- Test spatial query
SELECT 
    school_name,
    school_type,
    state,
    ST_Area(geometry::geography) / 1000000 as area_km2
FROM gnaf.school_catchments
WHERE state = 'NSW'
LIMIT 5;
*/
