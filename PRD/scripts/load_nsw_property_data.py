#!/usr/bin/env python3
"""
Load NSW Property Sales and Valuation data into PostgreSQL (public schema).

Source: NSW Spatial Services / Valuer General
MapServer: https://maps.six.nsw.gov.au/arcgis/rest/services/public/Valuation/MapServer

Tables created / maintained:
  public.nsw_property_sales              – Sales transactions
                                           UNIQUE(propid, dealing)
                                           ON CONFLICT: upsert price/date if changed
  public.nsw_property_valuation          – Current land valuations (wide format)
                                           UNIQUE(propid)
                                           ON CONFLICT: always upsert all val columns
  public.nsw_property_valuation_history  – Normalized history (1 row per propid+base_date)
                                           PRIMARY KEY(propid, base_date)
                                           ON CONFLICT: DO NOTHING (insert-only)
  public.nsw_property_load_log           – ETL checkpoint / audit log

Conflict / update strategy:
  sales        : new dealings INSERT; existing dealing re-checked → UPDATE only if
                 price / sale_date / validity_d changed; rowcount=0 means no change
  valuation    : every run upserts the wide row so val1..val5 always reflect API state
  val_history  : idempotent – existing (propid, base_date) rows are never overwritten,
                 new base_date rows are appended.  Old base dates pushed off the API
                 are permanently retained here.

Partial / incremental load:
  Use --where to scope each run (postcode, suburb, OBJECTID range, etc.)
  Load log stores max_oid_loaded per run so the next run can use
  --where "OBJECTID > <checkpoint>" for the sales layer.

Usage:
    python load_nsw_property_data.py [options]

Options:
    --where TEXT        ArcGIS WHERE clause for the SALES layer
                        (default: postcode IN (2077,2119,2125,2120,2076))
                        Sales layer has: propid, dealing, postcode, suburb, ...
    --val-where TEXT    ArcGIS WHERE clause for the VALUATION layer
                        (default: address LIKE '%NSW 2077%' OR ... for 5 postcodes)
                        Valuation layer has NO postcode field; uses address instead.
                        LIKE filters are handled via returnIdsOnly→OBJECTID IN batches.
    --batch-size INT    Records per API page (default: 1000)
    --dry-run           Fetch one batch and print sample; no DB writes
    --truncate          DROP + recreate all three tables before loading
    --no-sales          Skip property sales layer
    --no-valuations     Skip valuation layers
    --timeout INT       HTTP timeout seconds (default: 60)

Environment variables (read from webapp/.env or local .env):
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────────────────────
# Environment / DB config
# ─────────────────────────────────────────────────────────────────────────────
_here = Path(__file__).resolve().parent
load_dotenv(_here.parent / "webapp" / ".env")
load_dotenv()

DB_HOST     = os.getenv("DB_HOST",     "localhost")
DB_PORT     = os.getenv("DB_PORT",     "5432")
DB_NAME     = os.getenv("DB_NAME",     "gnaf_db")
DB_USER     = os.getenv("DB_USER",     "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# ─────────────────────────────────────────────────────────────────────────────
# Service configuration
# ─────────────────────────────────────────────────────────────────────────────
VALUATION_MAPSERVER = (
    "https://maps.six.nsw.gov.au/arcgis/rest/services/public/Valuation/MapServer"
)

# Layer 1 = NSW Property Sales-SS  (street-scale; most detailed, highest record count)
# Layer 5 = NSW Property Valuations-SS
SALES_LAYER_ID      = 1
VALUATION_LAYER_ID  = 5

# postcode is an INTEGER field in the sales API — no quotes around values
DEFAULT_WHERE = "postcode IN (2077, 2119, 2125, 2120, 2076)"

# Valuation layer has NO postcode field. Filter by address text (ends with "NSW XXXX").
# IMPORTANT: LIKE filters work for returnCountOnly / returnIdsOnly but NOT for
# direct feature retrieval on this service. The loader uses a two-phase approach:
#   1. returnIdsOnly=true  → get matching OBJECTIDs (LIKE allowed here)
#   2. OBJECTID IN (...)   → fetch features in batches (uses primary key index)
DEFAULT_VAL_WHERE = (
    "address LIKE '%NSW 2077%' OR address LIKE '%NSW 2119%' OR "
    "address LIKE '%NSW 2125%' OR address LIKE '%NSW 2120%' OR "
    "address LIKE '%NSW 2076%'"
)


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helpers
# ─────────────────────────────────────────────────────────────────────────────

def fetch_json(url: str, params: dict | None = None, timeout: int = 60) -> dict | None:
    """GET JSON from an ArcGIS REST endpoint. Returns None on network/API error."""
    all_params = {"f": "json"}
    if params:
        all_params.update(params)
    full_url = f"{url}?{urllib.parse.urlencode(all_params)}"
    try:
        req = urllib.request.Request(
            full_url,
            headers={
                "User-Agent": "Mozilla/5.0 (NSWProperty-Loader/1.0)",
                "Accept":     "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw  = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
            if isinstance(data, dict) and "error" in data:
                print(f"  [API ERROR] {data['error']}")
                return None
            return data
    except Exception as exc:
        print(f"  [HTTP ERROR] {exc}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Geometry helpers
# ─────────────────────────────────────────────────────────────────────────────

def esri_geometry_to_wkt(geometry: dict, geom_type: str) -> str | None:
    """Convert ESRI JSON geometry to WKT string. Returns None if geometry is absent."""
    if not geometry:
        return None
    try:
        if geom_type == "esriGeometryPoint":
            x = geometry.get("x")
            y = geometry.get("y")
            if x is None or y is None:
                return None
            return f"POINT({x} {y})"
        elif geom_type == "esriGeometryPolygon":
            rings = geometry.get("rings", [])
            if not rings:
                return None
            parts = []
            for ring in rings:
                coords = ", ".join(f"{x} {y}" for x, y in ring)
                parts.append(f"({coords})")
            if len(parts) == 1:
                return f"POLYGON({parts[0]})"
            return "MULTIPOLYGON(" + ", ".join(f"({p})" for p in parts) + ")"
    except Exception as exc:
        print(f"  [GEOM WARN] {exc}")
    return None


def detect_srid(layer_meta: dict) -> int:
    """Extract source SRID from layer metadata spatial reference."""
    spatial_ref = (
        layer_meta.get("extent", {}).get("spatialReference")
        or layer_meta.get("spatialReference")
        or {}
    )
    wkid = spatial_ref.get("latestWkid") or spatial_ref.get("wkid") or 4326
    # Web Mercator → 3857; GDA94 / GDA2020 stay as-is
    return 3857 if wkid == 102100 else wkid


# ─────────────────────────────────────────────────────────────────────────────
# Database helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_conn():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME,
        user=DB_USER, password=DB_PASSWORD,
    )


def ensure_postgis(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    conn.commit()
    print("✓ PostGIS extension ready")


def create_tables(conn, truncate: bool, dry_run: bool) -> None:
    """
    Create all four tables and their indexes.
    With --truncate: DROP CASCADE then recreate (picks up schema changes).
    Without --truncate: CREATE TABLE IF NOT EXISTS (safe for repeated runs).
    """

    tables_to_drop = [
        "nsw_property_sales",
        "nsw_property_valuation",
        "nsw_property_valuation_history",
    ]

    ddl_statements = [
        # ── Load / checkpoint log ──────────────────────────────────────────
        """\
