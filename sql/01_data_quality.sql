-- ============================================================
-- 01. Data Quality & Sanity Checks
-- ============================================================

-- Row counts vs. expected (peptides=9, regions=4, sources=5,
-- dates=209, search_interest=3292, events=334)
SELECT 'dim_peptides' AS table_name, COUNT(*) AS row_count FROM dim_peptides
UNION ALL
SELECT 'dim_regions', COUNT(*) FROM dim_regions
UNION ALL
SELECT 'dim_sources', COUNT(*) FROM dim_sources
UNION ALL
SELECT 'dim_dates', COUNT(*) FROM dim_dates
UNION ALL
SELECT 'fact_search_interest', COUNT(*) FROM fact_search_interest
UNION ALL
SELECT 'fact_events', COUNT(*) FROM fact_events;

-- Null counts for nullable columns (region_id is the only nullable
-- FK, present in both fact tables)
SELECT
    'fact_search_interest' AS table_name,
    COUNT(*) FILTER (WHERE region_id IS NULL) AS null_region_id,
    COUNT(*) AS total_rows
FROM fact_search_interest
UNION ALL
SELECT
    'fact_events',
    COUNT(*) FILTER (WHERE region_id IS NULL),
    COUNT(*)
FROM fact_events;

-- region_id null-rate by source in fact_search_interest
-- expect ~100% for Wikipedia (no regional breakdown), near-0% for
-- Google Trends' regional rows
SELECT
    s.source_name,
    COUNT(*) AS total_rows,
    COUNT(*) FILTER (WHERE fsi.region_id IS NULL) AS null_region_rows,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE fsi.region_id IS NULL) / COUNT(*), 2
    ) AS pct_null_region_id
FROM fact_search_interest fsi
JOIN dim_sources s ON s.source_id = fsi.source_id
GROUP BY s.source_name
ORDER BY pct_null_region_id DESC;

-- Duplicate (date_id, peptide_id, region_id, source_id) combinations
-- in fact_search_interest
SELECT date_id, peptide_id, region_id, source_id, COUNT(*) AS n
FROM fact_search_interest
GROUP BY date_id, peptide_id, region_id, source_id
HAVING COUNT(*) > 1
ORDER BY n DESC;

-- Duplicate events (same peptide, date, category, title)
SELECT event_date, peptide_id, category, title, COUNT(*) AS n
FROM fact_events
GROUP BY event_date, peptide_id, category, title
HAVING COUNT(*) > 1
ORDER BY n DESC;

-- interest_score range sanity check per source -- confirms Google
-- Trends is a ~0-100 relative scale vs. Wikipedia's raw pageviews
SELECT
    s.source_name,
    MIN(fsi.interest_score) AS min_score,
    MAX(fsi.interest_score) AS max_score,
    ROUND(AVG(fsi.interest_score), 2) AS avg_score,
    ROUND(STDDEV(fsi.interest_score), 2) AS stddev_score
FROM fact_search_interest fsi
JOIN dim_sources s ON s.source_id = fsi.source_id
GROUP BY s.source_name
ORDER BY s.source_name;
