-- ─────────────────────────────────────────────────────────
-- 1. STUDIES BY STATE
--    Which states have the most documented flood studies?
-- ─────────────────────────────────────────────────────────
SELECT
    UPPER(state)                          AS state,
    COUNT(*)                              AS study_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM public.afrip_flood_studies
WHERE state IS NOT NULL AND state <> ''
GROUP BY state
ORDER BY study_count DESC;


-- ─────────────────────────────────────────────────────────
-- 2. STUDIES BY DECADE
--    Temporal trend: when was most flood research done?
-- ─────────────────────────────────────────────────────────
SELECT
    (year / 10 * 10)::text || 's'         AS decade,
    COUNT(*)                               AS study_count
FROM public.afrip_flood_studies
WHERE year BETWEEN 1900 AND 2030
GROUP BY decade
ORDER BY decade;


-- ─────────────────────────────────────────────────────────
-- 3. TOP COMMISSIONING ORGANISATIONS
--    Who funds the most flood studies?
-- ─────────────────────────────────────────────────────────
SELECT
    commission,
    COUNT(*)  AS study_count
FROM public.afrip_flood_studies
WHERE commission IS NOT NULL AND commission <> ''
GROUP BY commission
ORDER BY study_count DESC
LIMIT 20;


-- ─────────────────────────────────────────────────────────
-- 4. TOP CONSULTING FIRMS
--    Who delivers the most flood studies?
-- ─────────────────────────────────────────────────────────
SELECT
    lead_consu                            AS consultant,
    COUNT(*)                              AS study_count
FROM public.afrip_flood_studies
WHERE lead_consu IS NOT NULL AND lead_consu <> ''
GROUP BY lead_consu
ORDER BY study_count DESC
LIMIT 20;


-- ─────────────────────────────────────────────────────────
-- 5. DATA COMPLETENESS SCORECARD
--    How many studies have each type of supporting data?
-- ─────────────────────────────────────────────────────────
SELECT
    'Terrain Survey'      AS data_type, COUNT(*) FILTER (WHERE terrain_su = 'Y') AS studies_with,
        ROUND(100.0 * COUNT(*) FILTER (WHERE terrain_su = 'Y') / COUNT(*), 1)    AS pct
FROM public.afrip_flood_studies
UNION ALL SELECT 'Hydrologic Data',  COUNT(*) FILTER (WHERE hydrologic = 'Y'),  ROUND(100.0 * COUNT(*) FILTER (WHERE hydrologic = 'Y')  / COUNT(*), 1) FROM public.afrip_flood_studies
UNION ALL SELECT 'Hydraulic Data',   COUNT(*) FILTER (WHERE hydraulic_ = 'Y'),  ROUND(100.0 * COUNT(*) FILTER (WHERE hydraulic_ = 'Y')  / COUNT(*), 1) FROM public.afrip_flood_studies
UNION ALL SELECT 'Damage Assessment',COUNT(*) FILTER (WHERE damage_ass = 'Y'),  ROUND(100.0 * COUNT(*) FILTER (WHERE damage_ass = 'Y')  / COUNT(*), 1) FROM public.afrip_flood_studies
UNION ALL SELECT 'Depth Map',        COUNT(*) FILTER (WHERE depth_map_ = 'Y'),  ROUND(100.0 * COUNT(*) FILTER (WHERE depth_map_ = 'Y') / COUNT(*), 1) FROM public.afrip_flood_studies
UNION ALL SELECT 'Extent Map',       COUNT(*) FILTER (WHERE extent_map = 'Y'),  ROUND(100.0 * COUNT(*) FILTER (WHERE extent_map = 'Y') / COUNT(*), 1) FROM public.afrip_flood_studies
UNION ALL SELECT 'Hazard Map',       COUNT(*) FILTER (WHERE hazard_map = 'Y'),  ROUND(100.0 * COUNT(*) FILTER (WHERE hazard_map = 'Y') / COUNT(*), 1) FROM public.afrip_flood_studies
UNION ALL SELECT 'Velocity Data',    COUNT(*) FILTER (WHERE velocity_m = 'Y'),  ROUND(100.0 * COUNT(*) FILTER (WHERE velocity_m = 'Y') / COUNT(*), 1) FROM public.afrip_flood_studies
UNION ALL SELECT 'Floor Survey',     COUNT(*) FILTER (WHERE floor_surv = 'Y'),  ROUND(100.0 * COUNT(*) FILTER (WHERE floor_surv = 'Y') / COUNT(*), 1) FROM public.afrip_flood_studies
UNION ALL SELECT 'GIS Data',         COUNT(*) FILTER (WHERE gis_data_i = 'Y'),  ROUND(100.0 * COUNT(*) FILTER (WHERE gis_data_i = 'Y') / COUNT(*), 1) FROM public.afrip_flood_studies
UNION ALL SELECT 'Mitigation Data',  COUNT(*) FILTER (WHERE mitigation = 'Y'),  ROUND(100.0 * COUNT(*) FILTER (WHERE mitigation = 'Y') / COUNT(*), 1) FROM public.afrip_flood_studies
ORDER BY studies_with DESC;


