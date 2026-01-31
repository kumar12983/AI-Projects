-- ============================================================================
-- Create School Type Lookup Table with School Profile Integration
-- ============================================================================
-- This table maps school catchment data with school profile information
-- It extracts school names without abbreviations and matches with profiles

-- Drop existing table if exists
DROP TABLE IF EXISTS gnaf.school_type_lookup CASCADE;

-- Create main lookup table
CREATE TABLE gnaf.school_type_lookup AS
with school_type AS (
  -- Extract school abbreviation and map to full name
    SELECT 
        c.school_id,
        c.school_name,
        array_length(string_to_array(c.school_name, ' '), 1) as word_count,
        array_to_string(
            (string_to_array(c.school_name, ' '))[1:array_length(string_to_array(c.school_name, ' '), 1)-1], 
            ' '
        ) as school_first,
        split_part(c.school_name, ' ', array_length(string_to_array(c.school_name, ' '), 1)) as abbrev,
        CASE 
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
,
school_name_full AS (
    -- Build full school name for matching
    SELECT 
        school_id,
        school_name,
        word_count,
        school_first,
        abbrev,
        school_type_name,
        school_first || ' ' || abbrev as school_name_constructed
    FROM school_type
    WHERE school_type_name IS NOT NULL
)

select sf.school_id, sf.school_name as catchment_school_name 
, pf.*
from gnaf.school_profile_2025 pf 
LEFT JOIN school_name_full sf on sf.school_first||' '||school_type_name = pf.school_name
WHERE pf.state = 'NSW' and pf.school_sector = 'Government' 
;

-- Create indexes for performance
CREATE INDEX idx_school_type_lookup_school_id ON gnaf.school_type_lookup(school_id);
CREATE INDEX idx_school_type_lookup_acara_sml_id ON gnaf.school_type_lookup(acara_sml_id);
CREATE INDEX idx_school_type_lookup_school_name ON gnaf.school_type_lookup(catchment_school_name);
CREATE INDEX idx_school_type_lookup_state ON gnaf.school_type_lookup(state);

-- Add comment to table
COMMENT ON TABLE gnaf.school_type_lookup IS 
'Lookup table mapping school catchments with school profile data. 
Extracts school abbreviations (PS, HS, etc.) and matches with profile information.';

-- Display summary of the lookup table
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT school_id) as unique_schools,
    COUNT(acara_sml_id) as matched_with_profile,
    COUNT(DISTINCT state) as states_covered
FROM gnaf.school_type_lookup;
