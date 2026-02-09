-- Create school_geometry table with spatial data and 5km buffers
-- This table combines school profile data with location coordinates and catchment zones
-- Database: gnaf_db
-- Schema: gnaf

SET search_path TO gnaf, public;

DROP TABLE IF EXISTS gnaf.school_geometry CASCADE;

CREATE TABLE gnaf.school_geometry AS
WITH school_geometry AS 
(
    SELECT 
        pf.acara_sml_id,
        pf.school_name,
        pf.state,
        pf.school_sector,
        pf.longitude,
        pf.latitude,
        -- Create 5km buffer geometry (only if coordinates exist)
        CASE 
            WHEN pf.latitude IS NOT NULL AND pf.longitude IS NOT NULL THEN
                ST_Buffer(
                    ST_Transform(
                        ST_Point(pf.longitude, pf.latitude, 4326),
                        3857
                    ),
                    5000
                )::geometry
            ELSE NULL
        END AS geom_5km_buffer,
        lf.school_id,
        cs.geometry AS catchment_zone,
        CASE WHEN cs.geometry IS NOT NULL THEN 'Y' ELSE 'N' END AS has_catchment
    FROM gnaf.school_profile_2025 pf 
    LEFT JOIN gnaf.school_type_lookup lf ON pf.acara_sml_id = lf.acara_sml_id
    LEFT JOIN gnaf.school_catchments cs ON cs.school_id = lf.school_id
)
SELECT 
    *,
    CASE WHEN geom_5km_buffer IS NOT NULL THEN 'Y' ELSE 'N' END AS has_geom_buffer
FROM school_geometry;

-- Add full-text search vector column
ALTER TABLE gnaf.school_geometry 
ADD COLUMN search_vector tsvector 
GENERATED ALWAYS AS (to_tsvector('english', school_name)) STORED;

-- Create indexes for performance optimization

-- Full-text search index
CREATE INDEX idx_school_geometry_search ON gnaf.school_geometry USING GIN(search_vector);

-- Spatial indexes
CREATE INDEX idx_school_geom_5km_buffer ON gnaf.school_geometry USING GIST(geom_5km_buffer);
CREATE INDEX idx_school_catchment_zone ON gnaf.school_geometry USING GIST(catchment_zone);

-- Support indexes for joins & filters
CREATE INDEX idx_school_geom_acara_sml_id ON gnaf.school_geometry(acara_sml_id);
CREATE INDEX idx_school_geom_school_id ON gnaf.school_geometry(school_id);
CREATE INDEX idx_school_geom_state ON gnaf.school_geometry(state);
CREATE INDEX idx_school_geom_sector ON gnaf.school_geometry(school_sector);
CREATE INDEX idx_school_geom_coords ON gnaf.school_geometry(latitude, longitude);

-- Add comments for documentation
COMMENT ON TABLE gnaf.school_geometry IS 'School geometry data with 5km buffers and catchment zones - coordinates sourced from school_location table via school_profile_2025';
COMMENT ON COLUMN gnaf.school_geometry.acara_sml_id IS 'Unique school identifier from ACARA';
COMMENT ON COLUMN gnaf.school_geometry.latitude IS 'Geographic latitude (decimal degrees) - sourced from school_location';
COMMENT ON COLUMN gnaf.school_geometry.longitude IS 'Geographic longitude (decimal degrees) - sourced from school_location';
COMMENT ON COLUMN gnaf.school_geometry.geom_5km_buffer IS '5km radius buffer around school location in Web Mercator projection';
COMMENT ON COLUMN gnaf.school_geometry.catchment_zone IS 'School catchment zone geometry if available';
COMMENT ON COLUMN gnaf.school_geometry.has_catchment IS 'Flag indicating if school has a defined catchment zone (Y/N)';
COMMENT ON COLUMN gnaf.school_geometry.has_geom_buffer IS 'Flag indicating if 5km buffer geometry exists (Y/N)';
COMMENT ON COLUMN gnaf.school_geometry.search_vector IS 'Full-text search vector for school name';

-- Display summary statistics
DO $$
DECLARE
    total_schools INTEGER;
    schools_with_coords INTEGER;
    schools_with_buffer INTEGER;
    schools_with_catchment INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_schools FROM gnaf.school_geometry;
    SELECT COUNT(*) INTO schools_with_coords FROM gnaf.school_geometry WHERE latitude IS NOT NULL;
    SELECT COUNT(*) INTO schools_with_buffer FROM gnaf.school_geometry WHERE geom_5km_buffer IS NOT NULL;
    SELECT COUNT(*) INTO schools_with_catchment FROM gnaf.school_geometry WHERE catchment_zone IS NOT NULL;
    
    RAISE NOTICE '';
    RAISE NOTICE '========================================================';
    RAISE NOTICE 'SCHOOL GEOMETRY TABLE CREATED';
    RAISE NOTICE '========================================================';
    RAISE NOTICE 'Total schools: %', total_schools;
    RAISE NOTICE 'Schools with coordinates: %', schools_with_coords;
    RAISE NOTICE 'Schools with 5km buffer: %', schools_with_buffer;
    RAISE NOTICE 'Schools with catchment zones: %', schools_with_catchment;
    RAISE NOTICE '========================================================';
END $$;

-- Example query to test the search functionality
SELECT 
    school_name, 
    state, 
    school_sector,
    acara_sml_id,
    latitude,
    longitude,
    has_geom_buffer,
    has_catchment
FROM gnaf.school_geometry 
WHERE search_vector @@ plainto_tsquery('english', 'hornsby')
LIMIT 10;