-- ─────────────────────────────────────────────────────────
-- 6. STUDIES WITH THE MOST ATTACHMENTS
--    Top 20 best-documented flood studies (reports + GIS)
-- ─────────────────────────────────────────────────────────
SELECT
    s.flood_stud                          AS study_id,
    s.name                                AS study_name,
    UPPER(s.state)                        AS state,
    s.year,
    COUNT(a.flood_study_id)               AS attachment_count
FROM public.afrip_flood_studies s
JOIN public.afrip_flood_attachments a
  ON a.flood_study_id::integer = s.flood_stud
GROUP BY s.flood_stud, s.name, s.state, s.year
ORDER BY attachment_count DESC
LIMIT 20;


-- ─────────────────────────────────────────────────────────
-- 7. STUDIES WITH NO ATTACHMENTS (data gaps)
-- ─────────────────────────────────────────────────────────
SELECT
    s.flood_stud,
    s.name,
    UPPER(s.state) AS state,
    s.year,
    s.commission
FROM public.afrip_flood_studies s
LEFT JOIN public.afrip_flood_attachments a
  ON a.flood_study_id::integer = s.flood_stud
WHERE a.flood_study_id IS NULL
ORDER BY s.year DESC;


-- ─────────────────────────────────────────────────────────
-- 8. STATE × DECADE HEATMAP
--    Cross-tab of study activity by state and decade
-- ─────────────────────────────────────────────────────────
SELECT
    UPPER(state)                          AS state,
    COUNT(*) FILTER (WHERE year BETWEEN 1980 AND 1989) AS "1980s",
    COUNT(*) FILTER (WHERE year BETWEEN 1990 AND 1999) AS "1990s",
    COUNT(*) FILTER (WHERE year BETWEEN 2000 AND 2009) AS "2000s",
    COUNT(*) FILTER (WHERE year BETWEEN 2010 AND 2018) AS "2010-18",
    COUNT(*)                                            AS total
FROM public.afrip_flood_studies
WHERE state IS NOT NULL AND state <> ''
  AND year BETWEEN 1980 AND 2018
GROUP BY state
ORDER BY total DESC;


-- ─────────────────────────────────────────────────────────
-- 9. ATTACHMENT FILE TYPE BREAKDOWN
--    PDFs vs GIS data files
-- ─────────────────────────────────────────────────────────
SELECT
    LOWER(RIGHT(filename, 4))             AS extension,
    COUNT(*)                              AS file_count
FROM public.afrip_flood_attachments
WHERE filename IS NOT NULL
GROUP BY extension
ORDER BY file_count DESC;


-- ─────────────────────────────────────────────────────────
-- 10. MOST CITED RIVERS
--     Which rivers have the most flood studies?
-- ─────────────────────────────────────────────────────────
SELECT
    TRIM(river_name)                      AS river,
    COUNT(*)                              AS study_count
FROM public.afrip_flood_studies,
     LATERAL UNNEST(STRING_TO_ARRAY(rivers, ';')) AS river_name
WHERE rivers IS NOT NULL AND rivers <> ''
GROUP BY river
ORDER BY study_count DESC
LIMIT 20;


-- ─────────────────────────────────────────────────────────
-- 11. FULLY-EQUIPPED STUDIES
--     Studies that have ALL key data types (best quality)
-- ─────────────────────────────────────────────────────────
SELECT
    flood_stud, name, UPPER(state) AS state, year, commission
FROM public.afrip_flood_studies
WHERE hydrologic = 'Y'
  AND hydraulic_ = 'Y'
  AND damage_ass = 'Y'
  AND depth_map_ = 'Y'
  AND hazard_map = 'Y'
  AND extent_map = 'Y'
ORDER BY year DESC;