CREATE TABLE IF NOT EXISTS public.nsw_property_load_log (
    id             SERIAL PRIMARY KEY,
    layer_name     TEXT,
    where_clause   TEXT,
    max_oid_loaded INTEGER,
    rows_inserted  INTEGER,
    rows_updated   INTEGER,
    rows_skipped   INTEGER,
    run_at         TIMESTAMPTZ DEFAULT NOW()
);""",

        # ── Property Sales ─────────────────────────────────────────────────
        #   UNIQUE(propid, dealing) — natural business key.
        #   A property (propid) appears once per instrument (dealing).
        #   Multi-property sales have the same dealing on multiple propid rows.
        """\
CREATE TABLE IF NOT EXISTS public.nsw_property_sales (
    source_objectid  INTEGER,
    propid           BIGINT,
    dealing          TEXT,
    house_no         TEXT,
    street           TEXT,
    suburb           TEXT,
    postcode         INTEGER,
    bp_address       TEXT,
    price            BIGINT,
    sale_date        TEXT,
    area             DOUBLE PRECISION,
    strata           INTEGER,
    last_sale        TEXT,
    deal_props       INTEGER,
    urbanity         TEXT,
    kmlid            TEXT,
    validity_d       TEXT,
    geometry         geometry(Point, 4326),
    loaded_at        TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_nsw_property_sales UNIQUE (propid, dealing)
);""",

        # ── Property Valuation — current state (wide, 1 row per propid) ───
        #   UNIQUE(propid) — one current valuation snapshot per property.
        #   val1..val5 columns are a rolling 5-year window provided by the API.
        #   This table is always upserted to reflect the latest API state.
        """\
