-- Materialized view to map addresses to school catchments
-- This pre-computes the expensive ST_Contains spatial join

-- Drop existing materialized view if it exists
DROP MATERIALIZED VIEW IF EXISTS public.school_catchment_addresses CASCADE;

-- Create materialized view with address to school catchment mapping but do not populate yet.
-- We'll create the necessary unique index(s) and other indexes CONCURRENTLY, then
-- REFRESH the materialized view concurrently to avoid long exclusive locks.
CREATE MATERIALIZED VIEW public.school_catchment_addresses
WITH NO DATA
AS
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

-- Create the unique index required to support REFRESH MATERIALIZED VIEW CONCURRENTLY.
-- IMPORTANT: REFRESH ... CONCURRENTLY requires a unique index to exist beforehand.
-- If the materialized view is empty (we created it WITH NO DATA), creating the unique
-- index NON-CONCURRENTLY is safe and fast (no rows to index) and ensures the
-- concurrent refresh will succeed. Other supporting indexes can still be created CONCURRENTLY.
CREATE UNIQUE INDEX IF NOT EXISTS idx_school_catchment_addresses_unique
ON public.school_catchment_addresses(address_detail_pid, school_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_school_catchment_addresses_school_id 
ON public.school_catchment_addresses(school_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_school_catchment_addresses_address_pid 
ON public.school_catchment_addresses(address_detail_pid);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_school_catchment_addresses_school_type 
ON public.school_catchment_addresses(school_type);

-- Populate the materialized view using a concurrent refresh (requires the unique index above).
REFRESH MATERIALIZED VIEW CONCURRENTLY public.school_catchment_addresses;

-- Analyze the materialized view for query optimization
ANALYZE public.school_catchment_addresses;

-- Drop existing materialized view if it exists
DROP MATERIALIZED VIEW IF EXISTS public.school_catchment_streets CASCADE;

-- Create the streets materialized view WITHOUT data, add unique index and other indexes
-- concurrently, then REFRESH CONCURRENTLY to populate the view without exclusive locks.
CREATE MATERIALIZED VIEW public.school_catchment_streets
WITH NO DATA
AS
SELECT DISTINCT ca.school_id
, st.street_name
, st.street_type_code
, st.street_suffix_code
, l.locality_name
, l.postcode 
FROM public.school_catchment_addresses ca 
INNER JOIN gnaf.address_detail ad on ca.address_detail_pid = ad.address_detail_pid
INNER JOIN gnaf.street_locality st on st.street_locality_pid = ad.street_locality_pid 
INNER JOIN gnaf.locality_postcodes l on ad.locality_pid = l.locality_pid
;

-- Create a unique index that covers the view's natural key so REFRESH CONCURRENTLY works.
-- As above: create the unique index NON-CONCURRENTLY when the view is empty so the
-- subsequent REFRESH MATERIALIZED VIEW CONCURRENTLY can run. Other indexes remain CONCURRENTLY.
CREATE UNIQUE INDEX IF NOT EXISTS idx_school_catchment_streets_unique
ON public.school_catchment_streets(school_id, street_name, street_type_code, street_suffix_code, locality_name, postcode);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_school_catchment_street_school_id 
ON public.school_catchment_streets(school_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_school_catchment_street_locality_name 
ON public.school_catchment_streets(locality_name);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_school_catchment_street_name 
ON public.school_catchment_streets(street_name);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_school_catchment_street_postcode   
ON public.school_catchment_streets(postcode);

-- Populate the view without taking long exclusive locks
REFRESH MATERIALIZED VIEW CONCURRENTLY public.school_catchment_streets;

-- Analyze the materialized view for query optimization
ANALYZE public.school_catchment_streets;


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
--