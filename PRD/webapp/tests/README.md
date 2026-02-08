# Test and Analysis Scripts

This folder contains testing and analysis scripts for database performance optimization and application testing.

## Application Testing Scripts

### `test_app.py`
Unit tests for the Flask application.

### `test_address_results.py`
Tests address search results and formatting.

### `test_school_autocomplete.py`
Tests school autocomplete functionality.

### `verify_queries.py`
Verifies SQL queries are correctly formed.

---

## Performance Testing Scripts

### `test_final_query.py` ⭐ **Recommended**
Tests the final optimized query with the GIST spatial index.

**Usage:**
```bash
cd PRD/webapp
python tests/test_final_query.py
```

**Output:**
- Query execution time
- Performance comparison (before/after optimization)
- Sample results

**Expected Performance:** < 0.5 seconds


### `test_optimized_query.py`
Tests the intermediate optimized query (before creating the spatial index).

**Usage:**
```bash
python tests/test_optimized_query.py
```

**Expected Performance:** ~6-7 seconds (still faster than original 31s)


### `debug_performance.py`
Comprehensive performance debugging script that tests multiple query variations.

**Usage:**
```bash
python tests/debug_performance.py
```

**Tests:**
1. Original query with geography casting
2. Query with geom column (if exists)
3. Query with pre-computed buffer

---

## Database Analysis Scripts

### `query_indexes.py`
Lists all indexes on `gnaf.address_default_geocode` table.

**Usage:**
```bash
python tests/query_indexes.py
```

**Output:**
- Index names and definitions
- Index sizes
- Index types (GIST, BTREE)


### `analyze_duplicate_indexes.py`
Analyzes which spatial index is being used and identifies redundant indexes.

**Usage:**
```bash
python tests/analyze_duplicate_indexes.py
```

**Output:**
- Active index identification
- Redundancy analysis
- Disk space savings recommendations


### `check_geom.py`
Verifies the existence and population of the `geom` column.

**Usage:**
```bash
python tests/check_geom.py
```

**Output:**
- Whether geom column exists
- Number of non-null geom values
- List of spatial indexes

---

## Setup/Maintenance Scripts (in parent directory)

These are kept in the main webapp directory as they're used for setup:

- **`create_spatial_index.py`** - Creates the critical GIST spatial index
- **`drop_redundant_index.py`** - Removes redundant indexes to save disk space

---

## Performance Benchmarks

| Script | Query Type | Expected Time |
|--------|------------|---------------|
| test_final_query.py | With GIST index | **< 0.5s** ✓ |
| test_optimized_query.py | Optimized without index | ~6-7s |
| debug_performance.py | Original query | ~31s |

---

## Dependencies

All scripts require:
- `psycopg2`
- `python-dotenv`
- `.env` file with database credentials

---

## Quick Test

To verify database performance is optimal:

```bash
cd PRD/webapp
python tests/test_final_query.py
```

Look for: **"✓ EXCELLENT! Query is now under 2 seconds!"**

If query is slow (> 2 seconds), run:
```bash
python tests/analyze_duplicate_indexes.py
```

This will identify missing indexes or query plan issues.
