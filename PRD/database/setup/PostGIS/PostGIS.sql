CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

SELECT PostGIS_Version();


SET search_path TO gnaf, public;

ALTER TABLE address_default_geocode 
ADD COLUMN IF NOT EXISTS geom geometry(Point, 4326);

COMMENT ON COLUMN address_default_geocode.geom IS 'Point geometry in WGS84 (SRID 4326) coordinate system';

ALTER TABLE IF EXISTS postcodes 
ADD COLUMN IF NOT EXISTS geom geometry(Point, 4326);

UPDATE address_default_geocode 
SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
WHERE longitude IS NOT NULL 
  AND latitude IS NOT NULL
  AND geom IS NULL;

  select * from address_default_geocode limit 1

  select * from information_schema.columns where column_name like '%postcode%';

  with locality_postcodes as (
  select distinct locality_name, primary_postcode, ad.postcode from locality loc
  INNER JOIN address_detail ad on ad.locality_pid = loc.locality_pid
  )

  select locality_name, count(distinct po)
  
  ;

  
  

