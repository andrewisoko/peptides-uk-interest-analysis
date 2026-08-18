-- ============================================================
-- 04. Regional Analysis
-- ============================================================
-- Only rows with a populated region_id (national-only rows and all
-- Wikipedia rows, which never carry a region, are excluded here by
-- construction).

SELECT
    r.region_name,
    p.peptide_name,
    d.date,
    fsi.interest_score
FROM fact_search_interest fsi
JOIN dim_regions r ON r.region_id = fsi.region_id
JOIN dim_peptides p ON p.peptide_id = fsi.peptide_id
JOIN dim_dates d ON d.date_id = fsi.date_id
ORDER BY r.region_name, p.peptide_name, d.date;

-- Region ranking by growth % (first 90 days vs. last 90 days of the
-- regional series) -- feeds KPI 9.4 in 07_kpis.sql
WITH bounds AS (
    SELECT MIN(d.date) AS min_date, MAX(d.date) AS max_date
    FROM fact_search_interest fsi
    JOIN dim_dates d ON d.date_id = fsi.date_id
    WHERE fsi.region_id IS NOT NULL
),
periods AS (
    SELECT
        fsi.region_id,
        CASE WHEN d.date < b.min_date + 90 THEN 'baseline'
             WHEN d.date > b.max_date - 90 THEN 'current'
             ELSE NULL END AS period,
        fsi.interest_score
    FROM fact_search_interest fsi
    JOIN dim_dates d ON d.date_id = fsi.date_id
    CROSS JOIN bounds b
    WHERE fsi.region_id IS NOT NULL
)
SELECT
    r.region_name,
    r.population,
    ROUND(AVG(periods.interest_score) FILTER (WHERE period = 'baseline'), 2) AS baseline_avg,
    ROUND(AVG(periods.interest_score) FILTER (WHERE period = 'current'), 2) AS current_avg,
    ROUND(
        100.0 * (AVG(periods.interest_score) FILTER (WHERE period = 'current')
                 - AVG(periods.interest_score) FILTER (WHERE period = 'baseline'))
        / NULLIF(AVG(periods.interest_score) FILTER (WHERE period = 'baseline'), 0),
        2
    ) AS growth_pct
FROM periods
JOIN dim_regions r ON r.region_id = periods.region_id
WHERE period IS NOT NULL
GROUP BY r.region_name, r.population
ORDER BY growth_pct DESC NULLS LAST;

-- Population-normalized interest (per million population) -- does
-- the ranking change vs. raw average interest_score?
SELECT
    r.region_name,
    r.population,
    ROUND(AVG(fsi.interest_score), 2) AS raw_avg_interest,
    ROUND(AVG(fsi.interest_score) / (r.population / 1000000.0), 4) AS interest_per_million_pop
FROM fact_search_interest fsi
JOIN dim_regions r ON r.region_id = fsi.region_id
GROUP BY r.region_name, r.population
ORDER BY interest_per_million_pop DESC;