-- ─────────────────────────────────────────────────────────
-- 12. NEAREST STUDIES TO A GIVEN POINT (e.g. Brisbane CBD)
--     Replace ST_MakePoint(lon, lat) with any coordinates
-- ─────────────────────────────────────────────────────────
SELECT
    s.flood_stud,
    s.name,
    UPPER(s.state)                                  AS state,
    s.year,
    s.commission,
    ROUND(ST_Distance(
        s.geometry::geography,
        ST_SetSRID(ST_MakePoint(153.0251, -27.4698), 4326)::geography
    )::numeric / 1000, 2)                           AS distance_km
FROM public.afrip_flood_studies s
ORDER BY s.geometry <-> ST_SetSRID(ST_MakePoint(153.0251, -27.4698), 4326)
LIMIT 10;


-- ─────────────────────────────────────────────────────────
-- 13. STUDIES WITHIN A BOUNDING BOX (e.g. Greater Sydney)
-- ─────────────────────────────────────────────────────────
SELECT
    flood_stud, name, year, commission, state
FROM public.afrip_flood_studies
WHERE ST_Within(
    geometry,
    ST_MakeEnvelope(150.5, -34.2, 151.5, -33.4, 4326)
)
ORDER BY year DESC;


-- ─────────────────────────────────────────────────────────
-- 14. REPORT COMPLETENESS SCORE DISTRIBUTION
--     reportcomp is a 0–10 completeness rating
-- ─────────────────────────────────────────────────────────
SELECT
    reportcomp                            AS completeness_score,
    COUNT(*)                              AS study_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM public.afrip_flood_studies
WHERE reportcomp IS NOT NULL
GROUP BY reportcomp
ORDER BY completeness_score;


-- ─────────────────────────────────────────────────────────
-- 15. SUMMARY DASHBOARD (single-query overview)
-- ─────────────────────────────────────────────────────────
SELECT
    COUNT(*)                                             AS total_studies,
    COUNT(DISTINCT UPPER(state))                         AS states_covered,
    MIN(year)                                            AS earliest_year,
    MAX(year)                                            AS latest_year,
    COUNT(*) FILTER (WHERE gis_data_i = 'Y')             AS with_gis_data,
    COUNT(*) FILTER (WHERE hydraulic_ = 'Y')             AS with_hydraulic,
    COUNT(*) FILTER (WHERE hazard_map = 'Y')             AS with_hazard_map,
    ROUND(AVG(reportcomp), 2)                            AS avg_completeness,
    (SELECT COUNT(*) FROM public.afrip_flood_attachments) AS total_attachments
FROM public.afrip_flood_studies;

-- ─────────────────────────────────────────────────────────────────────
-- CAVEAT: This data is a study catalogue (not flood event measurements).
-- "Most affected" proxies:
--   • Study density  → how often floods occur / how serious the risk is
--   • Hazard map presence → authorities formally mapped flood hazard
--   • Damage assessment presence → economic impact was documented
--   • Study area coverage (bbox) → spatial extent of flood risk
-- ─────────────────────────────────────────────────────────────────────


-- 1. MOST AFFECTED STATES
--    Ranked by study count + hazard documentation rate
-- ─────────────────────────────────────────────────────────────────────
SELECT
    UPPER(state)                                          AS state,
    COUNT(*)                                              AS total_studies,
    COUNT(*) FILTER (WHERE hazard_map  = 'Y')             AS with_hazard_map,
    COUNT(*) FILTER (WHERE damage_ass  = 'Y')             AS with_damage_assessment,
    COUNT(*) FILTER (WHERE hydraulic_  = 'Y')             AS with_hydraulic_model,
    ROUND(AVG(reportcomp), 1)                             AS avg_completeness,
    ROUND(100.0 * COUNT(*) FILTER (WHERE hazard_map = 'Y') / COUNT(*), 0) AS hazard_pct
FROM public.afrip_flood_studies
WHERE state IS NOT NULL AND state <> ''
GROUP BY state
ORDER BY total_studies DESC;


-- 2. SPATIAL DENSITY — 1° GRID CELLS (approx 100km)
--    Which geographic areas have the highest flood study concentration?
-- ─────────────────────────────────────────────────────────────────────
SELECT
    FLOOR(ST_X(geometry))::int   AS lon_bucket,
    FLOOR(ST_Y(geometry))::int   AS lat_bucket,
    COUNT(*)                     AS study_count,
    -- centroid of bucket for mapping
    FLOOR(ST_X(geometry))::int + 0.5  AS lon_centre,
    FLOOR(ST_Y(geometry))::int + 0.5  AS lat_centre
