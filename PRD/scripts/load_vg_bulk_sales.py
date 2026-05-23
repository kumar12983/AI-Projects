#!/usr/bin/env python3
"""
Load NSW Valuer General Bulk Property Sales data into PostgreSQL.

Source: NSW Valuer General Property Sales Information (PSI)
  Yearly:  https://www.valuergeneral.nsw.gov.au/__psi/yearly/YYYY.zip   (1990 – prev year)
  Weekly:  https://www.valuergeneral.nsw.gov.au/__psi/weekly/YYYYMMDD.zip (current year)

Data format:
  .zip → (optional inner .zip) → .dat files (semicolon-delimited)
  Record B = the sale record (purchase price, address, dates)
  Two sub-formats identified by a heuristic on parts[2]:
    Current  (2001+)    : B;district;propid(numeric);counter;...  → 25+ fields
    Archived (1990-2001): B;district;source(alpha);...            → 15+ fields

Tables created / maintained:
  public.nsw_vg_sales_history  – All VG bulk sale records (insert-only, ON CONFLICT DO NOTHING)
  public.gnaf_vg_sale_link     – Bridge: address_detail_pid → most recent sale
                                  Used by app.py as a simple LEFT JOIN in place of the
                                  spatial LATERAL join against nsw_property_sales.
  public.nsw_property_load_log – ETL audit log (shared with ArcGIS loader)

GNAF matching strategy (bridge table rebuild):
  Joins nsw_vg_sales_history to gnaf.address_detail on:
    1. postcode (integer cast)
    2. unit_number  = GNAF flat_number   (blank VG unit ↔ NULL GNAF flat_number)
    3. house_number leading digits       = GNAF number_first
    4. house_number alpha suffix (e.g. 'A' in '14A') = GNAF number_first_suffix
    5. street_name ILIKE GNAF street_name || ' %'     (VG includes type: 'KIRKHAM STREET')
    6. locality    ILIKE GNAF locality_name
  Picks the most recent sale per address_detail_pid via DISTINCT ON + ORDER BY contract_date DESC.

Usage:
    python load_vg_bulk_sales.py                      # download + load default postcodes
    python load_vg_bulk_sales.py --postcodes 2077 2119 2148
    python load_vg_bulk_sales.py --all-postcodes      # load + bridge for all of NSW
    python load_vg_bulk_sales.py --skip-download      # use existing files in --data-dir
    python load_vg_bulk_sales.py --skip-weekly        # yearly files only (no current-year weekly)
    python load_vg_bulk_sales.py --no-bridge          # skip bridge table rebuild
    python load_vg_bulk_sales.py --truncate           # drop + recreate tables before loading
    python load_vg_bulk_sales.py --dry-run            # parse + print sample, no DB writes
    python load_vg_bulk_sales.py --start-year 2000    # only load data from 2000 onward

Environment variables (read from webapp/.env or local .env):
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
"""

import argparse
import io
import os
import sys
import time
import urllib.request
import urllib.error
import zipfile
from datetime import date, timedelta
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────────────────────
# Environment / DB config
# ─────────────────────────────────────────────────────────────────────────────
_here = Path(__file__).resolve().parent
load_dotenv(_here.parent / ".env")          # PRD/.env
load_dotenv(_here.parent / "webapp" / ".env")  # PRD/webapp/.env (fallback)
load_dotenv()                               # local .env (fallback)

DB_HOST     = os.getenv("DB_HOST",     "localhost")
DB_PORT     = os.getenv("DB_PORT",     "5432")
DB_NAME     = os.getenv("DB_NAME",     "gnaf_db")
DB_USER     = os.getenv("DB_USER",     "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# ─────────────────────────────────────────────────────────────────────────────
# VG PSI download constants
# ─────────────────────────────────────────────────────────────────────────────
VG_BASE_URL   = "https://www.valuergeneral.nsw.gov.au/__psi/"
VG_YEARLY_URL = VG_BASE_URL + "yearly/"
VG_WEEKLY_URL = VG_BASE_URL + "weekly/"

DEFAULT_POSTCODES   = {2077, 2119, 2125, 2120, 2076}
RETRY_ATTEMPTS      = 3
RETRY_DELAY_SECS    = 5
# Exclude the most recent N days of weekly files (VG typically takes 2–3 weeks to publish)
WEEKLY_PUBLISH_LAG  = 21


# ─────────────────────────────────────────────────────────────────────────────
# Database helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_conn():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME,
        user=DB_USER, password=DB_PASSWORD,
    )


