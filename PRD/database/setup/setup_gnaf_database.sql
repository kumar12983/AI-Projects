-- ============================================
-- PostgreSQL Database Setup for GNAF Data
-- Geocoded National Address File (GNAF)
-- ============================================

-- ============================================
-- Step 1: Create Database
-- ============================================
-- Note: Run this separately as a superuser, then connect to the new database
-- DROP DATABASE IF EXISTS gnaf_db;
CREATE DATABASE gnaf_db
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;

COMMENT ON DATABASE gnaf_db IS 'GNAF - Geocoded National Address File database';

-- ============================================
-- Connect to the database before proceeding
-- \c gnaf_db
-- ============================================

-- ============================================
-- Step 2: Create Schema
-- ============================================
DROP SCHEMA IF EXISTS gnaf CASCADE;
CREATE SCHEMA gnaf;

COMMENT ON SCHEMA gnaf IS 'Schema for GNAF address data';

-- Set search path to use the gnaf schema
SET search_path TO gnaf, public;

-- ============================================
-- Step 3: Create Core Tables
-- ============================================

-- -----------------------
-- Localities Table
-- -----------------------
CREATE TABLE gnaf.localities (
    locality_id SERIAL PRIMARY KEY,
    locality_pid VARCHAR(15) UNIQUE,
    locality_name VARCHAR(100) NOT NULL,
    primary_postcode VARCHAR(4),
    locality_class_code VARCHAR(1),
    state_pid VARCHAR(15),
    state_abbreviation VARCHAR(3),
    gnaf_locality_pid VARCHAR(15),
    gnaf_reliability_code SMALLINT,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_date TIMESTAMP,
    CONSTRAINT chk_postcode_format CHECK (primary_postcode ~ '^[0-9]{4}$' OR primary_postcode IS NULL)
);

CREATE INDEX idx_localities_name ON gnaf.localities(locality_name);
CREATE INDEX idx_localities_postcode ON gnaf.localities(primary_postcode);
CREATE INDEX idx_localities_state ON gnaf.localities(state_abbreviation);

COMMENT ON TABLE gnaf.localities IS 'GNAF localities (suburbs, towns, cities)';
COMMENT ON COLUMN gnaf.localities.locality_pid IS 'Unique persistent identifier for locality';
COMMENT ON COLUMN gnaf.localities.locality_name IS 'Official name of the locality';
COMMENT ON COLUMN gnaf.localities.primary_postcode IS '4-digit Australian postcode';

-- -----------------------
-- Postcodes Table
-- -----------------------
CREATE TABLE gnaf.postcodes (
    postcode_id SERIAL PRIMARY KEY,
    postcode VARCHAR(4) NOT NULL UNIQUE,
    locality VARCHAR(100),
    state VARCHAR(3),
    latitude DECIMAL(9, 6),
    longitude DECIMAL(9, 6),
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_postcode_valid CHECK (postcode ~ '^[0-9]{4}$')
);

CREATE INDEX idx_postcodes_code ON gnaf.postcodes(postcode);
CREATE INDEX idx_postcodes_state ON gnaf.postcodes(state);

COMMENT ON TABLE gnaf.postcodes IS 'Australian postcodes lookup table';
COMMENT ON COLUMN gnaf.postcodes.postcode IS '4-digit Australian postcode';

-- -----------------------
-- Suburb-Postcode Mapping Table
-- -----------------------
CREATE TABLE gnaf.suburb_postcode (
    mapping_id SERIAL PRIMARY KEY,
    suburb VARCHAR(100) NOT NULL,
    postcode VARCHAR(4) NOT NULL,
    state VARCHAR(3),
    locality_pid VARCHAR(15),
    is_primary BOOLEAN DEFAULT false,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_suburb_postcode CHECK (postcode ~ '^[0-9]{4}$'),
    CONSTRAINT uq_suburb_postcode UNIQUE (suburb, postcode)
);

CREATE INDEX idx_suburb_postcode_suburb ON gnaf.suburb_postcode(suburb);
CREATE INDEX idx_suburb_postcode_postcode ON gnaf.suburb_postcode(postcode);
CREATE INDEX idx_suburb_postcode_state ON gnaf.suburb_postcode(state);
CREATE INDEX idx_suburb_postcode_combined ON gnaf.suburb_postcode(suburb, postcode);