CREATE TABLE IF NOT EXISTS public.nsw_property_valuation (
    source_objectid  INTEGER,
    propid           BIGINT,
    address          TEXT,
    zone_desc        TEXT,
    prop_area        TEXT,
    basis_desc       TEXT,
    lga_cbd          TEXT,
    lga_pbd          TEXT,
    lga_cbdr         TEXT,
    urbanity         TEXT,
    val1_bd          TEXT,
    val1_lv          TEXT,
    val1_con         TEXT,
    val2_bd          TEXT,
    val2_lv          TEXT,
    val2_con         TEXT,
    val3_bd          TEXT,
    val3_lv          TEXT,
    val3_con         TEXT,
    val4_bd          TEXT,
    val4_lv          TEXT,
    val4_con         TEXT,
    val5_bd          TEXT,
    val5_lv          TEXT,
    val5_con         TEXT,
    conapplies       INTEGER,
    pbdapplies       INTEGER,
    underspflag      INTEGER,
    kmlid            TEXT,
    validity_d       TEXT,
    geometry         geometry(Point, 4326),
    loaded_at        TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_nsw_property_valuation UNIQUE (propid)
);""",

        # ── Valuation History — normalized (1 row per propid + base_date) ─
        #   PRIMARY KEY(propid, base_date) — insert-only, never overwritten.
        #   ETL unpivots val1_bd..val5_bd from the wide table into individual rows.
        #   Old base dates that fall off the API window are permanently retained here.
        #   New annual base dates append exactly 1 new row per property.
        """\
CREATE TABLE IF NOT EXISTS public.nsw_property_valuation_history (
    propid           BIGINT  NOT NULL,
    base_date        TEXT    NOT NULL,
    land_value       TEXT,
    concession       TEXT,
    loaded_at        TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT pk_nsw_valuation_history PRIMARY KEY (propid, base_date)
);""",
    ]

    index_statements = [
        "CREATE INDEX IF NOT EXISTS nsw_property_sales_geom_idx      ON public.nsw_property_sales              USING GIST (geometry);",
        "CREATE INDEX IF NOT EXISTS nsw_property_sales_propid_idx     ON public.nsw_property_sales              (propid);",
        "CREATE INDEX IF NOT EXISTS nsw_property_sales_suburb_idx     ON public.nsw_property_sales              (suburb);",
        "CREATE INDEX IF NOT EXISTS nsw_property_sales_postcode_idx   ON public.nsw_property_sales              (postcode);",
        "CREATE INDEX IF NOT EXISTS nsw_property_val_geom_idx         ON public.nsw_property_valuation          USING GIST (geometry);",
        "CREATE INDEX IF NOT EXISTS nsw_property_val_propid_idx       ON public.nsw_property_valuation          (propid);",
        "CREATE INDEX IF NOT EXISTS nsw_property_val_suburb_idx       ON public.nsw_property_valuation          (address);",
        "CREATE INDEX IF NOT EXISTS nsw_val_hist_propid_idx           ON public.nsw_property_valuation_history  (propid);",
        "CREATE INDEX IF NOT EXISTS nsw_val_hist_base_date_idx        ON public.nsw_property_valuation_history  (base_date);",
    ]

    if dry_run:
        print("\n[DRY RUN] DDL that would be executed:")
        for ddl in ddl_statements:
            print(f"\n{ddl}")
        return

    with conn.cursor() as cur:
        if truncate:
            for tbl in tables_to_drop:
                cur.execute(f'DROP TABLE IF EXISTS public."{tbl}" CASCADE;')
                print(f"  Dropped  public.{tbl}")
        for ddl in ddl_statements:
            cur.execute(ddl)
        for idx in index_statements:
            cur.execute(idx)
    conn.commit()
    print("✓ Tables and indexes ready")


def write_load_log(
    conn, layer_name: str, where_clause: str,
    max_oid: int, inserted: int, updated: int, skipped: int,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """\
INSERT INTO public.nsw_property_load_log
    (layer_name, where_clause, max_oid_loaded, rows_inserted, rows_updated, rows_skipped)
