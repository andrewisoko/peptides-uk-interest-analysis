-- ============================================================
-- 05. Cross-Source Comparison (Google Trends vs. Wikipedia)
-- ============================================================
-- Google Trends and Wikipedia are two independent signals of the
-- same underlying interest. Agreement between them is part of the
-- project's ">=3 independent sources" success metric (together with
-- events data as a third -- see 06_events_exploration.sql).

-- Weekly, per-peptide series side by side
SELECT
    d.date,
    p.peptide_name,
    ROUND(AVG(fsi.interest_score) FILTER (WHERE s.source_name = 'Google Trends'), 2) AS google_trends_score,
    ROUND(AVG(fsi.interest_score) FILTER (WHERE s.source_name = 'Wikipedia'), 2) AS wikipedia_score
FROM fact_search_interest fsi
JOIN dim_dates d ON d.date_id = fsi.date_id
JOIN dim_peptides p ON p.peptide_id = fsi.peptide_id
JOIN dim_sources s ON s.source_id = fsi.source_id
GROUP BY d.date, p.peptide_name
ORDER BY p.peptide_name, d.date;

-- Per-peptide correlation between the Google Trends and Wikipedia
-- series -- where do the two sources agree on timing/direction, and
-- where do they diverge?
WITH by_source AS (
    SELECT
        d.date,
        p.peptide_id,
        p.peptide_name,
        AVG(fsi.interest_score) FILTER (WHERE s.source_name = 'Google Trends') AS gt_score,
        AVG(fsi.interest_score) FILTER (WHERE s.source_name = 'Wikipedia') AS wiki_score
    FROM fact_search_interest fsi
    JOIN dim_dates d ON d.date_id = fsi.date_id
    JOIN dim_peptides p ON p.peptide_id = fsi.peptide_id
    JOIN dim_sources s ON s.source_id = fsi.source_id
    GROUP BY d.date, p.peptide_id, p.peptide_name
)
SELECT
    peptide_name,
    COUNT(*) AS n_weeks,
    ROUND(CORR(gt_score, wiki_score)::NUMERIC, 3) AS correlation
FROM by_source
GROUP BY peptide_name
ORDER BY correlation DESC NULLS LAST;
