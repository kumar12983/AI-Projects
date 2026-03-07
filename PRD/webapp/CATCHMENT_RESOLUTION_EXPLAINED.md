# How Catchments are Resolved in app.py

## Two Query Patterns (Same Logic, Reversed)

### 1️⃣ Address Search → Find Schools
**Endpoint:** `/api/address/schools` (Lines 557-613)
**Question:** "Which school catchments contain THIS address?"

```python
@app.route('/api/address/schools', methods=['GET'])
@login_required
def get_schools_for_address():
    # INPUT: lat, lng, state
    lat = float(request.args.get('lat'))
    lng = float(request.args.get('lng'))
    state = str(request.args.get('state', 'NSW'))
    
    # QUERY: Find all catchments that contain this point
    query = """
        SELECT DISTINCT
            school_id, school_name, campus_name,
            school_type, state, year_level_code
        FROM gnaf.school_catchments
        WHERE state = %s
        AND ST_Contains(
            geometry,                                    -- School catchment polygon
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)      -- Address point
        )
        ORDER BY school_type, school_name
    """
    cursor.execute(query, (state, lng, lat))
    schools = cursor.fetchall()
    
    return jsonify({'count': len(schools), 'schools': schools})
```

**Used By:**
- Address Lookup page (address_lookup.html)
- Frontend: `static/js/address.js` line 444

---

### 2️⃣ School Search → Find Addresses  
**Endpoint:** `/api/school/<school_id>/addresses` (Lines 1656-1874)
**Question:** "Which addresses are within THIS school's catchment?"

```python
@app.route('/api/school/<school_id>/addresses', methods=['GET'])
@login_required
def get_school_addresses(school_id):
    # INPUT: school_id, optional filters (street, suburb, etc.)
    
    # QUERY: Find all addresses within this school's catchment
    query = """
        WITH school_catchment AS (
            SELECT geometry FROM gnaf.school_catchments WHERE school_id = %s
        )
        SELECT DISTINCT ON (ad.address_detail_pid)
            ad.address_detail_pid,
            -- ... address fields ...
            agc.latitude,
            agc.longitude
        FROM gnaf.address_detail ad
        JOIN gnaf.address_default_geocode agc 
            ON ad.address_detail_pid = agc.address_detail_pid
        CROSS JOIN school_catchment sc
        WHERE ad.date_retired IS NULL
        AND agc.geom IS NOT NULL
        AND ST_Contains(
            sc.geometry,    -- School catchment polygon
            agc.geom        -- Address point
        )
        LIMIT %s OFFSET %s
    """
    
    cursor.execute(query, [school_id, ...])
    addresses = cursor.fetchall()
    
    return jsonify({'addresses': addresses, 'total_count': total_count})
```

**Used By:**
- School Catchment Search page (school_search.html)
- Frontend: `static/js/school_search.js`

---

## Core Spatial Query Pattern

Both endpoints use **the same PostGIS function**:

```sql
ST_Contains(polygon_geometry, point_geometry)
```

**How it works:**
1. **Address Search:** `ST_Contains(school_catchment.geometry, address_point)` 
   - Returns `true` if the address point is inside the catchment polygon

2. **School Search:** `ST_Contains(school_catchment.geometry, address_point)`
   - Same query! Just iterating over all addresses instead of one point

**The table:** `gnaf.school_catchments`
- Contains both NSW and VIC catchment polygons
- `geometry` column: MultiPolygon with SRID 4326 (WGS84)
- Indexed with GIST for fast spatial queries

---

## Key Differences

| Aspect | Address Search | School Search |
|--------|----------------|---------------|
| **Input** | lat, lng, state | school_id |
| **Returns** | List of schools | List of addresses |
| **Filter** | `state` first, then spatial | `school_id` first, then spatial |
| **Use Case** | "What schools serve this address?" | "What addresses in this catchment?" |
| **Performance** | Very fast (1 point lookup) | Slower (scan many addresses) |
| **Auth** | Requires login | Requires login |

---

## Performance Optimization

Both queries use **state/school_id filtering BEFORE spatial query**:

```sql
-- ✅ GOOD: Filter by state first (indexed)
WHERE state = 'VIC'
AND ST_Contains(geometry, point)

-- ❌ BAD: Spatial query on all states
WHERE ST_Contains(geometry, point)
AND state = 'VIC'
```

**Why?** 
- State index reduces candidates from 5,205 → ~3,083 (VIC) or ~2,122 (NSW)
- Then spatial index handles smaller dataset

---

## Coordinate Order ⚠️

**CRITICAL:** `ST_MakePoint(longitude, latitude)` - longitude FIRST!

```sql
-- ✅ CORRECT
ST_MakePoint(145.014316, -37.822245)  -- lng, lat

-- ❌ WRONG
ST_MakePoint(-37.822245, 145.014316)  -- lat, lng (REVERSED!)
```

This is the most common mistake in spatial queries!

---

## Related Code

### Frontend (JavaScript)
```javascript
// address.js - Line 444
const state = row.dataset.state || 'NSW';
const response = await fetch(
    `/api/address/schools?lat=${lat}&lng=${lng}&state=${state}`
);
```

### Database Schema
```sql
gnaf.school_catchments
├── catchment_id (PK)
├── school_id         -- NSW: use_id, VIC: entity_code
├── school_name
├── geometry          -- MULTIPOLYGON, SRID 4326
├── state             -- 'NSW', 'VIC'
└── centroid_lat/lng  -- School center point

-- Indexes
CREATE INDEX idx_school_catchments_geometry ON gnaf.school_catchments USING GIST(geometry);
CREATE INDEX idx_school_catchments_state ON gnaf.school_catchments(state);
```

---

## Summary

✅ **YES** - The query I provided matches exactly how app.py resolves catchments:
- Same `ST_Contains(geometry, point)` logic
- Same state filtering
- Same `gnaf.school_catchments` table
- Works for both NSW and VIC

The only difference is which direction you're querying:
- **Address → Schools** (find which catchments contain an address)
- **School → Addresses** (find which addresses are in a catchment)

Both are powered by the same spatial containment check! 🎯
