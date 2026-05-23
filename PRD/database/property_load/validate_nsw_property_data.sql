/*#	Query	What it validates
1	Row counts	Totals match expected (20116 / 30555 / 151785)
2	Load log	ETL run history and checkpoints
3	Sales by postcode	Only target postcodes present; price range sanity
4	Sales by suburb	Top suburbs and average prices
5	Sales quality	Null propid/dealing/price/geometry counts
6	Sales geometry	SRID=4326, coords within Sydney Hills area
7	Valuation by zone	R2/R3/E4 zone distribution
8	Land value bands	Distribution across price brackets
9	Valuation quality	Null address/zone/val1_lv/geometry
10	History rows/property	Should be mostly 5 rows each
11	History by base_date	Shows 2021–2025 valuation years and avg per year
12	Cross-join coverage	How many propids appear in both tables
13	Sample joined rows	5 most expensive properties with valuation detail
14	Single property history	Full val history for one property
15	Spatial: 500m radius	Properties near Pennant Hills station
*/

-- ============================================================
-- NSW Property Data Validation Scripts
-- Run against: gnaf_db (postgres@localhost:5432)
-- Tables: public.nsw_property_sales
--         public.nsw_property_valuation
--         public.nsw_property_valuation_history
--         public.nsw_property_load_log
-- ============================================================


-- ─────────────────────────────────────────────────
-- 1. ROW COUNTS  (expect: 20116 / 30555 / 151785)
-- ─────────────────────────────────────────────────
SELECT 'nsw_property_sales'             AS tbl, COUNT(*) FROM public.nsw_property_sales
UNION ALL
SELECT 'nsw_property_valuation'         AS tbl, COUNT(*) FROM public.nsw_property_valuation
UNION ALL
SELECT 'nsw_property_valuation_history' AS tbl, COUNT(*) FROM public.nsw_property_valuation_history
UNION ALL
SELECT 'nsw_property_load_log'          AS tbl, COUNT(*) FROM public.nsw_property_load_log
ORDER BY tbl;


-- ─────────────────────────────────────────────────
-- 2. LOAD LOG  (last 10 ETL runs)
-- ─────────────────────────────────────────────────
SELECT
    layer_name,
    rows_inserted,
    rows_updated,
    rows_skipped,
    max_oid_loaded,
    TO_CHAR(run_at AT TIME ZONE 'Australia/Sydney', 'YYYY-MM-DD HH24:MI:SS') AS run_at_aest
FROM public.nsw_property_load_log
ORDER BY id DESC
LIMIT 10;


-- ─────────────────────────────────────────────────
-- 3. SALES: postcode breakdown
--    (should only have 2077 / 2076 / 2119 / 2120 / 2125)
-- ─────────────────────────────────────────────────
SELECT
    postcode,
    COUNT(*)                                      AS sales_records,
    COUNT(DISTINCT propid)                        AS unique_properties,
    MIN(price)                                    AS min_price,
    MAX(price)                                    AS max_price,
    ROUND(AVG(price))                             AS avg_price
FROM public.nsw_property_sales
GROUP BY postcode
ORDER BY postcode;


-- ─────────────────────────────────────────────────
-- 4. SALES: suburb breakdown
-- ─────────────────────────────────────────────────
SELECT
    suburb,
    postcode,
    COUNT(*)               AS num_sales,
    COUNT(DISTINCT propid) AS unique_properties,
    ROUND(AVG(price))      AS avg_sale_price
FROM public.nsw_property_sales
WHERE price > 0
GROUP BY suburb, postcode
ORDER BY num_sales DESC
LIMIT 20;


