# PostgreSQL GNAF Database Setup Guide

This guide will help you set up a PostgreSQL database for your GNAF (Geocoded National Address File) data.

## Prerequisites

- PostgreSQL installed (version 12 or higher recommended)
- Python 3.8 or higher
- psycopg2 Python package

## Step 1: Install Dependencies

```powershell
# Install psycopg2 for PostgreSQL connectivity
pip install psycopg2-binary
```

## Step 2: Create the Database

You have two options:

### Option A: Using psql Command Line

```powershell
# Connect to PostgreSQL as superuser
psql -U postgres

# In psql, run:
CREATE DATABASE gnaf_db;
\c gnaf_db
\i setup_gnaf_database.sql
\q
```

### Option B: Using pgAdmin

1. Open pgAdmin
2. Right-click on "Databases" → "Create" → "Database"
3. Name it `gnaf_db`
4. Open the Query Tool for the new database
5. Open and execute `setup_gnaf_database.sql`

## Step 3: Verify Database Setup

Connect to your database and verify the schema:

```sql
-- List all tables in the gnaf schema
\dt gnaf.*

-- Check states table
SELECT * FROM gnaf.states;
```

Expected tables:
- `gnaf.localities` - Main locality/suburb data
- `gnaf.postcodes` - Postcode lookup
- `gnaf.suburb_postcode` - Suburb-postcode mapping
- `gnaf.addresses` - Full GNAF address details
- `gnaf.streets` - Street information
- `gnaf.states` - Australian states/territories

## Step 4: Load Your CSV Data

Run the Python loader script:

```powershell
python load_gnaf_data.py
```

The script will:
1. Connect to the PostgreSQL database
2. Load data from your CSV files (`nsw_suburbs_postcodes.csv`, etc.)
3. Create locality records
4. Display statistics

### Manual Data Loading (Alternative)

You can also load data manually using psql:

```sql
-- Load suburb-postcode data
COPY gnaf.suburb_postcode(suburb, postcode, state)
FROM 'C:/Users/kumar/Documents/workspace/nsw_suburbs_postcodes.csv'
DELIMITER ','
CSV HEADER;
```

## Database Schema Overview

### Core Tables

#### 1. `gnaf.localities`
Main table for suburbs/localities
- `locality_id` - Primary key
- `locality_name` - Suburb/locality name
- `primary_postcode` - Main postcode
- `state_abbreviation` - State (NSW, VIC, etc.)

#### 2. `gnaf.suburb_postcode`
Many-to-many mapping between suburbs and postcodes
- `suburb` - Suburb name
- `postcode` - 4-digit postcode
- `state` - State abbreviation
- `is_primary` - Whether this is the primary postcode

#### 3. `gnaf.addresses`
Full GNAF address details (for when you load complete GNAF data)
- Address components (street, number, flat, etc.)
- Geocoding information (lat/long)
- Links to localities

#### 4. `gnaf.states`
Australian states and territories (pre-populated)

### Useful Views

#### `gnaf.v_nsw_suburb_postcode`
All NSW suburbs with their postcodes

```sql
SELECT * FROM gnaf.v_nsw_suburb_postcode;
```

#### `gnaf.v_suburb_summary`
Summary statistics by state

```sql
SELECT * FROM gnaf.v_suburb_summary;
```

## Common Queries

### Find all suburbs for a postcode

```sql
-- Using the function
SELECT * FROM gnaf.get_suburbs_by_postcode('2000');

-- Or direct query
SELECT suburb, state 
FROM gnaf.suburb_postcode 
WHERE postcode = '2000'
ORDER BY suburb;
```

### Find all postcodes for a suburb

```sql
-- Using the function
SELECT * FROM gnaf.get_postcodes_by_suburb('Sydney');

-- Or direct query
SELECT postcode, state 
FROM gnaf.suburb_postcode 
WHERE UPPER(suburb) = 'SYDNEY'
ORDER BY postcode;
```

### Search suburbs by partial name

```sql
SELECT DISTINCT suburb, postcode, state
FROM gnaf.suburb_postcode
WHERE suburb ILIKE '%BEACH%'
ORDER BY suburb;
```

### Count suburbs per postcode