def create_tables(conn, truncate: bool) -> None:
    """Create or verify all required tables. With --truncate: drop and recreate."""
    tables_to_drop = ["nsw_vg_sales_history", "gnaf_vg_sale_link"]

    ddl_statements = [
        # ── Shared ETL audit log (also used by load_nsw_property_data.py) ──
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

        # ── VG bulk sales history — insert-only, all postcodes ──────────────
        #   UNIQUE(district_code, property_id, contract_date, purchase_price)
        #   Covers both current (has dealing_number) and archived (no dealing_number).
        #   Records with the same propid / contract_date / price are idempotent.
        """\
CREATE TABLE IF NOT EXISTS public.nsw_vg_sales_history (
    id                 SERIAL PRIMARY KEY,
    district_code      TEXT,
    property_id        TEXT,
    sale_counter       TEXT,
    unit_number        TEXT,
    house_number       TEXT,
    street_name        TEXT,
    locality           TEXT,
    postcode           INTEGER,
    contract_date      DATE,
    settlement_date    DATE,
    purchase_price     BIGINT,
    area               DOUBLE PRECISION,
    area_type          TEXT,       -- 'M' = sqm, 'H' = hectares
    zoning             TEXT,
    nature_of_property TEXT,
    primary_purpose    TEXT,
    strata_lot_number  TEXT,
    dealing_number     TEXT,       -- Land Registry dealing (current format only)
    legal_description  TEXT,
    data_format        TEXT,       -- 'current' | 'archived'
    loaded_at          TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_nsw_vg_sales UNIQUE (district_code, property_id, contract_date, purchase_price)
);""",

        # ── Bridge table — GNAF address_detail_pid → most recent VG sale ───
        #   Rebuilt after every load run (or manually with --no-bridge skip).
        #   app.py uses:  LEFT JOIN public.gnaf_vg_sale_link gvl
        #                   ON gvl.address_detail_pid = ad.address_detail_pid
        """\
CREATE TABLE IF NOT EXISTS public.gnaf_vg_sale_link (
    address_detail_pid  TEXT PRIMARY KEY,
    purchase_price      BIGINT,
    contract_date       DATE,
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);""",
    ]

    index_statements = [
        "CREATE INDEX IF NOT EXISTS nsw_vg_sales_postcode_idx  ON public.nsw_vg_sales_history (postcode);",
        "CREATE INDEX IF NOT EXISTS nsw_vg_sales_date_idx      ON public.nsw_vg_sales_history (contract_date DESC);",
        "CREATE INDEX IF NOT EXISTS nsw_vg_sales_address_idx   ON public.nsw_vg_sales_history (postcode, house_number, street_name);",
        "CREATE INDEX IF NOT EXISTS nsw_vg_sales_propid_idx    ON public.nsw_vg_sales_history (district_code, property_id);",
    ]

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


def write_load_log(conn, layer_name: str, where_clause: str,
                   rows_inserted: int, rows_skipped: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """\
INSERT INTO public.nsw_property_load_log
    (layer_name, where_clause, max_oid_loaded, rows_inserted, rows_updated, rows_skipped)
VALUES (%s, %s, NULL, %s, 0, %s)""",
            (layer_name, where_clause, rows_inserted, rows_skipped),
        )
    conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Download helpers
# ─────────────────────────────────────────────────────────────────────────────

def download_file(url: str, filepath: str, timeout: int) -> bool:
    """Download url → filepath with retry. Returns True on success, False on 404."""
    for attempt in range(RETRY_ATTEMPTS):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0 (NSWVGLoader/1.0)"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp, \
                 open(filepath, "wb") as out:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    out.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded * 100 // total
                        print(
                            f"    {downloaded // 1024:,} KB / {total // 1024:,} KB ({pct}%)  ",
                            end="\r", flush=True,
                        )
            print()
            return True
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return False          # file doesn't exist on server — not a transient error
            print(f"  [HTTP {exc.code}] {url} (attempt {attempt + 1}/{RETRY_ATTEMPTS})")
        except Exception as exc:
            print(f"  [ERR] {exc} (attempt {attempt + 1}/{RETRY_ATTEMPTS})")
        if attempt < RETRY_ATTEMPTS - 1:
            time.sleep(RETRY_DELAY_SECS)
    return False


