-- Materialized view to map addresses to school catchments
-- This pre-computes the expensive ST_Contains spatial join

-- Drop existing materialized view if it exists
DROP MATERIALIZED VIEW IF EXISTS public.school_catchment_addresses CASCADE;

-- Create materialized view with address to school catchment mapping
CREATE MATERIALIZED VIEW public.school_catchment_addresses AS
SELECT DISTINCT ON (ad.address_detail_pid, sc.school_id)
    ad.address_detail_pid,
    sc.school_id,
    sc.school_name,
    sc.school_type,
    sc.school_lat,
    sc.school_lng
FROM gnaf.address_detail ad
JOIN gnaf.address_default_geocode agc ON ad.address_detail_pid = agc.address_detail_pid
CROSS JOIN (
    -- Get all school catchments with their centroids
    SELECT 
        "USE_ID" as school_id,
        "USE_DESC" as school_name,
        "CATCH_TYPE" as school_type,
        geometry,
        ST_Y(ST_Centroid(geometry)) as school_lat,
        ST_X(ST_Centroid(geometry)) as school_lng
    FROM public.school_catchments_primary
    
    UNION ALL
    
    SELECT 
        "USE_ID" as school_id,
        "USE_DESC" as school_name,
        "CATCH_TYPE" as school_type,
        geometry,
        ST_Y(ST_Centroid(geometry)) as school_lat,
        ST_X(ST_Centroid(geometry)) as school_lng
    FROM public.school_catchments_secondary
    
    UNION ALL
    
    SELECT 
        "USE_ID" as school_id,
        "USE_DESC" as school_name,
        "CATCH_TYPE" as school_type,
        geometry,
        ST_Y(ST_Centroid(geometry)) as school_lat,
        ST_X(ST_Centroid(geometry)) as school_lng
    FROM public.school_catchments_future
) sc
WHERE ad.date_retired IS NULL
AND agc.date_retired IS NULL
AND ST_Contains(sc.geometry, ST_SetSRID(ST_MakePoint(agc.longitude, agc.latitude), 4326));

-- Create indexes for fast lookups
CREATE INDEX idx_school_catchment_addresses_school_id 
ON public.school_catchment_addresses(school_id);

CREATE INDEX idx_school_catchment_addresses_address_pid 
ON public.school_catchment_addresses(address_detail_pid);

CREATE INDEX idx_school_catchment_addresses_school_type 
ON public.school_catchment_addresses(school_type);

-- Analyze the materialized view for query optimization
ANALYZE public.school_catchment_addresses;

-- Display statistics
SELECT 
    school_type,
    COUNT(DISTINCT school_id) as num_schools,
    COUNT(DISTINCT address_detail_pid) as num_addresses,
    COUNT(*) as total_mappings
FROM public.school_catchment_addresses
GROUP BY school_type
ORDER BY school_type;

SELECT 
    'Total distinct addresses' as metric,
    COUNT(DISTINCT address_detail_pid) as count
FROM public.school_catchment_addresses
UNION ALL
SELECT 
    'Total distinct schools' as metric,
    COUNT(DISTINCT school_id) as count
FROM public.school_catchment_addresses;
