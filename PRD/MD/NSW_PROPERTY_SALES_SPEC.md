# NSW Property Sales & Valuation — Build Specification

> **Purpose:** Complete specification for the NSW property sales/valuation pipeline and its UX/UI integration into the webapp. Reflects the current production state as of 2026-05-22.

---

## 1. Overview

The system surfaces the most recent sale price for every address displayed across three webapp pages. There are **two data sources**, each serving a different purpose:

| Source | Script | Purpose |
|---|---|---|
| NSW VG Bulk PSI (zip files) | `load_vg_bulk_sales.py` | Full sale history 1990–present → `nsw_vg_sales_history` + `gnaf_vg_sale_link` bridge |
| NSW Spatial Services ArcGIS MapServer | `load_nsw_property_data.py` | Current-snapshot land valuations → `nsw_property_valuation` |

**The `last_sold_price` / `last_sale_date` shown in the UI comes exclusively from `gnaf_vg_sale_link`** (the VG bulk pipeline). The ArcGIS sales table (`nsw_property_sales`) is retained for reference but is no longer used for price display — it has been superseded.

**Currently loaded postcodes:** 2076, 2077, 2119, 2120, 2125

**Row counts (as of 2026-05-22):**
| Table | Rows | Notes |
|---|---|---|
| `public.nsw_vg_sales_history` | 76,348 | VG bulk records 1915–2026-04-13 |
| `public.gnaf_vg_sale_link` | 38,679 | One row per matched GNAF address |
| `public.nsw_property_sales` | 20,116 | ArcGIS snapshot (not used for UI price) |
| `public.nsw_property_valuation` | 30,446 | Current land valuations |
| `public.nsw_property_valuation_history` | 151,785 | Unpivoted valuation history |

---

## 2. Database Schema

