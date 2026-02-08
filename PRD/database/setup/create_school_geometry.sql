DROP TABLE IF EXISTS gnaf.school_geometry;
CREATE TABLE gnaf.school_geometry as
with school_geometry as 
(
SELECT 
  pf.acara_sml_id,
  pf.school_name,
  pf.state,
  pf.school_sector,
  pf.longitude,
  pf.latitude,
  -- Create 5km buffer geometry
  ST_Buffer(
    ST_Transform(
      ST_Point(pf.longitude, pf.latitude, 4326),
      3857
    ),
    5000
  )::geometry AS geom_5km_buffer
  , lf.school_id
  , cs.geometry as catchment_zone
  , CASE WHEN cs.geometry is not null THEN 'Y' ELSE 'N' END as has_catchment
FROM school_profile_2025 pf 
left join school_type_lookup lf on pf.acara_sml_id = lf.acara_sml_id
left join gnaf.school_catchments cs on cs.school_id = lf.school_id

)

select *
, case when geom_5km_buffer is not null then 'Y' ELSE 'N' END as has_geom_buffer
FROM school_geometry
;

ALTER TABLE gnaf.school_geometry 
ADD COLUMN search_vector tsvector 
GENERATED ALWAYS AS (to_tsvector('english', school_name)) STORED;

-- Create GIN index for fast full-text searches
CREATE INDEX idx_school_geometry_search ON gnaf.school_geometry USING GIN(search_vector);

-- Example query to test the search
SELECT 
  school_name, 
  state, 
  school_sector,
  acara_sml_id
FROM gnaf.school_geometry 
WHERE search_vector @@ plainto_tsquery('english', 'hornsby')
LIMIT 10;


CREATE INDEX idx_school_geom_5km_buffer ON gnaf.school_geometry USING GIST(geom_5km_buffer);
CREATE INDEX idx_school_catchment_zone ON gnaf.school_geometry USING GIST(catchment_zone);

-- Support indexes for joins & filters
CREATE INDEX idx_school_geom_acara_sml_id ON gnaf.school_geometry(acara_sml_id);
CREATE INDEX idx_school_geom_school_id ON gnaf.school_geometry(school_id);
CREATE INDEX idx_school_geom_state ON gnaf.school_geometry(state);