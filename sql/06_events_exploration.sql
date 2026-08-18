-- ============================================================
-- 06. Events Exploration
-- ============================================================
-- category distinguishes the two sources combined into fact_events:
-- 'News/Media' (GDELT) vs. 'Clinical research' (PubMed). There is no
-- source_id column on this table (see database/schema.sql).

SELECT category, COUNT(*) AS n_events
FROM fact_events
GROUP BY category
ORDER BY n_events DESC;

-- Events per quarter by category
SELECT
    EXTRACT(YEAR FROM event_date) AS year,
    EXTRACT(QUARTER FROM event_date) AS quarter,
    category,
    COUNT(*) AS n_events
FROM fact_events
GROUP BY year, quarter, category
ORDER BY year, quarter, category;

-- Events per peptide, ranked
SELECT
    p.peptide_name,
    COUNT(*) AS n_events
FROM fact_events fe
JOIN dim_peptides p ON p.peptide_id = fe.peptide_id
GROUP BY p.peptide_name
ORDER BY n_events DESC;

-- Events with unusually high related_article_count or source_count
-- (at or above the 90th percentile within their own category), and
-- whether they cluster around particular peptides/dates
WITH thresholds AS (
    SELECT
        category,
        PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY related_article_count) AS article_p90,
        PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY source_count) AS source_p90
    FROM fact_events
    GROUP BY category
)
SELECT
    fe.event_date,
    p.peptide_name,
    fe.category,
    fe.title,
    fe.related_article_count,
    fe.source_count
FROM fact_events fe
JOIN dim_peptides p ON p.peptide_id = fe.peptide_id
JOIN thresholds t ON t.category = fe.category
WHERE fe.related_article_count >= t.article_p90
   OR fe.source_count >= t.source_p90
ORDER BY fe.related_article_count DESC, fe.source_count DESC;
