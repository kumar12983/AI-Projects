-- Create table for School Profile 2025 data
-- Database: gnaf_db
-- Schema: gnaf_schema
-- Table: school_profile_2025

CREATE TABLE gnaf.school_profile_2025 (
    -- Identifiers
    calendar_year INT NOT NULL,
    acara_sml_id INT NOT NULL PRIMARY KEY,
    location_age_id NUMERIC,
    school_age_id NUMERIC,
    
    -- School Information
    school_name VARCHAR(255) NOT NULL,
    suburb VARCHAR(100) NOT NULL,
    state VARCHAR(10) NOT NULL,
    postcode INT NOT NULL,
    school_sector VARCHAR(100),
    school_type VARCHAR(100),
    campus_type VARCHAR(100),
    rolled_reporting_description VARCHAR(255),
    year_range VARCHAR(50),
    
    -- School URLs and Governance
    school_url TEXT,
    governing_body VARCHAR(255),
    governing_body_url TEXT,
    
    -- Geographic Data
    geolocation VARCHAR(255),
    
    -- School Quality Index (ICSEA)
    icsea NUMERIC,
    icsea_percentile NUMERIC,
    bottom_seaquarter_pct NUMERIC,
    lower_middle_seaquarter_pct NUMERIC,
    upper_middle_seaquarter_pct NUMERIC,
    top_seaquarter_pct NUMERIC,
    
    -- Staffing Data
    teaching_staff NUMERIC,
    full_time_equivalent_teaching_staff NUMERIC,
    non_teaching_staff NUMERIC,
    full_time_equivalent_non_teaching_staff NUMERIC,
    
    -- Enrolment Data
    total_enrolments NUMERIC,
    girls_enrolments NUMERIC,
    boys_enrolments NUMERIC,
    full_time_equivalent_enrolments NUMERIC,
    
    -- Demographic Data
    indigenous_enrolments_pct NUMERIC,
    language_background_other_than_english_yes_pct NUMERIC,
    language_background_other_than_english_no_pct NUMERIC,
    language_background_other_than_english_not_stated_pct NUMERIC,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for common queries
CREATE INDEX idx_school_profile_2025_school_name ON gnaf.school_profile_2025(school_name);
CREATE INDEX idx_school_profile_2025_postcode ON gnaf.school_profile_2025(postcode);
CREATE INDEX idx_school_profile_2025_suburb ON gnaf.school_profile_2025(suburb);
CREATE INDEX idx_school_profile_2025_state ON gnaf.school_profile_2025(state);
CREATE INDEX idx_school_profile_2025_school_sector ON gnaf.school_profile_2025(school_sector);
CREATE INDEX idx_school_profile_2025_school_type ON gnaf.school_profile_2025(school_type);
CREATE INDEX idx_school_profile_2025_calendar_year ON gnaf.school_profile_2025(calendar_year);

-- Add comments to table and columns for documentation
COMMENT ON TABLE gnaf.school_profile_2025 IS 'School Profile 2025 data from ACARA containing school information, staffing, enrolment, and demographic data';
COMMENT ON COLUMN gnaf.school_profile_2025.calendar_year IS 'The year to which the data relates';
COMMENT ON COLUMN gnaf.school_profile_2025.acara_sml_id IS 'Unique ID allocated to a given school by ACARA';
COMMENT ON COLUMN gnaf.school_profile_2025.location_age_id IS 'The Australian Government Department of Education Location ID';
COMMENT ON COLUMN gnaf.school_profile_2025.school_age_id IS 'The Australian Government Department of Education School ID';
COMMENT ON COLUMN gnaf.school_profile_2025.icsea IS 'Index of Community Socio-Educational Advantage';
COMMENT ON COLUMN gnaf.school_profile_2025.geolocation IS 'Geographic coordinates in WKT or other format';
