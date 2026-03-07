# Production Deployment Checklist - Victoria School Catchments

## 📋 Overview
This checklist ensures safe deployment of Victoria school catchment integration to production.

**Estimated Total Time:** 30-45 minutes  
**Required Downtime:** 5-10 minutes (can be reduced to 0 with CONCURRENT indexes)  
**Rollback Time:** < 5 minutes

---

## 🎯 Key Changes from Development Migration

### 1. **Backup Strategy**
- ❌ **Dev:** Creates backup table in same database
- ✅ **Prod:** Requires external `pg_dump` backup BEFORE migration
- **Why:** Protection against catastrophic failures, disk space issues

### 2. **Transaction & Locking**
- ❌ **Dev:** Simple BEGIN/COMMIT
- ✅ **Prod:** Optional table locking, batched updates
- **Why:** Prevent data corruption from concurrent writes

### 3. **Data Updates**
- ❌ **Dev:** Single large UPDATE statements
- ✅ **Prod:** Batched updates (1,000 rows at a time)
- **Why:** Reduces lock contention, allows concurrent queries

### 4. **Index Creation**
- ❌ **Dev:** Regular CREATE INDEX (blocks reads/writes)
- ✅ **Prod:** CREATE INDEX CONCURRENTLY (zero downtime)
- **Why:** Maintains service availability during deployment

### 5. **Pre-flight Checks**
- ❌ **Dev:** None
- ✅ **Prod:** Validates table exists, checks row counts, estimates time
- **Why:** Early failure detection

### 6. **Data Validation**
- ❌ **Dev:** Constraints added without validation
- ✅ **Prod:** Validates data before adding NOT NULL constraints
- **Why:** Prevents constraint violation failures

### 7. **Monitoring & Rollback**
- ❌ **Dev:** Basic success message
- ✅ **Prod:** Validation checks, rollback procedures, monitoring queries
- **Why:** Production safety and observability

---

## 📝 Pre-Deployment Checklist

### Week Before Deployment

- [ ] **Test on staging environment**
  - Run full migration on staging database
  - Load Victoria data (3,083 records)
  - Run smoke tests on application
  - Verify query performance
  - Document any issues

- [ ] **Review resource requirements**
  - Check current database size: `SELECT pg_size_pretty(pg_database_size('gnaf_db'));`
  - Ensure 2x free disk space (for backup)
  - Verify PostgreSQL version ≥ 12
  - Confirm PostGIS extension installed

- [ ] **Prepare rollback plan**
  - Review rollback procedure in migration script
  - Test rollback on staging
  - Assign rollback decision-maker

- [ ] **Schedule maintenance window**
  - Coordinate with stakeholders
  - Choose low-traffic time (e.g., Sunday 2-3 AM)
  - Send notifications to users
  - Prepare status page updates

### Day Before Deployment

- [ ] **Verify geometry SRID** (optional check)
  ```sql
  -- Check current SRID
  SELECT Find_SRID('gnaf', 'school_catchments', 'geometry') as current_srid;
  -- Should return 4326
  -- If returns 0 or other value, migration script will fix it automatically
  ```

- [ ] **Create external backup**
  ```bash
  # Full database backup
  pg_dump -h <host> -U postgres -d gnaf_db \
    -Fc -f gnaf_db_backup_$(date +%Y%m%d).dump
  
  # Table-specific backup
  pg_dump -h <host> -U postgres -d gnaf_db \
    -t gnaf.school_catchments \
    -f school_catchments_backup.sql
  
  # Verify backup size
  ls -lh *.dump *.sql
  ```

- [ ] **Verify backup integrity**
  ```bash
  pg_restore --list gnaf_db_backup_*.dump | head -20
  ```

- [ ] **Copy backups to safe location**
  - Upload to S3/Azure Blob Storage
  - Copy to separate server
  - Verify checksums

- [ ] **Prepare deployment scripts**
  - Copy `add_victoria_support_PRODUCTION.sql` to server
  - Copy `add_victoria_support_indexes.sql` to server
  - Copy `load_victoria_catchments.py` to server
  - Verify Python environment has required packages

- [ ] **Review monitoring setup**
  - Ensure database monitoring is active
  - Set up alerts for long-running queries
  - Prepare dashboard for migration metrics

### Deployment Day - Pre-Migration

- [ ] **Final backup** (run immediately before migration)
  ```bash
  pg_dump -h <host> -U postgres -d gnaf_db \
    -t gnaf.school_catchments \
    -f school_catchments_pre_migration_$(date +%Y%m%d_%H%M%S).sql
  ```

