# School Catchment Database Integration Guide

## Database: `gnaf_db`

---

## Tables Overview

### GNAF Tables (Schema: `gnaf`)
| Table | Records | Description |
|-------|---------|-------------|
| `address_detail` | 15M+ | Core address records with street numbers, postcodes |
| `address_default_geocode` | 15M+ | Latitude/longitude coordinates for addresses |
| `locality` | 14,125 | Suburbs/localities |
| `street_locality` | ~500K | Street names and types |
| `state` | 9 | Australian states/territories |
| `street_type_aut` | ~50 | Street type codes (St, Rd, Ave, etc.) |
| `flat_type_aut` | ~30 | Unit/flat type codes |
| `suburb_postcode` | Custom | Suburb-postcode mapping table |

### School Catchment Tables (Schema: `public`)
| Table | Records | Description |
|-------|---------|-------------|
| `school_catchments_primary` | 1,661 | Primary school catchment boundaries (K-6) |
| `school_catchments_secondary` | 447 | Secondary school catchment boundaries (7-12) |
| `school_catchments_future` | 14 | Future/planned school catchments |

### PostGIS Extension
✅ **Enabled** - Provides spatial query functions (ST_Contains, ST_Distance, etc.)

---

## School Catchment Table Schema

### Columns (All tables share same structure):
| Column | Type | Description |
|--------|------|-------------|
| `USE_ID` | Integer | Unique school identifier |
| `USE_DESC` | String | School name (e.g., "Hornsby NPS") |
| `CATCH_TYPE` | String | "PRIMARY", "SECONDARY", or "FUTURE" |
| `ADD_DATE` | String | Date catchment was added (YYYYMMDD) |
| `KINDERGART` | String | "Y" if catchment includes Kindergarten |
| `YEAR1` - `YEAR12` | String | "Y" if catchment includes that year level |
| `PRIORITY` | String | Priority level (if applicable) |
| `geometry` | Geometry | Polygon defining catchment boundary (EPSG:4326) |

---

## Useful SQL Queries

### 1. Find School Catchment for a Specific Address

**By Coordinates:**
```sql
SELECT 
    sc."USE_ID" as school_id,
    sc."USE_DESC" as school_name,
    sc."CATCH_TYPE" as catchment_type,
    ARRAY_AGG(
        CASE 
            WHEN sc."KINDERGART" = 'Y' THEN 'K'
            WHEN sc."YEAR1" = 'Y' THEN '1'
            WHEN sc."YEAR2" = 'Y' THEN '2'
            WHEN sc."YEAR3" = 'Y' THEN '3'
            WHEN sc."YEAR4" = 'Y' THEN '4'
            WHEN sc."YEAR5" = 'Y' THEN '5'
            WHEN sc."YEAR6" = 'Y' THEN '6'
        END
    ) as years_offered
FROM school_catchments_primary sc
WHERE ST_Contains(
    sc.geometry, 
    ST_SetSRID(ST_MakePoint(151.09256307, -33.69457754), 4326)
)
GROUP BY sc."USE_ID", sc."USE_DESC", sc."CATCH_TYPE";
```

**By GNAF Address ID:**
```sql
SELECT 
    sc."USE_DESC" as school_name,
    sc."CATCH_TYPE" as type
FROM gnaf.address_detail ad
JOIN gnaf.address_default_geocode adg ON ad.address_detail_pid = adg.address_detail_pid
JOIN school_catchments_primary sc ON ST_Contains(
    sc.geometry,
    ST_SetSRID(ST_MakePoint(adg.longitude, adg.latitude), 4326)
)
WHERE ad.address_detail_pid = 'GANSW704953448';
```

---

### 2. Find All Addresses in a School Catchment

```sql
SELECT 
    ad.address_detail_pid,
    CONCAT_WS(' ',
        ad.number_first,
        CASE WHEN ad.number_last IS NOT NULL THEN '-' || ad.number_last END,
        sl.street_name,
        st.name
    ) as full_address,
    l.locality_name as suburb,
    ad.postcode,
    adg.latitude,
    adg.longitude
FROM school_catchments_primary sc
JOIN LATERAL (
    SELECT ad.*, adg.latitude, adg.longitude
    FROM gnaf.address_detail ad
    JOIN gnaf.address_default_geocode adg ON ad.address_detail_pid = adg.address_detail_pid
    WHERE ST_Contains(sc.geometry, ST_SetSRID(ST_MakePoint(adg.longitude, adg.latitude), 4326))
    AND ad.date_retired IS NULL
) ad_with_coords ON true
JOIN gnaf.address_detail ad ON ad.address_detail_pid = ad_with_coords.address_detail_pid
LEFT JOIN gnaf.street_locality sl ON ad.street_locality_pid = sl.street_locality_pid
LEFT JOIN gnaf.street_type_aut st ON sl.street_type_code = st.code
LEFT JOIN gnaf.locality l ON ad.locality_pid = l.locality_pid
WHERE UPPER(sc."USE_DESC") LIKE '%HORNSBY%'
LIMIT 100;
```