COMMENT ON TABLE gnaf.suburb_postcode IS 'Mapping between suburbs and postcodes (many-to-many relationship)';
COMMENT ON COLUMN gnaf.suburb_postcode.is_primary IS 'Indicates if this is the primary postcode for the suburb';

-- -----------------------
-- Addresses Table (Core GNAF)
-- -----------------------
CREATE TABLE gnaf.addresses (
    address_id SERIAL PRIMARY KEY,
    address_detail_pid VARCHAR(15) UNIQUE,
    street_locality_pid VARCHAR(15),
    locality_pid VARCHAR(15),
    building_name VARCHAR(200),
    lot_number_prefix VARCHAR(2),
    lot_number VARCHAR(5),
    lot_number_suffix VARCHAR(2),
    flat_type VARCHAR(7),
    flat_number_prefix VARCHAR(2),
    flat_number SMALLINT,
    flat_number_suffix VARCHAR(2),
    level_type VARCHAR(4),
    level_number_prefix VARCHAR(2),
    level_number SMALLINT,
    level_number_suffix VARCHAR(2),
    number_first_prefix VARCHAR(3),
    number_first INTEGER,
    number_first_suffix VARCHAR(2),
    number_last_prefix VARCHAR(3),
    number_last INTEGER,
    number_last_suffix VARCHAR(2),
    street_name VARCHAR(100),
    street_type_code VARCHAR(15),
    street_suffix_code VARCHAR(15),
    postal_delivery_type VARCHAR(20),
    postal_delivery_number SMALLINT,
    postcode VARCHAR(4),
    latitude DECIMAL(11, 8),
    longitude DECIMAL(11, 8),
    geocode_type VARCHAR(10),
    confidence SMALLINT,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_date TIMESTAMP
);

CREATE INDEX idx_addresses_locality ON gnaf.addresses(locality_pid);
CREATE INDEX idx_addresses_postcode ON gnaf.addresses(postcode);
CREATE INDEX idx_addresses_street ON gnaf.addresses(street_name);
CREATE INDEX idx_addresses_location ON gnaf.addresses(latitude, longitude);

COMMENT ON TABLE gnaf.addresses IS 'GNAF address details';
COMMENT ON COLUMN gnaf.addresses.address_detail_pid IS 'Unique persistent identifier for address';

