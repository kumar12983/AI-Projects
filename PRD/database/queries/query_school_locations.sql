-- Query examples for school_location table
-- Database: gnaf_db
-- Schema: gnaf

SET search_path TO gnaf, public;

-- ============================================================================
-- BASIC QUERIES
-- ============================================================================

-- 1. Get all schools with coordinates in a specific state
SELECT 
    acara_sml_id,
    school_name,
    suburb,
    state,
    latitude,
    longitude
FROM gnaf.school_location
WHERE state = 'VIC'
ORDER BY school_name
LIMIT 10;

-- 2. Count schools by state
SELECT 
    state,
    COUNT(*) as school_count,
    COUNT(CASE WHEN latitude IS NOT NULL THEN 1 END) as schools_with_coords
FROM gnaf.school_location
GROUP BY state
ORDER BY school_count DESC;

-- 3. Find schools in a specific remoteness area
SELECT 
    acara_sml_id,
    school_name,
    suburb,
    state,
    abs_remoteness_area_name,
    latitude,
    longitude
FROM gnaf.school_location
WHERE abs_remoteness_area_name = 'Major Cities of Australia'
ORDER BY school_name
LIMIT 20;

-- ============================================================================
-- GEOGRAPHIC QUERIES
-- ============================================================================

-- 4. Find schools within a bounding box (example: Melbourne CBD area)
SELECT 
    acara_sml_id,
    school_name,
    suburb,
    latitude,
    longitude
FROM gnaf.school_location
WHERE latitude BETWEEN -37.85 AND -37.80
AND longitude BETWEEN 144.95 AND 145.00
ORDER BY school_name;

-- 5. Find schools by Statistical Area 2
SELECT 
    acara_sml_id,
    school_name,
    suburb,
    statistical_area_2_name,
    latitude,
    longitude
FROM gnaf.school_location
WHERE statistical_area_2_name ILIKE '%Melbourne%'
ORDER BY school_name
LIMIT 20;

-- 6. Count schools by Local Government Area
SELECT 
    local_government_area_name,
    COUNT(*) as school_count
FROM gnaf.school_location
WHERE local_government_area_name IS NOT NULL
GROUP BY local_government_area_name
ORDER BY school_count DESC
LIMIT 20;

-- ============================================================================
-- JOIN QUERIES (with school_profile_2025)
-- ============================================================================

-- 7. Get schools with both profile and location data
SELECT 
    sp.acara_sml_id,
    sp.school_name,
    sp.suburb,
    sp.state,
    sl.latitude,
    sl.longitude,
    sp.icsea,
    sp.total_enrolments
FROM gnaf.school_profile_2025 sp
INNER JOIN gnaf.school_location sl ON sp.acara_sml_id = sl.acara_sml_id
WHERE sp.state = 'NSW'
ORDER BY sp.total_enrolments DESC
LIMIT 20;

-- 8. Find schools in profile but missing from location table
SELECT 
    sp.acara_sml_id,
    sp.school_name,
    sp.suburb,
    sp.state
FROM gnaf.school_profile_2025 sp
LEFT JOIN gnaf.school_location sl ON sp.acara_sml_id = sl.acara_sml_id
WHERE sl.acara_sml_id IS NULL
ORDER BY sp.school_name;

-- 9. Find schools in location but missing from profile table
SELECT 
    sl.acara_sml_id,
    sl.school_name,
    sl.suburb,
    sl.state
FROM gnaf.school_location sl
LEFT JOIN gnaf.school_profile_2025 sp ON sp.acara_sml_id = sl.acara_sml_id
WHERE sp.acara_sml_id IS NULL
ORDER BY sl.school_name;

-- ============================================================================
-- ANALYTICAL QUERIES
-- ============================================================================

-- 10. Average ICSEA by remoteness area
SELECT 
    sl.abs_remoteness_area_name,
    COUNT(*) as school_count,
    ROUND(AVG(sp.icsea), 2) as avg_icsea,
    ROUND(AVG(sp.total_enrolments), 2) as avg_enrolments
FROM gnaf.school_location sl
INNER JOIN gnaf.school_profile_2025 sp ON sl.acara_sml_id = sp.acara_sml_id
WHERE sp.icsea IS NOT NULL
AND sl.abs_remoteness_area_name IS NOT NULL
GROUP BY sl.abs_remoteness_area_name
ORDER BY avg_icsea DESC;

-- 11. Schools by type and sector with coordinates
SELECT 
    sl.school_type,
    sl.school_sector,
    COUNT(*) as school_count,
    COUNT(CASE WHEN sl.latitude IS NOT NULL THEN 1 END) as with_coords
FROM gnaf.school_location sl
GROUP BY sl.school_type, sl.school_sector
ORDER BY school_count DESC;

-- 12. Special schools by state
SELECT 
    state,
    COUNT(*) as special_school_count
FROM gnaf.school_location
WHERE special_school = 1
GROUP BY state
ORDER BY special_school_count DESC;

-- ============================================================================
-- SPATIAL DISTANCE QUERY (using coordinates)
-- ============================================================================

-- 13. Find schools near a specific coordinate (example: Melbourne CBD)
-- Using Haversine formula approximation
SELECT 
    acara_sml_id,
    school_name,
    suburb,
    latitude,
    longitude,
    ROUND(
        (6371 * acos(
            cos(radians(-37.8136)) * 
            cos(radians(latitude)) * 
            cos(radians(longitude) - radians(144.9631)) + 
            sin(radians(-37.8136)) * 
            sin(radians(latitude))
        ))::numeric, 
        2
    ) as distance_km
FROM gnaf.school_location
WHERE latitude IS NOT NULL 
AND longitude IS NOT NULL
ORDER BY distance_km
LIMIT 20;

-- ============================================================================
-- DATA QUALITY CHECKS
-- ============================================================================

-- 14. Check for missing coordinates
SELECT 
    state,
    COUNT(*) as total_schools,
    COUNT(CASE WHEN latitude IS NULL THEN 1 END) as missing_latitude,
    COUNT(CASE WHEN longitude IS NULL THEN 1 END) as missing_longitude
FROM gnaf.school_location
GROUP BY state
ORDER BY state;

-- 15. Check coordinate ranges (validate data quality)
SELECT 
    state,
    MIN(latitude) as min_lat,
    MAX(latitude) as max_lat,
    MIN(longitude) as min_lon,
    MAX(longitude) as max_lon
FROM gnaf.school_location
WHERE latitude IS NOT NULL 
AND longitude IS NOT NULL
GROUP BY state
ORDER BY state;
