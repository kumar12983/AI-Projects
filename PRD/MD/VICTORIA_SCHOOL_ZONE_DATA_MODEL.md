# Victoria School Zone Data Model - Harmonization with gnaf.school_catchments

## Executive Summary

This document provides a comprehensive data model for integrating Victoria School Zone 2024 data with the existing NSW school catchment infrastructure, ensuring compatibility with the `gnaf.school_catchments` table and school search functionality.

---

## Current State Analysis

### NSW Data Structure (gnaf.school_catchments)

**Source**: NSW Department of Education Catchment Shapefiles  
**Format**: Shapefile (.shp)  
**Schema**: Combined table for PRIMARY, SECONDARY, and FUTURE schools

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `school_id` | TEXT | Unique school identifier (USE_ID) | "1937" |
| `school_name` | VARCHAR | School name (USE_DESC) | "Hornsby NPS" |
| `school_type` | VARCHAR | Catchment type (CATCH_TYPE) | "PRIMARY", "SECONDARY", "FUTURE" |
| `ADD_DATE` | VARCHAR | Date added (YYYYMMDD) | "20240101" |
| `KINDERGART` | VARCHAR(1) | Kindergarten included | "Y" or "N" |
| `YEAR1` - `YEAR12` | VARCHAR(1) | Year level included | "Y" or "N" |
| `PRIORITY` | VARCHAR | Priority level | "1", "2", etc. |
| `geometry` | GEOMETRY(POLYGON, 4326) | Catchment boundary | PostGIS geometry |

**Characteristics**:
- Single catchment polygon per school
- All year levels in one record
- NSW-specific (state_abbreviation = 'NSW')

---

### Victoria Data Structure (DataVic School Zones 2024)

**Source**: DataVic - Victorian Department of Education  
**Location**: `C:\Users\kumar\Documents\workspace\dv371_DataVic_School_Zones_2024`  
**Format**: GeoJSON + MapInfo TAB files  
**Files**: 10 separate files for different school types and year levels

#### File Breakdown:

1. **Primary_Integrated_2024.geojson** (1,255 catchments)
   - Year Level: "P6" (Prep to Year 6)

2. **Secondary_Integrated_Year7_2024.geojson** 
3. **Secondary_Integrated_Year8_2024.geojson**
4. **Secondary_Integrated_Year9_2024.geojson**
5. **Secondary_Integrated_Year10_2024.geojson**
6. **Secondary_Integrated_Year11_2024.geojson**
7. **Secondary_Integrated_Year12_2024.geojson**
   - Year-specific secondary catchments

8. **Standalone_juniorsec_2024.geojson**
9. **Standalone_seniorsec_2024.geojson**
10. **Standalone_singlesex_2024.geojson**
    - Specialized school types

#### Victoria GeoJSON Properties:

```json
{
  "School_Name": "Lockwood Primary School",
  "Campus_Name": "Lockwood Primary School",
  "ENTITY_CODE": 1074401,
  "Year_Level": "P6",
  "Boundary_Year": 2024,
  "geometry": {...}
}
```

**Characteristics**:
- Multiple catchment files per school (one per year level for secondary)
- ENTITY_CODE as unique identifier
- Victoria-specific
- Year_Level codes: "P6", "7", "8", "9", "10", "11", "12"

---

## Key Differences & Challenges

### 1. Data Granularity
- **NSW**: One catchment per school with all year levels
- **VIC**: Separate catchments per year level (especially secondary schools)

### 2. Identifiers
- **NSW**: USE_ID (numeric string)
- **VIC**: ENTITY_CODE (integer)

### 3. Year Level Encoding
- **NSW**: Boolean columns (YEAR1-YEAR12, KINDERGART)
- **VIC**: String code (Year_Level = "P6", "7", "8", etc.)

### 4. School Types
- **NSW**: CATCH_TYPE (PRIMARY, SECONDARY, FUTURE)
- **VIC**: Implied by file name and Year_Level

---

## Proposed Harmonized Data Model

### Option 1: Extended Unified Table (RECOMMENDED)

Extend `gnaf.school_catchments` to support both NSW and Victoria data with backward compatibility.

