
 <div align="center">

 # UK Peptides Interest Analysis 💉💊

</div>

An end-to-end data pipeline and analysis project studying public and clinical
interest in nine research/performance peptides in the UK, from 2023 through
2026. Raw signals from five independent sources are extracted, transformed
into a star schema, loaded into Postgres, and explored in SQL and a Jupyter
notebook to answer a fixed set of research questions and KPIs.

## Table of contents

- [Project scope](#project-scope)
- [Peptides tracked](#peptides-tracked)
- [Data sources](#data-sources)
- [Architecture](#architecture)
- [Star schema](#star-schema)
- [Key data decisions](#key-data-decisions)
- [Getting started](#getting-started)
- [Running the pipeline](#running-the-pipeline)
- [Analysis](#analysis)
- [Success metrics and KPIs](#success-metrics-and-kpis)
- [Known data gaps and limitations](#known-data-gaps-and-limitations)
- [Repository layout](#repository-layout)

## Project scope

The brief (`data/data_dictionary/Peptides_UK_Setup_Info.xlsx`) asks: **is UK
interest in these peptides growing, where, for which peptides, and does that
interest track with real-world events (news coverage and clinical research
output)?** The project window is **2023-01-01 to 2026-12-31**, and every
fact table, date bound, and validation check in the codebase enforces that
window.

Success for the project is defined as:

- Every research question answered with evidence, not opinion.
- Findings corroborated by **at least 3 independent data sources** where
  possible (Google Trends + Wikipedia as two independent "popularity"
  signals, GDELT + PubMed as two independent "real-world activity"
  signals, plus ONS for regional population context).
- Reproducible end-to-end from this repository — anyone can re-run
  extract → transform → load → analyse and get the same tables.
- A report that names the *drivers* of interest, not just describes trends.
- A dashboard that lets a stakeholder answer every research question
  interactively (not yet built — see [Known data gaps and
  limitations](#known-data-gaps-and-limitations)).

## Peptides tracked

Nine peptides, spanning approved pharmaceuticals, late-stage trial
candidates, and unregulated research-chemical-market compounds:

| Peptide | Primary usage (authored, see [Key data decisions](#key-data-decisions)) | Approved (MHRA/FDA/EMA) |
|---|---|---|
| BPC-157 | Gastric/tissue injury repair, studied mainly in animal models | No |
| TB-500 | Tissue repair and wound healing, studied mainly in animal models | No |
| Retatrutide | Triple hormone-receptor agonist studied for obesity and T2D weight loss | No |
| Semaglutide | GLP-1 receptor agonist for T2D and chronic weight management | Yes |
| Ipamorelin | Growth hormone secretagogue studied for GH release and body composition | No |
| GHK-Cu | Copper-binding peptide studied for skin repair, collagen production, wound healing | No |
| Epitalon | Synthetic tetrapeptide studied for telomerase activation and cellular ageing | No |
| Tesamorelin | GHRH analogue for visceral fat reduction; US-approved (Egrifta) but not MHRA-approved | No |
| CJC-1295 | GHRH analogue studied for sustained GH/IGF-1 elevation | No |

`approved` and `primary_usage` reflect status **as of the project's
2023-2026 data window** and should be re-verified before reuse — several of
these, Retatrutide especially, are active late-stage trial candidates whose
regulatory status changes.

## Data sources

| Source | What it provides | Feeds |
|---|---|---|
| **Google Trends** | Weekly national + baseline/current regional (nation-level) search interest, 0-100 relative index | `fact_search_interest` |
| **Wikipedia (Wikimedia Pageviews API)** | Daily en.wikipedia pageviews per peptide article | `fact_search_interest` |
| **GDELT** (Global Database of Events, Language, and Tone) | Top 250 most-relevant news articles per peptide, no date filter | `fact_events` (category = `News/Media`) |
| **PubMed** (NCBI E-utilities) | Publication search + summaries per peptide, date-bounded 2023-2026 | `fact_events` (category = `Clinical research`) |
| **ONS** (Office for National Statistics) | Mid-2024 UK population estimates by nation | `dim_regions` |

All five raw extractors live under `data/raw/<source>/<source>_api.py` and
follow the same pattern (`data/raw/design_pattern.py`): a `requests`-based
fetch with exponential backoff on HTTP 429 (60s, 120s, 240s, 480s, 960s,
plus jitter), a fixed `User-Agent`, and a `save_raw()` that writes untouched
JSON/XLSX straight to `data/raw/`. Nothing under `data/raw/` is cleaned or
reshaped — that only happens in `src/transform/`.

## Architecture

The pipeline is a classic four-stage ETL, run in order:

```
1. EXTRACT   data/raw/<source>/<source>_api.py
             -> data/raw/<source>/*.json (or .xlsx)

2. TRANSFORM src/transform/*.py
             parse -> clean -> standardise -> integrate -> validate
             -> data/processed/{dimensions,search_interest,events,geography}/*.csv

3. LOAD      src/load/*.py  (src/load/run_all.py runs all of them, in FK order)
             -> Postgres (docker-compose), truncate-then-bulk-insert per table

4. ANALYSE   sql/*.sql               (ad-hoc SQL exploration + KPI queries)
             notebooks/01_eda_roadmap.ipynb  (Python/pandas EDA + KPI notebook)
```

Every transform script follows the same five-method shape — `parse`,
`clean`, `standardise`, `integrate`, `validate` — so the source-specific
logic (what a `<1%` Google Trends cell means, how GDELT's `seendate` string
parses, whether a source has regional granularity) is the only thing that
differs between them; I/O, ID resolution, and the shared null/FK/date-bound
checks are centralised in `src/utils/`.

## Star schema

Four dimension tables and two fact tables (`database/schema.sql`):

```
dim_peptides (9 rows)      dim_regions (4 rows)      dim_sources (5 rows)      dim_dates (209 rows)
  peptide_id PK               region_id PK               source_id PK              date_id PK (YYYYMMDD int)
  peptide_name                region_name                source_name               date
  primary_usage                population                reliability (1-10)        month / quarter / year
  price_range (nullable)
  approved

fact_search_interest                         fact_events
  date_id      FK -> dim_dates                 event_date
  peptide_id   FK -> dim_peptides               related_article_count
  region_id    FK -> dim_regions, NULLABLE      source_count
  source_id    FK -> dim_sources                category ("News/Media" | "Clinical research")
  interest_score                               title
                                                region_id  FK -> dim_regions, NULLABLE
                                                peptide_id FK -> dim_peptides
```

**Both fact tables are each fed by two sources sharing one grain**, rather
than being split into four separate fact tables:

- `fact_search_interest` = Google Trends rows + Wikipedia rows. Both are
  weekly peptide-level "popularity" signals on a 0-100 scale, told apart by
  `source_id`.
- `fact_events` = GDELT rows + PubMed rows, aggregated to one row per
  peptide/week. Both are weekly peptide-level "real-world activity" counts,
  told apart by `category` (no `source_id` column exists on this table —
  see `src/transform/transform_gdelt.py`'s header comment for the
  reasoning).

`region_id` is a **nullable FK on both fact tables**, because Wikipedia
pageviews and PubMed/GDELT records carry no UK-region signal at all — only
Google Trends' regional snapshots do. Any regional query must filter to
`region_id IS NOT NULL`, which (by construction) restricts it to Google
Trends rows.

`database/schema.sql` is mounted into the Postgres container's
`docker-entrypoint-initdb.d/`, so it runs automatically, once, the first
time `docker compose up` creates the data volume.

## Key data decisions

A running list of the non-obvious calls made while wrangling five
inconsistent raw sources into one consistent schema — each is also
commented at its source in code.

- **Weekly grain, Sunday-anchored.** Every fact row is bucketed to the
  Sunday-starting week it falls in (`src/utils/dates.py::to_week_start`),
  matching Google Trends' own `Week` column convention. Wikipedia's daily
  pageviews are summed into weekly totals to match.
- **`YYYYMMDD` integer date keys.** `dim_dates.date_id` is an int like
  `20230101` — sorts and joins like a normal surrogate key while staying
  human-readable in the fact tables.
- **Google Trends `"<1%"` / `"<1"` → `0.5`.** Google's way of saying "some
  interest, but under 1%" is treated as the midpoint rather than 0 or 1.
- **Google Trends blank regional cells → `0.0`**, not dropped — this keeps
  every region × window × peptide combination present in the output rather
  than producing gappy regional coverage.
- **Regional snapshots are two static windows, not a time series.**
  Google Trends' regional pages don't support genuine weekly regional data
  at UK-nation granularity, so each peptide has a `baseline`
  (2023-01-01) and `current` (2026-05-15) snapshot, each collapsed to one
  representative week. **Every regional query is a two-point comparison,
  not a trend line.**
- **Regions are nation-level only (England/Scotland/Wales/Northern
  Ireland),** not the finer 9-English-region breakdown ONS also provides
  (`data/raw/ons/regions_uk.json`). Google Trends' English sub-region
  export kept failing server-side, so the whole regional dimension was
  scoped down to match what could actually be collected.
- **Wikipedia scores are self-normalised, not cross-comparable.**
  Wikipedia pageviews have no shared "anchor" term the way Google Trends
  queries do, so each peptide's weekly views are indexed against *its own*
  peak week (`views / peak_views * 100`). A Wikipedia `interest_score` is
  only meaningful week-to-week within one peptide — never compare it
  across peptides, and never mix it with Google Trends scores in the same
  aggregate (see below).
- **KPIs are computed on Google Trends only.** Google Trends' 0-100 scale
  is consistent across the whole date range and across peptides; Wikipedia
  pageviews are a different, larger, non-comparable scale. All growth/spike
  KPIs in `sql/07_kpis.sql` filter to `source_name = 'Google Trends'` for
  this reason — mixing sources would silently distort every figure.
  Wikipedia still serves its purpose as the second independent source for
  cross-source *validation* (agreement/disagreement, not blended averages).
- **`dim_sources.reliability` and event `category` are authored, not
  parsed.** None of the five raw sources self-report a reliability score
  or classify their own content, so these are documented judgment calls
  (`src/utils/mappings.py::SOURCE_RELIABILITY`) rather than derived values:
  ONS 10, PubMed 9, Google Trends 7, Wikipedia 6, GDELT 5.
- **`dim_peptides.primary_usage` / `price_range` / `approved` are
  manually authored**, evidence-assisted by mining each peptide's PubMed
  title keywords (`src/transform/build_dim_peptides.py`) but written by
  hand — no raw source gives clinical usage, pricing, or approval status.
  `price_range` is left `NULL` for every peptide: no source has reliable
  pricing data, and a fabricated number would be worse than an honest gap.
- **GDELT has no date filter server-side.** Its free `doc` API returns
  only the top 250 most-relevant hits with no date bound, so the
  transform enforces the project's 2023-2026 window itself at validation
  time rather than trusting the API response.
- **PubMed's `sortpubdate` can fall just outside the fetch window.**
  The search itself is date-bounded (`datetype=pdat`), but
  `sortpubdate` reflects a different date facet (e.g. an earlier epub
  date) that occasionally lands outside 2023-2026. Those rare rows are
  dropped during `clean()` rather than allowed to violate the project's
  date bounds downstream.
- **GDELT/PubMed events are aggregated to peptide/week**, not kept as
  individual articles — `related_article_count` and `source_count`
  (distinct domains/journals) are computed per group, and `title` keeps
  the *most relevant* article/publication for that week (both APIs
  return results pre-sorted by relevance, so `first` after grouping is a
  deliberate pick, not an arbitrary one).
- **GDELT/PubMed events have no region.** Neither API ties an
  article/publication to a UK nation (GDELT's `sourcecountry` is the
  *outlet's* country, not the subject's), so `region_id` is `NULL` for
  every event row.

## Getting started

**Prerequisites:** Python 3.11, Docker Desktop (for Postgres).

```bash
# 1. Clone and enter the repo, then create a virtual environment
python -m venv .venv
.venv/Scripts/activate       # Windows
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env         # then edit POSTGRES_* values as needed

# 3. Start Postgres (creates the star schema automatically on first run)
docker compose up -d
```

## Running the pipeline

Raw data is already committed under `data/raw/` (extract has already been
run), so a fresh clone only needs transform + load to reproduce
`data/processed/` and the database. Re-run extract only to refresh the raw
snapshots.

```bash
# 1. EXTRACT (optional — re-fetches from live APIs; raw data is already committed)
python data/raw/gdelt/gdelt_api.py
python data/raw/pubmed/pubmed_api.py
python data/raw/wikipedia/wikipedia_api.py
python data/raw/ons/ons_api.py
# Google Trends has no API script — its CSVs were exported manually from
# https://trends.google.com and placed under data/raw/google_trends/.

# 2. TRANSFORM — run from the repo root, produces data/processed/*
python -m src.transform.build_dim_peptides
python -m src.transform.build_dim_sources
python -m src.transform.build_dim_dates
python -m src.transform.transform_ons
python -m src.transform.transform_google_trends
python -m src.transform.transform_wikipedia
python -m src.transform.transform_gdelt
python -m src.transform.transform_pubmed

# 3. LOAD — loads dimensions before facts (FK order enforced internally)
python -m src.load.run_all

# 4. ANALYSE
jupyter notebook notebooks/01_eda_roadmap.ipynb
# or run sql/*.sql directly against the Postgres instance
```

Every transform and load script validates its own output before writing —
null checks, foreign-key checks against the dimension CSVs, and date-bound
checks (`src/utils/validate.py`) — and raises a `ValueError` with the
offending row count/values rather than silently writing bad data.

## Analysis

`sql/` holds seven numbered exploration scripts, meant to be worked through
in order against the loaded database:

1. `01_data_quality.sql` — null counts, row counts, `region_id` null-rate by
   source (sanity-checks the design decisions above).
2. `02_dimension_profiling.sql` — dimension contents (peptides, regions by
   population, sources by reliability).
3. `03_distribution_and_trends.sql` — `interest_score` distribution by
   source (confirms Google Trends vs. Wikipedia are non-comparable scales).
4. `04_regional_analysis.sql` — baseline vs. current regional snapshots.
5. `05_cross_source_comparison.sql` — Google Trends vs. Wikipedia agreement
   per peptide (the multi-source-validation success metric).
6. `06_events_exploration.sql` — GDELT vs. PubMed event volume over time.
7. `07_kpis.sql` — the KPI formulas from the brief, computed on Google
   Trends only (see [Key data decisions](#key-data-decisions)).

`notebooks/01_eda_roadmap.ipynb` mirrors this same progression in
pandas/matplotlib/seaborn, with one section per KPI and a closing "Insights
Synthesis" section for report-writing. It's a **roadmap with starter cells
and TODOs, not a finished analysis** — event-lift KPIs (9.6/9.7) in
particular are left as `NotImplementedError` stubs for the analyst to
complete.

## Success metrics and KPIs

Defined in the `Success Metrics` and `KPIs` sheets of
`data/data_dictionary/Peptides_UK_Setup_Info.xlsx`; every KPI formula uses
`(current - baseline) / baseline * 100`.

| # | KPI | Status |
|---|---|---|
| 9.1 | Overall UK Search Interest Growth % | Implemented (`sql/07_kpis.sql`) |
| 9.2 | Year-over-Year Growth % | Implemented |
| 9.3 | Top Growing Peptide | Implemented |
| 9.4 | Fastest Growing UK Region | Implemented |
| 9.5 | Largest Search Spike | Implemented |
| 9.6 | Event-Associated Excess Search Lift % | Not implemented — needs a windowing decision around each event (see below) |
| 9.7 | Event Attribution Rate % | Not implemented — depends on 9.6 and 9.5's spike list |
| 9.8 | Most Common User Intent | Out of scope — data gap, no source captures user intent |

## Known data gaps and limitations

- **No "user intent" data exists anywhere in the pipeline.** KPI 9.8 asks
  for search/response intent, but none of the five sources capture *why*
  someone searched — `dim_peptides.primary_usage` describes the peptide,
  not a searcher's goal. Computing 9.8 as specified would require new data
  (e.g. query-log or survey data) this project doesn't have.
- **Event-lift KPIs (9.6, 9.7) are stubbed, not computed.** They require
  choosing pre/post/baseline windows around each individual event before a
  lift figure is meaningful; `notebooks/01_eda_roadmap.ipynb` section 8
  leaves this as a `TODO` for the analyst.
- **Regional data is two static snapshots, not a trend.** Anything asking
  "how has region X changed over time" cannot be answered from
  `fact_search_interest`'s regional rows — only baseline-vs-current can be.
- **No dashboard yet.** The "Dashboard completeness" success metric (an
  interactive tool for stakeholders) isn't built in this repository; the
  SQL scripts and notebook are the analysis layer today.
- **`price_range` is `NULL` for all nine peptides** — no source in this
  project has reliable pricing data.
- **`approved` / `primary_usage` are point-in-time judgments** (as of the
  2023-2026 window) and should be re-verified before reuse, especially for
  peptides in active trials.

  # Dashboard example

  ![ image alt](https://github.com/andrewisoko/peptides-uk-interest-analysis/blob/fa149f4fce2dc3e60e5af0c459668ecd91ad2ac0/screenshots/Overview.png)


## Repository layout

```
data/
  raw/                    Untouched extractor output, one folder per source
    <source>/<source>_api.py
  processed/              Transform output (gitignored contents regenerate
                           from raw via src/transform/*.py)
    dimensions/            peptides.csv, regions.csv, sources.csv, dates.csv
    search_interest/       search_interest_google_trends.csv, search_interest_wikipedia.csv
    events/                events_gdelt.csv, events_pubmed.csv
    geography/             ons_population_staging.csv
  data_dictionary/        Peptides_UK_Setup_Info.xlsx — the project brief
                           (Data Dictionary, Success Metrics, KPIs sheets)
database/
  schema.sql              Star schema DDL, auto-applied by docker-compose
src/
  transform/               parse -> clean -> standardise -> integrate -> validate,
                           one file per source (+ build_dim_* for authored dimensions)
  load/                    Postgres loaders, one per table, plus run_all.py
  utils/                   Shared date/ID/validation/I-O helpers
sql/                      Numbered exploration + KPI queries
notebooks/
  01_eda_roadmap.ipynb    pandas/seaborn EDA roadmap, mirrors sql/ progression
docker-compose.yml         Single postgres:16 service, schema auto-init
requirements.txt
.env.example               Copy to .env; POSTGRES_* credentials (gitignored)
```