- [ ] **Check database health**
  ```sql
  -- Check for active connections
  SELECT count(*) FROM pg_stat_activity 
  WHERE datname = 'gnaf_db' AND state = 'active';
  
  -- Check for long-running queries
  SELECT pid, usename, query, state, 
         now() - query_start AS duration
  FROM pg_stat_activity
  WHERE datname = 'gnaf_db' 
  AND state != 'idle'
  AND query_start < now() - interval '5 minutes';
  
  -- Check table bloat
  SELECT schemaname, tablename, 
         pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
  FROM pg_tables
  WHERE schemaname = 'gnaf' AND tablename = 'school_catchments';
  ```

- [ ] **Stop or pause non-critical services** (optional)
  - Background jobs that query school_catchments
  - Scheduled reports
  - Data sync processes

---

## 🚀 Deployment Steps

### Step 1: Database Schema Migration (5-10 minutes)

```bash
# Connect to production database
psql -h <prod-host> -U postgres -d gnaf_db

# Run production migration script
\i /path/to/add_victoria_support_PRODUCTION.sql

# Monitor progress (script has built-in progress messages)
# Look for:
# - PRE-FLIGHT CHECKS
# - BACKUP CREATED
# - Data validation passed
# - MIGRATION COMPLETE
```

**Expected Output:**
```
PRE-FLIGHT CHECKS
========================================================
Table exists: YES
Current row count: 2122
Estimated migration time: 4 minutes
========================================================

✓ BACKUP CREATED: gnaf.school_catchments_backup_20260210_123456
✓ Records backed up: 2122
✓ Updated 2122 records with state=NSW
✓ Calculated centroids for 2122 records
✓ Data validation passed

========================================================
MIGRATION COMPLETE
========================================================
Total catchments: 2122
NSW catchments: 2122
VIC catchments: 0
Validation errors: 0
```

- [ ] **Verify migration success**
  ```sql
  -- Check new columns exist
  SELECT column_name FROM information_schema.columns
  WHERE table_schema = 'gnaf' AND table_name = 'school_catchments'
  AND column_name IN ('state', 'boundary_year', 'campus_name', 'entity_code');
  
  -- Check data updated
  SELECT state, COUNT(*) FROM gnaf.school_catchments GROUP BY state;
  
  -- Check views created
  SELECT viewname FROM pg_views 
  WHERE schemaname = 'gnaf' 
  AND viewname LIKE '%school_catchments%';
  ```

### Step 2: Create Indexes (CONCURRENT - 10-15 minutes, no downtime)

```bash
# In a new psql session (migration script has committed)
psql -h <prod-host> -U postgres -d gnaf_db

# Run concurrent index creation
\i /path/to/add_victoria_support_indexes.sql
```

**Monitor Progress** (in separate session):
```sql
SELECT 
    phase,
    blocks_done,
    blocks_total,
    ROUND((blocks_done::numeric / NULLIF(blocks_total, 0)) * 100, 2) as pct_complete
FROM pg_stat_progress_create_index;
```

- [ ] **Verify all indexes created**
  ```sql
  SELECT indexname FROM pg_indexes
  WHERE schemaname = 'gnaf' AND tablename = 'school_catchments'
  ORDER BY indexname;
  
  -- Expected indexes:
  -- idx_school_catchments_boundary_year
  -- idx_school_catchments_centroid
  -- idx_school_catchments_entity_code
  -- idx_school_catchments_geom
  -- idx_school_catchments_name_trgm
  -- idx_school_catchments_state
  -- idx_school_catchments_state_type
  ```

### Step 3: Load Victoria Data (5-10 minutes)

```bash
# Test with dry run first
python load_victoria_catchments.py --dry-run

# Load data with backup
python load_victoria_catchments.py --backup
```

**Expected Output:**
```
✓ Database connection established
✓ All required columns exist
✓ Backup created: 2122 records

Processing 10 files...
✓ Loaded 1255 PRIMARY records
✓ Loaded 1818 SECONDARY records
✓ Loaded 2 JUNIOR_SECONDARY records
✓ Loaded 3 SENIOR_SECONDARY records
✓ Loaded 5 SINGLE_SEX records

MIGRATION COMPLETE
Files loaded: 10
Total records loaded: 3,083
```

