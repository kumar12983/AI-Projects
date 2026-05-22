#!/usr/bin/env python3
"""
Load Australian Flood Risk Information Portal (AFRIP) data into PostgreSQL (public schema)

Source portal:
  https://experience.arcgis.com/experience/064d72c01bcb4d16979753545c4b72b4

This script fetches feature data from ArcGIS FeatureServer REST endpoints,
converts geometry to WGS84 (EPSG:4326), and loads the following tables into
the 'public' schema:

  public.afrip_flood_studies         – Flood study area boundaries (polygons)
  public.afrip_flood_extents         – Flood extent polygons (1% AEP, 10% AEP, PMF, etc.)
  public.afrip_flood_model_metadata  – Non-spatial metadata rows for each flood study
  public.afrip_flood_points          – Flood study centroid points (for fast lookups)

Usage:
    python load_afrip_flood_data.py [options]

Options:
    --service-url URL   ArcGIS FeatureServer base URL (overrides defaults)
    --layer-id  INT     Only load a specific layer ID (default: load all)
    --batch-size INT    Records per API page request (default: 1000)
    --schema TEXT       Target PostgreSQL schema (default: public)
    --dry-run           Print what would happen without writing to the database
    --truncate          TRUNCATE target tables before loading (default: append)
    --timeout INT       HTTP timeout in seconds (default: 60)

Environment variables (or webapp/.env):
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
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────────────────────
# Environment / DB config
# ─────────────────────────────────────────────────────────────────────────────
_here = Path(__file__).resolve().parent
load_dotenv(_here.parent / "webapp" / ".env")
load_dotenv()  # also try local .env

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "gnaf_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# ─────────────────────────────────────────────────────────────────────────────
# AFRIP service configuration
#
# Primary service:  Geoscience Australia AFRIP FeatureServer
# Fallback services are listed in order of preference.
#
# To find the correct URL:
#  1. Open https://experience.arcgis.com/experience/064d72c01bcb4d16979753545c4b72b4
#  2. DevTools → Network → filter "FeatureServer"
#  3. Paste the base URL here (everything up to and including "FeatureServer")
# ─────────────────────────────────────────────────────────────────────────────
# Real AFRIP service endpoints (Digital Atlas of Australia / aus_digitalatlas)
# Flood study point layer (AFRIP catalogue, 2018 one-off dataset)
DEFAULT_SERVICE_URLS = [
    "https://services-ap1.arcgis.com/ypkPEy1AmwPKGNNv/arcgis/rest/services/flood_study_summary_3ce61/FeatureServer",
]

# S3 attachments lookup table (PDF reports + GIS data links)
ATTACHMENTS_SERVICE_URL = (
    "https://services-ap1.arcgis.com/ypkPEy1AmwPKGNNv/arcgis/rest/services/"
    "Flood_Attachments_S3/FeatureServer"
)

# Layer ID → target table name mapping.
LAYER_TABLE_MAP: dict[int, str] = {
    0: "afrip_flood_studies",   # esriGeometryPoint – one record per flood study
}

ATTACHMENTS_LAYER_TABLE_MAP: dict[int, str] = {
    0: "afrip_flood_attachments",  # non-spatial table – S3 URLs for each study
}

# ArcGIS geometry type → PostGIS geometry type
GEOM_TYPE_MAP = {
    "esriGeometryPolygon": "MULTIPOLYGON",
    "esriGeometryPoint": "POINT",
    "esriGeometryMultipoint": "MULTIPOINT",
    "esriGeometryPolyline": "MULTILINESTRING",
    "esriGeometryEnvelope": "POLYGON",
}

# ArcGIS field type → PostgreSQL column type
FIELD_TYPE_MAP = {
    "esriFieldTypeOID": "INTEGER",
    "esriFieldTypeInteger": "INTEGER",
    "esriFieldTypeSmallInteger": "SMALLINT",
    "esriFieldTypeDouble": "DOUBLE PRECISION",
    "esriFieldTypeSingle": "REAL",
    "esriFieldTypeString": "TEXT",
    "esriFieldTypeDate": "BIGINT",          # Unix ms – convert in SQL if needed
    "esriFieldTypeGlobalID": "TEXT",
    "esriFieldTypeGUID": "TEXT",
    "esriFieldTypeGeometry": None,          # handled separately
    "esriFieldTypeBlob": "BYTEA",
    "esriFieldTypeRaster": "BYTEA",
    "esriFieldTypeXML": "TEXT",
}


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helpers
# ─────────────────────────────────────────────────────────────────────────────

def fetch_json(url: str, params: dict | None = None, timeout: int = 60) -> dict | None:
    """GET JSON from an ArcGIS REST endpoint. Returns None on error."""
    all_params = {"f": "json"}
    if params:
        all_params.update(params)
    query = urllib.parse.urlencode(all_params)
    full_url = f"{url}?{query}"
    try:
        req = urllib.request.Request(
            full_url,
            headers={
                "User-Agent": "Mozilla/5.0 (AFRIP-Loader/1.0)",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
            if isinstance(data, dict) and "error" in data:
                print(f"  [API ERROR] {data['error']}")
                return None
            return data
    except Exception as exc:
        print(f"  [HTTP ERROR] {exc}")
        return None


def probe_feature_server(url: str, timeout: int = 60) -> dict | None:
    """Return FeatureServer metadata dict or None if not reachable."""
    data = fetch_json(url, timeout=timeout)
    if data and ("layers" in data or "tables" in data):
        return data
    return None


# ─────────────────────────────────────────────────────────────────────────────
# ArcGIS → GeoJSON helpers
# ─────────────────────────────────────────────────────────────────────────────

def esri_ring_to_wkt_polygon(rings: list) -> str:
    """Convert ESRI polygon rings to WKT POLYGON."""
    parts = []
    for ring in rings:
        coords = ", ".join(f"{x} {y}" for x, y in ring)
        parts.append(f"({coords})")
    return "POLYGON(" + ", ".join(parts) + ")"


def esri_paths_to_wkt_multilinestring(paths: list) -> str:
    parts = []
    for path in paths:
        coords = ", ".join(f"{x} {y}" for x, y in path)
        parts.append(f"({coords})")
    return "MULTILINESTRING(" + ", ".join(parts) + ")"


def esri_geometry_to_wkt(geometry: dict, geom_type: str) -> str | None:
    """Convert an ESRI JSON geometry dict to a WKT string."""
    if not geometry:
        return None
    try:
        if geom_type == "esriGeometryPolygon":
            rings = geometry.get("rings", [])
            if not rings:
                return None
            if len(rings) == 1:
                coords = ", ".join(f"{x} {y}" for x, y in rings[0])
                return f"POLYGON(({coords}))"
            parts = []
            for ring in rings:
                coords = ", ".join(f"{x} {y}" for x, y in ring)
                parts.append(f"(({coords}))")
            return "MULTIPOLYGON(" + ", ".join(parts) + ")"

        elif geom_type == "esriGeometryPoint":
            x = geometry.get("x")
            y = geometry.get("y")
            if x is None or y is None:
                return None
            return f"POINT({x} {y})"

        elif geom_type == "esriGeometryMultipoint":
            points = geometry.get("points", [])
            if not points:
                return None
            coords = ", ".join(f"{x} {y}" for x, y in points)
            return f"MULTIPOINT({coords})"

        elif geom_type == "esriGeometryPolyline":
            paths = geometry.get("paths", [])
            if not paths:
                return None
            return esri_paths_to_wkt_multilinestring(paths)

        elif geom_type == "esriGeometryEnvelope":
            xmin = geometry.get("xmin")
            ymin = geometry.get("ymin")
            xmax = geometry.get("xmax")
            ymax = geometry.get("ymax")
            if None in (xmin, ymin, xmax, ymax):
                return None
            return (
                f"POLYGON(({xmin} {ymin}, {xmax} {ymin}, "
                f"{xmax} {ymax}, {xmin} {ymax}, {xmin} {ymin}))"
            )
    except Exception as exc:
        print(f"  [GEOM WARN] Could not convert geometry: {exc}")
    return None


def detect_srid(spatial_ref: dict | None) -> int:
    """Extract WKID from spatial reference, defaulting to 4326."""
    if not spatial_ref:
        return 4326
    wkid = spatial_ref.get("latestWkid") or spatial_ref.get("wkid") or 4326
    # GDA94 / GDA2020 common codes
    if wkid in (4283, 7844):
        return wkid
    if wkid == 102100:
        return 3857  # Web Mercator
    return wkid


# ─────────────────────────────────────────────────────────────────────────────
# Database helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_db_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def ensure_postgis(conn: psycopg2.extensions.connection) -> None:
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    conn.commit()
    print("✓ PostGIS extension ready")


def build_create_table_sql(
    table_name: str,
    schema: str,
    fields: list[dict],
    geom_type: str | None,
    srid: int,
) -> str:
    """Generate CREATE TABLE IF NOT EXISTS DDL."""
    cols = ['"source_objectid" INTEGER']

    for field in fields:
        pg_type = FIELD_TYPE_MAP.get(field["type"])
        if pg_type is None:
            continue  # skip geometry/blob columns handled separately
        col_name = field["name"].lower().replace(" ", "_")
        nullable = "" if field.get("nullable", True) else " NOT NULL"
        cols.append(f'"{col_name}" {pg_type}{nullable}')

    if geom_type:
        pg_geom = GEOM_TYPE_MAP.get(geom_type, "GEOMETRY")
        # Always store in WGS84 (4326); ST_Transform is applied on insert
        cols.append(f'"geometry" geometry({pg_geom}, 4326)')

    cols.append('"loaded_at" TIMESTAMPTZ DEFAULT NOW()')

    col_defs = ",\n    ".join(cols)
    return (
        f'CREATE TABLE IF NOT EXISTS {schema}."{table_name}" (\n'
        f"    {col_defs}\n"
        f");"
    )


def truncate_table(conn: psycopg2.extensions.connection, schema: str, table: str) -> None:
    with conn.cursor() as cur:
        cur.execute(f'TRUNCATE TABLE {schema}."{table}" RESTART IDENTITY;')
    conn.commit()


def create_spatial_index(
    conn: psycopg2.extensions.connection, schema: str, table: str
) -> None:
    idx_name = f"{table}_geom_idx"
    with conn.cursor() as cur:
        cur.execute(
            f'CREATE INDEX IF NOT EXISTS "{idx_name}" '
            f'ON {schema}."{table}" USING GIST ("geometry");'
        )
    conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Feature fetching (handles pagination)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_all_features(
    service_url: str,
    layer_id: int,
    batch_size: int = 1000,
    timeout: int = 60,
) -> tuple[list[dict], dict, str | None]:
    """
    Page through a FeatureServer layer/table using offset pagination and return:
      (features, fields_meta, geometry_type)

    Uses resultOffset/resultRecordCount instead of objectIds to avoid
    URL length limits on large datasets.
    """
    layer_url = f"{service_url}/{layer_id}"
    meta = fetch_json(layer_url, timeout=timeout)
    if not meta:
        return [], {}, None

    geom_type: str | None = meta.get("geometryType")
    fields_meta: dict = {f["name"]: f for f in meta.get("fields", [])}
    max_record: int = min(meta.get("maxRecordCount", batch_size), batch_size)

    # Get total count first
    query_url = f"{layer_url}/query"
    count_data = fetch_json(
        query_url,
        {"where": "1=1", "returnCountOnly": "true"},
        timeout=timeout,
    )
    total: int = (count_data or {}).get("count", 0)
    if total == 0:
        print(f"  Layer {layer_id}: no features found")
        return [], fields_meta, geom_type

    print(f"  Layer {layer_id}: {total} features to fetch (batch={max_record})")

    all_features: list[dict] = []
    offset = 0
    while offset < total:
        params: dict = {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true" if geom_type else "false",
            "geometryPrecision": "6",
            "resultOffset": str(offset),
            "resultRecordCount": str(max_record),
        }
        feat_data = fetch_json(query_url, params, timeout=timeout)
        if not feat_data:
            print(f"\n  [WARN] Empty response at offset {offset}, stopping")
            break
        batch_features = feat_data.get("features", [])
        if not batch_features:
            break
        all_features.extend(batch_features)
        offset += len(batch_features)
        print(f"    Fetched {offset}/{total} …", end="\r")
        time.sleep(0.1)  # be polite to the API

    print(f"  Layer {layer_id}: fetched {len(all_features)} features        ")
    return all_features, fields_meta, geom_type


# ─────────────────────────────────────────────────────────────────────────────
# Main load logic
# ─────────────────────────────────────────────────────────────────────────────

def load_layer(
    conn: psycopg2.extensions.connection,
    service_url: str,
    layer_id: int,
    table_name: str,
    schema: str,
    batch_size: int,
    do_truncate: bool,
    dry_run: bool,
    timeout: int,
) -> int:
    """Fetch and load one FeatureServer layer. Returns number of rows inserted."""

    print(f"\n{'─' * 60}")
    print(f"Layer {layer_id} → {schema}.{table_name}")
    print(f"{'─' * 60}")

    # Fetch layer metadata + features
    layer_url = f"{service_url}/{layer_id}"
    meta = fetch_json(layer_url, timeout=timeout)
    if not meta:
        print("  [SKIP] Could not fetch layer metadata")
        return 0

    geom_type: str | None = meta.get("geometryType")
    fields: list[dict] = [
        f for f in meta.get("fields", [])
        if f.get("type") != "esriFieldTypeGeometry"
    ]
    spatial_ref = meta.get("extent", {}).get("spatialReference") or meta.get(
        "spatialReference"
    )
    srid = detect_srid(spatial_ref)

    print(f"  Geometry type : {geom_type or 'none (table only)'}")
    print(f"  SRID          : {srid}")
    print(f"  Fields        : {len(fields)}")

    # DDL
    ddl = build_create_table_sql(table_name, schema, fields, geom_type, srid)
    if dry_run:
        print(f"\n[DRY RUN] DDL:\n{ddl}")
    else:
        with conn.cursor() as cur:
            if do_truncate:
                # DROP + recreate ensures schema/SRID changes are picked up
                cur.execute(f'DROP TABLE IF EXISTS {schema}."{table_name}";')
            cur.execute(ddl)
        conn.commit()
        print(f"  ✓ Table {schema}.{table_name} {'recreated' if do_truncate else 'created/verified'}")

    # Fetch features
    features, fields_meta, _ = fetch_all_features(
        service_url, layer_id, batch_size, timeout
    )

    if not features:
        print("  No features to load")
        return 0

    if dry_run:
        print(f"[DRY RUN] Would insert {len(features)} rows into {schema}.{table_name}")
        return len(features)

    # Build column list (skip geometry-type fields)
    attr_cols = [
        f["name"] for f in fields
        if FIELD_TYPE_MAP.get(f["type"]) is not None
    ]
    col_names_sql = (
        '"source_objectid", '
        + ", ".join(f'"{c.lower()}"' for c in attr_cols)
    )

    # Build geometry placeholder – WKT passed as %s parameter, SRIDs are integers
    if geom_type:
        col_names_sql += ', "geometry"'
        if srid != 4326:
            geom_placeholder = f"ST_Transform(ST_GeomFromText(%s, {srid}), 4326)"
        else:
            geom_placeholder = "ST_GeomFromText(%s, 4326)"
        attr_placeholders = ["%s"] * (1 + len(attr_cols))
        placeholders = ", ".join(attr_placeholders) + f", {geom_placeholder}"
    else:
        placeholders = ", ".join(["%s"] * (1 + len(attr_cols)))

    insert_sql = (
        f'INSERT INTO {schema}."{table_name}" ({col_names_sql}) '
        f"VALUES ({placeholders}) ON CONFLICT DO NOTHING;"
    )

    oid_field = meta.get("objectIdField", "OBJECTID")
    rows_inserted = 0

    with conn.cursor() as cur:
        for feat in features:
            attrs = feat.get("attributes", {})
            geom = feat.get("geometry")

            row: list[Any] = [attrs.get(oid_field)]
            for col in attr_cols:
                row.append(attrs.get(col))

            if geom_type:
                wkt = esri_geometry_to_wkt(geom, geom_type)
                row.append(wkt)  # None or WKT string; ST_GeomFromText handles None gracefully

            cur.execute(insert_sql, row)
            rows_inserted += 1

    conn.commit()
    print(f"  ✓ Inserted {rows_inserted} rows")

    # Spatial index
    if geom_type and not dry_run:
        create_spatial_index(conn, schema, table_name)
        print(f"  ✓ Spatial index created")

    return rows_inserted


def run(args: argparse.Namespace) -> None:
    schema = args.schema

    # Resolve service URL
    service_urls = [args.service_url] if args.service_url else DEFAULT_SERVICE_URLS
    service_url: str | None = None

    print("=" * 70)
    print("AFRIP Flood Data Loader")
    print("=" * 70)
    print(f"Target: {schema} schema on {DB_HOST}:{DB_PORT}/{DB_NAME}")
    print()

    print("Probing service endpoints …")
    for url in service_urls:
        print(f"  → {url}")
        meta = probe_feature_server(url, args.timeout)
        if meta:
            service_url = url
            layers_info = meta.get("layers", []) + meta.get("tables", [])
            print(f"  ✓ Reachable – {len(layers_info)} layer(s) available")
            for lyr in layers_info:
                print(f"      Layer {lyr['id']:>3} : {lyr.get('name', 'unnamed')}")
            break
        print("  ✗ Not reachable")

    if not service_url:
        print(
            "\n[ERROR] No AFRIP service endpoints are reachable.\n"
            "Run discover_afrip_services.py first, or supply --service-url.\n"
            "The service may require authentication or the URL may have changed."
        )
        sys.exit(1)

    # Connect to database
    if not args.dry_run:
        print("\nConnecting to database …")
        try:
            conn = get_db_connection()
            ensure_postgis(conn)
        except psycopg2.Error as exc:
            print(f"[DB ERROR] {exc}")
            sys.exit(1)
    else:
        conn = None  # type: ignore[assignment]
        print("[DRY RUN] Skipping database connection")

    # Determine which layers to process
    meta = probe_feature_server(service_url, args.timeout)
    available_layers = {
        lyr["id"]: lyr.get("name", f"layer_{lyr['id']}")
        for lyr in (meta.get("layers", []) + meta.get("tables", []))
    }

    if args.layer_id is not None:
        target_layers = {args.layer_id: available_layers.get(args.layer_id, f"layer_{args.layer_id}")}
    else:
        target_layers = available_layers

    total_rows = 0
    for layer_id, layer_name in sorted(target_layers.items()):
        # Determine table name: use manifest mapping, else derive from layer name
        table_name = LAYER_TABLE_MAP.get(
            layer_id,
            f"afrip_{layer_name.lower().replace(' ', '_').replace('-', '_')}",
        )

        rows = load_layer(
            conn=conn,
            service_url=service_url,
            layer_id=layer_id,
            table_name=table_name,
            schema=schema,
            batch_size=args.batch_size,
            do_truncate=args.truncate,
            dry_run=args.dry_run,
            timeout=args.timeout,
        )
        total_rows += rows

    # Optionally load the S3 attachments lookup table
    if args.load_attachments:
        print(f"\nProbing attachments service …")
        print(f"  → {ATTACHMENTS_SERVICE_URL}")
        att_meta = probe_feature_server(ATTACHMENTS_SERVICE_URL, args.timeout)
        if att_meta:
            att_layers = {t["id"]: t.get("name", f"table_{t['id']}")
                          for t in (att_meta.get("layers", []) + att_meta.get("tables", []))}
            print(f"  ✓ Reachable – {len(att_layers)} table(s)")
            for tid, tname in sorted(att_layers.items()):
                att_table = ATTACHMENTS_LAYER_TABLE_MAP.get(
                    tid,
                    f"afrip_{tname.lower().replace(' ', '_').replace('-', '_')}",
                )
                rows = load_layer(
                    conn=conn,
                    service_url=ATTACHMENTS_SERVICE_URL,
                    layer_id=tid,
                    table_name=att_table,
                    schema=schema,
                    batch_size=args.batch_size,
                    do_truncate=args.truncate,
                    dry_run=args.dry_run,
                    timeout=args.timeout,
                )
                total_rows += rows
        else:
            print("  ✗ Attachments service not reachable – skipping")

    print(f"\n{'=' * 70}")
    print(f"Load complete. Total rows loaded: {total_rows}")
    print(f"{'=' * 70}")

    if conn:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--service-url",
        default=None,
        help="ArcGIS FeatureServer base URL (e.g. https://services.ga.gov.au/…/FeatureServer)",
    )
    parser.add_argument(
        "--layer-id",
        type=int,
        default=None,
        help="Load only this layer ID (default: all layers)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Records per API page request (default: 1000)",
    )
    parser.add_argument(
        "--schema",
        default="public",
        help="Target PostgreSQL schema (default: public)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without writing to the database",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="TRUNCATE tables before loading (default: append / upsert)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="HTTP timeout in seconds (default: 60)",
    )
    parser.add_argument(
        "--load-attachments",
        action="store_true",
        help="Also load the Flood_Attachments_S3 lookup table into afrip_flood_attachments",
    )
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
