-- Option 2: Lightweight materialized view with just school statistics
-- Only stores aggregate counts, not individual address mappings

DROP MATERIALIZED VIEW IF EXISTS public.school_catchment_stats CASCADE;

CREATE MATERIALIZED VIEW public.school_catchment_stats AS
SELECT 
    sc.school_id,
    sc.school_name,
    sc.school_type,
    sc.school_lat,
    sc.school_lng,
    COUNT(DISTINCT ad.address_detail_pid) as total_addresses
FROM (
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
LEFT JOIN gnaf.address_detail ad ON ad.date_retired IS NULL
LEFT JOIN gnaf.address_default_geocode agc ON 
    ad.address_detail_pid = agc.address_detail_pid 
    AND agc.date_retired IS NULL
    AND ST_Contains(sc.geometry, ST_SetSRID(ST_MakePoint(agc.longitude, agc.latitude), 4326))
GROUP BY sc.school_id, sc.school_name, sc.school_type, sc.school_lat, sc.school_lng, sc.geometry;

-- Create indexes
CREATE INDEX idx_school_stats_school_id ON public.school_catchment_stats(school_id);
CREATE INDEX idx_school_stats_school_type ON public.school_catchment_stats(school_type);

-- Analyze
ANALYZE public.school_catchment_stats;

-- Display statistics
SELECT 
    school_type,
    COUNT(*) as num_schools,
    SUM(total_addresses) as total_addresses,
    AVG(total_addresses)::int as avg_addresses_per_school,
    MAX(total_addresses) as max_addresses
FROM public.school_catchment_stats
GROUP BY school_type
ORDER BY school_type;

-- Show top 10 schools by address count
SELECT school_name, school_type, total_addresses
FROM public.school_catchment_stats
ORDER BY total_addresses DESC
LIMIT 10;