- [ ] **Verify Victoria data**
  ```sql
  -- Check total counts
  SELECT state, COUNT(*) FROM gnaf.school_catchments GROUP BY state;
  -- Expected: NSW: 2122, VIC: 3083
  
  -- Test spatial query (Melbourne CBD)
  SELECT school_name, school_type, year_level_code
  FROM gnaf.school_catchments
  WHERE state = 'VIC'
  AND ST_Contains(geometry, ST_SetSRID(ST_MakePoint(144.9631, -37.8136), 4326))
  ORDER BY school_type;
  ```

### Step 4: Smoke Tests (5 minutes)

- [ ] **API endpoint tests**
  ```bash
  # Test NSW school search (existing functionality)
  curl "http://api.example.com/schools/search?lat=-33.8688&lng=151.2093&state=NSW"
  
  # Test Victoria school search (new functionality)
  curl "http://api.example.com/schools/search?lat=-37.8136&lng=144.9631&state=VIC"
  
  # Test multi-state response
  curl "http://api.example.com/schools/summary"
  ```

- [ ] **Database query performance**
  ```sql
  -- Enable timing
  \timing on
  
  -- Test spatial query performance (should be < 100ms)
  EXPLAIN ANALYZE
  SELECT school_name FROM gnaf.school_catchments
  WHERE state = 'VIC'
  AND ST_Contains(geometry, ST_SetSRID(ST_MakePoint(144.9631, -37.8136), 4326));
  
  -- Test state filter performance
  EXPLAIN ANALYZE
  SELECT COUNT(*) FROM gnaf.school_catchments WHERE state = 'NSW';
  ```

- [ ] **Application functionality**
  - Load homepage - verify no errors
  - Search NSW address - verify results
  - Search VIC address - verify results
  - Check error logs for warnings

### Step 5: Monitoring & Validation (Ongoing)

- [ ] **Set up monitoring**
  ```sql
  -- Create monitoring view
  CREATE OR REPLACE VIEW monitoring.school_catchments_health AS
  SELECT 
      COUNT(*) as total_records,
      COUNT(*) FILTER (WHERE state = 'NSW') as nsw_records,
      COUNT(*) FILTER (WHERE state = 'VIC') as vic_records,
      COUNT(*) FILTER (WHERE NOT ST_IsValid(geometry)) as invalid_geoms,
      COUNT(*) FILTER (WHERE centroid_lat IS NULL) as missing_centroids,
      pg_size_pretty(pg_total_relation_size('gnaf.school_catchments')) as total_size,
      NOW() as last_checked
  FROM gnaf.school_catchments;
  
  -- Check health
  SELECT * FROM monitoring.school_catchments_health;
  ```

- [ ] **Monitor application metrics**
  - Response times for school search endpoints
  - Error rates
  - Database connection pool usage
  - Query latency

- [ ] **Check database performance**
  ```sql
  -- Slow query log
  SELECT query, mean_exec_time, calls
  FROM pg_stat_statements
  WHERE query LIKE '%school_catchments%'
  ORDER BY mean_exec_time DESC
  LIMIT 10;
  
  -- Index usage
  SELECT 
      indexrelname,
      idx_scan,
      idx_tup_read,
      idx_tup_fetch
  FROM pg_stat_user_indexes
  WHERE schemaname = 'gnaf' AND relname = 'school_catchments'
  ORDER BY idx_scan DESC;
  ```

---

## 🔄 Rollback Procedure

**If migration fails or issues detected:**

### Immediate Rollback (< 5 minutes)

```sql
-- Step 1: Find backup table
SELECT tablename, 
       obj_description(('"gnaf"."' || tablename || '"')::regclass) as comment
FROM pg_tables 
WHERE schemaname = 'gnaf' 
AND tablename LIKE 'school_catchments_backup_%'
ORDER BY tablename DESC 
LIMIT 1;

-- Step 2: Start rollback transaction
BEGIN;

-- Drop current table and views
DROP VIEW IF EXISTS gnaf.vic_school_catchments CASCADE;
DROP VIEW IF EXISTS gnaf.nsw_school_catchments CASCADE;
DROP VIEW IF EXISTS gnaf.school_catchments_summary CASCADE;
DROP TABLE IF EXISTS gnaf.school_catchments CASCADE;

-- Restore from backup (replace timestamp with actual)
ALTER TABLE gnaf.school_catchments_backup_YYYYMMDD_HHMMSS 
RENAME TO school_catchments;

-- Verify restoration
SELECT COUNT(*), state FROM gnaf.school_catchments GROUP BY state;

-- If verification passes:
COMMIT;

-- If something wrong:
ROLLBACK;
```