**Database:** `gnaf_db` on `localhost:5432`  
**User:** `postgres`  
**Credentials:** `PRD/.env` (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`)

### 2.1 `public.nsw_vg_sales_history` ← **Primary sale source**

Insert-only table storing all VG bulk PSI records. Populated by `load_vg_bulk_sales.py`.

```sql
CREATE TABLE public.nsw_vg_sales_history (
    id                 SERIAL PRIMARY KEY,
    district_code      TEXT,
    property_id        TEXT,
    sale_counter       TEXT,
    unit_number        TEXT,
    house_number       TEXT,          -- e.g. '53', '53A', '11 B', '53-57'
    street_name        TEXT,          -- e.g. 'KIRKHAM STREET' (includes street type)
    locality           TEXT,          -- e.g. 'BEECROFT'
    postcode           INTEGER,
    contract_date      DATE,
    settlement_date    DATE,
    purchase_price     BIGINT,        -- whole dollars
    area               DOUBLE PRECISION,
    area_type          TEXT,          -- 'M' = sqm, 'H' = hectares
    zoning             TEXT,
    nature_of_property TEXT,
    primary_purpose    TEXT,
    strata_lot_number  TEXT,
    dealing_number     TEXT,          -- Land Registry dealing (current format only)
    legal_description  TEXT,
    data_format        TEXT,          -- 'current' | 'archived'
    loaded_at          TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_nsw_vg_sales UNIQUE (district_code, property_id, contract_date, purchase_price)
);

CREATE INDEX nsw_vg_sales_postcode_idx  ON public.nsw_vg_sales_history (postcode);
CREATE INDEX nsw_vg_sales_date_idx      ON public.nsw_vg_sales_history (contract_date DESC);
CREATE INDEX nsw_vg_sales_address_idx   ON public.nsw_vg_sales_history (postcode, house_number, street_name);
CREATE INDEX nsw_vg_sales_propid_idx    ON public.nsw_vg_sales_history (district_code, property_id);
```

**VG `house_number` format patterns:**
| Format | Example | Notes |
|---|---|---|
| Plain number | `53` | Standard |
| Alpha suffix (no space) | `53A` | Joined |
| Alpha suffix (with space) | `11 B` | Space before letter — handled by regex |
| Range | `53-57` | Address range |

**VG `street_name` format:** Always includes the street type — e.g., `'KIRKHAM STREET'`, `'ADA AVENUE'`, `'THE CRESCENT'`. GNAF `street_name` stores only the base name (`'KIRKHAM'`, `'ADA'`) with `street_type_code` separate — except for compound names like `'THE CRESCENT'` where `street_type_code` is NULL and the full name is in `street_name`.

### 2.2 `public.gnaf_vg_sale_link` ← **Bridge table used by app.py**

Pre-computed mapping from GNAF `address_detail_pid` to the most recent matching VG sale. Rebuilt after every `load_vg_bulk_sales.py` run.

```sql
CREATE TABLE public.gnaf_vg_sale_link (
    address_detail_pid  TEXT PRIMARY KEY,
    purchase_price      BIGINT,
    contract_date       DATE,
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);
```

**How `app.py` uses it — the join is a simple lookup (no spatial geometry required):**
```sql
LEFT JOIN public.gnaf_vg_sale_link gvl ON gvl.address_detail_pid = ad.address_detail_pid

-- SELECT columns:
TO_CHAR(gvl.purchase_price, 'FM$999,999,999') AS last_sold_price,
TO_CHAR(gvl.contract_date,  'FMDD Month YYYY') AS last_sale_date
```

This replaces the previous `LEFT JOIN LATERAL (SELECT ... FROM nsw_property_sales WHERE ST_DWithin...)` pattern. All three Flask endpoints now use the bridge join.

### 2.3 `public.nsw_property_sales` ← ArcGIS snapshot (retained, not used for price display)

```sql
CREATE TABLE public.nsw_property_sales (
    source_objectid  INTEGER,
    propid           BIGINT,
    dealing          TEXT,
    house_no         TEXT,            -- e.g. '53', '9/53', '53-57', '4/53A'
    street           TEXT,            -- e.g. 'BURDETT STREET'
    suburb           TEXT,
    postcode         INTEGER,
    bp_address       TEXT,
    price            BIGINT,
    sale_date        TEXT,            -- e.g. '7 November 2024'
    area             DOUBLE PRECISION,
    strata           INTEGER,
    last_sale        TEXT,            -- Always 'Y' (API only exposes most recent per property)
    deal_props       INTEGER,
    urbanity         TEXT,
    kmlid            TEXT,
    validity_d       TEXT,
    geometry         geometry(Point, 4326),
    loaded_at        TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_nsw_property_sales UNIQUE (propid, dealing)
);
```

> **Note:** The ArcGIS endpoint only publishes the single most recent sale per property. It has no historical data and no `last_sale='N'` records. This table is no longer the source of `last_sold_price` in the UI.

### 2.4 `public.nsw_property_valuation`

One row per property — current land valuation snapshot. Rolling 5-year window (`val1`–`val5`). Updated (upserted) on every ArcGIS load run.

```sql
CREATE TABLE public.nsw_property_valuation (
    source_objectid  INTEGER,
    propid           BIGINT,
    address          TEXT,            -- e.g. '137 AIKEN RD, WEST PENNANT HILLS NSW 2125'
    zone_desc        TEXT,
    prop_area        TEXT,
    basis_desc       TEXT,
    lga_cbd          TEXT,            -- Base date string e.g. '1 July 2025' (NOT an LGA name)
    lga_pbd          TEXT,
    lga_cbdr         TEXT,
    urbanity         TEXT,
    val1_bd          TEXT,            -- Base date for most recent valuation
    val1_lv          TEXT,            -- Land value, e.g. ' $1,270,000' (leading space)
    val1_con         TEXT,
    val2_bd          TEXT,  val2_lv  TEXT,  val2_con TEXT,
    val3_bd          TEXT,  val3_lv  TEXT,  val3_con TEXT,
    val4_bd          TEXT,  val4_lv  TEXT,  val4_con TEXT,
    val5_bd          TEXT,  val5_lv  TEXT,  val5_con TEXT,
    conapplies       INTEGER,
    pbdapplies       INTEGER,
    underspflag      INTEGER,
    kmlid            TEXT,
    validity_d       TEXT,
    geometry         geometry(Point, 4326),
    loaded_at        TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_nsw_property_valuation UNIQUE (propid)
);
```

**Note:** `val1_lv`–`val5_lv` have a leading space and `$` sign — use `TRIM()` before display.

### 2.5 `public.nsw_property_valuation_history`

Normalized, insert-only. ETL unpivots `val1_bd..val5_bd` into individual rows.

```sql
CREATE TABLE public.nsw_property_valuation_history (
    propid      BIGINT  NOT NULL,
    base_date   TEXT    NOT NULL,   -- e.g. '1 July 2025'
    land_value  TEXT,               -- e.g. ' $1,270,000'
    concession  TEXT,
    loaded_at   TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT pk_nsw_valuation_history PRIMARY KEY (propid, base_date)
);
```

### 2.6 `public.nsw_property_load_log`

ETL audit log. Shared by both loaders.

```sql
CREATE TABLE public.nsw_property_load_log (
    id             SERIAL PRIMARY KEY,
    layer_name     TEXT,
    where_clause   TEXT,
    max_oid_loaded INTEGER,
    rows_inserted  INTEGER,
    rows_updated   INTEGER,
    rows_skipped   INTEGER,
    run_at         TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 3. VG Bulk Sales ETL — `load_vg_bulk_sales.py`

**File:** `PRD/scripts/load_vg_bulk_sales.py`

### 3.1 Data Sources

```
Yearly:  https://www.valuergeneral.nsw.gov.au/__psi/yearly/YYYY.zip   (1990 – prev year)
Weekly:  https://www.valuergeneral.nsw.gov.au/__psi/weekly/YYYYMMDD.zip (current year)
```

Data directory: `PRD/scripts/vg_data/` — 53 zip files downloaded as of 2026-05-22 (36 yearly + 17 weekly).

Each zip contains `.dat` files (semicolon-delimited). Record `B` = sale record. Two sub-formats:

| Format | Identifier | Price field | Date field | House number |
|---|---|---|---|---|
| Current (2001+) | `parts[2]` is numeric | `parts[15]` | `parts[13]` (`CCYYMMDD`) | `parts[7]` |
| Archived (1990–2001) | `parts[2]` is alpha | `parts[11]` | `parts[10]` (`DD/MM/YYYY`) | `parts[6]` |

Heuristic: `parts[2].isalpha()` → archived format.

### 3.2 CLI Usage

```powershell
# Full run: download all files + load + rebuild bridge (default postcodes)
python load_vg_bulk_sales.py

# Specify postcodes
python load_vg_bulk_sales.py --postcodes 2077 2119 2148

# Use already-downloaded files, skip download
python load_vg_bulk_sales.py --skip-download

# Skip current-year weekly files
python load_vg_bulk_sales.py --skip-weekly

# Load only data from 2000 onward
python load_vg_bulk_sales.py --start-year 2000

# Drop + recreate tables before loading
python load_vg_bulk_sales.py --truncate

# Parse + print sample, no DB writes
python load_vg_bulk_sales.py --dry-run

# Skip bridge rebuild after load
python load_vg_bulk_sales.py --no-bridge

# Incremental update with new weekly files already in vg_data/
python load_vg_bulk_sales.py --skip-download
```

### 3.3 Upsert Behaviour

| Table | Conflict Key | On Conflict |
|---|---|---|
| `nsw_vg_sales_history` | `(district_code, property_id, contract_date, purchase_price)` | `DO NOTHING` |
| `gnaf_vg_sale_link` | `address_detail_pid` | `DO UPDATE` only if `EXCLUDED.contract_date` is more recent |

---

## 4. Bridge Table Rebuild — GNAF Matching Logic

After every load run `rebuild_bridge_table(conn, postcodes)` executes a single `INSERT ... SELECT DISTINCT ON` that joins `nsw_vg_sales_history` to `gnaf.address_detail` and writes the most recent matched sale into `gnaf_vg_sale_link`.

### 4.1 Join Conditions (all must match)

| # | Condition | Notes |
|---|---|---|
| 1 | `ad.postcode = vg.postcode::text` | VG postcode is INTEGER; GNAF is TEXT — explicit cast required |
| 2 | `COALESCE(NULLIF(TRIM(vg.unit_number), ''), '') = COALESCE(ad.flat_number::text, '')` | Blank/NULL VG unit matches NULL GNAF flat_number (non-unit address) |
| 3 | `regexp_replace(vg.house_number, '[^0-9].*', '') = ad.number_first::text` | Strips suffix/range: `'53A'→'53'`, `'53-57'→'53'` |
| 4 | Suffix regex (see below) | Alpha suffix match: `'53A'→'A'`, `'53'→''` |
| 5 | `(vg.street_name ILIKE sl.street_name \|\| ' %' OR vg.street_name ILIKE sl.street_name)` | Prefix match for `'KIRKHAM STREET'↔'KIRKHAM'`; exact match for `'THE CRESCENT'↔'THE CRESCENT'` |
| 6 | `loc.locality_name ILIKE vg.locality` | Case-insensitive suburb match |
| 7 | `ad.postcode = ANY(postcodes_text)` | **Performance filter** — prevents 7M-row GNAF scan; forces postcode index use |
| 8 | `date_retired IS NULL` on `address_detail`, `street_locality`, `locality` | Active GNAF records only |

**Suffix extraction (condition 4) — handles VG's space-before-letter format:**
```sql
AND UPPER(COALESCE(NULLIF(
    regexp_replace(
        regexp_replace(COALESCE(vg.house_number, ''), '\s+', ''),  -- strip spaces: '11 B'→'11B'
        '^[0-9]+([A-Za-z]?).*', '\1'                               -- extract suffix: '11B'→'B'
    ), ''), ''))
= UPPER(COALESCE(ad.number_first_suffix, ''))
```

**Why two regex steps are needed:**  
VG stores `'11 B'` (space between number and letter). A single regex on the raw value captures `''` (the `[A-Za-z]?` matches empty at the space position, `.*` consumes ` B`). Stripping spaces first ensures `'11 B'→'11B'→suffix 'B'` — matching GNAF's `number_first_suffix='B'`.

**Why the exact street name match (`OR ... ILIKE sl.street_name`) is needed:**  
Streets like `'THE CRESCENT'` have `street_type_code = NULL` in GNAF — the word "CRESCENT" is part of the name itself. The trailing-space prefix `ILIKE sl.street_name || ' %'` evaluates to `'THE CRESCENT' ILIKE 'THE CRESCENT %'` which fails. The exact match branch handles these correctly.

### 4.2 DISTINCT ON + ORDER BY

```sql
SELECT DISTINCT ON (ad.address_detail_pid)
    ad.address_detail_pid, vg.purchase_price, vg.contract_date
FROM ...
ORDER BY ad.address_detail_pid, vg.contract_date DESC NULLS LAST
```

This picks the **most recent sale** per GNAF address across all years of VG history.

### 4.3 Conflict Resolution

```sql
ON CONFLICT (address_detail_pid) DO UPDATE
    SET purchase_price = EXCLUDED.purchase_price,
        contract_date  = EXCLUDED.contract_date,
        updated_at     = NOW()
    WHERE EXCLUDED.contract_date > gnaf_vg_sale_link.contract_date
       OR gnaf_vg_sale_link.contract_date IS NULL
```

Makes the rebuild idempotent — safe to re-run without clearing existing data. Only updates when a newer sale is found.

### 4.4 bind parameters

```python
cur.execute(_BRIDGE_REBUILD_SQL, {
    "postcodes":      list(postcodes),           # list of int — used on vg side
    "postcodes_text": [str(p) for p in postcodes],  # list of str — used on GNAF side
})
```

Two separate bind parameters are required because VG `postcode` is INTEGER and GNAF `postcode` is TEXT.

---

## 5. ArcGIS Valuation ETL — `load_nsw_property_data.py`

**File:** `PRD/scripts/load_nsw_property_data.py`

**Data source:**
```
https://maps.six.nsw.gov.au/arcgis/rest/services/public/Valuation/MapServer
  Layer 1 — NSW Property Sales-SS    (integer postcode field, ~4,987 records per postcode)
  Layer 5 — NSW Property Valuations-SS (no postcode field; filter by address LIKE)
```

### 5.1 CLI Usage

```powershell
# Full load (default postcodes)
python load_nsw_property_data.py

# Truncate and reload
python load_nsw_property_data.py --truncate

# Dry run
python load_nsw_property_data.py --dry-run

# Add postcodes
python load_nsw_property_data.py --where "postcode IN (2077,2119,2125,2120,2076,2148)" \
  --val-where "address LIKE '%NSW 2077%' OR address LIKE '%NSW 2148%'"

# Skip valuations (sales only)
python load_nsw_property_data.py --no-valuations

# Skip sales (valuations only)
python load_nsw_property_data.py --no-sales
```

### 5.2 Fetch Strategies

**Layer 1 (Sales) — Offset pagination:**  
`resultOffset` / `resultRecordCount` pagination. Works because `postcode` is an indexed integer field.

**Layer 5 (Valuations) — ReturnIdsOnly → OBJECTID IN batches:**  
- Phase 1: `returnIdsOnly=true` with `LIKE` filter → array of OBJECTIDs  
- Phase 2: fetch features in batches of 500 via `OBJECTID IN (...)`  
- Required because Layer 5 rejects LIKE clauses in direct feature queries.

### 5.3 Upsert Behaviour

| Table | Conflict Key | On Conflict |
|---|---|---|
| `nsw_property_sales` | `(propid, dealing)` | `DO UPDATE` if `price`, `sale_date`, `bp_address`, `area`, or `validity_d` changed |
| `nsw_property_valuation` | `(propid)` | Always overwrites all val1–val5 columns |
| `nsw_property_valuation_history` | `(propid, base_date)` | `DO NOTHING` — insert-only, never overwrites |

---

## 6. Flask API — Price Display

**All three endpoints** in `PRD/webapp/app.py` use the same pattern:

```sql
LEFT JOIN public.gnaf_vg_sale_link gvl ON gvl.address_detail_pid = ad.address_detail_pid
```

with SELECT columns:
```sql
TO_CHAR(gvl.purchase_price, 'FM$999,999,999') AS last_sold_price,
TO_CHAR(gvl.contract_date,  'FMDD Month YYYY') AS last_sale_date
```

| Endpoint | Function | app.py line |
|---|---|---|
| `GET /api/address/search` | `search_address()` | ~634 |
| `GET /api/australia-school/<id>/addresses` | `get_australia_school_addresses()` | ~1298 |
| `GET /api/school/<id>/addresses` | `get_school_addresses()` | ~1982 |

Returns `NULL` for both columns when no bridge entry exists. The UI renders `—` (grey dash).

---

## 7. UX/UI Integration

### 7.1 Address Lookup Page (`/address-lookup`)

**File:** `PRD/webapp/static/js/address.js` | **API:** `GET /api/address/search`

Last Sold is column 10 in the 12-column results table:

```javascript
<td style="font-size: 0.85rem; white-space: nowrap;">
    ${addr.last_sold_price
        ? `<strong style="color: #166534;">${addr.last_sold_price}</strong>
           <br><span style="font-size: 0.72rem; color: #6b7280;">${addr.last_sale_date || ''}</span>`
        : '<span style="color: #d1d5db;">—</span>'}
</td>
```

### 7.2 Australia School Search Page (`/australia-school-search`)

**File:** `PRD/webapp/static/js/australia_school.js` | **API:** `GET /api/australia-school/<acara_sml_id>/addresses`

Last Sold is a `detail-item` in the expandable row `detail-grid`, placed before "PROPERTY LINKS":

```javascript
<div class="detail-item">
    <div class="detail-label">LAST SOLD</div>
    <div class="detail-value">
        ${addr.last_sold_price
            ? `<strong style="color: #166534;">${addr.last_sold_price}</strong>
               <span style="font-size: 0.75rem; color: #6b7280; margin-left: 6px;">${addr.last_sale_date || ''}</span>`
            : '<span style="color: #9ca3af;">—</span>'}
    </div>
</div>
```

### 7.3 School Catchment Search Page (`/school-search`)

**File:** `PRD/webapp/static/js/school.js` | **API:** `GET /api/school/<school_id>/addresses`

**Desktop (detail-grid, before "Property Links"):**
```javascript
<div class="detail-item">
    <div class="detail-label">Last Sold</div>
    <div class="detail-value">
        ${addr.last_sold_price
            ? `<strong style="color: #166534;">${addr.last_sold_price}</strong>
               <span style="font-size: 0.75rem; color: #6b7280; margin-left: 6px;">${addr.last_sale_date || ''}</span>`
            : '<span style="color: #9ca3af;">—</span>'}
    </div>
</div>
```

**Mobile (card-info-grid, after "Geocode Type"):**
```javascript
<div class="card-info-item">
    <div class="card-info-label">Last Sold</div>
    <div class="card-info-value">
        ${addr.last_sold_price
            ? `<strong style="color: #166534;">${addr.last_sold_price}</strong>
               <span style="font-size: 0.75rem; color: #6b7280; display: block;">${addr.last_sale_date || ''}</span>`
            : '<span style="color: #9ca3af;">—</span>'}
    </div>
</div>
```

---

## 8. Known Limitations

| Limitation | Detail |
|---|---|
| Loaded postcodes only | Any address outside `{2076, 2077, 2119, 2120, 2125}` returns `—`. |
| Bridge matches non-unit addresses only | Unit (flat) addresses: VG `unit_number` must be non-blank to match GNAF `flat_number`. Units where VG records them differently may not match. |
| VG `street_name` must begin with GNAF `street_name` | The bridge uses `ILIKE sl.street_name || ' %'` (prefix) or exact match. Abbreviated types (e.g. `'KIRKHAM ST'` vs GNAF `'KIRKHAM'`) would not match — observed VG data uses full forms (`STREET`, `AVENUE`, `ROAD`) and this has not been an issue. |
| Bridge holds most recent sale only | `gnaf_vg_sale_link` stores one row per GNAF address — the most recent matched VG sale. Historical price trend is in `nsw_vg_sales_history` and queryable directly. |
| VG data publish lag | Weekly files are typically published 2–3 weeks after the sale week. The script excludes files within 21 days of today (`WEEKLY_PUBLISH_LAG = 21`). |

---

## 9. Bugs Fixed (history)

| Bug | Symptom | Fix |
|---|---|---|
| Missing GNAF postcode filter | Bridge rebuild scanned all 7M GNAF rows; query ran >9 min | Added `AND ad.postcode = ANY(%(postcodes_text)s)` — separate TEXT-typed bind param |
| VG alpha suffix with space (`'11 B'`) | `'11 B'` matched plain `11` instead of `11B`; wrong price shown | Inner `regexp_replace(..., '\s+', '')` strips spaces before suffix extraction |
| Street exact-match missing (`'THE CRESCENT'`) | Streets where type is part of name never matched; no price shown | Added `OR vg.street_name ILIKE sl.street_name` branch to street join condition |
| `.env` path wrong | Script couldn't connect to DB | Changed `_here.parent / "webapp" / ".env"` → `_here.parent / ".env"` |

---

## 10. File Index

| File | Purpose |
|---|---|
| `PRD/scripts/load_vg_bulk_sales.py` | **Primary ETL**: VG bulk zip → `nsw_vg_sales_history` + `gnaf_vg_sale_link` |
| `PRD/scripts/load_nsw_property_data.py` | ArcGIS ETL → `nsw_property_sales` + `nsw_property_valuation` |
| `PRD/scripts/vg_data/` | Downloaded VG zip files (53 files, ~400MB) |
| `PRD/.env` | DB credentials — single `.env` at `PRD/` level |
| `PRD/webapp/app.py` | Flask API; bridge join at lines ~634, ~1298, ~1982 |
| `PRD/webapp/static/js/address.js` | Last Sold column in address lookup table |
| `PRD/webapp/static/js/australia_school.js` | Last Sold detail-item in expandable row |
| `PRD/webapp/static/js/school.js` | Last Sold in desktop detail-grid + mobile card |
