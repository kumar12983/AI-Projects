#!/usr/bin/env python3
"""
Verify and query AFRIP flood data loaded into PostgreSQL public schema

Usage:
    python verify_afrip_data.py [--schema public] [--address "123 Main St, Sydney NSW"]

This script:
  1. Reports row counts and coverage stats for each AFRIP table
  2. Checks spatial index presence
  3. Optionally queries which flood studies cover a given address/coordinate
"""

import argparse
import os
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

_here = Path(__file__).resolve().parent
load_dotenv(_here.parent / "webapp" / ".env")
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "gnaf_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

AFRIP_TABLES = [
    "afrip_flood_studies",       # point layer – one record per flood study
    "afrip_flood_attachments",   # non-spatial table – S3 links for each study
]


def get_conn():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT,
        database=DB_NAME, user=DB_USER, password=DB_PASSWORD,
    )


def table_exists(cur, schema: str, table: str) -> bool:
    cur.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = %s AND table_name = %s",
        (schema, table),
    )
    return cur.fetchone() is not None


def check_spatial_index(cur, schema: str, table: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM pg_indexes
        WHERE schemaname = %s
          AND tablename  = %s
          AND indexdef   LIKE '%%USING gist%%'
        LIMIT 1
        """,
        (schema, table),
    )
    return cur.fetchone() is not None


def print_table_stats(cur, schema: str, table: str) -> None:
    cur.execute(f'SELECT COUNT(*) FROM {schema}."{table}"')
    count = cur.fetchone()[0]

    has_geom = False
    cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s AND column_name = 'geometry'",
        (schema, table),
    )
    if cur.fetchone():
        has_geom = True

    idx = "✓" if check_spatial_index(cur, schema, table) else "✗"
    loaded_at = ""
    cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s AND column_name = 'loaded_at'",
        (schema, table),
    )
    if cur.fetchone():
        cur.execute(f'SELECT MAX(loaded_at) FROM {schema}."{table}"')
        row = cur.fetchone()
        if row and row[0]:
            loaded_at = f"  last_loaded={row[0].strftime('%Y-%m-%d %H:%M UTC')}"

    bbox = ""
    if has_geom and count > 0:
        cur.execute(
            f"""
            SELECT
                ROUND(ST_XMin(ST_Extent(geometry))::numeric, 4),
                ROUND(ST_YMin(ST_Extent(geometry))::numeric, 4),
                ROUND(ST_XMax(ST_Extent(geometry))::numeric, 4),
                ROUND(ST_YMax(ST_Extent(geometry))::numeric, 4)
            FROM {schema}."{table}"
            """
        )
        row = cur.fetchone()
        if row and row[0] is not None:
            bbox = f"  bbox=({row[0]},{row[1]}) → ({row[2]},{row[3]})"

    geom_icon = "🗺" if has_geom else "📋"
    spatial_idx = f"  spatial_idx={idx}" if has_geom else ""
    print(
        f"  {geom_icon} {schema}.{table:<40} "
        f"rows={count:<8}{spatial_idx}{bbox}{loaded_at}"
    )


def query_flood_studies_for_point(
    cur,
    schema: str,
    lon: float,
    lat: float,
) -> list[dict]:
    """Find which flood studies are nearest to the given coordinate (point layer)."""
    results = []
    table = "afrip_flood_studies"
    if not table_exists(cur, schema, table):
        return results
    cur.execute(
        f"""
        SELECT *, ST_Distance(
            geometry::geography,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
        ) AS distance_m
        FROM {schema}."{table}"
        ORDER BY geometry <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
        LIMIT 5
        """,
        (lon, lat, lon, lat),
    )
    cols = [desc[0] for desc in cur.description]
    for row in cur.fetchall():
        rec = dict(zip(cols, row))
        rec.pop("geometry", None)
        rec["_source_table"] = table
        results.append(rec)
    return results


def run(args: argparse.Namespace) -> None:
    schema = args.schema

    print("=" * 70)
    print("AFRIP Flood Data Verification")
    print("=" * 70)
    print(f"Database : {DB_HOST}:{DB_PORT}/{DB_NAME}")
    print(f"Schema   : {schema}")
    print()

    try:
        conn = get_conn()
    except psycopg2.Error as exc:
        print(f"[DB ERROR] {exc}")
        sys.exit(1)

    with conn.cursor() as cur:
        print("Table statistics:")
        print("-" * 70)
        any_found = False
        for table in AFRIP_TABLES:
            if table_exists(cur, schema, table):
                print_table_stats(cur, schema, table)
                any_found = True
            else:
                print(f"  ✗ {schema}.{table:<44} (not found)")

        if not any_found:
            print()
            print("No AFRIP tables found. Run load_afrip_flood_data.py first.")
            conn.close()
            return

        # Optional point-in-polygon query
        if args.lon is not None and args.lat is not None:
            print()
            print(f"Flood studies at ({args.lon}, {args.lat}):")
            print("-" * 70)
            results = query_flood_studies_for_point(cur, schema, args.lon, args.lat)
            if results:
                for rec in results:
                    src = rec.pop("_source_table", "")
                    print(f"  [{src}]")
                    for k, v in rec.items():
                        if v is not None:
                            print(f"    {k}: {v}")
                    print()
            else:
                print("  No flood studies found for this coordinate.")

        # Summary query: most recent studies loaded
        print()
        print("Sample data (first 5 rows from afrip_flood_studies):")
        print("-" * 70)
        if table_exists(cur, schema, "afrip_flood_studies"):
            cur.execute(
                f"""
                SELECT source_objectid,
                       loaded_at,
                       ST_AsText(ST_Centroid(geometry)) AS centroid
                FROM {schema}."afrip_flood_studies"
                ORDER BY source_objectid
                LIMIT 5
                """
            )
            rows = cur.fetchall()
            if rows:
                for row in rows:
                    print(f"  OID={row[0]}  loaded={row[1]}  centroid={row[2]}")
            else:
                print("  (empty table)")

    conn.close()
    print()
    print("Verification complete.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--schema", default="public")
    parser.add_argument("--lon", type=float, default=None, help="Longitude for point query")
    parser.add_argument("--lat", type=float, default=None, help="Latitude for point query")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