VALUES (%s, %s, %s, %s, %s, %s)""",
            (layer_name, where_clause, max_oid, inserted, updated, skipped),
        )
    conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Feature fetch — two strategies
# ─────────────────────────────────────────────────────────────────────────────

def _layer_meta(layer_id: int, timeout: int) -> tuple[str | None, int, int, str]:
    """Fetch layer metadata. Returns (geom_type, srid, max_record_count, query_url)."""
    layer_url = f"{VALUATION_MAPSERVER}/{layer_id}"
    meta = fetch_json(layer_url, timeout=timeout)
    if not meta:
        print(f"  [ERROR] Could not fetch metadata for layer {layer_id}")
        return None, 4326, 1000, f"{layer_url}/query"
    geom_type  = meta.get("geometryType")
    srid       = detect_srid(meta)
    max_record = meta.get("maxRecordCount", 1000)
    return geom_type, srid, max_record, f"{layer_url}/query"


def fetch_all_features(
    layer_id: int,
    where: str,
    batch_size: int = 1000,
    timeout: int = 60,
    max_features: int | None = None,
) -> tuple[list[dict], str | None, int]:
    """
    Strategy A — offset pagination (resultOffset / resultRecordCount).
    Use for layers whose WHERE fields support direct feature queries (e.g. sales,
    which filters by the indexed integer field `postcode`).

    max_features: cap for --dry-run (fetches only one batch).
    """
    geom_type, srid, max_record, query_url = _layer_meta(layer_id, timeout)
    max_record = min(max_record, batch_size)

    count_data = fetch_json(query_url, {"where": where, "returnCountOnly": "true"}, timeout=timeout)
    total = (count_data or {}).get("count", 0)
    if total == 0:
        print(f"  Layer {layer_id}: 0 features match filter → {where}")
        return [], geom_type, srid

    effective_total = min(total, max_features) if max_features else total
    print(f"  Layer {layer_id}: {total:,} features available (fetching {effective_total:,}, batch={max_record}, srid={srid})")

    all_features: list[dict] = []
    offset = 0
    while offset < effective_total:
        this_batch = min(max_record, effective_total - offset)
        params = {
            "where":             where,
            "outFields":         "*",
            "returnGeometry":    "true" if geom_type else "false",
            "geometryPrecision": "6",
            "resultOffset":      str(offset),
            "resultRecordCount": str(this_batch),
            "orderByFields":     "OBJECTID ASC",
        }
        page = fetch_json(query_url, params, timeout=timeout)
        if not page:
            print(f"\n  [WARN] Empty response at offset {offset}, stopping")
            break
        batch = page.get("features", [])
        if not batch:
            break
        all_features.extend(batch)
        offset += len(batch)
        print(f"    Fetched {offset:,}/{effective_total:,} …", end="\r", flush=True)
        time.sleep(0.1)

    print(f"  Layer {layer_id}: {len(all_features):,} features fetched            ")
    return all_features, geom_type, srid


def fetch_all_features_by_ids(
    layer_id: int,
    where: str,
    batch_size: int = 1000,
    timeout: int = 60,
    max_features: int | None = None,
) -> tuple[list[dict], str | None, int]:
    """
    Strategy B — returnIdsOnly → OBJECTID IN (...) batches.

    Use for layers where LIKE / non-indexed WHERE clauses cause 400 errors on
    direct feature retrieval but work fine for returnIdsOnly=true.

    The NSW Valuation layer (layer 5) falls into this category: `address LIKE`
    succeeds for counts/IDs but fails for feature output.  Fetching by explicit
    OBJECTID lists uses the primary-key index and always succeeds.

    max_features: cap for --dry-run.
    """
    geom_type, srid, max_record, query_url = _layer_meta(layer_id, timeout)
    max_record = min(max_record, batch_size)

    # Phase 1: get all matching OBJECTIDs (LIKE filter is allowed here)
    ids_data = fetch_json(
        query_url,
        {"where": where, "returnIdsOnly": "true", "orderByFields": "OBJECTID ASC"},
        timeout=timeout,
    )
    all_ids: list[int] = (ids_data or {}).get("objectIds") or []
    if not all_ids:
        print(f"  Layer {layer_id}: 0 OBJECTIDs match filter → {where}")
        return [], geom_type, srid

    if max_features:
        all_ids = all_ids[:max_features]

    total = len(all_ids)
    print(f"  Layer {layer_id}: {total:,} OBJECTIDs matched (batch={max_record}, srid={srid})")

    # Phase 2: fetch features in OBJECTID IN (...) batches
    all_features: list[dict] = []
    for i in range(0, total, max_record):
        id_batch = all_ids[i : i + max_record]
        id_list  = ",".join(str(x) for x in id_batch)
        params = {
            "where":             f"OBJECTID IN ({id_list})",
            "outFields":         "*",
            "returnGeometry":    "true" if geom_type else "false",
            "geometryPrecision": "6",
            "orderByFields":     "OBJECTID ASC",
        }
        page = fetch_json(query_url, params, timeout=timeout)
        if not page:
            print(f"\n  [WARN] Empty response for IDs batch at index {i}, stopping")
            break
        batch = page.get("features", [])
        if not batch:
            break
        all_features.extend(batch)
        fetched = min(i + max_record, total)
        print(f"    Fetched {fetched:,}/{total:,} …", end="\r", flush=True)
        time.sleep(0.1)

    print(f"  Layer {layer_id}: {len(all_features):,} features fetched            ")
    return all_features, geom_type, srid


# ─────────────────────────────────────────────────────────────────────────────
# Sales loader
# ─────────────────────────────────────────────────────────────────────────────

def load_sales(
    conn, where: str, batch_size: int, dry_run: bool, timeout: int,
) -> dict:
    """
    Load sales layer into public.nsw_property_sales.

    Conflict strategy  UNIQUE(propid, dealing):
      • New dealing           → INSERT (rowcount = 1)
      • Existing, data changed → UPDATE price/sale_date/validity_d (rowcount = 1)
      • Existing, no change   → DO UPDATE WHERE condition false → rowcount = 0 (skipped)
    """
    print(f"\n{'─' * 60}")
    print(f"SALES  →  public.nsw_property_sales")
    print(f"Filter : {where}")
    print(f"{'─' * 60}")

    features, geom_type, srid = fetch_all_features(
        SALES_LAYER_ID, where, batch_size, timeout,
        max_features=batch_size if dry_run else None,
    )
    if not features:
        return {"inserted": 0, "updated": 0, "skipped": 0, "max_oid": 0}

    if dry_run:
        sample = features[0].get("attributes", {})
        print(f"\n[DRY RUN] Sample sales record fields:\n{json.dumps(sample, indent=2)}")
        print(f"[DRY RUN] Would process {len(features):,} records shown above — no DB writes")
        return {"inserted": 0, "updated": 0, "skipped": 0, "max_oid": 0}

    # ── geometry placeholder ─────────────────────────────────────────────────
    if srid != 4326:
        geom_expr = f"ST_Transform(ST_GeomFromText(%(wkt)s, {srid}), 4326)"
    else:
        geom_expr = "ST_GeomFromText(%(wkt)s, 4326)"

    # ── upsert SQL ───────────────────────────────────────────────────────────
    #   ON CONFLICT DO UPDATE ... WHERE ensures rowcount=0 when nothing changed.
    #   This lets us distinguish "written" vs "no-change skipped" without xmax tricks.
    upsert_sql = f"""\