```sql
-- Enhanced school_catchments table
CREATE TABLE gnaf.school_catchments (
    -- Primary key
    catchment_id SERIAL PRIMARY KEY,
    
    -- School identification
    school_id VARCHAR(50) NOT NULL,           -- USE_ID (NSW) or ENTITY_CODE (VIC)
    school_name VARCHAR(255) NOT NULL,        -- School name
    campus_name VARCHAR(255),                 -- Campus name (VIC specific)
    school_type VARCHAR(50) NOT NULL,         -- PRIMARY, SECONDARY, FUTURE, JUNIOR_SEC, SENIOR_SEC, SINGLE_SEX
    
    -- Geographic/Administrative
    state VARCHAR(3) NOT NULL,                -- 'NSW', 'VIC', etc.
    boundary_year INTEGER NOT NULL,           -- Year of boundary data (2024)
    
    -- Year level coverage (NSW approach - backward compatible)
    kindergart VARCHAR(1),                    -- 'Y' or 'N'
    year1 VARCHAR(1),
    year2 VARCHAR(1),
    year3 VARCHAR(1),
    year4 VARCHAR(1),
    year5 VARCHAR(1),
    year6 VARCHAR(1),
    year7 VARCHAR(1),
    year8 VARCHAR(1),
    year9 VARCHAR(1),
    year10 VARCHAR(1),
    year11 VARCHAR(1),
    year12 VARCHAR(1),
    
    -- Victoria-specific fields
    year_level_code VARCHAR(10),              -- 'P6', '7', '8', etc. (VIC)
    entity_code INTEGER,                      -- Original VIC ENTITY_CODE
    
    -- NSW-specific fields
    use_id VARCHAR(50),                       -- Original NSW USE_ID
    add_date VARCHAR(8),                      -- NSW add date (YYYYMMDD)
    priority VARCHAR(10),                     -- NSW priority
    
    -- Spatial data
    geometry GEOMETRY(GEOMETRY, 4326) NOT NULL,  -- Supports both POLYGON and MULTIPOLYGON
    centroid_lat DOUBLE PRECISION,            -- Cached centroid
    centroid_lng DOUBLE PRECISION,            -- Cached centroid
    
    -- Metadata
    data_source VARCHAR(50) NOT NULL,         -- 'NSW_DET', 'DATAVIC'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_state CHECK (state IN ('NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'NT', 'ACT')),
    CONSTRAINT chk_year_values CHECK (
        kindergart IN ('Y', 'N', NULL) AND
        year1 IN ('Y', 'N', NULL) AND
        year2 IN ('Y', 'N', NULL) AND
        year3 IN ('Y', 'N', NULL) AND
        year4 IN ('Y', 'N', NULL) AND
        year5 IN ('Y', 'N', NULL) AND
        year6 IN ('Y', 'N', NULL) AND
        year7 IN ('Y', 'N', NULL) AND
        year8 IN ('Y', 'N', NULL) AND
        year9 IN ('Y', 'N', NULL) AND
        year10 IN ('Y', 'N', NULL) AND
        year11 IN ('Y', 'N', NULL) AND
        year12 IN ('Y', 'N', NULL)
    )
);

-- Indexes for performance
CREATE INDEX idx_school_catchments_geom ON gnaf.school_catchments USING GIST (geometry);
CREATE INDEX idx_school_catchments_school_id ON gnaf.school_catchments (school_id);
CREATE INDEX idx_school_catchments_state ON gnaf.school_catchments (state);
CREATE INDEX idx_school_catchments_school_type ON gnaf.school_catchments (school_type);
CREATE INDEX idx_school_catchments_entity_code ON gnaf.school_catchments (entity_code) WHERE entity_code IS NOT NULL;
CREATE INDEX idx_school_catchments_centroid ON gnaf.school_catchments (centroid_lat, centroid_lng);
CREATE INDEX idx_school_catchments_boundary_year ON gnaf.school_catchments (boundary_year);

-- Composite index for common queries
CREATE INDEX idx_school_catchments_state_type ON gnaf.school_catchments (state, school_type);

-- Full-text search on school names
CREATE INDEX idx_school_catchments_name_trgm ON gnaf.school_catchments USING GIN (school_name gin_trgm_ops);
```

---

### Option 2: Separate Victoria Table (Alternative)

Create a separate table for Victoria data if keeping them isolated is preferred.