def weekly_dates_for_current_year() -> list[date]:
    """
    Return all weekly file dates for the current year.
    VG weekly files are dated by the Monday of each week.
    Excludes dates within WEEKLY_PUBLISH_LAG days of today (not yet published).
    """
    today = date.today()
    # First Monday on or after Jan 7 (skips partial first week)
    jan7 = date(today.year, 1, 7)
    first_monday = jan7 - timedelta(days=jan7.weekday())
    cutoff = today - timedelta(days=WEEKLY_PUBLISH_LAG)
    dates = []
    current = first_monday
    while current < cutoff:
        dates.append(current)
        current += timedelta(days=7)
    return dates


def download_data(
    data_dir: str,
    start_year: int,
    skip_weekly: bool,
    timeout: int,
) -> list[str]:
    """
    Download yearly (start_year → last year) and weekly (current year) zip files.
    Files already on disk are skipped.  Returns list of available zip file paths.
    """
    os.makedirs(data_dir, exist_ok=True)
    available: list[str] = []
    today = date.today()

    # ── Yearly files ─────────────────────────────────────────────────────────
    print(f"\nDownloading yearly files ({start_year} – {today.year - 1})...")
    for year in range(start_year, today.year):
        filename = f"{year}.zip"
        filepath = os.path.join(data_dir, filename)
        if os.path.exists(filepath):
            print(f"  {filename}  (already on disk)")
            available.append(filepath)
            continue
        url = VG_YEARLY_URL + filename
        print(f"  Downloading {url} ...")
        if download_file(url, filepath, timeout):
            print(f"  ✓ {filename}")
            available.append(filepath)
        else:
            print(f"  ✗ {filename}  (not available — skipping)")

    # ── Weekly files (current year) ──────────────────────────────────────────
    if not skip_weekly:
        weekly = weekly_dates_for_current_year()
        print(f"\nDownloading {len(weekly)} weekly files for {today.year}...")
        for d in weekly:
            filename = d.strftime("%Y%m%d") + ".zip"
            filepath = os.path.join(data_dir, filename)
            if os.path.exists(filepath):
                available.append(filepath)
                continue
            url = VG_WEEKLY_URL + filename
            print(f"  Downloading {url} ...", end=" ", flush=True)
            if download_file(url, filepath, timeout):
                print(f"✓ {filename}")
                available.append(filepath)
            else:
                print(f"✗ (not available)")

    print(f"\n✓ {len(available)} zip files available for processing")
    return available


# ─────────────────────────────────────────────────────────────────────────────
# Record-B parsing — current (2001+) and archived (1990-2001) formats
# ─────────────────────────────────────────────────────────────────────────────

def _parse_date_current(s: str) -> "date | None":
    """Parse CCYYMMDD string → date.  Returns None on any error."""
    s = s.strip()
    if len(s) != 8 or not s.isdigit():
        return None
    try:
        return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    except ValueError:
        return None


def _parse_date_archived(s: str) -> "date | None":
    """Parse DD/MM/YYYY string → date.  Returns None on any error."""
    s = s.strip()
    if len(s) != 10 or s[2] != "/" or s[5] != "/":
        return None
    try:
        return date(int(s[6:10]), int(s[3:5]), int(s[0:2]))
    except ValueError:
        return None


def _parse_price(s: str) -> "int | None":
    """Convert price string to positive integer.  Returns None if invalid or zero."""
    try:
        v = int(s.strip().replace(",", "").replace("$", ""))
        return v if v > 0 else None
    except (ValueError, TypeError):
        return None


def _parse_area(s: str) -> "float | None":
    """Convert area string to float.  Returns None if blank / invalid."""
    s = s.strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _parse_postcode(s: str) -> "int | None":
    """Parse postcode string to integer.  Returns None if invalid."""
    try:
        return int(s.strip())
    except (ValueError, TypeError):
        return None


