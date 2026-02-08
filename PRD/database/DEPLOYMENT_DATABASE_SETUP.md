# Database Deployment Guide for Australia School Search App

## Critical Database Setup Considerations

### 1. **PostGIS Extension (REQUIRED)**
The app requires PostGIS for spatial queries.

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
SELECT PostGIS_Version();  -- Verify installation
```

**Considerations:**
- PostGIS must be installed on the PostgreSQL server
- Requires PostgreSQL 12+ and PostGIS 3.0+
- On RDS/Aurora: PostGIS is available as an extension
- On Docker: Use `postgis/postgis` official image

---

### 2. **Geometry Column Population (REQUIRED)**
The `geom` column must be populated from latitude/longitude.

```sql
-- Add geom column (if not exists)
ALTER TABLE gnaf.address_default_geocode 
ADD COLUMN IF NOT EXISTS geom geometry(Point, 4326);

-- Populate geom from lat/lng
UPDATE gnaf.address_default_geocode 
SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
WHERE longitude IS NOT NULL 
  AND latitude IS NOT NULL
  AND geom IS NULL;
```

**Considerations:**
- This UPDATE takes ~2-3 minutes for 16.7M rows
- Run during off-peak hours in production
- Monitor disk space (temporary files during UPDATE)

---

### 3. **CRITICAL Spatial Index (REQUIRED for Performance)**
**Without this index, queries take 31+ seconds. With it: 0.27 seconds.**

```sql
-- Create GIST spatial index
CREATE INDEX CONCURRENTLY idx_address_default_geocode_geom 
ON gnaf.address_default_geocode USING GIST (geom);
```

**Considerations:**
- Build time: 60-90 seconds for 16.7M rows
- Index size: ~664 MB disk space
- Use `CONCURRENTLY` to avoid table locks
- **CRITICAL**: This index is essential for production performance

**File:** [`PRD/database/setup/performance_optimization_indexes.sql`](../database/setup/performance_optimization_indexes.sql)

---

### 4. **Supporting Indexes**
These indexes support joins and filters in address queries.

```sql
-- Address detail indexes
CREATE INDEX IF NOT EXISTS idx_address_detail_active 
ON gnaf.address_detail(address_detail_pid) WHERE date_retired IS NULL;

CREATE INDEX IF NOT EXISTS idx_address_street_locality_pid 
ON gnaf.address_detail(street_locality_pid);

CREATE INDEX IF NOT EXISTS idx_address_locality_pid 
ON gnaf.address_detail(locality_pid);

-- Geocode join index
CREATE INDEX IF NOT EXISTS idx_address_geocode_pid 
ON gnaf.address_default_geocode(address_detail_pid);

-- School lookup indexes
CREATE INDEX IF NOT EXISTS idx_school_geom_acara_sml_id 
ON gnaf.school_geometry(acara_sml_id);

CREATE INDEX IF NOT EXISTS idx_school_geom_5km_buffer 
ON gnaf.school_geometry USING GIST(geom_5km_buffer);
```

---

### 5. **Database Configuration Tuning**

**For Production PostgreSQL (16.7M address records):**

```conf
# Memory settings (adjust based on available RAM)
shared_buffers = 4GB                  # 25% of RAM for dedicated DB server
effective_cache_size = 12GB           # 75% of RAM
work_mem = 64MB                       # Per operation memory
maintenance_work_mem = 2GB            # For index creation/VACUUM

# Query planner
random_page_cost = 1.1                # For SSD storage
effective_io_concurrency = 200        # For SSD

# Connection settings
max_connections = 100                 # Based on expected load
```

**RDS/Aurora Considerations:**
- Use appropriate instance size (db.t3.medium minimum for dev)
- Enable enhanced monitoring
- Configure automatic backups
- Set up read replicas for high-traffic scenarios

---

### 6. **Table Statistics (REQUIRED after index creation)**

```sql
ANALYZE gnaf.address_detail;
ANALYZE gnaf.address_default_geocode;
ANALYZE gnaf.school_geometry;
```

**Considerations:**
- Run after data loading and index creation
- Set up auto-vacuum for regular updates
- Monitor table bloat

---

### 7. **Optional: Remove Redundant Index (Save 664 MB)**

If `idx_address_geocode_point` exists, it's redundant:

```sql
-- Check if redundant index exists
SELECT pg_size_pretty(pg_relation_size('gnaf.idx_address_geocode_point'));

-- Drop it to save 664 MB (only after verifying all queries use geom column)
DROP INDEX CONCURRENTLY IF EXISTS gnaf.idx_address_geocode_point;
```

---

### 8. **Data Volume Considerations**

**Current Database Size:**
- Address records: ~16.7 million
- School records: ~9,500
- Spatial indexes: ~1.3 GB
- Total database: ~15-20 GB

**Deployment Requirements:**
- Minimum disk: 50 GB (with growth buffer)
- Recommended: 100 GB for logs, backups, temp files
- Backup strategy: Daily full + WAL archiving

---

### 9. **Connection Pooling**

For production, use connection pooling to handle concurrent requests:

**Option 1: PgBouncer (Recommended)**
```conf
[databases]
gnaf_db = host=localhost port=5432 dbname=gnaf_db