```sql
CREATE TABLE gnaf.vic_school_catchments (
    catchment_id SERIAL PRIMARY KEY,
    entity_code INTEGER NOT NULL,
    school_name VARCHAR(255) NOT NULL,
    campus_name VARCHAR(255) NOT NULL,
    school_type VARCHAR(50) NOT NULL,          -- Derived from file
    year_level_code VARCHAR(10) NOT NULL,       -- 'P6', '7', '8', etc.
    boundary_year INTEGER NOT NULL DEFAULT 2024,
    geometry GEOMETRY(GEOMETRY, 4326) NOT NULL,
    centroid_lat DOUBLE PRECISION,
    centroid_lng DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Normalized year flags for compatibility
    kindergart VARCHAR(1) GENERATED ALWAYS AS (
        CASE WHEN year_level_code = 'P6' THEN 'Y' ELSE 'N' END
    ) STORED,
    year1 VARCHAR(1) GENERATED ALWAYS AS (
        CASE WHEN year_level_code = 'P6' THEN 'Y' ELSE 'N' END
    ) STORED,
    -- ... similar for other years
    
    CONSTRAINT uk_vic_catchment UNIQUE (entity_code, year_level_code)
);

-- Create unified view
CREATE VIEW gnaf.school_catchments_unified AS
SELECT 
    CONCAT('NSW_', school_id) as catchment_id,
    school_id,
    school_name,
    NULL as campus_name,
    school_type,
    'NSW' as state,
    2024 as boundary_year,
    kindergart, year1, year2, year3, year4, year5, year6,
    year7, year8, year9, year10, year11, year12,
    NULL as year_level_code,
    NULL as entity_code,
    geometry,
    ST_Y(ST_Centroid(geometry)) as centroid_lat,
    ST_X(ST_Centroid(geometry)) as centroid_lng
FROM gnaf.school_catchments
WHERE state = 'NSW'

UNION ALL

SELECT
    CONCAT('VIC_', catchment_id) as catchment_id,
    entity_code::VARCHAR as school_id,
    school_name,
    campus_name,
    school_type,
    'VIC' as state,
    boundary_year,
    kindergart, year1, year2, year3, year4, year5, year6,
    year7, year8, year9, year10, year11, year12,
    year_level_code,
    entity_code,
    geometry,
    centroid_lat,
    centroid_lng
FROM gnaf.vic_school_catchments;
```

---

## Data Transformation Strategy

### Victoria Year Level Mapping

```python
# Map Victoria year_level_code to year flags
def map_vic_year_levels(year_level_code, school_type):
    """
    Map Victoria year_level codes to NSW-style year flags
    
    Args:
        year_level_code: 'P6', '7', '8', '9', '10', '11', '12'
        school_type: 'PRIMARY', 'SECONDARY', etc.
    
    Returns:
        dict: Year flags (kindergart, year1-year12)
    """
    year_flags = {f'year{i}': 'N' for i in range(1, 13)}
    year_flags['kindergart'] = 'N'
    
    if year_level_code == 'P6':
        # Primary integrated: Prep (Kindergarten) to Year 6
        year_flags['kindergart'] = 'Y'
        for i in range(1, 7):
            year_flags[f'year{i}'] = 'Y'
    
    elif year_level_code.isdigit():
        # Specific year level (7-12)
        year_num = int(year_level_code)
        if 7 <= year_num <= 12:
            year_flags[f'year{year_num}'] = 'Y'
    
    return year_flags

# Map file names to school types
FILE_TO_SCHOOL_TYPE = {
    'Primary_Integrated': 'PRIMARY',
    'Secondary_Integrated': 'SECONDARY',
    'Standalone_juniorsec': 'JUNIOR_SECONDARY',
    'Standalone_seniorsec': 'SENIOR_SECONDARY',
    'Standalone_singlesex': 'SINGLE_SEX',
}
```

### Data Loading Process