def parse_current_record(parts: list[str]) -> "dict | None":
    """
    Parse a B; record in current format (2001+).
    Field positions from 'Current Property Sales Data File Format 2001 to Current':
      [1]  district_code   [2]  property_id     [3]  sale_counter
      [4]  download_dt     [5]  property_name   [6]  unit_number
      [7]  house_number    [8]  street_name     [9]  locality
      [10] postcode        [11] area            [12] area_type
      [13] contract_date   [14] settlement_date [15] purchase_price
      [16] zoning          [17] nature_of_property [18] primary_purpose
      [19] strata_lot_no   [23] dealing_number
    Returns None if fewer than 24 fields or purchase_price is missing / zero.
    """
    if len(parts) < 24:
        return None
    price = _parse_price(parts[15])
    if price is None:
        return None
    postcode = _parse_postcode(parts[10])
    if postcode is None:
        return None
    return {
        "district_code":       parts[1].strip(),
        "property_id":         parts[2].strip(),
        "sale_counter":        parts[3].strip() or None,
        "unit_number":         parts[6].strip() or None,
        "house_number":        parts[7].strip() or None,
        "street_name":         parts[8].strip().upper() or None,
        "locality":            parts[9].strip().upper() or None,
        "postcode":            postcode,
        "contract_date":       _parse_date_current(parts[13]),
        "settlement_date":     _parse_date_current(parts[14]),
        "purchase_price":      price,
        "area":                _parse_area(parts[11]),
        "area_type":           parts[12].strip() or None,
        "zoning":              parts[16].strip() or None,
        "nature_of_property":  parts[17].strip() or None,
        "primary_purpose":     parts[18].strip() or None,
        "strata_lot_number":   parts[19].strip() or None,
        "dealing_number":      parts[23].strip() or None,
        "legal_description":   None,
        "data_format":         "current",
    }


def parse_archived_record(parts: list[str]) -> "dict | None":
    """
    Parse a B; record in archived format (1990-2001).
    Field positions from 'Archived Property Sales Data File Format 1990 to 2001':
      [1]  district_code   [4]  property_id     [5]  unit_number
      [6]  house_number    [7]  street_name     [8]  locality
      [9]  postcode        [10] contract_date (DD/MM/YYYY)
      [11] purchase_price  [12] legal_description
      [13] area            [14] area_type        [17] zoning
    Returns None if fewer than 15 fields or purchase_price is missing / zero.
    """
    if len(parts) < 15:
        return None
    price = _parse_price(parts[11])
    if price is None:
        return None
    postcode = _parse_postcode(parts[9])
    if postcode is None:
        return None
    return {
        "district_code":       parts[1].strip(),
        "property_id":         parts[4].strip(),
        "sale_counter":        None,
        "unit_number":         parts[5].strip() or None,
        "house_number":        parts[6].strip() or None,
        "street_name":         parts[7].strip().upper() or None,
        "locality":            parts[8].strip().upper() or None,
        "postcode":            postcode,
        "contract_date":       _parse_date_archived(parts[10]),
        "settlement_date":     None,
        "purchase_price":      price,
        "area":                _parse_area(parts[13]),
        "area_type":           parts[14].strip() or None,
        "zoning":              parts[17].strip() if len(parts) > 17 else None,
        "nature_of_property":  None,
        "primary_purpose":     None,
        "strata_lot_number":   None,
        "dealing_number":      None,
        "legal_description":   parts[12].strip() or None,
        "data_format":         "archived",
    }


def _process_dat_lines(lines: list[str], target_postcodes: set[int] | None) -> list[dict]:
    """Parse B; lines from a .dat file and return records matching target_postcodes.
    Pass target_postcodes=None to accept all NSW postcodes.
    """
    records: list[dict] = []
    for line in lines:
        if not line.startswith("B;"):
            continue
        parts = [p.strip() for p in line.split(";")]
        if len(parts) < 10:
            continue
        # Heuristic: archived format has an alpha source code in parts[2]
        # (e.g. 'ARCHIVE', 'VALNET1'). Current format has a numeric property ID there.
        is_archived = len(parts) > 2 and parts[2].replace(" ", "").isalpha()
        record = parse_archived_record(parts) if is_archived else parse_current_record(parts)
        if record is None:
            continue
        if target_postcodes is not None and record["postcode"] not in target_postcodes:
            continue
        records.append(record)
    return records


