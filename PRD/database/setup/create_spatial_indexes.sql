-- Spatial indexes for fast ST_Contains queries on school catchments
-- Using gnaf schema tables

-- Ensure geometry columns have GIST indexes for spatial queries
CREATE INDEX IF NOT EXISTS idx_primary_school_catchments_geom 
ON gnaf.primary_school_catchments USING GIST (geometry);

CREATE INDEX IF NOT EXISTS idx_secondary_school_catchments_geom 
ON gnaf.secondary_school_catchments USING GIST (geometry);

CREATE INDEX IF NOT EXISTS idx_future_school_catchments_geom 
ON gnaf.future_school_catchments USING GIST (geometry);

-- Index on the union table (most important for queries)
CREATE INDEX IF NOT EXISTS idx_school_catchments_geom 
ON gnaf.school_catchments USING GIST (geometry);

-- Index on school IDs for fast filtering
CREATE INDEX IF NOT EXISTS idx_school_catchments_use_id 
ON gnaf.school_catchments(school_id);

CREATE INDEX IF NOT EXISTS idx_school_catchments_catch_type 
ON gnaf.school_catchments(school_type);

-- Index on address geocodes for spatial lookups
CREATE INDEX IF NOT EXISTS idx_address_geocode_point 
ON gnaf.address_default_geocode USING GIST (
    ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
);

-- Analyze tables for query optimization
ANALYZE gnaf.primary_school_catchments;
ANALYZE gnaf.secondary_school_catchments;
ANALYZE gnaf.future_school_catchments;
ANALYZE gnaf.school_catchments;
ANALYZE gnaf.address_default_geocode;

-- Test query performance using the union table
EXPLAIN ANALYZE
SELECT COUNT(DISTINCT ad.address_detail_pid)
FROM gnaf.address_detail ad
JOIN gnaf.address_default_geocode agc ON ad.address_detail_pid = agc.address_detail_pid
JOIN gnaf.school_catchments sc ON 
    ST_Contains(sc.geometry, ST_SetSRID(ST_MakePoint(agc.longitude, agc.latitude), 4326))
WHERE ad.date_retired IS NULL
AND agc.date_retired IS NULL
AND sc."USE_ID" = '1937'
LIMIT 1;