```python
import geopandas as gpd
import json
from pathlib import Path

def load_victoria_geojson(file_path, school_type):
    """
    Load Victoria school zone GeoJSON and transform to unified schema
    
    Args:
        file_path: Path to GeoJSON file
        school_type: School type classification
    
    Returns:
        GeoDataFrame with normalized schema
    """
    # Read GeoJSON
    gdf = gpd.read_file(file_path)
    
    # Ensure WGS84 (EPSG:4326)
    if gdf.crs != 'EPSG:4326':
        gdf = gdf.to_crs('EPSG:4326')
    
    # Calculate centroids
    gdf['centroid_lat'] = gdf.geometry.centroid.y
    gdf['centroid_lng'] = gdf.geometry.centroid.x
    
    # Transform columns
    gdf_normalized = gdf.rename(columns={
        'ENTITY_CODE': 'entity_code',
        'School_Name': 'school_name',
        'Campus_Name': 'campus_name',
        'Year_Level': 'year_level_code',
        'Boundary_Year': 'boundary_year'
    })
    
    # Add year flags
    year_cols = []
    for idx, row in gdf_normalized.iterrows():
        year_flags = map_vic_year_levels(row['year_level_code'], school_type)
        for key, val in year_flags.items():
            gdf_normalized.at[idx, key] = val
    
    # Add metadata
    gdf_normalized['school_id'] = gdf_normalized['entity_code'].astype(str)
    gdf_normalized['school_type'] = school_type
    gdf_normalized['state'] = 'VIC'
    gdf_normalized['data_source'] = 'DATAVIC'
    
    return gdf_normalized
```

---

## Migration Script Template

```python
#!/usr/bin/env python3
"""
Load Victoria School Zone Data into gnaf.school_catchments

Usage:
    python load_victoria_catchments.py
"""

import geopandas as gpd
from sqlalchemy import create_engine
import psycopg2
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv('webapp/.env')

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'gnaf_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'admin')

connection_string = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

# Victoria data location
VIC_DATA_DIR = Path(r'C:\Users\kumar\Documents\workspace\dv371_DataVic_School_Zones_2024')

# File mappings
VIC_FILES = {
    'Primary_Integrated_2024.geojson': {
        'school_type': 'PRIMARY',
        'description': 'Primary schools (Prep-Year 6)'
    },
    'Secondary_Integrated_Year7_2024.geojson': {
        'school_type': 'SECONDARY',
        'description': 'Secondary schools - Year 7 catchments'
    },
    'Secondary_Integrated_Year8_2024.geojson': {
        'school_type': 'SECONDARY',
        'description': 'Secondary schools - Year 8 catchments'
    },
    'Secondary_Integrated_Year9_2024.geojson': {
        'school_type': 'SECONDARY',
        'description': 'Secondary schools - Year 9 catchments'
    },
    'Secondary_Integrated_Year10_2024.geojson': {
        'school_type': 'SECONDARY',
        'description': 'Secondary schools - Year 10 catchments'
    },
    'Secondary_Integrated_Year11_2024.geojson': {
        'school_type': 'SECONDARY',
        'description': 'Secondary schools - Year 11 catchments'
    },
    'Secondary_Integrated_Year12_2024.geojson': {
        'school_type': 'SECONDARY',
        'description': 'Secondary schools - Year 12 catchments'
    },
    'Standalone_juniorsec_2024.geojson': {
        'school_type': 'JUNIOR_SECONDARY',
        'description': 'Standalone junior secondary schools'
    },
    'Standalone_seniorsec_2024.geojson': {
        'school_type': 'SENIOR_SECONDARY',
        'description': 'Standalone senior secondary schools'
    },
    'Standalone_singlesex_2024.geojson': {
        'school_type': 'SINGLE_SEX',
        'description': 'Single-sex schools'
    }
}

def map_year_levels(year_level_code):
    """Map Victoria year level codes to year flags"""
    year_flags = {f'year{i}': 'N' for i in range(1, 13)}
    year_flags['kindergart'] = 'N'
    
    if year_level_code == 'P6':
        year_flags['kindergart'] = 'Y'
        for i in range(1, 7):
            year_flags[f'year{i}'] = 'Y'
    elif year_level_code and year_level_code.isdigit():
        year_num = int(year_level_code)
        if 7 <= year_num <= 12:
            year_flags[f'year{year_num}'] = 'Y'
    
    return year_flags

def load_victoria_file(file_path, school_type, engine):
    """Load a single Victoria GeoJSON file"""
    print(f"\nLoading: {file_path.name}")
    print(f"  School Type: {school_type}")
    
    # Read GeoJSON
    gdf = gpd.read_file(file_path)
    print(f"  Records: {len(gdf)}")
    
    # Convert CRS if needed
    if gdf.crs and gdf.crs != 'EPSG:4326':
        print(f"  Converting CRS from {gdf.crs} to EPSG:4326...")
        gdf = gdf.to_crs('EPSG:4326')
    
    # Transform data
    transformed_records = []
    for idx, row in gdf.iterrows():
        # Map year levels
        year_flags = map_year_levels(row.get('Year_Level'))
        
        # Build record
        record = {
            'school_id': str(row['ENTITY_CODE']),
            'school_name': row['School_Name'],
            'campus_name': row['Campus_Name'],
            'school_type': school_type,
            'state': 'VIC',
            'boundary_year': row.get('Boundary_Year', 2024),
            **year_flags,
            'year_level_code': row.get('Year_Level'),
            'entity_code': row['ENTITY_CODE'],
            'use_id': None,
            'add_date': None,
            'priority': None,
            'geometry': row['geometry'],
            'centroid_lat': row.geometry.centroid.y,
            'centroid_lng': row.geometry.centroid.x,
            'data_source': 'DATAVIC'
        }
        transformed_records.append(record)
    
    # Create GeoDataFrame
    gdf_transformed = gpd.GeoDataFrame(transformed_records, crs='EPSG:4326')
    
    # Load to database
    print(f"  Writing to database...")
    gdf_transformed.to_postgis(
        'school_catchments',
        engine,
        schema='gnaf',
        if_exists='append',
        index=False
    )
    
    print(f"  ✓ Loaded {len(gdf_transformed)} records")
    return len(gdf_transformed)

def main():
    print("=" * 70)
    print("Victoria School Zone Data Loader")
    print("=" * 70)
    
    # Create engine
    engine = create_engine(connection_string)
    
    total_loaded = 0
    
    # Load each file
    for filename, config in VIC_FILES.items():
        file_path = VIC_DATA_DIR / filename
        
        if not file_path.exists():
            print(f"\n⚠ File not found: {filename}")
            continue
        
        try:
            count = load_victoria_file(
                file_path,
                config['school_type'],
                engine
            )
            total_loaded += count
        except Exception as e:
            print(f"\n✗ Error loading {filename}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print(f"✓ Migration complete!")
    print(f"  Total records loaded: {total_loaded}")
    print("=" * 70)

if __name__ == '__main__':
    main()
```

