-- Analytical schema for the peptides-uk-interest-analysis project.
-- Mirrors data/processed/: 4 dimension tables + 2 fact tables. The fact
-- tables each combine two processed CSVs from different sources (Google
-- Trends + Wikipedia; GDELT + PubMed) that share one grain and are already
-- distinguished by source_id/category -- see src/transform/transform_gdelt.py
-- for why those pairs are one logical fact table rather than two.
-- Runs automatically on first `docker compose up` via docker-entrypoint-initdb.d.

CREATE TABLE dim_peptides (
    peptide_id      INTEGER PRIMARY KEY,
    peptide_name    TEXT NOT NULL,
    primary_usage   TEXT NOT NULL,
    price_range     TEXT,
    approved        BOOLEAN NOT NULL
);

CREATE TABLE dim_regions (
    region_id       INTEGER PRIMARY KEY,
    region_name     TEXT NOT NULL,
    population      BIGINT NOT NULL
);

CREATE TABLE dim_sources (
    source_id       INTEGER PRIMARY KEY,
    source_name     TEXT NOT NULL,
    reliability     SMALLINT NOT NULL
);

-- date_id is YYYYMMDD as an int (e.g. 20230101), one row per ISO week
-- (Sunday-anchored) -- see src/utils/dates.py.
CREATE TABLE dim_dates (
    date_id         INTEGER PRIMARY KEY,
    date            DATE NOT NULL,
    month           SMALLINT NOT NULL,
    quarter         SMALLINT NOT NULL,
    year            SMALLINT NOT NULL
);

-- Loaded from search_interest_google_trends.csv + search_interest_wikipedia.csv.
-- region_id is nullable: Wikipedia page-view data has no UK-region breakdown.
CREATE TABLE fact_search_interest (
    date_id         INTEGER NOT NULL REFERENCES dim_dates(date_id),
    peptide_id      INTEGER NOT NULL REFERENCES dim_peptides(peptide_id),
    region_id       INTEGER REFERENCES dim_regions(region_id),
    source_id       INTEGER NOT NULL REFERENCES dim_sources(source_id),
    interest_score  NUMERIC NOT NULL
);

-- Loaded from events_gdelt.csv + events_pubmed.csv. category ("News/Media"
-- vs "Clinical research") is what tells the two sources apart, since this
-- table has no source_id column of its own (see transform_gdelt.py).
CREATE TABLE fact_events (
    event_date              DATE NOT NULL,
    related_article_count   INTEGER NOT NULL,
    source_count            INTEGER NOT NULL,
    category                TEXT NOT NULL,
    title                   TEXT NOT NULL,
    region_id               INTEGER REFERENCES dim_regions(region_id),
    peptide_id              INTEGER NOT NULL REFERENCES dim_peptides(peptide_id)
);

CREATE INDEX idx_fact_search_interest_peptide ON fact_search_interest(peptide_id);
CREATE INDEX idx_fact_search_interest_date ON fact_search_interest(date_id);
CREATE INDEX idx_fact_events_peptide ON fact_events(peptide_id);