INSERT INTO public.nsw_property_sales
    (source_objectid, propid, dealing, house_no, street, suburb, postcode,
     bp_address, price, sale_date, area, strata, last_sale, deal_props,
     urbanity, kmlid, validity_d, geometry, loaded_at)
VALUES
    (%(source_objectid)s, %(propid)s, %(dealing)s, %(house_no)s, %(street)s,
     %(suburb)s, %(postcode)s, %(bp_address)s, %(price)s, %(sale_date)s,
     %(area)s, %(strata)s, %(last_sale)s, %(deal_props)s,
     %(urbanity)s, %(kmlid)s, %(validity_d)s,
     CASE WHEN %(wkt)s IS NOT NULL THEN {geom_expr} ELSE NULL END,
     NOW())
ON CONFLICT (propid, dealing) DO UPDATE SET
    price      = EXCLUDED.price,
    sale_date  = EXCLUDED.sale_date,
    bp_address = EXCLUDED.bp_address,
    area       = EXCLUDED.area,
    validity_d = EXCLUDED.validity_d,
    loaded_at  = NOW()
WHERE (
    nsw_property_sales.price      IS DISTINCT FROM EXCLUDED.price      OR
    nsw_property_sales.sale_date  IS DISTINCT FROM EXCLUDED.sale_date  OR
    nsw_property_sales.validity_d IS DISTINCT FROM EXCLUDED.validity_d
)"""

    inserted = updated = skipped = 0
    max_oid  = 0

    with conn.cursor() as cur:
        for feat in features:
            a   = feat.get("attributes", {})
            g   = feat.get("geometry")
            oid = a.get("OBJECTID") or a.get("objectid") or 0
            if oid:
                max_oid = max(max_oid, oid)

            propid  = a.get("propid")
            dealing = a.get("dealing")
            if propid is None or dealing is None:
                # Cannot enforce uniqueness without both keys — skip
                skipped += 1
                continue

            wkt = esri_geometry_to_wkt(g, geom_type) if g else None

            row = {
                "source_objectid": oid,
                "propid":          propid,
                "dealing":         dealing,
                "house_no":        a.get("house_no"),
                "street":          a.get("street"),
                "suburb":          a.get("suburb"),
                "postcode":        a.get("postcode"),
                "bp_address":      a.get("bp_address"),
                "price":           a.get("price"),
                "sale_date":       a.get("sale_date"),
                "area":            a.get("area"),
                "strata":          a.get("strata"),
                "last_sale":       a.get("last_sale"),
                "deal_props":      a.get("deal_props"),
                "urbanity":        a.get("urbanity"),
                "kmlid":           a.get("KMLid"),
                "validity_d":      a.get("Validity_d"),
                "wkt":             wkt,
            }

            cur.execute(upsert_sql, row)
            if cur.rowcount == 1:
                inserted += 1    # new row or data-changed update
            else:
                skipped  += 1   # existing row, nothing changed

    conn.commit()

    # Distinguish inserts vs updates is complex without RETURNING xmax.
    # For the log we report all written rows under "inserted"; truly updated rows
    # are a subset but not separately counted here.
    print(f"  ✓ Sales: {inserted:,} written (new/updated), {skipped:,} skipped (no change / null key)")
    return {"inserted": inserted, "updated": 0, "skipped": skipped, "max_oid": max_oid}


# ─────────────────────────────────────────────────────────────────────────────
# Valuation loader
# ─────────────────────────────────────────────────────────────────────────────

def load_valuations(
    conn, val_where: str, batch_size: int, dry_run: bool, timeout: int,
) -> dict:
    """
    Load valuation layer into:
      1. public.nsw_property_valuation  (wide, upsert — always reflects current API state)
      2. public.nsw_property_valuation_history  (normalized, insert-only)

    Uses fetch_all_features_by_ids (returnIdsOnly → OBJECTID IN batches) because the
    valuation layer rejects LIKE-filtered direct feature queries with HTTP 400 but
    allows them for returnIdsOnly=true.

    Notes on the API response:
      - `address` is a virtual field: present in fieldAliases but NOT returned in
        feature attributes. The column is kept in the DB table but will always be NULL
        unless a future API version starts returning it.
      - `lga_cbd`, `lga_pbd`, `lga_cbdr` contain current base dates, not LGA names.
      - Field casing: `UnderspFlag`, `Validity_d`, `KMLid` are mixed-case.
    """
    print(f"\n{'─' * 60}")
    print(f"VALUATIONS  →  public.nsw_property_valuation")
    print(f"             + public.nsw_property_valuation_history")
    print(f"Filter : {val_where}")
    print(f"{'─' * 60}")

    features, geom_type, srid = fetch_all_features_by_ids(
        VALUATION_LAYER_ID, val_where, batch_size, timeout,
        max_features=batch_size if dry_run else None,
    )
    if not features:
        return {"inserted": 0, "updated": 0, "skipped": 0, "history_inserted": 0, "max_oid": 0}

    if dry_run:
        sample = features[0].get("attributes", {})
        print(f"\n[DRY RUN] Sample valuation record fields:\n{json.dumps(sample, indent=2)}")
        print(f"[DRY RUN] Would process {len(features):,} records shown above — no DB writes")
        return {"inserted": 0, "updated": 0, "skipped": 0, "history_inserted": 0, "max_oid": 0}

    # ── geometry placeholder ─────────────────────────────────────────────────
    if srid != 4326:
        geom_expr = f"ST_Transform(ST_GeomFromText(%(wkt)s, {srid}), 4326)"
    else:
        geom_expr = "ST_GeomFromText(%(wkt)s, 4326)"

    # ── wide upsert SQL ──────────────────────────────────────────────────────
    # Note: `address` column is included but will be NULL (virtual API field).
    upsert_val_sql = f"""\