-- -----------------------
-- Streets Table
-- -----------------------
CREATE TABLE gnaf.streets (
    street_id SERIAL PRIMARY KEY,
    street_locality_pid VARCHAR(15) UNIQUE,
    street_name VARCHAR(100) NOT NULL,
    street_type_code VARCHAR(15),
    street_suffix_code VARCHAR(15),
    locality_pid VARCHAR(15),
    gnaf_street_pid VARCHAR(15),
    gnaf_street_confidence SMALLINT,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_streets_name ON gnaf.streets(street_name);
CREATE INDEX idx_streets_locality ON gnaf.streets(locality_pid);

COMMENT ON TABLE gnaf.streets IS 'GNAF street locality information';

-- -----------------------
-- States Table
-- -----------------------
CREATE TABLE gnaf.states (
    state_id SERIAL PRIMARY KEY,
    state_pid VARCHAR(15) UNIQUE,
    state_name VARCHAR(50) NOT NULL,
    state_abbreviation VARCHAR(3) NOT NULL UNIQUE,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO gnaf.states (state_pid, state_name, state_abbreviation) VALUES
    ('NSW', 'New South Wales', 'NSW'),
    ('VIC', 'Victoria', 'VIC'),
    ('QLD', 'Queensland', 'QLD'),
    ('SA', 'South Australia', 'SA'),
    ('WA', 'Western Australia', 'WA'),
    ('TAS', 'Tasmania', 'TAS'),
    ('NT', 'Northern Territory', 'NT'),
    ('ACT', 'Australian Capital Territory', 'ACT'),
    ('OT', 'Other Territories', 'OT');

COMMENT ON TABLE gnaf.states IS 'Australian states and territories';

-- ============================================
-- Step 4: Create Foreign Key Constraints
-- ============================================

ALTER TABLE gnaf.localities 
    ADD CONSTRAINT fk_localities_state 
    FOREIGN KEY (state_abbreviation) 
    REFERENCES gnaf.states(state_abbreviation);

ALTER TABLE gnaf.suburb_postcode
    ADD CONSTRAINT fk_suburb_postcode_state
    FOREIGN KEY (state)
    REFERENCES gnaf.states(state_abbreviation);

ALTER TABLE gnaf.addresses
    ADD CONSTRAINT fk_addresses_locality
    FOREIGN KEY (locality_pid)
    REFERENCES gnaf.localities(locality_pid);

ALTER TABLE gnaf.streets
    ADD CONSTRAINT fk_streets_locality
    FOREIGN KEY (locality_pid)
    REFERENCES gnaf.localities(locality_pid);

-- ============================================
-- Step 5: Create Views
-- ============================================

-- NSW Suburbs and Postcodes View
CREATE OR REPLACE VIEW gnaf.v_nsw_suburb_postcode AS
SELECT DISTINCT
    suburb,
    postcode,
    state
FROM gnaf.suburb_postcode
WHERE state = 'NSW'
ORDER BY suburb, postcode;

COMMENT ON VIEW gnaf.v_nsw_suburb_postcode IS 'NSW suburbs with their postcodes';

-- All States Suburb Summary
CREATE OR REPLACE VIEW gnaf.v_suburb_summary AS
SELECT 
    state,
    COUNT(DISTINCT suburb) as suburb_count,
    COUNT(DISTINCT postcode) as postcode_count,
    COUNT(*) as mapping_count
FROM gnaf.suburb_postcode
GROUP BY state
ORDER BY state;

COMMENT ON VIEW gnaf.v_suburb_summary IS 'Summary of suburbs and postcodes by state';

-- Localities with Address Counts
CREATE OR REPLACE VIEW gnaf.v_locality_statistics AS
SELECT 
    l.locality_name,
    l.primary_postcode,
    l.state_abbreviation,
    COUNT(a.address_id) as address_count
FROM gnaf.localities l
LEFT JOIN gnaf.addresses a ON l.locality_pid = a.locality_pid
GROUP BY l.locality_id, l.locality_name, l.primary_postcode, l.state_abbreviation
ORDER BY address_count DESC;

COMMENT ON VIEW gnaf.v_locality_statistics IS 'Localities with address counts';

-- ============================================
-- Step 6: Create Utility Functions
-- ============================================

-- Function to search suburbs by postcode
CREATE OR REPLACE FUNCTION gnaf.get_suburbs_by_postcode(p_postcode VARCHAR)
RETURNS TABLE (suburb VARCHAR, state VARCHAR, is_primary BOOLEAN) AS $$
BEGIN
    RETURN QUERY
    SELECT sp.suburb, sp.state, sp.is_primary
    FROM gnaf.suburb_postcode sp
    WHERE sp.postcode = p_postcode
    ORDER BY sp.is_primary DESC, sp.suburb;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION gnaf.get_suburbs_by_postcode IS 'Get all suburbs for a given postcode';

-- Function to search postcodes by suburb
CREATE OR REPLACE FUNCTION gnaf.get_postcodes_by_suburb(p_suburb VARCHAR)
RETURNS TABLE (postcode VARCHAR, state VARCHAR, is_primary BOOLEAN) AS $$
BEGIN
    RETURN QUERY
    SELECT sp.postcode, sp.state, sp.is_primary
    FROM gnaf.suburb_postcode sp
    WHERE UPPER(sp.suburb) = UPPER(p_suburb)
    ORDER BY sp.is_primary DESC, sp.postcode;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION gnaf.get_postcodes_by_suburb IS 'Get all postcodes for a given suburb name';

-- ============================================
-- Step 7: Grant Permissions (adjust as needed)
-- ============================================

-- Grant usage on schema
GRANT USAGE ON SCHEMA gnaf TO PUBLIC;

-- Grant select on all tables to public (adjust for your security needs)
GRANT SELECT ON ALL TABLES IN SCHEMA gnaf TO PUBLIC;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA gnaf TO PUBLIC;

-- For inserting data, you may want to create a specific role
-- CREATE ROLE gnaf_admin;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA gnaf TO gnaf_admin;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA gnaf TO gnaf_admin;

-- ============================================
-- Summary
-- ============================================
-- Database created: gnaf_db
-- Schema created: gnaf
-- Tables created:
--   - localities (main locality/suburb data)
--   - postcodes (postcode lookup)
--   - suburb_postcode (suburb-postcode mapping)
--   - addresses (full GNAF address details)
--   - streets (street information)
--   - states (Australian states/territories)
-- Views created:
--   - v_nsw_suburb_postcode
--   - v_suburb_summary
--   - v_locality_statistics
-- Functions created:
--   - get_suburbs_by_postcode()
--   - get_postcodes_by_suburb()
