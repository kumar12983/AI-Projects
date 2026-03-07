# Victoria School Catchments - Quick Reference Guide

## 🚀 Quick Start

### 1. Prerequisites
- PostgreSQL with PostGIS extension
- Python 3.8+ with geopandas, psycopg2, sqlalchemy
- Victoria school zone data files in GeoJSON format

### 2. Migration Steps (First Time Setup)

```bash
# Step 1: Backup existing data
pg_dump -h localhost -U postgres -d gnaf_db -t gnaf.school_catchments > backup_$(date +%Y%m%d).sql

# Step 2: Run schema migration
psql -h localhost -U postgres -d gnaf_db -f database/migrations/add_victoria_support.sql

# Step 3: Verify schema
psql -h localhost -U postgres -d gnaf_db -c "SELECT column_name FROM information_schema.columns WHERE table_name='school_catchments' AND table_schema='gnaf';"

# Step 4: Load Victoria data (dry run first)
python PRD/scripts/load_victoria_catchments.py --dry-run

# Step 5: Load Victoria data (actual)
python PRD/scripts/load_victoria_catchments.py --backup

# Step 6: Verify data
psql -h localhost -U postgres -d gnaf_db -f database/queries/verify_victoria_data.sql
```

---

## 📊 Data Model Quick Reference

### Schema Comparison

| Aspect | NSW | Victoria |
|--------|-----|----------|
| **Identifier** | `USE_ID` (text) | `ENTITY_CODE` (integer) |
| **School Name** | `USE_DESC` | `School_Name` + `Campus_Name` |
| **School Type** | `CATCH_TYPE` | Derived from file name |
| **Year Levels** | Single record with Y/N flags | Separate records per year level |
| **State Column** | 'NSW' | 'VIC' |
| **Data Source** | 'NSW_DET' | 'DATAVIC' |

### Unified Table Structure

```sql
gnaf.school_catchments
├── catchment_id (SERIAL) ← Primary key
├── school_id (VARCHAR) ← NSW: USE_ID, VIC: ENTITY_CODE as string
├── school_name (VARCHAR) ← School name
├── campus_name (VARCHAR) ← VIC only
├── school_type (VARCHAR) ← PRIMARY, SECONDARY, etc.
├── state (VARCHAR) ← NSW, VIC
├── boundary_year (INTEGER) ← 2024
├── kindergart, year1-year12 (VARCHAR) ← Y/N flags
├── year_level_code (VARCHAR) ← VIC: P6, 7, 8, etc.
├── entity_code (INTEGER) ← VIC: Original ENTITY_CODE
├── use_id (VARCHAR) ← NSW: Original USE_ID
├── geometry (GEOMETRY) ← Catchment boundary
├── centroid_lat, centroid_lng (DOUBLE PRECISION) ← Cached
└── data_source (VARCHAR) ← NSW_DET, DATAVIC
```

---

## 🔍 Common Queries

### Find Schools by Address (Multi-State)

```sql
-- Find all schools serving a specific address
SELECT 
    sc.school_name,
    sc.campus_name,
    sc.school_type,
    sc.state,
    STRING_AGG(
        CASE 
            WHEN kindergart = 'Y' THEN 'K'
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
    ) as year_levels,
    ST_Distance(
        geometry::geography,
        ST_SetSRID(ST_MakePoint(144.9631, -37.8136), 4326)::geography
    ) / 1000 as distance_km
FROM gnaf.school_catchments sc
WHERE ST_Contains(
    sc.geometry,
    ST_SetSRID(ST_MakePoint(144.9631, -37.8136), 4326)  -- Melbourne CBD
)
ORDER BY school_type, distance_km;
```

### Count Catchments by State and Type

```sql
SELECT 
    state,
    school_type,
    COUNT(*) as catchment_count,
    COUNT(DISTINCT school_id) as unique_schools
FROM gnaf.school_catchments
GROUP BY state, school_type
ORDER BY state, school_type;
```

### Find Victoria Primary Schools in a Region

```sql
SELECT 
    school_name,
    campus_name,
    year_level_code,
    centroid_lat,
    centroid_lng
FROM gnaf.school_catchments
WHERE state = 'VIC'
AND school_type = 'PRIMARY'
AND ST_DWithin(
    geometry::geography,
    ST_SetSRID(ST_MakePoint(144.9631, -37.8136), 4326)::geography,
    10000  -- 10km
)
ORDER BY school_name;
```

### Victoria Secondary School Year-Level Breakdown

```sql
-- Show how many secondary catchments each year level has
SELECT 
    year_level_code,
    COUNT(*) as catchment_count,
    COUNT(DISTINCT school_id) as unique_schools
FROM gnaf.school_catchments
WHERE state = 'VIC'
AND school_type = 'SECONDARY'
GROUP BY year_level_code
ORDER BY year_level_code;
```

---

## 🐍 Python Usage Examples

### Search Schools by Coordinates

```python
import psycopg2
from psycopg2.extras import RealDictCursor

def find_schools_by_location(lat, lng, state='VIC'):
    """Find schools serving a specific location"""
    conn = psycopg2.connect(
        host='localhost',
        database='gnaf_db',
        user='postgres',
        password='admin'
    )
    
    query = """
        SELECT 
            school_id,
            school_name,
            campus_name,
            school_type,
            year_level_code,
            CASE 
                WHEN kindergart = 'Y' THEN 'Y' ELSE 'N'
            END as has_kindergarten,
            centroid_lat,
            centroid_lng
        FROM gnaf.school_catchments
        WHERE ST_Contains(
            geometry,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)
        )
        AND state = %s
        ORDER BY school_type, school_name
    """
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query, (lng, lat, state))
        results = cursor.fetchall()
    
    conn.close()
    return results

# Example usage
schools = find_schools_by_location(-37.8136, 144.9631, state='VIC')
for school in schools:
    print(f"{school['school_name']} ({school['school_type']}) - {school['year_level_code']}")
```