INSERT INTO public.nsw_property_valuation
    (source_objectid, propid, address, zone_desc, prop_area, basis_desc,
     lga_cbd, lga_pbd, lga_cbdr, urbanity,
     val1_bd, val1_lv, val1_con,
     val2_bd, val2_lv, val2_con,
     val3_bd, val3_lv, val3_con,
     val4_bd, val4_lv, val4_con,
     val5_bd, val5_lv, val5_con,
     conapplies, pbdapplies, underspflag, kmlid, validity_d,
     geometry, loaded_at)
VALUES
    (%(source_objectid)s, %(propid)s, %(address)s, %(zone_desc)s, %(prop_area)s,
     %(basis_desc)s, %(lga_cbd)s, %(lga_pbd)s, %(lga_cbdr)s, %(urbanity)s,
     %(val1_bd)s, %(val1_lv)s, %(val1_con)s,
     %(val2_bd)s, %(val2_lv)s, %(val2_con)s,
     %(val3_bd)s, %(val3_lv)s, %(val3_con)s,
     %(val4_bd)s, %(val4_lv)s, %(val4_con)s,
     %(val5_bd)s, %(val5_lv)s, %(val5_con)s,
     %(conapplies)s, %(pbdapplies)s, %(underspflag)s, %(kmlid)s, %(validity_d)s,
     CASE WHEN %(wkt)s IS NOT NULL THEN {geom_expr} ELSE NULL END,
     NOW())