---

## Search & Query Compatibility

### Updated Search Queries

```sql
-- Find schools serving an address (supports both NSW and VIC)
SELECT 
    sc.school_id,
    sc.school_name,
    sc.campus_name,
    sc.school_type,
    sc.state,
    sc.year_level_code,
    CASE 
        WHEN sc.kindergart = 'Y' THEN 'K, '
        ELSE ''
    END ||
    STRING_AGG(
        DISTINCT CASE 
            WHEN year1 = 'Y' THEN '1'
            WHEN year2 = 'Y' THEN '2'
            WHEN year3 = 'Y' THEN '3'
            WHEN year4 = 'Y' THEN '4'
            WHEN year5 = 'Y' THEN '5'
            WHEN year6 = 'Y' THEN '6'
            WHEN year7 = 'Y' THEN '7'
            WHEN year8 = 'Y' THEN '8'
            WHEN year9 = 'Y' THEN '9'
            WHEN year10 = 'Y' THEN '10'
            WHEN year11 = 'Y' THEN '11'
            WHEN year12 = 'Y' THEN '12'
        END, ', '
    ) as year_levels
FROM gnaf.school_catchments sc
JOIN gnaf.address_detail ad ON ST_Contains(
    sc.geometry,
    ST_SetSRID(ST_MakePoint(ad.longitude, ad.latitude), 4326)
)
WHERE ad.address_detail_pid = ?
GROUP BY sc.school_id, sc.school_name, sc.campus_name, sc.school_type, sc.state, sc.year_level_code;
```

### Flask App Updates

```python
# app.py - Updated to handle Victoria data

@app.route('/api/schools/search')
def search_schools():
    """Search schools by address - supports NSW and VIC"""
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    state = request.args.get('state', 'NSW')  # Add state filter
    
    query = """
        SELECT 
            school_id,
            school_name,
            campus_name,
            school_type,
            state,
            year_level_code,
            centroid_lat,
            centroid_lng,
            ST_Distance(
                geometry::geography,
                ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
            ) / 1000 as distance_km
        FROM gnaf.school_catchments
        WHERE ST_Contains(
            geometry,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)
        )
        AND state = %s
        ORDER BY school_type, school_name
    """
    
    cursor.execute(query, (lng, lat, lng, lat, state))
    results = cursor.fetchall()
    
    return jsonify({
        'schools': [dict(row) for row in results],
        'count': len(results),
        'state': state
    })
```

