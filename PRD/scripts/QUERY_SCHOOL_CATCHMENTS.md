# School Catchment Query Reference

Quick reference for querying school catchments by address coordinates.

## 📋 Quick Query

```sql
SELECT DISTINCT
    school_id,
    school_name,
    campus_name,
    school_type,
    state,
    year_level_code
FROM gnaf.school_catchments
WHERE state = 'VIC'  -- or 'NSW'
AND ST_Contains(
    geometry,
    ST_SetSRID(ST_MakePoint(145.014316, -37.822245), 4326)  -- lng, lat
)
ORDER BY school_type, school_name;
```

**⚠️ IMPORTANT:** ST_MakePoint takes **(longitude, latitude)** - longitude FIRST!

## 🗺️ Example Addresses

### Richmond, VIC
- **Address:** 55 YARRA BVD, RICHMOND, VIC 3121
- **Coordinates:** -37.822245, 145.014316
- **State:** VIC

```sql
-- Returns: Hawthorn West PS, Richmond HS, Melbourne Girls College
ST_MakePoint(145.014316, -37.822245)
```

### Hornsby, NSW
- **Coordinates:** -33.7044, 151.0993
- **State:** NSW

```sql
ST_MakePoint(151.0993, -33.7044)
```

### Melbourne CBD, VIC
- **Coordinates:** -37.8136, 144.9631
- **State:** VIC

```sql
ST_MakePoint(144.9631, -37.8136)
```

## 📁 Available Scripts

### 1. SQL Script
**File:** [queries/get_school_catchments_by_address.sql](../database/queries/get_school_catchments_by_address.sql)

Contains:
- Basic catchment query
- Query with distance calculations
- Batch query for multiple addresses
- Nearest school finder (for addresses outside catchments)
- School count by type

### 2. Python Script
**File:** [scripts/get_catchments_for_address.py](get_catchments_for_address.py)

```bash
# Usage
python get_catchments_for_address.py --lat -37.822245 --lng 145.014316 --state VIC

# Output as JSON
python get_catchments_for_address.py --lat -37.822245 --lng 145.014316 --state VIC --json
```

## 🔍 Query Patterns

### Basic Point-in-Polygon
```sql
WHERE ST_Contains(geometry, ST_SetSRID(ST_MakePoint(lng, lat), 4326))
```

### With Distance Calculation
```sql
ROUND(
    ST_Distance(
        ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography,
        ST_SetSRID(ST_MakePoint(centroid_lng, centroid_lat), 4326)::geography
    ) / 1000, 2
) AS distance_km
```

### Nearest Catchment (if outside all zones)
```sql
ORDER BY geometry::geography <-> ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography
LIMIT 5
```

## 🏫 School Type Values

- **PRIMARY** - Primary schools (K-6)
- **SECONDARY** - Secondary schools (7-12)
- **JUNIOR_SECONDARY** - Junior secondary (VIC only)
- **SENIOR_SECONDARY** - Senior secondary (VIC only)
- **SINGLE_SEX** - Single-sex schools (VIC only)
- **FUTURE** - Future/planned schools (NSW only)

## 📊 Result Fields

### Common Fields (All States)
- `school_id` - Unique identifier
- `school_name` - School name
- `school_type` - Type (PRIMARY, SECONDARY, etc.)
- `state` - State code (NSW, VIC)
- `centroid_lat`, `centroid_lng` - School location

### Victoria-Specific Fields
- `campus_name` - Campus name (often same as school_name)
- `year_level_code` - Year level (e.g., "P6", "7", "7 to 12")
- `entity_code` - VIC department ID

### NSW-Specific Fields
- `use_id` - NSW department ID
- `add_date` - Date added to system
- `priority` - Catchment priority

## 🔧 API Endpoint (Flask)

```http
GET /api/address/schools?lat=-37.822245&lng=145.014316&state=VIC
```

**Response:**
```json
{
  "count": 8,
  "schools": [
    {
      "school_id": "1029301",
      "school_name": "Hawthorn West Primary School",
      "campus_name": "Hawthorn West Primary School",
      "school_type": "PRIMARY",
      "state": "VIC",
      "year_level_code": "P6"
    }
  ]
}
```

## 📈 Performance Tips

1. **Always filter by state first** - Much faster than spatial query alone
2. **Use spatial indexes** - Ensure `geometry` column has GIST index
3. **Limit results** - Add `LIMIT` for large result sets
4. **Project to geography** - Use `::geography` for accurate distance calculations

## 🗄️ Database Schema

```sql
gnaf.school_catchments
├── catchment_id (PK)
├── school_id
├── school_name
├── campus_name (VIC)
├── school_type
├── state
├── year_level_code (VIC)
├── entity_code (VIC)
├── use_id (NSW)
├── geometry (MultiPolygon, SRID 4326)
└── centroid_lat, centroid_lng
```

**Indexes:**
- `idx_school_catchments_geometry` (GIST on geometry)
- `idx_school_catchments_state` (BTREE on state)

## 🧪 Testing

```bash
# Test Victoria data
python PRD/webapp/test_catchment_fix.py

# Test generic query
cd PRD/scripts
python get_catchments_for_address.py --lat -37.822245 --lng 145.014316 --state VIC
```

## 📚 Related Documentation

- [VICTORIA_IMPLEMENTATION_SUMMARY.md](../PRD/MD/VICTORIA_IMPLEMENTATION_SUMMARY.md)
- [BUGFIX_VICTORIA_CATCHMENT.md](../PRD/webapp/BUGFIX_VICTORIA_CATCHMENT.md)
- [app.py](../PRD/webapp/app.py) - See `get_schools_for_address()` function

---

**Last Updated:** February 11, 2026
