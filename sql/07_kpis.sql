-- ============================================================
-- 07. KPI Calculations
-- ============================================================
-- From data/data_dictionary/Peptides_UK_Setup_Info.xlsx (KPIs sheet).
-- Growth formula throughout: (current - baseline) / baseline * 100.
--
-- KPIs are computed on Google Trends interest_score only: it's the
-- one source on a consistent 0-100 relative scale across the whole
-- date range, whereas Wikipedia pageviews are a different, larger,
-- non-comparable scale (see 03_distribution_and_trends.sql). Mixing
-- the two would distort every growth/spike figure below.
--
-- Out of scope for this pass (see notebooks/01_eda_roadmap.ipynb):
--   9.6 Event-Associated Excess Search Lift %  -- needs pre/post/
--       baseline windowing decisions around each individual event.
--   9.7 Event Attribution Rate %                -- depends on 9.6 and
--       on 9.5's spike list.
--   9.8 Most Common User Intent                 -- data gap: no
--       user-intent column exists anywhere in the schema.

-- ---------------------------------------------------------------
-- 9.1 Overall UK Search Interest Growth %
-- baseline = first 90 days of data, current = last 90 days
-- ---------------------------------------------------------------
WITH bounds AS (
    SELECT MIN(d.date) AS min_date, MAX(d.date) AS max_date
    FROM fact_search_interest fsi
    JOIN dim_dates d ON d.date_id = fsi.date_id
    JOIN dim_sources s ON s.source_id = fsi.source_id
    WHERE s.source_name = 'Google Trends'
),
periods AS (
    SELECT
        CASE WHEN d.date < b.min_date + 90 THEN 'baseline'
             WHEN d.date > b.max_date - 90 THEN 'current'
             ELSE NULL END AS period,
        fsi.interest_score
    FROM fact_search_interest fsi
    JOIN dim_dates d ON d.date_id = fsi.date_id
    JOIN dim_sources s ON s.source_id = fsi.source_id
    CROSS JOIN bounds b
    WHERE s.source_name = 'Google Trends'
)
SELECT
    ROUND(AVG(interest_score) FILTER (WHERE period = 'baseline'), 2) AS baseline_avg,
    ROUND(AVG(interest_score) FILTER (WHERE period = 'current'), 2) AS current_avg,
    ROUND(
        100.0 * (AVG(interest_score) FILTER (WHERE period = 'current')
                 - AVG(interest_score) FILTER (WHERE period = 'baseline'))
        / NULLIF(AVG(interest_score) FILTER (WHERE period = 'baseline'), 0),
        2
    ) AS overall_growth_pct
FROM periods
WHERE period IS NOT NULL;

-- ---------------------------------------------------------------
-- 9.2 Year-over-Year Growth %
-- current = most recent full year present, baseline = year prior
-- ---------------------------------------------------------------
WITH latest_year AS (
    SELECT MAX(d.year) AS yr
    FROM fact_search_interest fsi
    JOIN dim_dates d ON d.date_id = fsi.date_id
    JOIN dim_sources s ON s.source_id = fsi.source_id
    WHERE s.source_name = 'Google Trends'
),
yearly AS (
    SELECT
        d.year,
        AVG(fsi.interest_score) AS avg_score
    FROM fact_search_interest fsi
    JOIN dim_dates d ON d.date_id = fsi.date_id
    JOIN dim_sources s ON s.source_id = fsi.source_id
    WHERE s.source_name = 'Google Trends'
    GROUP BY d.year
)
SELECT
    ly.yr AS current_year,
    ly.yr - 1 AS prior_year,
    ROUND(cur.avg_score, 2) AS current_year_avg,
    ROUND(prior.avg_score, 2) AS prior_year_avg,
    ROUND(
        100.0 * (cur.avg_score - prior.avg_score) / NULLIF(prior.avg_score, 0), 2
    ) AS yoy_growth_pct
FROM latest_year ly
LEFT JOIN yearly cur ON cur.year = ly.yr
LEFT JOIN yearly prior ON prior.year = ly.yr - 1;

-- ---------------------------------------------------------------
-- 9.3 Top Growing Peptide
-- per-peptide growth % (Google Trends, first 90 vs. last 90 days),
-- ranked descending -- the top row is the answer
-- ---------------------------------------------------------------
WITH bounds AS (
    SELECT MIN(d.date) AS min_date, MAX(d.date) AS max_date
    FROM fact_search_interest fsi
    JOIN dim_dates d ON d.date_id = fsi.date_id
    JOIN dim_sources s ON s.source_id = fsi.source_id
    WHERE s.source_name = 'Google Trends'
),
periods AS (
    SELECT
        fsi.peptide_id,
        CASE WHEN d.date < b.min_date + 90 THEN 'baseline'
             WHEN d.date > b.max_date - 90 THEN 'current'
             ELSE NULL END AS period,
        fsi.interest_score
    FROM fact_search_interest fsi
    JOIN dim_dates d ON d.date_id = fsi.date_id
    JOIN dim_sources s ON s.source_id = fsi.source_id
    CROSS JOIN bounds b
    WHERE s.source_name = 'Google Trends'
)
SELECT
    p.peptide_name,
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
WHERE period IS NOT NULL
GROUP BY p.peptide_name
ORDER BY growth_pct DESC NULLS LAST;

-- ---------------------------------------------------------------
-- 9.4 Fastest Growing UK Region
-- per-region growth % (Google Trends regional rows, first 90 vs.
-- last 90 days), ranked descending -- the top row is the answer.
-- Wikipedia rows never carry a region_id, so filtering to non-null
-- region_id already restricts this to Google Trends.
-- ---------------------------------------------------------------
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
GROUP BY r.region_name
ORDER BY growth_pct DESC NULLS LAST;

-- ---------------------------------------------------------------
-- 9.5 Largest Search Spike
-- (Peak Interest - Expected Interest) / Expected Interest x 100,
-- where Expected Interest = per-peptide mean (Google Trends) --
-- ranked descending, the top row is the answer
-- ---------------------------------------------------------------
WITH per_peptide AS (
    SELECT
        p.peptide_name,
        d.date,
        fsi.interest_score,
        AVG(fsi.interest_score) OVER (PARTITION BY fsi.peptide_id) AS expected_interest,
        ROW_NUMBER() OVER (PARTITION BY fsi.peptide_id ORDER BY fsi.interest_score DESC) AS rn
    FROM fact_search_interest fsi
    JOIN dim_dates d ON d.date_id = fsi.date_id
    JOIN dim_peptides p ON p.peptide_id = fsi.peptide_id
    JOIN dim_sources s ON s.source_id = fsi.source_id
    WHERE s.source_name = 'Google Trends'
)
SELECT
    peptide_name,
    date AS peak_date,
    interest_score AS peak_interest,
    ROUND(expected_interest, 2) AS expected_interest,
    ROUND(
        100.0 * (interest_score - expected_interest) / NULLIF(expected_interest, 0), 2
    ) AS spike_pct
FROM per_peptide
WHERE rn = 1
ORDER BY spike_pct DESC;