[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
```

**Option 2: SQLAlchemy Pool (in Flask app)**
```python
from sqlalchemy import create_engine
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)
```

---

### 10. **Security Considerations**

```sql
-- Create read-only user for app
CREATE USER app_readonly WITH PASSWORD 'strong_password';
GRANT CONNECT ON DATABASE gnaf_db TO app_readonly;
GRANT USAGE ON SCHEMA gnaf TO app_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA gnaf TO app_readonly;

-- Restrict modifications
REVOKE INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA gnaf FROM app_readonly;
```

**Environment Variables:**
```bash
DB_HOST=your-db-host
DB_NAME=gnaf_db
DB_USER=app_readonly
DB_PASSWORD=your-secure-password
DB_PORT=5432
```

---

## Deployment Checklist

### Pre-Deployment
- [ ] PostgreSQL 12+ installed
- [ ] PostGIS extension installed
- [ ] Database created (`gnaf_db`)
- [ ] Schema created (`gnaf`)
- [ ] GNAF data loaded into tables

### Critical Setup (Run these scripts)
- [ ] `gnaf_geospatial_setup.sql` - Create geom columns
- [ ] **`performance_optimization_indexes.sql`** - Create spatial indexes
- [ ] Verify index creation with test queries
- [ ] Run ANALYZE on all tables

### Performance Verification
- [ ] Test address query: < 0.5 seconds for 100 results
- [ ] Check query plan uses spatial index
- [ ] Monitor first 100 queries for slow queries

### Production Configuration
- [ ] Configure PostgreSQL memory settings
- [ ] Set up connection pooling
- [ ] Configure backups
- [ ] Set up monitoring (slow query log)
- [ ] Create read-only database user
- [ ] Secure database credentials

### Post-Deployment
- [ ] Monitor query performance
- [ ] Set up auto-vacuum schedule
- [ ] Configure log rotation
- [ ] Plan for index maintenance (REINDEX if bloated)

---

## Quick Start for New Deployment

```bash
# 1. Create database
createdb gnaf_db

# 2. Enable PostGIS
psql gnaf_db -c "CREATE EXTENSION postgis;"

# 3. Load GNAF schema and data (use existing scripts)
psql gnaf_db < PRD/database/setup/setup_gnaf_database.sql

# 4. Create geom columns and populate
psql gnaf_db < PRD/database/setup/PostGIS/gnaf_geospatial_setup.sql

# 5. Create CRITICAL performance indexes
psql gnaf_db < PRD/database/setup/performance_optimization_indexes.sql

# 6. Verify performance
psql gnaf_db -c "SELECT COUNT(*) FROM gnaf.address_default_geocode WHERE geom IS NOT NULL;"
```

---

## Performance Benchmarks

| Query Type | Without Index | With Index | Improvement |
|------------|---------------|------------|-------------|
| Get 100 addresses within 5km | 31 seconds | 0.27 seconds | **114x faster** |
| Count addresses in zone | 15 seconds | 6 seconds | 2.5x faster |
| School autocomplete | 2 seconds | 0.1 seconds | 20x faster |

---

## Troubleshooting

### Query is slow (> 2 seconds)
```sql
-- Check if spatial index exists
SELECT indexname FROM pg_indexes 
WHERE tablename = 'address_default_geocode' 
AND indexname = 'idx_address_default_geocode_geom';

-- Rebuild if needed
REINDEX INDEX CONCURRENTLY gnaf.idx_address_default_geocode_geom;
```

### Out of memory during index creation
```sql
-- Increase maintenance_work_mem temporarily
SET maintenance_work_mem = '2GB';
CREATE INDEX ...
```

### Table bloat
```sql
-- Check bloat
SELECT schemaname, tablename, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables WHERE schemaname = 'gnaf' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Vacuum if needed
VACUUM ANALYZE gnaf.address_default_geocode;
```

---

## Summary of Critical SQL Files

1. **`performance_optimization_indexes.sql`** ⭐ **CRITICAL**
   - Creates the essential spatial index
   - Must run for production deployment
   - Provides 114x performance improvement

2. **`gnaf_geospatial_setup.sql`** (Existing)
   - Creates geom columns
   - Populates geometry data

3. **`create_indexes.sql`** (Existing)
   - Creates supporting B-tree indexes

4. **`create_school_geometry.sql`** (Existing)
   - School spatial data and indexes

All scripts are in: `PRD/database/setup/`