```sql
SELECT 
    postcode,
    COUNT(DISTINCT suburb) as suburb_count,
    STRING_AGG(suburb, ', ' ORDER BY suburb) as suburbs
FROM gnaf.suburb_postcode
WHERE state = 'NSW'
GROUP BY postcode
HAVING COUNT(DISTINCT suburb) > 1
ORDER BY suburb_count DESC;
```

## Loading Full GNAF Data

If you have the complete GNAF dataset (PSV files), you can load them using Python:

```python
import csv
import psycopg2

conn = psycopg2.connect(database='gnaf_db', user='postgres', password='your_password')
cursor = conn.cursor()

# Load LOCALITY.psv
with open('path/to/LOCALITY.psv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter='|')
    for row in reader:
        cursor.execute("""
            INSERT INTO gnaf.localities 
            (locality_pid, locality_name, primary_postcode, state_abbreviation)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (locality_pid) DO NOTHING
        """, (
            row.get('LOCALITY_PID'),
            row.get('LOCALITY_NAME'),
            row.get('PRIMARY_POSTCODE'),
            row.get('STATE_ABBREVIATION')
        ))

conn.commit()
cursor.close()
conn.close()
```

## Backup and Restore

### Backup

```powershell
# Backup entire database
pg_dump -U postgres -d gnaf_db -f gnaf_db_backup.sql

# Backup only data
pg_dump -U postgres -d gnaf_db --data-only -f gnaf_db_data.sql

# Backup only schema
pg_dump -U postgres -d gnaf_db --schema-only -f gnaf_db_schema.sql
```

### Restore

```powershell
# Restore from backup
psql -U postgres -d gnaf_db -f gnaf_db_backup.sql
```

## Maintenance

### Update Statistics

```sql
ANALYZE gnaf.suburb_postcode;
ANALYZE gnaf.localities;
```

### Vacuum

```sql
VACUUM ANALYZE gnaf.suburb_postcode;
```

### Reindex

```sql
REINDEX TABLE gnaf.suburb_postcode;
```

## Security Considerations

1. **Create dedicated users:**

```sql
-- Create read-only user
CREATE USER gnaf_reader WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE gnaf_db TO gnaf_reader;
GRANT USAGE ON SCHEMA gnaf TO gnaf_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA gnaf TO gnaf_reader;

-- Create read-write user
CREATE USER gnaf_writer WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE gnaf_db TO gnaf_writer;
GRANT USAGE ON SCHEMA gnaf TO gnaf_writer;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA gnaf TO gnaf_writer;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA gnaf TO gnaf_writer;
```

2. **Use environment variables for credentials:**

```powershell
# Set environment variables
$env:PGUSER = "postgres"
$env:PGPASSWORD = "your_password"
$env:PGHOST = "localhost"
$env:PGDATABASE = "gnaf_db"
```

## Troubleshooting

### Connection Issues

If you can't connect to PostgreSQL:

1. Check PostgreSQL is running:
   ```powershell
   Get-Service postgresql*
   ```

2. Verify pg_hba.conf allows local connections
3. Check port 5432 is not blocked by firewall

### Permission Errors

```sql
-- Grant necessary permissions
GRANT ALL PRIVILEGES ON SCHEMA gnaf TO your_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA gnaf TO your_user;
```

### Data Loading Issues

- Ensure CSV files are UTF-8 encoded
- Check for invalid postcode formats (must be 4 digits)
- Verify no header row issues

## Next Steps

1. Load your CSV data using `load_gnaf_data.py`
2. Download full GNAF dataset for complete address data
3. Create additional indexes for your specific query patterns
4. Set up regular backups
5. Consider partitioning large tables by state for better performance

## Resources

- [GNAF on data.gov.au](https://data.gov.au/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [PostGIS for Spatial Queries](https://postgis.net/) (optional, for advanced geocoding)

## Files Included

- `setup_gnaf_database.sql` - Database schema creation script
- `load_gnaf_data.py` - Python script to load CSV data
- `README_GNAF_DATABASE.md` - This file

---

**Created:** January 2026  
**Database:** PostgreSQL 12+  
**Schema:** gnaf  
**Purpose:** GNAF address and locality data management