-- ─────────────────────────────────────────────────
-- 5. SALES: data quality checks
-- ─────────────────────────────────────────────────
SELECT
    COUNT(*)                                           AS total,
    COUNT(*) FILTER (WHERE propid IS NULL)             AS null_propid,
    COUNT(*) FILTER (WHERE dealing IS NULL)            AS null_dealing,
    COUNT(*) FILTER (WHERE postcode IS NULL)           AS null_postcode,
    COUNT(*) FILTER (WHERE price IS NULL OR price = 0) AS zero_or_null_price,
    COUNT(*) FILTER (WHERE sale_date IS NULL)          AS null_sale_date,
    COUNT(*) FILTER (WHERE geometry IS NULL)           AS null_geometry,
    COUNT(*) FILTER (WHERE last_sale = 'Y')            AS last_sale_flag_y
FROM public.nsw_property_sales;


-- ─────────────────────────────────────────────────
-- 6. SALES: geometry validity and SRID
-- ─────────────────────────────────────────────────
SELECT
    ST_SRID(geometry)                     AS srid,        -- should be 4326
    COUNT(*)                              AS total_rows,
    COUNT(*) FILTER (WHERE ST_IsValid(geometry))  AS valid_geom,
    COUNT(*) FILTER (WHERE NOT ST_IsValid(geometry)) AS invalid_geom,
    ROUND(MIN(ST_X(geometry))::numeric, 4) AS min_lng,
    ROUND(MAX(ST_X(geometry))::numeric, 4) AS max_lng,
    ROUND(MIN(ST_Y(geometry))::numeric, 4) AS min_lat,
    ROUND(MAX(ST_Y(geometry))::numeric, 4) AS max_lat
FROM public.nsw_property_sales
WHERE geometry IS NOT NULL
GROUP BY ST_SRID(geometry);
-- Expected: srid=4326, lng ~150.9–151.2, lat ~ -33.6 to -33.8


-- ─────────────────────────────────────────────────
-- 7. VALUATION: suburb / zone breakdown
-- ─────────────────────────────────────────────────
SELECT
    zone_desc,
    COUNT(*)               AS num_properties,
    COUNT(*) FILTER (WHERE pbdapplies = 1) AS pbd_applies,
    COUNT(*) FILTER (WHERE conapplies = 1) AS con_applies,
    COUNT(*) FILTER (WHERE underspflag = 1) AS undersupply
FROM public.nsw_property_valuation
GROUP BY zone_desc
ORDER BY num_properties DESC;


-- ─────────────────────────────────────────────────
-- 8. VALUATION: land value distribution (current = val1_lv)
--    val1_lv is stored as TEXT e.g. " $1,270,000"
--    Strip and cast for numeric analysis
-- ─────────────────────────────────────────────────
SELECT
    CASE
        WHEN val1_lv_num <  500000   THEN 'Under $500k'
        WHEN val1_lv_num <  1000000  THEN '$500k–$1M'
        WHEN val1_lv_num <  2000000  THEN '$1M–$2M'
        WHEN val1_lv_num <  3000000  THEN '$2M–$3M'
        ELSE 'Over $3M'
    END                  AS land_value_band,
    COUNT(*)             AS num_properties,
    ROUND(AVG(val1_lv_num)) AS avg_land_value
FROM (
    SELECT
        REGEXP_REPLACE(TRIM(val1_lv), '[\$,]', '', 'g')::BIGINT AS val1_lv_num
    FROM public.nsw_property_valuation
    WHERE val1_lv IS NOT NULL
      AND val1_lv ~ '\$'
) sub
GROUP BY land_value_band
ORDER BY MIN(val1_lv_num);


-- ─────────────────────────────────────────────────
-- 9. VALUATION: data quality checks
-- ─────────────────────────────────────────────────
SELECT
    COUNT(*)                                            AS total,
    COUNT(*) FILTER (WHERE address IS NULL)             AS null_address,
    COUNT(*) FILTER (WHERE zone_desc IS NULL)           AS null_zone,
    COUNT(*) FILTER (WHERE val1_lv IS NULL)             AS null_val1_lv,
    COUNT(*) FILTER (WHERE val1_bd IS NULL)             AS null_val1_bd,
    COUNT(*) FILTER (WHERE geometry IS NULL)            AS null_geometry,
    COUNT(DISTINCT validity_d)                          AS distinct_validity_dates