### Get Catchment Statistics

```python
def get_catchment_stats(state='VIC'):
    """Get statistics about catchments"""
    conn = psycopg2.connect(
        host='localhost',
        database='gnaf_db',
        user='postgres',
        password='admin'
    )
    
    query = """
        SELECT 
            school_type,
            COUNT(*) as total_catchments,
            COUNT(DISTINCT school_id) as unique_schools,
            ROUND(AVG(ST_Area(geometry::geography) / 1000000)::numeric, 2) as avg_area_km2,
            ROUND(MIN(ST_Area(geometry::geography) / 1000000)::numeric, 2) as min_area_km2,
            ROUND(MAX(ST_Area(geometry::geography) / 1000000)::numeric, 2) as max_area_km2
        FROM gnaf.school_catchments
        WHERE state = %s
        GROUP BY school_type
        ORDER BY school_type
    """
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query, (state,))
        results = cursor.fetchall()
    
    conn.close()
    return results
```

---

## 🔧 Maintenance Tasks

### Update Centroids (After Geometry Changes)

```sql
UPDATE gnaf.school_catchments
SET 
    centroid_lat = ST_Y(ST_Centroid(geometry)),
    centroid_lng = ST_X(ST_Centroid(geometry)),
    updated_at = CURRENT_TIMESTAMP
WHERE state = 'VIC'
AND (centroid_lat IS NULL OR centroid_lng IS NULL);
```

### Rebuild Spatial Index

```sql
REINDEX INDEX gnaf.idx_school_catchments_geom;
ANALYZE gnaf.school_catchments;
```

### Check for Invalid Geometries

```sql
SELECT 
    school_id,
    school_name,
    state,
    ST_IsValidReason(geometry) as invalid_reason
FROM gnaf.school_catchments
WHERE NOT ST_IsValid(geometry);
```

### Fix Invalid Geometries

```sql
UPDATE gnaf.school_catchments
SET geometry = ST_MakeValid(geometry)
WHERE NOT ST_IsValid(geometry);
```

---

## 📈 Performance Tips

### 1. Always Filter by State First

```sql
-- Good ✓
SELECT * FROM gnaf.school_catchments 
WHERE state = 'VIC' 
AND ST_Contains(geometry, point);

-- Bad ✗
SELECT * FROM gnaf.school_catchments 
WHERE ST_Contains(geometry, point) 
AND state = 'VIC';
```

### 2. Use Centroid for Distance Calculations

```sql
-- Good ✓ (uses indexed centroids)
SELECT * FROM gnaf.school_catchments
WHERE state = 'VIC'
AND SQRT(
    POW(centroid_lat - (-37.8136), 2) + 
    POW(centroid_lng - 144.9631, 2)
) < 0.1;

-- OK (uses geography distance, slower)
SELECT * FROM gnaf.school_catchments
WHERE state = 'VIC'
AND ST_DWithin(
    geometry::geography,
    ST_MakePoint(144.9631, -37.8136)::geography,
    10000
);
```

### 3. Use Prepared Statements

```python
# Good ✓
cursor.execute("""
    PREPARE find_schools AS
    SELECT * FROM gnaf.school_catchments
    WHERE state = $1 AND ST_Contains(geometry, ST_MakePoint($2, $3, 4326));
""")
cursor.execute("EXECUTE find_schools(%s, %s, %s)", ('VIC', 144.9631, -37.8136))

# Or in Python with execute many times - the driver will prepare automatically
```

---

## 🐛 Troubleshooting

### Problem: No Victoria Data Showing

```sql
-- Check if data loaded
SELECT COUNT(*) FROM gnaf.school_catchments WHERE state = 'VIC';

-- If 0, check if migration ran
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'school_catchments' 
AND column_name = 'state';
```

### Problem: Spatial Queries Not Working

```sql
-- Check if geometry is valid
SELECT ST_IsValid(geometry), COUNT(*) 
FROM gnaf.school_catchments 
WHERE state = 'VIC'
GROUP BY ST_IsValid(geometry);

-- Check SRID
SELECT DISTINCT ST_SRID(geometry) 
FROM gnaf.school_catchments 
WHERE state = 'VIC';
-- Should return 4326
```

### Problem: Slow Queries

```sql
-- Check if indexes exist
SELECT indexname FROM pg_indexes 
WHERE tablename = 'school_catchments';

-- Rebuild statistics
ANALYZE gnaf.school_catchments;

-- Check query plan
EXPLAIN ANALYZE
SELECT * FROM gnaf.school_catchments
WHERE state = 'VIC'
AND ST_Contains(geometry, ST_MakePoint(144.9631, -37.8136, 4326));
```

---

## 📚 Additional Resources

- [Full Data Model Documentation](VICTORIA_SCHOOL_ZONE_DATA_MODEL.md)
- [Migration Script](../scripts/load_victoria_catchments.py)
- [Schema Update SQL](../database/migrations/add_victoria_support.sql)
- [NSW Catchment Guide](SCHOOL_CATCHMENT_GUIDE.md)

---

## ⚠️ Important Notes

1. **Victoria Secondary Schools**: Each year level (7-12) may have a separate catchment zone
2. **NSW vs VIC**: NSW has one catchment per school, VIC may have multiple
3. **Year Level Codes**: VIC uses 'P6' for primary, '7'-'12' for secondary
4. **Centroids**: Always calculated and cached for performance
5. **Validation**: Always run with `--dry-run` first to validate data

---

**Last Updated**: February 10, 2026  
**Version**: 1.0