def extract_and_parse(
    zip_filepath: str,
    target_postcodes: set[int] | None,
    dry_run: bool = False,
) -> list[dict]:
    """
    Extract .dat files from a (possibly nested) zip archive and parse Record B entries.
    Pass target_postcodes=None to accept all NSW postcodes.
    With dry_run=True: stops after finding the first batch of matching records.
    """
    records: list[dict] = []

    def read_dat(content_bytes: bytes) -> None:
        try:
            text = content_bytes.decode("utf-8", errors="replace")
        except Exception:
            return
        new = _process_dat_lines(text.splitlines(), target_postcodes)
        records.extend(new)

    try:
        with zipfile.ZipFile(zip_filepath, "r") as outer:
            for name in outer.namelist():
                if name.lower().endswith(".dat"):
                    with outer.open(name) as f:
                        read_dat(f.read())
                    if dry_run and records:
                        return records
                elif name.lower().endswith(".zip"):
                    # Nested zip (yearly archives have this structure)
                    with outer.open(name) as inner_bytes:
                        with zipfile.ZipFile(io.BytesIO(inner_bytes.read())) as inner:
                            for inner_name in inner.namelist():
                                if inner_name.lower().endswith(".dat"):
                                    with inner.open(inner_name) as f:
                                        read_dat(f.read())
                                    if dry_run and records:
                                        return records
    except zipfile.BadZipFile:
        print(f"  [WARN] Bad zip file: {zip_filepath}")
    except FileNotFoundError:
        print(f"  [WARN] File not found: {zip_filepath}")

    return records


# ─────────────────────────────────────────────────────────────────────────────
# Database insert
# ─────────────────────────────────────────────────────────────────────────────

_INSERT_SQL = """\
INSERT INTO public.nsw_vg_sales_history (
    district_code, property_id, sale_counter,
    unit_number, house_number, street_name, locality, postcode,
    contract_date, settlement_date, purchase_price,
    area, area_type, zoning, nature_of_property, primary_purpose,
    strata_lot_number, dealing_number, legal_description, data_format,
    loaded_at
) VALUES (
    %(district_code)s, %(property_id)s, %(sale_counter)s,
    %(unit_number)s, %(house_number)s, %(street_name)s, %(locality)s, %(postcode)s,
    %(contract_date)s, %(settlement_date)s, %(purchase_price)s,
    %(area)s, %(area_type)s, %(zoning)s, %(nature_of_property)s, %(primary_purpose)s,
    %(strata_lot_number)s, %(dealing_number)s, %(legal_description)s, %(data_format)s,
    NOW()
)
ON CONFLICT (district_code, property_id, contract_date, purchase_price) DO NOTHING"""


def load_records_to_db(
    conn,
    records: list[dict],
    batch_size: int,
) -> tuple[int, int]:
    """
    Batch-insert records into nsw_vg_sales_history.
    Commits every batch_size records.
    Returns (inserted, skipped_duplicate) counts.
    """
    inserted = skipped = 0
    with conn.cursor() as cur:
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            for row in batch:
                cur.execute(_INSERT_SQL, row)
                if cur.rowcount == 1:
                    inserted += 1
                else:
                    skipped += 1
            conn.commit()
    return inserted, skipped


# ─────────────────────────────────────────────────────────────────────────────
# Bridge table rebuild
# ─────────────────────────────────────────────────────────────────────────────

# Note on %% escaping: psycopg2 requires literal % characters to be written as %%
# even when no query parameters are passed (i.e. cur.execute(sql) with no vars tuple).