FROM public.nsw_property_valuation;


-- ─────────────────────────────────────────────────
-- 10. VALUATION HISTORY: rows per property
--     Should be 5 per property (val1..val5), possibly fewer if API had nulls
-- ─────────────────────────────────────────────────
SELECT
    hist_count,
    COUNT(*) AS num_properties
FROM (
    SELECT propid, COUNT(*) AS hist_count
    FROM public.nsw_property_valuation_history
    GROUP BY propid
) sub
GROUP BY hist_count
ORDER BY hist_count;


-- ─────────────────────────────────────────────────
-- 11. VALUATION HISTORY: base_date breakdown
--     Shows which valuation years are present
-- ─────────────────────────────────────────────────
SELECT
    base_date,
    COUNT(*)                AS num_properties,
    ROUND(AVG(
        REGEXP_REPLACE(TRIM(land_value), '[\$,]', '', 'g')::BIGINT
    ))                      AS avg_land_value
FROM public.nsw_property_valuation_history
WHERE land_value IS NOT NULL
  AND land_value ~ '\$'
GROUP BY base_date
ORDER BY base_date DESC;


-- ─────────────────────────────────────────────────
-- 12. CROSS-JOIN: Properties with both sales AND valuation
-- ─────────────────────────────────────────────────
SELECT
    COUNT(DISTINCT s.propid)                        AS sales_propids,
    COUNT(DISTINCT v.propid)                        AS val_propids,
    COUNT(DISTINCT s.propid) FILTER
        (WHERE v.propid IS NOT NULL)                AS in_both,
    COUNT(DISTINCT s.propid) FILTER
        (WHERE v.propid IS NULL)                    AS sales_only,
    COUNT(DISTINCT v.propid) FILTER
        (WHERE s.propid IS NULL)                    AS val_only
FROM public.nsw_property_sales s
FULL OUTER JOIN public.nsw_property_valuation v USING (propid);


-- ─────────────────────────────────────────────────
-- 13. SAMPLE: 5 properties with full sales + valuation detail
-- ─────────────────────────────────────────────────
SELECT
    s.propid,
    s.bp_address,
    s.postcode,
    s.price            AS last_sale_price,
    s.sale_date,
    v.zone_desc,
    v.val1_bd          AS current_val_base_date,
    v.val1_lv          AS current_land_value,
    v.val2_lv          AS prev_year_land_value,
    v.prop_area
FROM public.nsw_property_sales s
JOIN public.nsw_property_valuation v USING (propid)
WHERE s.last_sale = 'Y'
  AND s.price > 0
ORDER BY s.price DESC
LIMIT 5;


-- ─────────────────────────────────────────────────
-- 14. SAMPLE: Valuation history for a single property
-- ─────────────────────────────────────────────────
SELECT
    h.propid,
    v.address,
    h.base_date,
    h.land_value,
    h.concession
FROM public.nsw_property_valuation_history h
JOIN public.nsw_property_valuation v USING (propid)
WHERE h.propid = (
    SELECT propid FROM public.nsw_property_valuation LIMIT 1
)
ORDER BY h.base_date DESC;


-- ─────────────────────────────────────────────────
-- 15. SPATIAL: Properties within 500m of a point
--     Example: ~centre of Pennant Hills station
-- ─────────────────────────────────────────────────
SELECT
    s.propid,
    s.bp_address,
    s.price,
    s.sale_date,
    ROUND(ST_Distance(
        s.geometry::geography,
        ST_SetSRID(ST_MakePoint(151.0716, -33.7365), 4326)::geography
    ))                     AS distance_m
FROM public.nsw_property_sales s
WHERE ST_DWithin(
    s.geometry::geography,
    ST_SetSRID(ST_MakePoint(151.0716, -33.7365), 4326)::geography,
    500
)
ORDER BY distance_m
LIMIT 10;