---

### 3. Count Addresses by School Catchment

```sql
SELECT 
    sc."USE_DESC" as school_name,
    sc."USE_ID" as school_id,
    COUNT(DISTINCT ad.address_detail_pid) as address_count
FROM school_catchments_primary sc
LEFT JOIN LATERAL (
    SELECT ad.address_detail_pid, adg.latitude, adg.longitude
    FROM gnaf.address_detail ad
    JOIN gnaf.address_default_geocode adg ON ad.address_detail_pid = adg.address_detail_pid
    WHERE ST_Contains(sc.geometry, ST_SetSRID(ST_MakePoint(adg.longitude, adg.latitude), 4326))
    AND ad.date_retired IS NULL
) ad ON true
GROUP BY sc."USE_DESC", sc."USE_ID"
ORDER BY address_count DESC
LIMIT 20;
```

---

### 4. Find Schools Near a Specific Address (Within Radius)

```sql
-- Find schools within 2km of an address
WITH address_point AS (
    SELECT 
        ST_SetSRID(ST_MakePoint(adg.longitude, adg.latitude), 4326) as geom
    FROM gnaf.address_detail ad
    JOIN gnaf.address_default_geocode adg ON ad.address_detail_pid = adg.address_detail_pid
    WHERE ad.address_detail_pid = 'GANSW704953448'
)
SELECT 
    sc."USE_DESC" as school_name,
    sc."CATCH_TYPE" as type,
    ST_Distance(
        ST_Transform(sc.geometry, 3857),
        ST_Transform(ap.geom, 3857)
    ) / 1000 as distance_km
FROM school_catchments_primary sc
CROSS JOIN address_point ap
WHERE ST_DWithin(
    ST_Transform(sc.geometry, 3857),
    ST_Transform(ap.geom, 3857),
    2000  -- 2km in meters
)
ORDER BY distance_km
LIMIT 10;
```

---

### 5. Find Addresses with Both Primary and Secondary Schools

```sql
SELECT 
    ad.address_detail_pid,
    CONCAT_WS(' ',
        ad.number_first,
        sl.street_name,
        st.name
    ) as address,
    l.locality_name as suburb,
    ad.postcode,
    sp."USE_DESC" as primary_school,
    ss."USE_DESC" as secondary_school
FROM gnaf.address_detail ad
JOIN gnaf.address_default_geocode adg ON ad.address_detail_pid = adg.address_detail_pid
LEFT JOIN gnaf.street_locality sl ON ad.street_locality_pid = sl.street_locality_pid
LEFT JOIN gnaf.street_type_aut st ON sl.street_type_code = st.code
LEFT JOIN gnaf.locality l ON ad.locality_pid = l.locality_pid
LEFT JOIN school_catchments_primary sp ON ST_Contains(
    sp.geometry,
    ST_SetSRID(ST_MakePoint(adg.longitude, adg.latitude), 4326)
)
LEFT JOIN school_catchments_secondary ss ON ST_Contains(
    ss.geometry,
    ST_SetSRID(ST_MakePoint(adg.longitude, adg.latitude), 4326)
)
WHERE ad.date_retired IS NULL
AND l.locality_name = 'HORNSBY'
LIMIT 50;
```

---

### 6. Compare Catchment Coverage by Suburb