# Used when specific postcodes are supplied (filters both VG and GNAF tables for speed)
_BRIDGE_REBUILD_SQL = """\
INSERT INTO public.gnaf_vg_sale_link (address_detail_pid, purchase_price, contract_date, vg_district_code, vg_property_id)
SELECT DISTINCT ON (ad.address_detail_pid)
    ad.address_detail_pid,
    vg.purchase_price,
    vg.contract_date,
    vg.district_code,
    vg.property_id
FROM public.nsw_vg_sales_history vg
JOIN gnaf.address_detail ad
    -- Postcode: nsw_vg_sales_history.postcode is INTEGER; gnaf.address_detail.postcode is TEXT
    ON  ad.postcode = vg.postcode::text
    -- Unit number: blank/NULL VG unit_number matches NULL GNAF flat_number (non-unit)
    AND COALESCE(NULLIF(TRIM(COALESCE(vg.unit_number, '')), ''), '') = COALESCE(ad.flat_number::text, '')
    -- House number: strip range/suffix to get leading numeric part
    --   '53A' → '53',  '53-57' → '53',  '53' → '53'
    AND regexp_replace(COALESCE(vg.house_number, ''), '[^0-9].*', '') = ad.number_first::text
    -- Alpha suffix: '14A' → 'A',  '14 A' → 'A',  '14' → '',  '53-57' → ''
    -- Strip internal whitespace first so '11 B' → '11B' before suffix extraction
    AND UPPER(COALESCE(NULLIF(regexp_replace(regexp_replace(COALESCE(vg.house_number, ''), '\\s+', ''), '^[0-9]+([A-Za-z]?).*', '\\1'), ''), ''))
          = UPPER(COALESCE(ad.number_first_suffix, ''))
JOIN gnaf.street_locality sl
    ON  sl.street_locality_pid = ad.street_locality_pid
    -- VG street_name includes type ('KIRKHAM STREET'); GNAF street_name is base name ('KIRKHAM')
    -- Also allow exact match for streets where the type is embedded in the name (e.g. 'THE CRESCENT')
    AND (vg.street_name ILIKE sl.street_name || ' %%' OR vg.street_name ILIKE sl.street_name)
JOIN gnaf.locality loc
    ON  loc.locality_pid = ad.locality_pid
    AND loc.locality_name ILIKE vg.locality
WHERE vg.purchase_price > 0
  AND vg.contract_date IS NOT NULL
  AND vg.house_number  IS NOT NULL
  AND vg.street_name   IS NOT NULL
  AND vg.postcode = ANY(%(postcodes)s)
  -- Explicit postcode filter on GNAF side prevents full 7M-row table scan;
  -- forces the planner to use the postcode index and limit GNAF to ~62K rows.
  AND ad.postcode = ANY(%(postcodes_text)s)
  AND ad.date_retired  IS NULL
  AND sl.date_retired  IS NULL
  AND loc.date_retired IS NULL
ORDER BY ad.address_detail_pid, vg.contract_date DESC NULLS LAST
ON CONFLICT (address_detail_pid) DO UPDATE
    SET purchase_price    = EXCLUDED.purchase_price,
        contract_date     = EXCLUDED.contract_date,
        vg_district_code  = EXCLUDED.vg_district_code,
        vg_property_id    = EXCLUDED.vg_property_id,
        updated_at        = NOW()
    WHERE EXCLUDED.contract_date > public.gnaf_vg_sale_link.contract_date
       OR public.gnaf_vg_sale_link.contract_date IS NULL"""

# Used with --all-postcodes: no postcode filter, full NSW join
_BRIDGE_REBUILD_SQL_ALL = """\
INSERT INTO public.gnaf_vg_sale_link (address_detail_pid, purchase_price, contract_date, vg_district_code, vg_property_id)
SELECT DISTINCT ON (ad.address_detail_pid)
    ad.address_detail_pid,
    vg.purchase_price,
    vg.contract_date,
    vg.district_code,
    vg.property_id
FROM public.nsw_vg_sales_history vg
JOIN gnaf.address_detail ad
    ON  ad.postcode = vg.postcode::text
    AND COALESCE(NULLIF(TRIM(COALESCE(vg.unit_number, '')), ''), '') = COALESCE(ad.flat_number::text, '')
    AND regexp_replace(COALESCE(vg.house_number, ''), '[^0-9].*', '') = ad.number_first::text
    AND UPPER(COALESCE(NULLIF(regexp_replace(regexp_replace(COALESCE(vg.house_number, ''), '\\s+', ''), '^[0-9]+([A-Za-z]?).*', '\\1'), ''), ''))
          = UPPER(COALESCE(ad.number_first_suffix, ''))
JOIN gnaf.street_locality sl
    ON  sl.street_locality_pid = ad.street_locality_pid
    AND (vg.street_name ILIKE sl.street_name || ' %%' OR vg.street_name ILIKE sl.street_name)
JOIN gnaf.locality loc
    ON  loc.locality_pid = ad.locality_pid
    AND loc.locality_name ILIKE vg.locality
WHERE vg.purchase_price > 0
  AND vg.contract_date IS NOT NULL
  AND vg.house_number  IS NOT NULL
  AND vg.street_name   IS NOT NULL
  AND ad.date_retired  IS NULL
  AND sl.date_retired  IS NULL
  AND loc.date_retired IS NULL
ORDER BY ad.address_detail_pid, vg.contract_date DESC NULLS LAST
ON CONFLICT (address_detail_pid) DO UPDATE
    SET purchase_price    = EXCLUDED.purchase_price,
        contract_date     = EXCLUDED.contract_date,
        vg_district_code  = EXCLUDED.vg_district_code,
        vg_property_id    = EXCLUDED.vg_property_id,
        updated_at        = NOW()
    WHERE EXCLUDED.contract_date > public.gnaf_vg_sale_link.contract_date
       OR public.gnaf_vg_sale_link.contract_date IS NULL"""


