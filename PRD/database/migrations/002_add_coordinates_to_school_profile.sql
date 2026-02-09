-- Migration: Add latitude and longitude to school_profile_2025
-- Date: 2026-02-09
-- Description: Adds coordinate columns to school_profile_2025 table and updates them
--              from school_location table using acara_sml_id as the join key
-- Prerequisites: 
--   - gnaf.school_profile_2025 table must exist
--   - gnaf.school_location table must exist and be populated

SET search_path TO gnaf, public;

-- Step 1: Add latitude and longitude columns if they don't exist
DO $$
BEGIN
    -- Add latitude column
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'gnaf' 
        AND table_name = 'school_profile_2025' 
        AND column_name = 'latitude'
    ) THEN
        ALTER TABLE gnaf.school_profile_2025 
        ADD COLUMN latitude NUMERIC(10, 7);
        
        RAISE NOTICE 'Added latitude column to school_profile_2025';
    ELSE
        RAISE NOTICE 'Latitude column already exists in school_profile_2025';
    END IF;
    
    -- Add longitude column
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'gnaf' 
        AND table_name = 'school_profile_2025' 
        AND column_name = 'longitude'
    ) THEN
        ALTER TABLE gnaf.school_profile_2025 
        ADD COLUMN longitude NUMERIC(10, 7);
        
        RAISE NOTICE 'Added longitude column to school_profile_2025';
    ELSE
        RAISE NOTICE 'Longitude column already exists in school_profile_2025';
    END IF;
END $$;

-- Step 2: Add comments to the new columns
COMMENT ON COLUMN gnaf.school_profile_2025.latitude IS 'Geographic latitude coordinate (decimal degrees) - sourced from school_location table';
COMMENT ON COLUMN gnaf.school_profile_2025.longitude IS 'Geographic longitude coordinate (decimal degrees) - sourced from school_location table';

-- Step 3: Update coordinates from school_location table
UPDATE gnaf.school_profile_2025 AS sp
SET 
    latitude = sl.latitude,
    longitude = sl.longitude
FROM gnaf.school_location AS sl
WHERE sp.acara_sml_id = sl.acara_sml_id
AND (sp.latitude IS NULL OR sp.longitude IS NULL); -- Only update if not already set

-- Step 4: Create index on coordinates for spatial queries
CREATE INDEX IF NOT EXISTS idx_school_profile_2025_coords 
ON gnaf.school_profile_2025(latitude, longitude);

-- Step 5: Display summary statistics
DO $$
DECLARE
    total_schools INTEGER;
    schools_with_coords INTEGER;
    schools_without_coords INTEGER;
BEGIN
    -- Count total schools
    SELECT COUNT(*) INTO total_schools
    FROM gnaf.school_profile_2025;
    
    -- Count schools with coordinates
    SELECT COUNT(*) INTO schools_with_coords
    FROM gnaf.school_profile_2025
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL;
    
    -- Count schools without coordinates
    schools_without_coords := total_schools - schools_with_coords;
    
    -- Display summary
    RAISE NOTICE '';
    RAISE NOTICE '================================================';
    RAISE NOTICE 'COORDINATE UPDATE SUMMARY';
    RAISE NOTICE '================================================';
    RAISE NOTICE 'Total schools in school_profile_2025: %', total_schools;
    RAISE NOTICE 'Schools with coordinates: %', schools_with_coords;
    RAISE NOTICE 'Schools without coordinates: %', schools_without_coords;
    RAISE NOTICE 'Update completion: % %%', ROUND((schools_with_coords::NUMERIC / total_schools * 100), 2);
    RAISE NOTICE '================================================';
    RAISE NOTICE '';
END $$;