ON CONFLICT (propid) DO UPDATE SET
    source_objectid = EXCLUDED.source_objectid,
    zone_desc       = EXCLUDED.zone_desc,
    prop_area       = EXCLUDED.prop_area,
    basis_desc      = EXCLUDED.basis_desc,
    lga_cbd         = EXCLUDED.lga_cbd,
    lga_pbd         = EXCLUDED.lga_pbd,
    lga_cbdr        = EXCLUDED.lga_cbdr,
    urbanity        = EXCLUDED.urbanity,
    val1_bd  = EXCLUDED.val1_bd,  val1_lv  = EXCLUDED.val1_lv,  val1_con  = EXCLUDED.val1_con,
    val2_bd  = EXCLUDED.val2_bd,  val2_lv  = EXCLUDED.val2_lv,  val2_con  = EXCLUDED.val2_con,
    val3_bd  = EXCLUDED.val3_bd,  val3_lv  = EXCLUDED.val3_lv,  val3_con  = EXCLUDED.val3_con,
    val4_bd  = EXCLUDED.val4_bd,  val4_lv  = EXCLUDED.val4_lv,  val4_con  = EXCLUDED.val4_con,
    val5_bd  = EXCLUDED.val5_bd,  val5_lv  = EXCLUDED.val5_lv,  val5_con  = EXCLUDED.val5_con,
    conapplies  = EXCLUDED.conapplies,
    pbdapplies  = EXCLUDED.pbdapplies,
    underspflag = EXCLUDED.underspflag,
    validity_d  = EXCLUDED.validity_d,
    loaded_at   = NOW()"""

    # ── history insert SQL ───────────────────────────────────────────────────
    upsert_hist_sql = """\
INSERT INTO public.nsw_property_valuation_history
    (propid, base_date, land_value, concession, loaded_at)