---

## Recommendations

### ✅ Recommended Approach: Option 1 (Extended Unified Table)

**Rationale**:
1. **Single source of truth**: One table for all school catchments
2. **Backward compatibility**: Existing NSW queries continue to work
3. **Future-proof**: Can accommodate other states (QLD, SA, etc.)
4. **Simplified maintenance**: One schema to maintain
5. **Better performance**: Single spatial index, simpler joins

### Implementation Priorities

1. **Phase 1: Schema Update** (1-2 hours)
   - Backup existing `gnaf.school_catchments` table
   - Add new columns (state, campus_name, entity_code, year_level_code, etc.)
   - Update indexes
   - Test backward compatibility

2. **Phase 2: Data Migration** (2-3 hours)
   - Update existing NSW records (set state='NSW', data_source='NSW_DET')
   - Load Victoria data files
   - Validate data integrity
   - Update materialized views

3. **Phase 3: Application Updates** (3-4 hours)
   - Update Flask routes to handle state parameter
   - Update search queries
   - Update frontend to support state selection
   - Test end-to-end functionality

4. **Phase 4: Documentation** (1 hour)
   - Update API documentation
   - Update database schema docs
   - Create user guide for multi-state support

### Total Estimated Time: 7-10 hours

---

## Testing Strategy

### Data Validation Queries

```sql
-- Verify Victoria data loaded correctly
SELECT 
    state,
    school_type,
    COUNT(*) as catchment_count,
    COUNT(DISTINCT school_id) as unique_schools
FROM gnaf.school_catchments
GROUP BY state, school_type
ORDER BY state, school_type;

-- Check for geometry issues
SELECT 
    school_id,
    school_name,
    state,
    ST_IsValid(geometry) as is_valid,
    ST_GeometryType(geometry) as geom_type
FROM gnaf.school_catchments
WHERE NOT ST_IsValid(geometry);

-- Verify centroids
SELECT 
    school_id,
    school_name,
    state,
    centroid_lat,
    centroid_lng,
    ST_Y(ST_Centroid(geometry)) as calc_lat,
    ST_X(ST_Centroid(geometry)) as calc_lng
FROM gnaf.school_catchments
WHERE ABS(centroid_lat - ST_Y(ST_Centroid(geometry))) > 0.0001
   OR ABS(centroid_lng - ST_X(ST_Centroid(geometry))) > 0.0001
LIMIT 10;

-- Test spatial queries
SELECT 
    sc.school_name,
    sc.state,
    sc.school_type,
    COUNT(*) as address_count
FROM gnaf.school_catchments sc
JOIN gnaf.address_detail ad ON ST_Contains(
    sc.geometry,
    ST_SetSRID(ST_MakePoint(
        ad.longitude, 
        ad.latitude
    ), 4326)
)
WHERE sc.state = 'VIC'
AND ad.state_pid IN (SELECT state_pid FROM gnaf.state WHERE state_abbreviation = 'VIC')
GROUP BY sc.school_name, sc.state, sc.school_type
LIMIT 20;
```

---

## Next Steps

1. **Review & Approve**: Review this data model and approve approach
2. **Backup Strategy**: Create full backup of current database
3. **Test Environment**: Set up test database with sample data
4. **Migration Execution**: Run migration scripts in test environment
5. **Validation**: Run all validation queries
6. **Production Deploy**: Schedule production migration
7. **Monitoring**: Monitor query performance and data accuracy

---

## References

- Current NSW Schema: [SCHOOL_CATCHMENT_GUIDE.md](SCHOOL_CATCHMENT_GUIDE.md)
- Victoria Data Source: DataVic - Department of Education (2024)
- PostGIS Documentation: https://postgis.net/docs/
- GeoDataFrame Documentation: https://geopandas.org/

---

**Document Version**: 1.0  
**Last Updated**: February 10, 2026  
**Author**: GitHub Copilot  
**Status**: Proposed for Review
