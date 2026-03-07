-- Fix geometry column SRID for school_catchments table
-- This sets the correct SRID (4326) for WGS84 coordinates

BEGIN;

-- Update the geometry column to use SRID 4326
SELECT UpdateGeometrySRID('gnaf', 'school_catchments', 'geometry', 4326);

-- Verify the SRID is set correctly
SELECT Find_SRID('gnaf', 'school_catchments', 'geometry') as current_srid;

COMMIT;