VALUES (%s, %s, %s, %s, NOW())
ON CONFLICT (propid, base_date) DO NOTHING"""

    written = skipped = history_inserted = history_skipped = 0
    max_oid = 0

    with conn.cursor() as cur:
        for feat in features:
            a      = feat.get("attributes", {})
            g      = feat.get("geometry")
            oid    = a.get("OBJECTID") or a.get("objectid") or 0
            propid = a.get("propid")

            if propid is None:
                skipped += 1
                continue

            if oid:
                max_oid = max(max_oid, oid)

            wkt = esri_geometry_to_wkt(g, geom_type) if g else None

            row = {
                "source_objectid": oid,
                "propid":     propid,
                "address":    a.get("address"),      # virtual field — will be NULL
                "zone_desc":  a.get("zone_desc"),
                "prop_area":  a.get("prop_area"),
                "basis_desc": a.get("basis_desc"),
                "lga_cbd":    a.get("lga_cbd"),      # actually the current base date
                "lga_pbd":    a.get("lga_pbd"),
                "lga_cbdr":   a.get("lga_cbdr"),
                "urbanity":   a.get("urbanity"),
                "val1_bd":    a.get("val1_bd"),
                "val1_lv":    a.get("val1_lv"),
                "val1_con":   a.get("val1_con"),
                "val2_bd":    a.get("val2_bd"),
                "val2_lv":    a.get("val2_lv"),
                "val2_con":   a.get("val2_con"),
                "val3_bd":    a.get("val3_bd"),
                "val3_lv":    a.get("val3_lv"),
                "val3_con":   a.get("val3_con"),
                "val4_bd":    a.get("val4_bd"),
                "val4_lv":    a.get("val4_lv"),
                "val4_con":   a.get("val4_con"),
                "val5_bd":    a.get("val5_bd"),
                "val5_lv":    a.get("val5_lv"),
                "val5_con":   a.get("val5_con"),
                "conapplies":  a.get("conapplies"),
                "pbdapplies":  a.get("pbdapplies"),
                "underspflag": a.get("UnderspFlag"),
                "kmlid":       a.get("KMLid"),
                "validity_d":  a.get("Validity_d"),
                "wkt":         wkt,
            }

            cur.execute(upsert_val_sql, row)
            written += 1

            # ── Unpivot val1..val5 into history table ────────────────────
            for vi in range(1, 6):
                bd  = a.get(f"val{vi}_bd")
                lv  = a.get(f"val{vi}_lv")
                con = a.get(f"val{vi}_con")
                if bd:
                    cur.execute(upsert_hist_sql, (propid, bd, lv, con))
                    if cur.rowcount == 1:
                        history_inserted += 1
                    else:
                        history_skipped  += 1

    conn.commit()

    print(f"  ✓ Valuation  : {written:,} upserted  (wide table reflects current API state)")
    print(f"  ✓ History    : {history_inserted:,} new history rows, "
          f"{history_skipped:,} already existed (DO NOTHING)")
    return {
        "inserted": written, "updated": 0, "skipped": skipped,
        "history_inserted": history_inserted, "max_oid": max_oid,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Load NSW Property Sales and Valuation data into PostgreSQL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--where", default=DEFAULT_WHERE,
        help=(
            "ArcGIS WHERE clause for the SALES layer (has postcode field). "
            f"Default: {DEFAULT_WHERE!r}. "
            "For incremental load use e.g. \"OBJECTID > 150000\". "
            "For full NSW load use \"1=1\" (millions of records)."
        ),
    )
    parser.add_argument(
        "--val-where", default=None,
        help=(
            "ArcGIS WHERE clause for the VALUATION layer (no postcode field). "
            f"Default: address LIKE filters for same 5 postcodes. "
            "For full NSW load use \"1=1\". "
            "Example: \"KMLid LIKE '573%%'\" for a specific lot range."
        ),
    )
    parser.add_argument("--batch-size",    type=int, default=1000,
                        help="Records per API page request (default: 1000)")
    parser.add_argument("--timeout",       type=int, default=60,
                        help="HTTP timeout in seconds (default: 60)")
    parser.add_argument("--dry-run",       action="store_true",
                        help="Fetch one page, print sample record, no DB writes")
    parser.add_argument("--truncate",      action="store_true",
                        help="DROP + recreate all three data tables before loading")
    parser.add_argument("--no-sales",      action="store_true",
                        help="Skip the property sales layer")
    parser.add_argument("--no-valuations", action="store_true",
                        help="Skip the property valuation layers")
    args = parser.parse_args()

    val_where = args.val_where or DEFAULT_VAL_WHERE

    print("=" * 60)
    print("NSW Property Data Loader")
    print(f"  DB         : {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    print(f"  Sales WHERE: {args.where}")
    print(f"  Val WHERE  : {val_where}")
    print(f"  Dry run    : {args.dry_run}")
    print(f"  Truncate   : {args.truncate}")
    print("=" * 60)

    try:
        conn = get_conn()
    except Exception as exc:
        print(f"[FATAL] Cannot connect to database: {exc}")
        sys.exit(1)

    ensure_postgis(conn)
    create_tables(conn, truncate=args.truncate, dry_run=args.dry_run)

    start = datetime.now()

    # ── Sales ────────────────────────────────────────────────────────────────
    if not args.no_sales:
        s = load_sales(conn, args.where, args.batch_size, args.dry_run, args.timeout)
        if not args.dry_run:
            write_load_log(
                conn, "sales", args.where,
                s["max_oid"], s["inserted"], s["updated"], s["skipped"],
            )

    # ── Valuations + History ─────────────────────────────────────────────────
    if not args.no_valuations:
        v = load_valuations(conn, val_where, args.batch_size, args.dry_run, args.timeout)
        if not args.dry_run:
            write_load_log(
                conn, "valuation", val_where,
                v["max_oid"], v["inserted"], v["updated"], v["skipped"],
            )
            write_load_log(
                conn, "valuation_history", val_where,
                v["max_oid"], v["history_inserted"], 0, 0,
            )

    elapsed = (datetime.now() - start).total_seconds()
    print(f"\n{'=' * 60}")
    print(f"Completed in {elapsed:.1f}s")

    # Print load log summary
    if not args.dry_run:
        with conn.cursor() as cur:
            cur.execute("""\
SELECT layer_name, rows_inserted, rows_updated, rows_skipped, max_oid_loaded, run_at
FROM public.nsw_property_load_log
ORDER BY run_at DESC
LIMIT 5""")
            rows = cur.fetchall()
        print("\nLoad log (last 5 entries):")
        print(f"  {'Layer':<25} {'Inserted':>10} {'Updated':>8} {'Skipped':>8} {'MaxOID':>10}  Run at")
        print("  " + "─" * 75)
        for r in rows:
            print(f"  {r[0]:<25} {r[1]:>10,} {r[2]:>8,} {r[3]:>8,} {r[4] or 0:>10,}  {r[5]}")

    conn.close()


if __name__ == "__main__":
    main()