FROM public.afrip_flood_studies
WHERE geometry IS NOT NULL
GROUP BY lon_bucket, lat_bucket
ORDER BY study_count DESC
LIMIT 30;


-- 3. HIGHEST-RISK STUDY AREAS (hazard + damage both documented)
--    Studies where BOTH hazard maps AND damage assessments exist
--    → strongest evidence of serious flood impact
-- ─────────────────────────────────────────────────────────────────────
SELECT
    UPPER(state)   AS state,
    COUNT(*)       AS high_risk_studies,
    STRING_AGG(DISTINCT commission, ', ' ORDER BY commission) AS key_commissioners
FROM public.afrip_flood_studies
WHERE hazard_map = 'Y'
  AND damage_ass = 'Y'
GROUP BY state
ORDER BY high_risk_studies DESC;


-- 4. MOST FLOOD-AFFECTED RIVERS
--    Rivers appearing most often across studies, filtered to
--    studies that include hazard or damage data
-- ─────────────────────────────────────────────────────────────────────
SELECT
    TRIM(river_name)                          AS river,
    COUNT(*)                                  AS study_count,
    COUNT(*) FILTER (WHERE hazard_map = 'Y')  AS hazard_documented,
    COUNT(*) FILTER (WHERE damage_ass = 'Y')  AS damage_documented,
    STRING_AGG(DISTINCT UPPER(state), ', ')   AS states
FROM public.afrip_flood_studies,
     LATERAL UNNEST(STRING_TO_ARRAY(rivers, ';')) AS river_name
WHERE rivers IS NOT NULL AND rivers <> ''
GROUP BY river
ORDER BY study_count DESC
LIMIT 25;


-- 5. STUDY AREA SIZE — which regions cover largest flood extents?
--    Uses the bbox fields (latn/lats/lone/lonw) to compute study area km²
--    (approximate — bounding box, not actual flood polygon)
-- ─────────────────────────────────────────────────────────────────────
SELECT
    flood_stud,
    name,
    UPPER(state)        AS state,
    year,
    ROUND(
        -- degrees to km: 1° lat ≈ 111km, 1° lon ≈ 111km × cos(lat)
        (latn - lats) * 111.0
        * (lone - lonw) * 111.0 * COS(RADIANS((latn + lats) / 2))
    , 0)                AS approx_area_km2,
    hazard_map,
    damage_ass
FROM public.afrip_flood_studies
WHERE latn <> 0 AND lats <> 0  -- exclude records with no bbox
  AND latn > lats               -- valid bbox
ORDER BY approx_area_km2 DESC NULLS LAST
LIMIT 20;


-- 6. COMPOSITE FLOOD RISK SCORE PER STATE
--    Weighted score: study density + hazard presence + damage presence
--    Score = studies + (2 × hazard) + (2 × damage) + hydraulic
-- ─────────────────────────────────────────────────────────────────────
SELECT
    UPPER(state)                                               AS state,
    COUNT(*)                                                   AS studies,
    COUNT(*) FILTER (WHERE hazard_map = 'Y')                   AS hazard,
    COUNT(*) FILTER (WHERE damage_ass = 'Y')                   AS damage,
    COUNT(*) FILTER (WHERE hydraulic_ = 'Y')                   AS hydraulic,
    -- composite score
    COUNT(*)
      + 2 * COUNT(*) FILTER (WHERE hazard_map = 'Y')
      + 2 * COUNT(*) FILTER (WHERE damage_ass = 'Y')
      +     COUNT(*) FILTER (WHERE hydraulic_ = 'Y')           AS risk_score
FROM public.afrip_flood_studies
WHERE state IS NOT NULL AND state <> ''
GROUP BY state
ORDER BY risk_score DESC;


-- 7. REPEAT FLOOD AREAS — same commissioner, multiple studies over time
--    Repeated commissioning in the same area → persistent flood problem
-- ─────────────────────────────────────────────────────────────────────
SELECT
    commission,
    UPPER(state)           AS state,
    COUNT(*)               AS study_count,
    MIN(year)              AS first_study,
    MAX(year)              AS latest_study,
    MAX(year) - MIN(year)  AS years_of_concern
FROM public.afrip_flood_studies
WHERE commission IS NOT NULL AND commission <> ''
GROUP BY commission, state
HAVING COUNT(*) >= 3
ORDER BY study_count DESC, years_of_concern DESC
LIMIT 30;