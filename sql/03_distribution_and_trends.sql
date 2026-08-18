-- ============================================================
-- 03. Univariate Distribution & Time-Series Trends
-- ============================================================
-- Google Trends scores are 0-100 (relative, per-keyword); Wikipedia
-- scores are raw pageviews -- not the same scale. Kept separate
-- throughout via GROUP BY source_name.

-- Distribution of interest_score by source
SELECT
    s.source_name,
    COUNT(*) AS n,
    MIN(fsi.interest_score) AS min_score,
    ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY fsi.interest_score)::NUMERIC, 2) AS p25,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY fsi.interest_score)::NUMERIC, 2) AS median,
    ROUND(AVG(fsi.interest_score), 2) AS mean_score,
    ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY fsi.interest_score)::NUMERIC, 2) AS p75,
    MAX(fsi.interest_score) AS max_score,
    ROUND(STDDEV(fsi.interest_score), 2) AS stddev_score
FROM fact_search_interest fsi
JOIN dim_sources s ON s.source_id = fsi.source_id
GROUP BY s.source_name
ORDER BY s.source_name;

-- Per-peptide, per-source weekly time series (averaged across
-- regions/national rows for that week)
SELECT
    d.date,
    p.peptide_name,
    s.source_name,
    ROUND(AVG(fsi.interest_score), 2) AS avg_interest_score
FROM fact_search_interest fsi
JOIN dim_dates d ON d.date_id = fsi.date_id
JOIN dim_peptides p ON p.peptide_id = fsi.peptide_id
JOIN dim_sources s ON s.source_id = fsi.source_id
GROUP BY d.date, p.peptide_name, s.source_name
ORDER BY p.peptide_name, s.source_name, d.date;

-- Growth indicator per peptide/source: first 90 days vs. last 90
-- days of the overall date range -- flags sustained growth vs. a
-- one-off spike. (07_kpis.sql applies the same window, restricted to
-- Google Trends only, for KPI 9.3.)
WITH bounds AS (
    SELECT MIN(date) AS min_date, MAX(date) AS max_date FROM dim_dates
),
periods AS (
    SELECT
        fsi.peptide_id,
        fsi.source_id,
        CASE WHEN d.date < b.min_date + 90 THEN 'baseline'
             WHEN d.date > b.max_date - 90 THEN 'current'
             ELSE NULL END AS period,
        fsi.interest_score
    FROM fact_search_interest fsi
    JOIN dim_dates d ON d.date_id = fsi.date_id
    CROSS JOIN bounds b
)
SELECT
    p.peptide_name,
    s.source_name,
    ROUND(AVG(periods.interest_score) FILTER (WHERE period = 'baseline'), 2) AS baseline_avg,
    ROUND(AVG(periods.interest_score) FILTER (WHERE period = 'current'), 2) AS current_avg,
    ROUND(
        100.0 * (AVG(periods.interest_score) FILTER (WHERE period = 'current')
                 - AVG(periods.interest_score) FILTER (WHERE period = 'baseline'))
        / NULLIF(AVG(periods.interest_score) FILTER (WHERE period = 'baseline'), 0),
        2
    ) AS growth_pct
FROM periods
JOIN dim_peptides p ON p.peptide_id = periods.peptide_id
JOIN dim_sources s ON s.source_id = periods.source_id
WHERE period IS NOT NULL
GROUP BY p.peptide_name, s.source_name
ORDER BY growth_pct DESC NULLS LAST;
