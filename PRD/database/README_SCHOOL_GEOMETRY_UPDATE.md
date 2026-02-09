# School Geometry Table Update Guide

This guide covers updating the `school_geometry` table after importing new school location data with coordinates.

## Files

### Migration Script
- **database/migrations/003_update_school_geometry_coordinates.sql**
  - Updates existing `school_geometry` table with new coordinates
  - Regenerates 5km buffer geometries
  - Shows summary statistics
  - Use this for incremental updates

### Setup Script (Updated)
- **database/setup/create_school_geometry.sql**
  - Complete table recreation from scratch
  - Now includes NULL checks for coordinates
  - Enhanced with additional indexes and comments
  - Use this for fresh installation

### Python Script
- **scripts/regenerate_school_geometry.py**
  - Automated table regeneration
  - Includes error handling and progress reporting
  - Use this for quick updates

## When to Update school_geometry

Update `school_geometry` after:
1. Importing new school location data
2. Updating coordinates in `school_profile_2025`
3. Adding new schools to the database

## Update Methods

### Method 1: Using Python Script (Recommended)

```bash
cd PRD/scripts
python regenerate_school_geometry.py
```

**Advantages:**
- Automated process
- Built-in error handling
- Shows detailed statistics
- Fast execution

### Method 2: Using Migration SQL Script

```bash
psql -U postgres -d gnaf_db -f "PRD/database/migrations/003_update_school_geometry_coordinates.sql"
```

**Advantages:**
- Updates in place (no table drop)
- Preserves existing data
- Good for incremental updates

### Method 3: Complete Table Recreation

```bash
psql -U postgres -d gnaf_db -f "PRD/database/setup/create_school_geometry.sql"
```

**Advantages:**
- Clean slate
- Ensures all indexes are optimal
- Better for major changes

## PowerShell Commands

```powershell
# Python method
cd C:\Users\Kumar\Documents\workspace\OpenAI\PRD\scripts
python regenerate_school_geometry.py

# SQL migration method
Get-Content "C:\Users\Kumar\Documents\workspace\OpenAI\PRD\database\migrations\003_update_school_geometry_coordinates.sql" | psql -U postgres -d gnaf_db

# SQL recreation method
Get-Content "C:\Users\Kumar\Documents\workspace\OpenAI\PRD\database\setup\create_school_geometry.sql" | psql -U postgres -d gnaf_db
```

## What Gets Updated

The update process affects:

1. **Coordinates**
   - `latitude` - from `school_profile_2025.latitude`
   - `longitude` - from `school_profile_2025.longitude`

2. **Geometry**
   - `geom_5km_buffer` - 5km radius around school (Web Mercator projection)
   - Calculated using ST_Buffer on updated coordinates

3. **Flags**
   - `has_geom_buffer` - Updated based on buffer existence

4. **Indexes**
   - Spatial indexes rebuilt for optimal performance
   - Full-text search vectors regenerated

## Verification

After update, verify with:

```sql
-- Check update statistics
SELECT 
    COUNT(*) as total_schools,
    COUNT(CASE WHEN latitude IS NOT NULL THEN 1 END) as with_coords,
    COUNT(CASE WHEN geom_5km_buffer IS NOT NULL THEN 1 END) as with_buffer
FROM gnaf.school_geometry;

-- Sample updated records
SELECT 
    acara_sml_id,
    school_name,
    state,
    latitude,
    longitude,
    has_geom_buffer
FROM gnaf.school_geometry
WHERE latitude IS NOT NULL
LIMIT 10;

-- Validate geometry types
SELECT 
    ST_GeometryType(geom_5km_buffer) as geom_type,
    COUNT(*) as count
FROM gnaf.school_geometry
WHERE geom_5km_buffer IS NOT NULL
GROUP BY ST_GeometryType(geom_5km_buffer);
```

## Complete Workflow

From fresh school location import to working webapp:

```bash
# 1. Import school location data
cd PRD/scripts
python import_school_location.py

# 2. Update school_profile_2025 with coordinates (if not done by import script)
# This is already done by import_school_location.py

# 3. Regenerate school_geometry table
python regenerate_school_geometry.py

# 4. Verify the update
psql -U postgres -d gnaf_db -c "SELECT COUNT(*) as total, COUNT(latitude) as with_coords FROM gnaf.school_geometry;"

# 5. Restart webapp to use new coordinates
cd ../webapp
python app.py
```

## Expected Results

After successful update:
- **~9,855** schools with coordinates (matching school_profile_2025)
- **~9,855** schools with 5km buffer geometries
- All spatial indexes rebuilt
- Web app shows accurate school markers and buffers

## Troubleshooting

**Issue: Buffer geometries are NULL**
- Check if coordinates exist in school_profile_2025
- Verify ST_Point and ST_Buffer functions work
- Ensure PostGIS extension is installed

**Issue: Coordinates not updated**
- Verify school_profile_2025 has coordinates
- Check acara_sml_id join between tables
- Run verification queries

**Issue: Spatial queries slow**
- Rebuild spatial indexes: `REINDEX INDEX idx_school_geom_5km_buffer;`
- Run VACUUM ANALYZE on school_geometry table

## Related Documentation

- [README_SCHOOL_LOCATION.md](README_SCHOOL_LOCATION.md) - School location import guide
- [create_school_geometry.sql](setup/create_school_geometry.sql) - Table creation script
- [003_update_school_geometry_coordinates.sql](migrations/003_update_school_geometry_coordinates.sql) - Migration script
