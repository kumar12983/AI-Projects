-- ============================================================================
-- Query School Catchments by Address Coordinates
-- ============================================================================
-- This script finds all school catchments that contain a given address
-- Usage: Replace the latitude, longitude, and state values in the query below
-- ============================================================================

-- Example 1: Richmond, VIC - 55 YARRA BVD, RICHMOND, VIC 3121
-- Coordinates: -37.822245, 145.014316

SELECT DISTINCT
    school_id,
    school_name,
    campus_name,
    school_type,
    state,
    year_level_code,
    boundary_year,
    centroid_lat,
    centroid_lng,
    -- Calculate distance from address to school centroid (in km)
    ROUND(
        ST_Distance(
            ST_SetSRID(ST_MakePoint(145.014316, -37.822245), 4326)::geography,
            ST_SetSRID(ST_MakePoint(centroid_lng, centroid_lat), 4326)::geography
        ) / 1000, 2
    ) AS distance_km,
    -- Calculate catchment area in square kilometers
    ROUND((ST_Area(geometry::geography) / 1000000)::numeric, 2) AS area_km2
FROM gnaf.school_catchments
WHERE state = 'VIC'  -- Filter by state first for performance
AND ST_Contains(
    geometry,
    ST_SetSRID(ST_MakePoint(145.014316, -37.822245), 4326)  -- lng, lat
)
ORDER BY school_type, school_name;


-- ============================================================================
-- Example 2: Sydney, NSW - Hornsby area
-- Coordinates: 151.0993, -33.7044
-- ============================================================================

SELECT DISTINCT
    school_id,
    school_name,
    campus_name,
    school_type,
    state,
    year_level_code,
    boundary_year,
    -- Calculate distance from address to school centroid
    ROUND(
        ST_Distance(
            ST_SetSRID(ST_MakePoint(151.0993, -33.7044), 4326)::geography,
            ST_SetSRID(ST_MakePoint(centroid_lng, centroid_lat), 4326)::geography
        ) / 1000, 2
    ) AS distance_km,
    ROUND((ST_Area(geometry::geography) / 1000000)::numeric, 2) AS area_km2
FROM gnaf.school_catchments
WHERE state = 'NSW'
AND ST_Contains(
    geometry,
    ST_SetSRID(ST_MakePoint(151.0993, -33.7044), 4326)
)
ORDER BY school_type, school_name;


-- ============================================================================
-- Parameterized Query Template (for use in applications)
-- ============================================================================
-- Replace $1 = state, $2 = longitude, $3 = latitude
-- 
-- SELECT DISTINCT
--     school_id,
--     school_name,
--     campus_name,
--     school_type,
--     state,
--     year_level_code
-- FROM gnaf.school_catchments
-- WHERE state = $1
-- AND ST_Contains(
--     geometry,
--     ST_SetSRID(ST_MakePoint($2, $3), 4326)
-- )
-- ORDER BY school_type, school_name;


-- ============================================================================
-- Query with Full School Details (including year levels)
-- ============================================================================

SELECT DISTINCT
    sc.school_id,
    sc.school_name,
    sc.campus_name,
    sc.school_type,
    sc.state,
    sc.year_level_code,
    sc.boundary_year,
    -- Year level flags
    sc.kindergart,
    sc.year1, sc.year2, sc.year3, sc.year4, sc.year5, sc.year6,
    sc.year7, sc.year8, sc.year9, sc.year10, sc.year11, sc.year12,
    -- Geographic data
    sc.centroid_lat,
    sc.centroid_lng,
    ROUND(
        ST_Distance(
            ST_SetSRID(ST_MakePoint(145.014316, -37.822245), 4326)::geography,
            ST_SetSRID(ST_MakePoint(sc.centroid_lng, sc.centroid_lat), 4326)::geography
        ) / 1000, 2
    ) AS distance_km,
    ROUND((ST_Area(sc.geometry::geography) / 1000000)::numeric, 2) AS area_km2,
    -- Metadata
    sc.data_source,
    sc.created_at,
    sc.updated_at
FROM gnaf.school_catchments sc
WHERE sc.state = 'VIC'
AND ST_Contains(
    sc.geometry,
    ST_SetSRID(ST_MakePoint(145.014316, -37.822245), 4326)
)
ORDER BY sc.school_type, sc.school_name;


-- ============================================================================
-- Find School Catchments for Multiple Addresses (Batch Query)
-- ============================================================================

WITH addresses AS (
    SELECT 'Richmond, VIC' AS location, 145.014316 AS lng, -37.822245 AS lat, 'VIC' AS state
    UNION ALL
    SELECT 'Hornsby, NSW', 151.0993, -33.7044, 'NSW'
    UNION ALL
    SELECT 'Melbourne CBD, VIC', 144.9631, -37.8136, 'VIC'
)
SELECT 
    a.location,
    a.lat,
    a.lng,
    sc.school_name,
    sc.campus_name,
    sc.school_type,
    sc.year_level_code,
    ROUND(
        ST_Distance(
            ST_SetSRID(ST_MakePoint(a.lng, a.lat), 4326)::geography,
            ST_SetSRID(ST_MakePoint(sc.centroid_lng, sc.centroid_lat), 4326)::geography
        ) / 1000, 2
    ) AS distance_km
FROM addresses a
LEFT JOIN gnaf.school_catchments sc ON (
    sc.state = a.state
    AND ST_Contains(sc.geometry, ST_SetSRID(ST_MakePoint(a.lng, a.lat), 4326))
)
ORDER BY a.location, sc.school_type, sc.school_name;


-- ============================================================================
-- Count Schools by Type for an Address
-- ============================================================================

SELECT 
    school_type,
    COUNT(*) as school_count,
    STRING_AGG(DISTINCT school_name, ', ' ORDER BY school_name) AS schools
FROM gnaf.school_catchments
WHERE state = 'VIC'
AND ST_Contains(
    geometry,
    ST_SetSRID(ST_MakePoint(145.014316, -37.822245), 4326)
)
GROUP BY school_type
ORDER BY school_type;


-- ============================================================================
-- Find Nearest School Catchment (if address is outside all catchments)
-- ============================================================================

SELECT 
    school_id,
    school_name,
    campus_name,
    school_type,
    state,
    year_level_code,
    ROUND(
        ST_Distance(
            ST_SetSRID(ST_MakePoint(145.014316, -37.822245), 4326)::geography,
            geometry::geography
        ) / 1000, 2
    ) AS distance_to_boundary_km,
    ROUND(
        ST_Distance(
            ST_SetSRID(ST_MakePoint(145.014316, -37.822245), 4326)::geography,
            ST_SetSRID(ST_MakePoint(centroid_lng, centroid_lat), 4326)::geography
        ) / 1000, 2
    ) AS distance_to_centroid_km
FROM gnaf.school_catchments
WHERE state = 'VIC'
ORDER BY 
    geometry::geography <-> ST_SetSRID(ST_MakePoint(145.014316, -37.822245), 4326)::geography
LIMIT 5;


-- ============================================================================
-- NOTES:
-- ============================================================================
-- 1. ST_MakePoint(longitude, latitude) - Note the order: lng FIRST, then lat
-- 2. SRID 4326 is WGS84 (standard GPS coordinates)
-- 3. ST_Contains checks if the point is inside the catchment polygon
-- 4. State filter is applied first for better query performance
-- 5. For Victoria: campus_name and year_level_code provide additional details
-- 6. For NSW: use_id field may be populated instead of entity_code
-- ============================================================================