def rebuild_bridge_table(conn, postcodes: set[int] | None) -> int:
    """
    Rebuild gnaf_vg_sale_link for the given postcodes.
    Pass postcodes=None to rebuild for all of NSW.
    Picks the most recent sale per address_detail_pid.
    Returns count of rows upserted.
    """
    print(f"\n{'─' * 60}")
    print("Rebuilding gnaf_vg_sale_link bridge table...")
    if postcodes is None:
        print("  Scoped to: ALL NSW postcodes")
    else:
        print(f"  Scoped to postcodes: {sorted(postcodes)}")
    print("  Matching VG address fields to GNAF address_detail...")

    with conn.cursor() as cur:
        if postcodes is None:
            cur.execute(_BRIDGE_REBUILD_SQL_ALL)
        else:
            cur.execute(_BRIDGE_REBUILD_SQL, {
                "postcodes": list(postcodes),
                "postcodes_text": [str(p) for p in postcodes],
            })
        rows = cur.rowcount
    conn.commit()

    print(f"  ✓ Bridge table: {rows:,} rows upserted (new or updated to more recent sale)")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Load NSW Valuer General Bulk Property Sales into PostgreSQL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--postcodes", nargs="+", type=int, default=sorted(DEFAULT_POSTCODES),
        metavar="INT",
        help=f"Target postcodes to load (default: {sorted(DEFAULT_POSTCODES)})",
    )
    parser.add_argument(
        "--all-postcodes", action="store_true",
        help="Load and bridge all NSW postcodes (overrides --postcodes; no postcode filter applied)",
    )
    parser.add_argument(
        "--start-year", type=int, default=1990,
        help="Earliest yearly file to download (default: 1990)",
    )
    parser.add_argument(
        "--data-dir", default="vg_data",
        help="Directory for downloaded zip files relative to this script (default: vg_data/)",
    )
    parser.add_argument(
        "--skip-download", action="store_true",
        help="Skip downloading; process existing files in --data-dir",
    )
    parser.add_argument(
        "--skip-weekly", action="store_true",
        help="Only process yearly files, skip current-year weekly files",
    )
    parser.add_argument(
        "--no-bridge", action="store_true",
        help="Skip rebuilding the gnaf_vg_sale_link bridge table after loading",
    )
    parser.add_argument(
        "--bridge-only", action="store_true",
        help="Skip history load; only rebuild the gnaf_vg_sale_link bridge table",
    )
    parser.add_argument(
        "--truncate", action="store_true",
        help="DROP + recreate nsw_vg_sales_history and gnaf_vg_sale_link before loading",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse first available file, print sample records, no DB writes",
    )
    parser.add_argument(
        "--batch-size", type=int, default=500,
        help="DB insert batch size per commit (default: 500)",
    )
    parser.add_argument(
        "--timeout", type=int, default=120,
        help="HTTP download timeout in seconds (default: 120)",
    )
    args = parser.parse_args()

    target_postcodes = None if args.all_postcodes else set(args.postcodes)
    data_dir = os.path.join(str(_here), args.data_dir)

    print("=" * 60)
    print("NSW VG Bulk Sales Loader")
    print(f"  DB          : {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    print(f"  Postcodes   : {'ALL NSW' if target_postcodes is None else sorted(target_postcodes)}")
    print(f"  Start year  : {args.start_year}")
    print(f"  Data dir    : {data_dir}")
    print(f"  Dry run     : {args.dry_run}")
    print(f"  Truncate    : {args.truncate}")
    print(f"  Skip weekly : {args.skip_weekly}")
    print(f"  No bridge   : {args.no_bridge}")
    print(f"  Bridge only : {args.bridge_only}")
    print("=" * 60)

    # ── Database setup ────────────────────────────────────────────────────────
    if not args.dry_run:
        try:
            conn = get_conn()
        except Exception as exc:
            print(f"[FATAL] Cannot connect to database: {exc}")
            sys.exit(1)
        create_tables(conn, truncate=args.truncate)
    else:
        conn = None
        print("[DRY RUN] Skipping database setup")

    # ── File list ─────────────────────────────────────────────────────────────
    if not args.skip_download:
        zip_files = download_data(data_dir, args.start_year, args.skip_weekly, args.timeout)
    else:
        zip_files = sorted(
            str(p) for p in Path(data_dir).glob("*.zip") if p.is_file()
        )
        print(f"\nUsing {len(zip_files)} existing zip files from: {data_dir}")

    if not zip_files:
        print("[WARN] No zip files found. Run without --skip-download to fetch data.")
        sys.exit(0)

    # ── Bridge-only: skip history load entirely ──────────────────────────────
    if args.bridge_only:
        if not args.dry_run and conn:
            bridge_rows = rebuild_bridge_table(conn, target_postcodes)
            postcode_desc = "ALL NSW" if target_postcodes is None else str(sorted(target_postcodes))
            write_load_log(
                conn,
                layer_name    = "gnaf_vg_bridge_rebuild",
                where_clause  = f"postcodes={postcode_desc}",
                rows_inserted = bridge_rows,
                rows_skipped  = 0,
            )
            conn.close()
        print("\nDone.")
        sys.exit(0)

    # ── Parse and load ────────────────────────────────────────────────────────
    total_inserted = total_skipped = total_parsed = 0
    t_start = time.time()

    for zip_path in zip_files:
        filename = os.path.basename(zip_path)
        print(f"\nProcessing {filename}...", end=" ", flush=True)

        records = extract_and_parse(zip_path, target_postcodes, dry_run=args.dry_run)
        total_parsed += len(records)
        print(f"{len(records):,} matching records")

        if args.dry_run:
            if records:
                print(f"\n[DRY RUN] Sample records from {filename}:")
                for r in records[:5]:
                    print(
                        f"  {r['data_format']:8s}  {r['postcode']}  "
                        f"{r.get('unit_number', '') or ''}"
                        f"{'/' if r.get('unit_number') else ''}"
                        f"{r.get('house_number', '')} {r.get('street_name', '')}  "
                        f"{r.get('locality', '')}  "
                        f"${r['purchase_price']:,}  {r['contract_date']}"
                    )
                print("\n[DRY RUN] No database writes performed. Stopping after first file.")
                break
            continue

        if not records:
            continue

        ins, skp = load_records_to_db(conn, records, args.batch_size)
        total_inserted += ins
        total_skipped  += skp
        elapsed = time.time() - t_start
        print(
            f"  ✓ Inserted: {ins:,}  Skipped (duplicate): {skp:,}  "
            f"[{elapsed:.0f}s elapsed]"
        )

    # ── Summary and bridge rebuild ────────────────────────────────────────────
    if not args.dry_run and conn:
        elapsed = time.time() - t_start
        print(f"\n{'─' * 60}")
        print(
            f"Load complete: {total_parsed:,} records parsed across all files\n"
            f"  {total_inserted:,} inserted  |  {total_skipped:,} skipped (duplicates)\n"
            f"  Total elapsed: {elapsed:.1f}s"
        )

        postcode_desc = "ALL NSW" if target_postcodes is None else str(sorted(target_postcodes))
        write_load_log(
            conn,
            layer_name    = "vg_bulk_sales",
            where_clause  = f"postcodes={postcode_desc}, years={args.start_year}-current",
            rows_inserted = total_inserted,
            rows_skipped  = total_skipped,
        )

        if not args.no_bridge:
            bridge_rows = rebuild_bridge_table(conn, target_postcodes)
            write_load_log(
                conn,
                layer_name    = "gnaf_vg_bridge_rebuild",
                where_clause  = f"postcodes={postcode_desc}",
                rows_inserted = bridge_rows,
                rows_skipped  = 0,
            )
        else:
            print("\n[INFO] Bridge table rebuild skipped (--no-bridge). "
                  "Re-run with --skip-download --no-sales to rebuild it later.")

        # Print load log tail
        with conn.cursor() as cur:
            cur.execute("""\
SELECT layer_name, rows_inserted, rows_skipped, run_at
FROM public.nsw_property_load_log
ORDER BY run_at DESC LIMIT 5""")
            rows = cur.fetchall()
        print("\nLoad log (last 5 entries):")
        print(f"  {'Layer':<30} {'Inserted':>10} {'Skipped':>8}  Run at")
        print("  " + "─" * 65)
        for r in rows:
            print(f"  {r[0]:<30} {r[1]:>10,} {r[2]:>8,}  {r[3]}")

        conn.close()

    print("\nDone.")


if __name__ == "__main__":
    main()
