-- Create table for School Location 2025 data
-- Database: gnaf_db
-- Schema: gnaf
-- Table: school_location
-- 
-- This table stores geographic location data for schools including latitude, longitude,
-- and various statistical area classifications from the Australian Bureau of Statistics.
-- Data source: School Location 2025.xlsx

CREATE TABLE gnaf.school_location (
    -- Identifiers
    calendar_year INT NOT NULL,
    acara_sml_id INT NOT NULL PRIMARY KEY,
    location_age_id NUMERIC,
    school_age_id NUMERIC,
    rolled_school_id INT,
    
    -- School Information
    school_name VARCHAR(255) NOT NULL,
    suburb VARCHAR(100) NOT NULL,
    state VARCHAR(10) NOT NULL,
    postcode INT NOT NULL,
    school_sector VARCHAR(100),
    school_type VARCHAR(100),
    special_school INT,
    campus_type VARCHAR(100),
    
    -- Geographic Coordinates
    latitude NUMERIC(10, 7),
    longitude NUMERIC(10, 7),
    
    -- ABS Geographic Areas
    abs_remoteness_area INT,
    abs_remoteness_area_name VARCHAR(100),
    meshblock BIGINT,
    statistical_area_1 BIGINT,
    statistical_area_2 BIGINT,
    statistical_area_2_name VARCHAR(255),
    statistical_area_3 BIGINT,
    statistical_area_3_name VARCHAR(255),
    statistical_area_4 BIGINT,
    statistical_area_4_name VARCHAR(255),
    
    -- Government Areas
    local_government_area BIGINT,
    local_government_area_name VARCHAR(255),
    state_electoral_division BIGINT,
    state_electoral_division_name VARCHAR(255),
    commonwealth_electoral_division BIGINT,
    commonwealth_electoral_division_name VARCHAR(255),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_school_location_acara_sml_id ON gnaf.school_location(acara_sml_id);
CREATE INDEX idx_school_location_coords ON gnaf.school_location(latitude, longitude);
CREATE INDEX idx_school_location_state ON gnaf.school_location(state);
CREATE INDEX idx_school_location_suburb ON gnaf.school_location(suburb);
CREATE INDEX idx_school_location_postcode ON gnaf.school_location(postcode);

-- Add comments for documentation
COMMENT ON TABLE gnaf.school_location IS 'School location data with geographic coordinates and statistical areas (2025)';
COMMENT ON COLUMN gnaf.school_location.acara_sml_id IS 'Unique ID allocated to a school by ACARA (Primary Key)';
COMMENT ON COLUMN gnaf.school_location.latitude IS 'Geographic latitude coordinate (decimal degrees)';
COMMENT ON COLUMN gnaf.school_location.longitude IS 'Geographic longitude coordinate (decimal degrees)';
COMMENT ON COLUMN gnaf.school_location.abs_remoteness_area IS 'ABS remoteness classification code';
COMMENT ON COLUMN gnaf.school_location.statistical_area_1 IS 'SA1 code - smallest statistical area';
COMMENT ON COLUMN gnaf.school_location.statistical_area_2 IS 'SA2 code - medium statistical area';
COMMENT ON COLUMN gnaf.school_location.statistical_area_3 IS 'SA3 code - large statistical area';
COMMENT ON COLUMN gnaf.school_location.statistical_area_4 IS 'SA4 code - largest statistical area';
COMMENT ON COLUMN gnaf.school_location.local_government_area IS 'LGA code';
COMMENT ON COLUMN gnaf.school_location.state_electoral_division IS 'State electoral division code';
COMMENT ON COLUMN gnaf.school_location.commonwealth_electoral_division IS 'Federal electoral division code';
