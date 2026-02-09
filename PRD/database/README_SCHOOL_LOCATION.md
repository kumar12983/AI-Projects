# School Location Database Scripts

This folder contains SQL scripts for managing school location data with geographic coordinates.

## Files

### Setup Scripts (`database/setup/`)

- **create_school_location_table.sql**
  - Creates the `gnaf.school_location` table with all 31 columns from the School Location 2025 dataset
  - Includes indexes for performance optimization
  - Contains comprehensive documentation via SQL comments

### Migration Scripts (`database/migrations/`)

- **002_add_coordinates_to_school_profile.sql**
  - Adds `latitude` and `longitude` columns to `gnaf.school_profile_2025`
  - Updates coordinates by joining with `gnaf.school_location` on `acara_sml_id`
  - Creates spatial index on coordinates
  - Displays summary statistics after update

### Query Scripts (`database/queries/`)

- **query_school_locations.sql**
  - Collection of 15+ example queries for working with school location data
  - Includes basic queries, geographic searches, joins, and data quality checks
  - Demonstrates spatial distance calculations using Haversine formula

## Usage

### Initial Setup

1. **Create the school_location table:**
   ```sql
   \i database/setup/create_school_location_table.sql
   ```

2. **Import data from Excel:**
   ```bash
   cd PRD/scripts
   python import_school_location.py
   ```

3. **Add coordinates to school_profile_2025:**
   ```sql
   \i database/migrations/002_add_coordinates_to_school_profile.sql
   ```

### Alternative: Using psql command line

```bash
# Create table
psql -U postgres -d gnaf_db -f "PRD/database/setup/create_school_location_table.sql"

# Run migration (after importing data)
psql -U postgres -d gnaf_db -f "PRD/database/migrations/002_add_coordinates_to_school_profile.sql"
```

### Using PowerShell

```powershell
# Create table
Get-Content "PRD\database\setup\create_school_location_table.sql" | psql -U postgres -d gnaf_db

# Run migration
Get-Content "PRD\database\migrations\002_add_coordinates_to_school_profile.sql" | psql -U postgres -d gnaf_db
```

## Table Structure

### gnaf.school_location

| Category | Columns |
|----------|---------|
| **Identifiers** | calendar_year, acara_sml_id (PK), location_age_id, school_age_id, rolled_school_id |
| **School Info** | school_name, suburb, state, postcode, school_sector, school_type, special_school, campus_type |
| **Coordinates** | latitude, longitude |
| **ABS Areas** | abs_remoteness_area, abs_remoteness_area_name, meshblock, statistical_area_1-4 (with names) |
| **Government Areas** | local_government_area, state_electoral_division, commonwealth_electoral_division (all with names) |
| **Metadata** | created_at, updated_at |

**Total Columns:** 33 (including metadata)

### Indexes Created

- `idx_school_location_acara_sml_id` - Primary key index
- `idx_school_location_coords` - Spatial index on (latitude, longitude)
- `idx_school_location_state` - State lookup
- `idx_school_location_suburb` - Suburb lookup
- `idx_school_location_postcode` - Postcode lookup
- `idx_school_profile_2025_coords` - Added to school_profile_2025 table

## Data Import Results

From the initial import (2026-02-09):
- **11,039** schools imported to `school_location`
- **9,855** schools updated in `school_profile_2025` with coordinates
- **100%** of location records have coordinates
- **1,184** schools in location table but not in profile (expected - different data sources)

## Example Queries

See [query_school_locations.sql](queries/query_school_locations.sql) for comprehensive examples including:

- Geographic searches within bounding boxes
- Distance calculations from a point
- Statistical analysis by remoteness area
- Joins between school_location and school_profile_2025
- Data quality validation queries

## Related Scripts

### Python Scripts (PRD/scripts/)

- **import_school_location.py** - Automated import tool with user prompts
- **verify_school_location.py** - Data verification and validation
- **examine_excel.py** - Excel file structure explorer

## Notes

- The `latitude` and `longitude` columns use `NUMERIC(10, 7)` precision for accurate coordinate storage
- The migration script is idempotent - safe to run multiple times
- All geographic queries use decimal degrees format
- Distance calculations use the Haversine formula (Earth radius = 6371 km)

## Dependencies

- PostgreSQL 12+ (with PostGIS recommended for advanced spatial queries)
- Python 3.x with pandas, psycopg2, openpyxl (for Python import script)
- Excel file: `School Location 2025.xlsx`

## Maintenance

To re-import or update data:
1. Run the Python import script again (it uses UPSERT logic)
2. Or manually run the migration script to update coordinates

The migration script only updates rows where coordinates are NULL, preventing accidental overwrites.