### From External Backup (if internal backup failed)

```bash
# Restore from pg_dump backup
pg_restore -h <host> -U postgres -d gnaf_db \
  --clean --if-exists \
  -t gnaf.school_catchments \
  gnaf_db_backup_YYYYMMDD.dump
  
# Or from SQL backup
psql -h <host> -U postgres -d gnaf_db \
  -c "DROP TABLE IF EXISTS gnaf.school_catchments CASCADE;"
  
psql -h <host> -U postgres -d gnaf_db \
  -f school_catchments_backup.sql
```

### Post-Rollback Steps

- [ ] Verify application functionality restored
- [ ] Check error logs cleared
- [ ] Notify stakeholders of rollback
- [ ] Schedule post-mortem meeting
- [ ] Document issues for retry

---

## 📊 Post-Deployment Validation

### Day 1 After Deployment

- [ ] **Verify data integrity**
  ```sql
  -- Run full validation
  SELECT * FROM monitoring.school_catchments_health;
  
  -- Check for gaps in Victoria data
  SELECT school_type, COUNT(*) 
  FROM gnaf.school_catchments 
  WHERE state = 'VIC'
  GROUP BY school_type;
  ```

- [ ] **Monitor query performance**
  - Baseline: NSW queries should maintain same performance
  - New: VIC queries should return in < 100ms
  - Track slow query log

- [ ] **Check application metrics**
  - Response times
  - Error rates
  - User feedback

### Week 1 After Deployment

- [ ] **Review backup cleanup**
  - Keep migration backup for 30 days
  - Archive external backups
  - Document backup locations

- [ ] **Performance tuning** (if needed)
  ```sql
  -- Identify missing indexes
  SELECT schemaname, tablename, attname, n_distinct, correlation
  FROM pg_stats
  WHERE schemaname = 'gnaf' AND tablename = 'school_catchments'
  AND n_distinct > 100
  ORDER BY correlation;
  
  -- Consider additional indexes based on usage patterns
  ```

- [ ] **Documentation updates**
  - Update API documentation with `state` parameter
  - Update user guides
  - Document known issues
  - Share lessons learned

---

## 🚨 Troubleshooting Common Issues

### Issue: Migration timeout

**Cause:** Large dataset, slow UPDATE queries  
**Solution:** Increase `statement_timeout`, run during low-traffic period

### Issue: Index creation fails

**Cause:** Concurrent writes, invalid geometries  
**Solution:** Use CONCURRENTLY, fix geometries first:
```sql
UPDATE gnaf.school_catchments 
SET geometry = ST_MakeValid(geometry) 
WHERE NOT ST_IsValid(geometry);
```

### Issue: Constraint violation

**Cause:** NULL values in required columns  
**Solution:** Validation checks will catch this before constraints added

### Issue: Disk space full

**Cause:** Backup table too large  
**Solution:** Use external backup, increase disk space before migration

### Issue: Query performance degraded

**Cause:** Missing indexes, outdated statistics  
**Solution:** 
```sql
ANALYZE gnaf.school_catchments;
REINDEX TABLE gnaf.school_catchments;
```

### Issue: SRID update fails during migration

**Cause:** Existing views depend on geometry column  
**Solution:** Migration script handles this automatically. If it fails:
```bash
# Run standalone SRID fix script (drops/recreates views)
python PRD/scripts/fix_geometry_srid.py
# Then re-run migration
```

### Issue: Victoria data load fails with CRS error

**Cause:** Geometry SRID is not 4326  
**Solution:** 
```sql
-- Check SRID
SELECT Find_SRID('gnaf', 'school_catchments', 'geometry');

-- If not 4326, run:
python PRD/scripts/fix_geometry_srid.py
```

---

## ✅ Success Criteria

Deployment is successful when:

- [ ] Migration completed without errors
- [ ] All 3,083 Victoria records loaded
- [ ] NSW queries maintain same performance (< 100ms)
- [ ] VIC queries perform well (< 100ms)
- [ ] No invalid geometries
- [ ] All indexes created successfully
- [ ] Application smoke tests pass
- [ ] No increase in error rates
- [ ] Backup retained for 30 days

---

## 📞 Contacts & Escalation

- **Database Team:** dba@example.com
- **Application Team:** dev@example.com  
- **On-call Engineer:** +1-XXX-XXX-XXXX
- **Rollback Decision Maker:** [Name]

---

**Document Version:** 1.0  
**Last Updated:** February 10, 2026  
**Next Review:** Before production deployment
