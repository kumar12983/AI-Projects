-- View: public.school_catchment_addresses

-- DROP MATERIALIZED VIEW IF EXISTS public.school_catchment_addresses;

CREATE MATERIALIZED VIEW IF NOT EXISTS public.school_catchment_addresses
TABLESPACE pg_default
AS
 SELECT DISTINCT ON (ad.address_detail_pid, sc.school_id) ad.address_detail_pid,
    sc.school_id,
    sc.school_name,
    sc.school_type,
    sc.school_lat,
    sc.school_lng
   FROM gnaf.address_detail ad
     JOIN gnaf.address_default_geocode agc ON ad.address_detail_pid::text = agc.address_detail_pid::text
     CROSS JOIN ( SELECT school_catchments_primary."USE_ID" AS school_id,
            school_catchments_primary."USE_DESC" AS school_name,
            school_catchments_primary."CATCH_TYPE" AS school_type,
            school_catchments_primary.geometry,
            st_y(st_centroid(school_catchments_primary.geometry)) AS school_lat,
            st_x(st_centroid(school_catchments_primary.geometry)) AS school_lng
           FROM school_catchments_primary
        UNION ALL
         SELECT school_catchments_secondary."USE_ID" AS school_id,
            school_catchments_secondary."USE_DESC" AS school_name,
            school_catchments_secondary."CATCH_TYPE" AS school_type,
            school_catchments_secondary.geometry,
            st_y(st_centroid(school_catchments_secondary.geometry)) AS school_lat,
            st_x(st_centroid(school_catchments_secondary.geometry)) AS school_lng
           FROM school_catchments_secondary
        UNION ALL
         SELECT school_catchments_future."USE_ID" AS school_id,
            school_catchments_future."USE_DESC" AS school_name,
            school_catchments_future."CATCH_TYPE" AS school_type,
            school_catchments_future.geometry,
            st_y(st_centroid(school_catchments_future.geometry)) AS school_lat,
            st_x(st_centroid(school_catchments_future.geometry)) AS school_lng
           FROM school_catchments_future) sc
  WHERE ad.date_retired IS NULL AND agc.date_retired IS NULL AND st_contains(sc.geometry, st_setsrid(st_makepoint(agc.longitude::double precision, agc.latitude::double precision), 4326))
WITH DATA;

ALTER TABLE IF EXISTS public.school_catchment_addresses
    OWNER TO postgres;


CREATE INDEX idx_school_catchment_addresses_address_pid
    ON public.school_catchment_addresses USING btree
    (address_detail_pid COLLATE pg_catalog."default")
    TABLESPACE pg_default;

CREATE INDEX idx_school_catchment_addresses_school_id
    ON public.school_catchment_addresses USING btree
    (school_id COLLATE pg_catalog."default")
    TABLESPACE pg_default;

CREATE INDEX idx_school_catchment_addresses_school_type
    ON public.school_catchment_addresses USING btree
    (school_type COLLATE pg_catalog."default")
    TABLESPACE pg_default;


	SELECT 
    school_type,
    COUNT(*) as num_schools,
    SUM(total_addresses) as total_addresses,
    AVG(total_addresses)::int as avg_addresses_per_school,
    MAX(total_addresses) as max_addresses
FROM public.school_catchment_stats
GROUP BY school_type
ORDER BY school_type;

select * from public.geometry_columns

select * from gnaf.school_catchments

 with school_type as (
select c.school_id, c.school_name  , array_length(string_to_array(c.school_name, ' '), 1) , split_part(c.school_name,' ', 1) as school_first
, CASE 
	WHEN split_part(c.school_name, ' ', array_length(string_to_array(c.school_name, ' '), 1)) = 'PS' then 'Public School'
	WHEN split_part(c.school_name, ' ', array_length(string_to_array(c.school_name, ' '), 1)) = 'HS' then 'High School'
	WHEN split_part(c.school_name, ' ', array_length(string_to_array(c.school_name, ' '), 1)) = 'GHS' then 'Girls High School'
	WHEN split_part(c.school_name, ' ', array_length(string_to_array(c.school_name, ' '), 1)) = 'BHS' then 'Boys High School'
	WHEN split_part(c.school_name, ' ', array_length(string_to_array(c.school_name, ' '), 1)) = 'NPS' then 'North Public School'
	WHEN split_part(c.school_name, ' ', array_length(string_to_array(c.school_name, ' '), 1)) = 'SPS' then 'South Public School'
	WHEN split_part(c.school_name, ' ', array_length(string_to_array(c.school_name, ' '), 1)) = 'WPS' then 'West Public School'
	WHEN split_part(c.school_name, ' ', array_length(string_to_array(c.school_name, ' '), 1)) = 'EPS' then 'East Public School'
	WHEN split_part(c.school_name, ' ', array_length(string_to_array(c.school_name, ' '), 1)) = 'CS' then 'Central School'
	WHEN split_part(c.school_name, ' ', array_length(string_to_array(c.school_name, ' '), 1)) = 'SC' then 'Secondary College'
	WHEN split_part(c.school_name, ' ', array_length(string_to_array(c.school_name, ' '), 1)) = 'WIS' then 'West Infants School'
	WHEN split_part(c.school_name, ' ', array_length(string_to_array(c.school_name, ' '), 1)) = 'SIS' then 'South Infants School'
	WHEN split_part(c.school_name, ' ', array_length(string_to_array(c.school_name, ' '), 1)) = 'EIS' then 'East Infants School'
	WHEN split_part(c.school_name, ' ', array_length(string_to_array(c.school_name, ' '), 1)) = 'NIS' then 'North Infants School'
	WHEN split_part(c.school_name, ' ', array_length(string_to_array(c.school_name, ' '), 1)) = 'IS' then 'Infants School'
 END as school_type_name
 FROM gnaf.school_catchments c 
 
 )

 , school_name as (
 select * 
 , school_first||' '||school_type_name as school_name
 from school_type
 where school_type_name is NOT NULL
 )

 select * FROM school_name
;
-- school data fix for heights public school (type: primary)
with school_id_fix_heights as (
select pf.school_name, c.school_name as catchment_school_name, c.school_id, pf.school_type 
from school_type_lookup pf 
inner join gnaf.school_catchments c on split_part(c.school_name , ' ', 1) = split_part(pf.school_name,' ', 1) and split_part(c.school_name, ' ', 2) = 'Hts' 
and split_part(pf.school_name, ' ', 2) = 'Heights'  and split_part(c.school_name, ' ', 3) = 'PS'
WHERE  split_part(pf.school_name, ' ', 2) = 'Heights' and pf.school_type = 'Primary'
)

update gnaf.school_type_lookup lf 
  set school_id = fh.school_id
   , catchment_school_name = fh.catchment_school_name
 FROM school_id_fix_heights fh 
 WHERE lf.school_name = fh.school_name
 ;
update gnaf.school_type_lookup 
set school_id = '8592' 
, school_name = 'Cherrybrook Technology High School'
, catchment_school_name = 'Cherrybrook THS'
where acara_sml_id = 41350;
