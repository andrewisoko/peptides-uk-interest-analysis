-- ============================================================
-- 02. Dimension Profiling
-- ============================================================

SELECT * FROM dim_peptides ORDER BY peptide_id;

SELECT * FROM dim_regions ORDER BY population DESC;

SELECT * FROM dim_sources ORDER BY reliability DESC;

SELECT MIN(date) AS earliest_date, MAX(date) AS latest_date, COUNT(*) AS n_weeks
FROM dim_dates;

-- Peptides that are absent or under-represented in the fact tables
SELECT
    p.peptide_id,
    p.peptide_name,
    COALESCE(si.n, 0) AS search_interest_rows,
    COALESCE(ev.n, 0) AS event_rows
FROM dim_peptides p
LEFT JOIN (
    SELECT peptide_id, COUNT(*) AS n FROM fact_search_interest GROUP BY peptide_id
) si ON si.peptide_id = p.peptide_id
LEFT JOIN (
    SELECT peptide_id, COUNT(*) AS n FROM fact_events GROUP BY peptide_id
) ev ON ev.peptide_id = p.peptide_id
ORDER BY search_interest_rows ASC, event_rows ASC;

-- Regions that are absent or under-represented in the fact tables
-- (region_id is nullable in both facts, so only non-null rows count
-- toward a region here)
SELECT
    r.region_id,
    r.region_name,
    COALESCE(si.n, 0) AS search_interest_rows,
    COALESCE(ev.n, 0) AS event_rows
FROM dim_regions r
LEFT JOIN (
    SELECT region_id, COUNT(*) AS n
    FROM fact_search_interest
    WHERE region_id IS NOT NULL
    GROUP BY region_id
) si ON si.region_id = r.region_id
LEFT JOIN (
    SELECT region_id, COUNT(*) AS n
    FROM fact_events
    WHERE region_id IS NOT NULL
    GROUP BY region_id
) ev ON ev.region_id = r.region_id
ORDER BY search_interest_rows ASC, event_rows ASC;