```sql
SELECT 
    l.locality_name as suburb,
    s.state_abbreviation as state,
    COUNT(DISTINCT ad.address_detail_pid) as total_addresses,
    COUNT(DISTINCT CASE WHEN sp."USE_ID" IS NOT NULL THEN ad.address_detail_pid END) as in_primary_catchment,
    COUNT(DISTINCT CASE WHEN ss."USE_ID" IS NOT NULL THEN ad.address_detail_pid END) as in_secondary_catchment,
    ROUND(
        100.0 * COUNT(DISTINCT CASE WHEN sp."USE_ID" IS NOT NULL THEN ad.address_detail_pid END) / 
        NULLIF(COUNT(DISTINCT ad.address_detail_pid), 0),
        2
    ) as primary_coverage_pct
FROM gnaf.address_detail ad
JOIN gnaf.locality l ON ad.locality_pid = l.locality_pid
JOIN gnaf.state s ON l.state_pid = s.state_pid
JOIN gnaf.address_default_geocode adg ON ad.address_detail_pid = adg.address_detail_pid
LEFT JOIN school_catchments_primary sp ON ST_Contains(
    sp.geometry,
    ST_SetSRID(ST_MakePoint(adg.longitude, adg.latitude), 4326)
)
LEFT JOIN school_catchments_secondary ss ON ST_Contains(
    ss.geometry,
    ST_SetSRID(ST_MakePoint(adg.longitude, adg.latitude), 4326)
)
WHERE ad.date_retired IS NULL
AND s.state_abbreviation = 'NSW'
GROUP BY l.locality_name, s.state_abbreviation
HAVING COUNT(DISTINCT ad.address_detail_pid) > 100
ORDER BY primary_coverage_pct DESC
LIMIT 20;
```

---

### 7. Find Overlapping School Catchments (Edge Cases)

```sql
-- Addresses that fall into multiple primary school catchments
SELECT 
    ad.address_detail_pid,
    CONCAT_WS(' ', ad.number_first, sl.street_name, st.name) as address,
    l.locality_name as suburb,
    STRING_AGG(sc."USE_DESC", ' | ') as schools,
    COUNT(*) as catchment_count
FROM gnaf.address_detail ad
JOIN gnaf.address_default_geocode adg ON ad.address_detail_pid = adg.address_detail_pid
LEFT JOIN gnaf.street_locality sl ON ad.street_locality_pid = sl.street_locality_pid
LEFT JOIN gnaf.street_type_aut st ON sl.street_type_code = st.code
LEFT JOIN gnaf.locality l ON ad.locality_pid = l.locality_pid
JOIN school_catchments_primary sc ON ST_Contains(
    sc.geometry,
    ST_SetSRID(ST_MakePoint(adg.longitude, adg.latitude), 4326)
)
WHERE ad.date_retired IS NULL
GROUP BY ad.address_detail_pid, address, suburb
HAVING COUNT(*) > 1
LIMIT 100;
```

---

### 8. School Catchment Statistics Summary

```sql
SELECT 
    'Primary Schools' as category,
    COUNT(*) as total_schools,
    SUM(CASE WHEN "KINDERGART" = 'Y' THEN 1 ELSE 0 END) as with_kindergarten,
    SUM(CASE WHEN "YEAR6" = 'Y' THEN 1 ELSE 0 END) as with_year6
FROM school_catchments_primary

UNION ALL

SELECT 
    'Secondary Schools' as category,
    COUNT(*) as total_schools,
    SUM(CASE WHEN "YEAR7" = 'Y' THEN 1 ELSE 0 END) as with_year7,
    SUM(CASE WHEN "YEAR12" = 'Y' THEN 1 ELSE 0 END) as with_year12
FROM school_catchments_secondary

UNION ALL

SELECT 
    'Future Schools' as category,
    COUNT(*) as total_schools,
    0 as stat1,
    0 as stat2
FROM school_catchments_future;
```

---

## Performance Tips

1. **Always use spatial indexes**: Already created during load
2. **Transform coordinates for distance calculations**: Use `ST_Transform(..., 3857)` for meter-based calculations
3. **Limit results**: Use `LIMIT` for large queries
4. **Use EXPLAIN ANALYZE**: Check query performance
   ```sql
   EXPLAIN ANALYZE
   SELECT ...
   ```

---

## Python Integration

Use the helper scripts:
- `load_school_catchments.py` - Load shapefiles into database
- `query_school_catchments.py` - Query examples in Python

**Example Python Query:**
```python
from query_school_catchments import find_school_catchment_by_coordinates

# Find school for address
catchment = find_school_catchment_by_coordinates(
    latitude=-33.8688,
    longitude=151.2093,
    school_type='primary'
)

print(f"School: {catchment['school_name']}")
```

---

## Next Steps

✅ **Completed:**
- PostGIS extension enabled
- School catchment data loaded (2,122 total catchments)
- Spatial indexes created
- Coordinate systems aligned (EPSG:4326)

🎯 **Potential Web App Features:**
1. Add school catchment info to address lookup results
2. Filter addresses by school catchment
3. Display catchment boundaries on a map
4. Show nearby schools with distances
5. Compare properties by school catchment

---

**Last Updated:** January 26, 2026  
**Database:** gnaf_db  
**Coordinate System:** EPSG:4326 (WGS84)
