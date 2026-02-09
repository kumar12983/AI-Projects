-- Migration: Update school_geometry coordinates and regenerate 5km buffers
-- Date: 2026-02-09
-- Description: Updates latitude/longitude in school_geometry from school_profile_2025
--              and regenerates the 5km buffer geometry with the new coordinates
-- Prerequisites: 
--   - gnaf.school_geometry table must exist
--   - gnaf.school_profile_2025 must have latitude and longitude populated

SET search_path TO gnaf, public;

-- Step 1: Update latitude and longitude from school_profile_2025
DO $$
DECLARE
    updated_count INTEGER;
BEGIN
    RAISE NOTICE 'Step 1: Updating coordinates in school_geometry...';
    
    UPDATE gnaf.school_geometry sg
    SET 
        latitude = pf.latitude,
        longitude = pf.longitude
    FROM gnaf.school_profile_2025 pf
    WHERE sg.acara_sml_id = pf.acara_sml_id
    AND pf.latitude IS NOT NULL 
    AND pf.longitude IS NOT NULL;
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated coordinates for % schools', updated_count;
END $$;

-- Step 2: Regenerate 5km buffer geometry using updated coordinates
DO $$
DECLARE
    updated_count INTEGER;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE 'Step 2: Regenerating 5km buffer geometries...';
    
    UPDATE gnaf.school_geometry
    SET geom_5km_buffer = ST_Buffer(
        ST_Transform(
            ST_Point(longitude, latitude, 4326),
            3857
        ),
        5000
    )::geometry
    WHERE latitude IS NOT NULL 
    AND longitude IS NOT NULL;
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RAISE NOTICE 'Regenerated 5km buffer for % schools', updated_count;
END $$;

-- Step 3: Update has_geom_buffer flag (if it exists as a column)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'gnaf' 
        AND table_name = 'school_geometry' 
        AND column_name = 'has_geom_buffer'
    ) THEN
        UPDATE gnaf.school_geometry
        SET has_geom_buffer = CASE 
            WHEN geom_5km_buffer IS NOT NULL THEN 'Y' 
            ELSE 'N' 
        END;
        
        RAISE NOTICE 'Updated has_geom_buffer flags';
    END IF;
END $$;

-- Step 4: Rebuild spatial index for better performance
REINDEX INDEX idx_school_geom_5km_buffer;
RAISE NOTICE '';
RAISE NOTICE 'Rebuilt spatial index on 5km buffer';

-- Step 5: Display summary statistics
DO $$
DECLARE
    total_schools INTEGER;
    schools_with_coords INTEGER;
    schools_with_buffer INTEGER;
    schools_without_coords INTEGER;
BEGIN
    -- Count total schools
    SELECT COUNT(*) INTO total_schools
    FROM gnaf.school_geometry;
    
    -- Count schools with coordinates
    SELECT COUNT(*) INTO schools_with_coords
    FROM gnaf.school_geometry
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL;
    
    -- Count schools with buffer geometry
    SELECT COUNT(*) INTO schools_with_buffer
    FROM gnaf.school_geometry
    WHERE geom_5km_buffer IS NOT NULL;
    
    -- Count schools without coordinates
    schools_without_coords := total_schools - schools_with_coords;
    
    -- Display summary
    RAISE NOTICE '';
    RAISE NOTICE '========================================================';
    RAISE NOTICE 'SCHOOL GEOMETRY UPDATE SUMMARY';
    RAISE NOTICE '========================================================';
    RAISE NOTICE 'Total schools in school_geometry: %', total_schools;
    RAISE NOTICE 'Schools with coordinates: %', schools_with_coords;
    RAISE NOTICE 'Schools with 5km buffer: %', schools_with_buffer;
    RAISE NOTICE 'Schools without coordinates: %', schools_without_coords;
    RAISE NOTICE 'Update completion: % %%', ROUND((schools_with_coords::NUMERIC / total_schools * 100), 2);
    RAISE NOTICE '========================================================';
    RAISE NOTICE '';
END $$;

-- Step 6: Validate a few sample geometries
SELECT 
    acara_sml_id,
    school_name,
    state,
    latitude,
    longitude,
    CASE WHEN geom_5km_buffer IS NOT NULL THEN 'YES' ELSE 'NO' END as has_buffer,
    ST_GeometryType(geom_5km_buffer) as buffer_type
FROM gnaf.school_geometry
WHERE latitude IS NOT NULL
LIMIT 5;
