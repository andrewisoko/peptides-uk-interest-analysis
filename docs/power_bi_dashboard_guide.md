# Power BI Dashboard Build Guide

A step-by-step walkthrough for building the KPI dashboard in Power BI Desktop
on top of the `peptides_uk` Postgres database. Follow this top to bottom —
each section depends on the one before it (connection → model →
relationships → measures → visuals).

Every DAX measure here reproduces one of the KPI queries in
`sql/07_kpis.sql` exactly. The expected result is noted next to each measure
so you can sanity-check your Power BI number against the SQL number once you
build it.

Prerequisite: the Postgres container must be running
(`docker compose up -d` from the repo root) and loaded
(`python -m src.load.run_all`). Both are already true as of this guide being
written — this session queried the live database directly.

---

## 1. Connect to the database

1. Open Power BI Desktop → **Get Data** → search **"PostgreSQL database"**.
2. **Server**: `localhost:5432` (from `POSTGRES_HOST`/`POSTGRES_PORT` in
   `.env` — change the port if you edited `.env` from the example).
3. **Database**: `peptides_uk`.
4. Leave **Data Connectivity mode** as **Import** (the whole dataset is
   ~3,600 rows total — no need for DirectQuery).
5. On the credentials prompt, choose **Database** authentication and enter
   the `POSTGRES_USER` / `POSTGRES_PASSWORD` values from your local `.env`
   file (not reproduced here — open `.env` yourself to copy them).
6. In the Navigator window, tick all 6 tables and click **Transform Data**
   (not Load yet):
   - `dim_peptides`
   - `dim_regions`
   - `dim_sources`
   - `dim_dates`
   - `fact_search_interest`
   - `fact_events`
7. In Power Query Editor, check each table's column types match what's in
   `database/schema.sql` (Power BI usually infers these correctly from
   Postgres, but confirm `dim_dates[date]` and `fact_events[event_date]` are
   typed as **Date**, not Date/Time). Click **Close & Apply**.

---

## 2. Build the relationships

Go to **Model view**. Power BI may auto-detect some relationships — verify
each one below and add any that are missing (drag from the "one" side's key
to the "many" side's key):

| From (dim) | To (fact) | Cardinality |
|---|---|---|
| `dim_peptides[peptide_id]` | `fact_search_interest[peptide_id]` | 1 → * |
| `dim_regions[region_id]` | `fact_search_interest[region_id]` | 1 → * |
| `dim_sources[source_id]` | `fact_search_interest[source_id]` | 1 → * |
| `dim_dates[date_id]` | `fact_search_interest[date_id]` | 1 → * |
| `dim_peptides[peptide_id]` | `fact_events[peptide_id]` | 1 → * |
| `dim_regions[region_id]` | `fact_events[region_id]` | 1 → * |
| `dim_dates[date]` | `fact_events[event_date]` | 1 → * |

**The last row is the one to pay attention to.** `fact_events` has no
`date_id` or `source_id` column at all (see `database/schema.sql`) — it only
carries a raw `event_date` date column. Every other fact-to-dim link in this
model goes through a surrogate integer key; this one has to be drawn
directly on the date values instead. There's also no relationship from
`dim_sources` to `fact_events` — that table distinguishes GDELT vs. PubMed
rows via the `category` text column, not a source key.

`region_id` is nullable on both fact tables (Wikipedia rows and some Google
Trends rows have no regional breakdown) — that's expected and doesn't break
the relationship; unmatched rows just won't participate in region-filtered
visuals, which is the correct behaviour.

---

## 3. Create the DAX measures

Create a new table for measures to keep things tidy: **Calculations → New
Table**, name it `_Measures`, formula `_Measures = ROW("x", BLANK())`, then
hide its one column (`x`). Add every measure below to this table
(**Calculations → New Measure** with `_Measures` selected). The live model
now has 20 measures across §3.1–3.8 — more than a first pass through this
guide would suggest, since §3.7 and §3.8 were added after a bug was found
during regional testing.

### 3.1 Date bounds (Google Trends only)

These hold the baseline/current windows fixed regardless of which peptide or
region a visual is filtered to — matching the SQL's `bounds` CTE, which is
computed from the whole Google Trends dataset, not per-peptide/per-region.

There are two versions of these bounds in the model. This pair (`MinDateGT`
/ `MaxDateGT`) is computed over **all** Google Trends rows, including the
ones with no regional breakdown. A second, region-scoped pair
(`MinDateGT_Region` / `MaxDateGT_Region`) was added later in §3.7 to fix a
bug in the by-region growth breakdown — use this original pair for
everything except KPI 9.4.

```dax
MinDateGT =
CALCULATE(
    MIN(dim_dates[date]),
    ALL(dim_peptides),
    ALL(dim_regions),
    dim_sources[source_name] = "Google Trends",
    CROSSFILTER(fact_search_interest[date_id], dim_dates[date_id], BOTH)
)


MaxDateGT =
CALCULATE(
    MAX(dim_dates[date]),
    ALL(dim_peptides),
    ALL(dim_regions),
    dim_sources[source_name] = "Google Trends",
    CROSSFILTER(fact_search_interest[date_id], dim_dates[date_id], BOTH)
)

```

### 3.2 Growth % — covers KPI 9.1 and 9.3 only (not 9.4 — see §3.7)

One measure pair. Dropped on a card with no other filters it reproduces
**KPI 9.1 (Overall Growth %)**. Dropped in a table/bar chart broken out by
`dim_peptides[peptide_name]` it reproduces **KPI 9.3 (Top Growing
Peptide)**.

**Do not break this measure out by `dim_regions[region_name]` for KPI
9.4** — it returns **-100% for every region**. `MaxDateGT` is the max date
across *all* Google Trends rows (2026-08-09), but the last ~90 days of data
have no regional breakdown at all — only rows with a blank `region_id`. Once
a specific region filter (e.g. Scotland) is applied on top of the `date >
MaxDateGT - 90` window, zero rows match, `Current Avg` comes back blank, and
`Growth %` divides a blank minus a real baseline by that baseline, i.e.
-100%. §3.7 has the fix and the measure to actually use for KPI 9.4
(`Region Growth %`).

Final DAX (uses a `VAR` for the bound so it's only evaluated once per call):

```dax
Baseline Avg =
VAR MinDate = [MinDateGT]
RETURN
CALCULATE(
    AVERAGE(fact_search_interest[interest_score]),
    dim_sources[source_name] = "Google Trends",
    FILTER(ALL(dim_dates), dim_dates[date] < MinDate + 90)
)

Current Avg =
VAR MaxDate = [MaxDateGT]
RETURN
CALCULATE(
    AVERAGE(fact_search_interest[interest_score]),
    dim_sources[source_name] = "Google Trends",
    FILTER(ALL(dim_dates), dim_dates[date] > MaxDate - 90)
)

Growth % =
DIVIDE([Current Avg] - [Baseline Avg], [Baseline Avg])
```

**Expected values to check against:**
- Overall (no filters): baseline **3.19**, current **15.62**, growth **389.85%**.
- By peptide, top row: **Retatrutide 70,580.77%**; bottom row: **Semaglutide 21.09%**.
- By region — do **not** use this measure; see §3.7 for the expected values.

Format `Growth %` as a percentage (divide by 100 is not needed — DIVIDE
already returns a ratio; just set the visual's format to `%` with 2 decimal
places, or wrap display-only cards in `FORMAT([Growth %], "0.00%")`).

### 3.3 Year-over-Year Growth % — KPI 9.2

```dax
CurrentYearGT =
CALCULATE(
    MAX(dim_dates[year]),
    ALL(dim_peptides),
    ALL(dim_regions),
    dim_sources[source_name] = "Google Trends"
)

Current Year Avg =
VAR CurrentYearGT = [CurrentYearGT]
RETURN
CALCULATE(
    AVERAGE(fact_search_interest[interest_score]),
    dim_sources[source_name] = "Google Trends",
    dim_dates[year] = CurrentYearGT
)

Prior Year Avg =
VAR CurrentYearGT = [CurrentYearGT]
RETURN
CALCULATE(
    AVERAGE(fact_search_interest[interest_score]),
    dim_sources[source_name] = "Google Trends",
    dim_dates[year] = CurrentYearGT - 1
)

YoY Growth % =
DIVIDE([Current Year Avg] - [Prior Year Avg], [Prior Year Avg])
```

**Expected:** current year **2026** (avg 12.94), prior year **2025** (avg
4.58), YoY growth **182.29%**.

### 3.4 Largest Search Spike — KPI 9.5

```dax
Expected Interest =
CALCULATE(
    AVERAGE(fact_search_interest[interest_score]),
    dim_sources[source_name] = "Google Trends",
    ALL(dim_dates)
)

Peak Interest =
CALCULATE(
    MAX(fact_search_interest[interest_score]),
    dim_sources[source_name] = "Google Trends"
)

Spike % =
DIVIDE([Peak Interest] - [Expected Interest], [Expected Interest])

Rank Within Peptide =
CALCULATE(
    RANKX(
        ALLSELECTED(dim_dates[date]),
        CALCULATE(
            MAX(fact_search_interest[interest_score]),
            dim_sources[source_name] = "Google Trends"
        )
    )
)
```

To show only each peptide's single peak row (matching the SQL's `rn = 1`
filter), build a table visual with `dim_peptides[peptide_name]`,
`dim_dates[date]`, `Peak Interest`, `Expected Interest`, `Spike %`, then add
a **visual-level filter**: `Rank Within Peptide` = **1**.

**Expected top rows, sorted by Spike % descending:** Epitalon (2026-01-04,
peak 2.0, expected 0.21, **872.84%**), TB-500 (2026-06-28, **802.29%**),
CJC-1295 (2026-07-12, **762.77%**), Tesamorelin (2026-05-10, **673.93%**),
Retatrutide (2026-08-02, peak 89.0, **435.03%**).

### 3.5 Population-normalized regional interest (context, not a formal KPI)

Raw regional averages don't account for England (58.6M) dwarfing Northern
Ireland (1.9M) in population. This measure gives a fairer per-capita view
for the Regional Analysis page:

```dax
Interest per Million Population =
DIVIDE(
    CALCULATE(
        AVERAGE(fact_search_interest[interest_score]),
        dim_sources[source_name] = "Google Trends",
        NOT ISBLANK(fact_search_interest[region_id])
    ),
    DIVIDE(SUM(dim_regions[population]), 1000000)
)
```

### 3.6 Cross-source correlation (context, KPI-adjacent)

Power BI's DAX doesn't have a simple built-in Pearson correlation over a
matrix the way SQL's `CORR()` does per-peptide without a custom table. The
straightforward way to get this into the report: import it as a **native
SQL query table** instead of a DAX measure (Get Data → PostgreSQL → paste
the second query from `sql/05_cross_source_comparison.sql` into the
"Advanced options → SQL statement" box before loading). 

1. Get Data → PostgreSQL database — same as your original connection (Get Data → search "PostgreSQL database").
2. In the connection dialog, enter the Server (localhost:5432) and Database (peptides_uk) the same as before.
3. Expand Advanced options in that same dialog (there's a small arrow/expander below the Server/Database fields).
4. A text box labeled "SQL statement (optional)" appears. Paste in the second query from sql/05_cross_source_comparison.sql

```
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

```
8. Click Transform Data if you want to rename columns or adjust types first (optional), or click Load directly to bring it straight into the model as its own standalone table.

9. Once loaded, you'll see this new table in your Fields pane — name it something clear like CrossSourceCorrelation if Power BI doesn't already give it a sensible name (you can rename it in Power Query Editor or directly in the Fields pane).

This one table is the exception to the "everything is a DAX measure" approach, since it's a smarter
per-peptide statistical summary rather than something that should respond
to slicers.

**Expected, ranked descending:** GHK-Cu 0.905, Tesamorelin 0.883, Retatrutide
0.818, CJC-1295 0.674, Ipamorelin 0.525, BPC-157 0.403, Epitalon 0.385,
Semaglutide 0.080, TB-500 0.078.

### 3.7 Region Growth % — the real KPI 9.4

`Growth %` (§3.2) breaks when filtered per-region because its date bounds
come from the *whole* Google Trends dataset, and the newest ~90 days of
data only exist as blank-region rows (no per-region breakdown yet). Once a
region filter is applied on top of that window, no rows match and the
measure silently returns -100%.

The fix is a second, region-scoped set of bounds that ignore rows with a
blank `region_id` when finding the min/max date — which pulls the "current"
window back to the last date that actually has regional data
(**2026-05-10**, vs. **2026-08-09** for the unrestricted bounds):

```dax
MinDateGT_Region =
CALCULATE(
    MIN(dim_dates[date]),
    ALL(dim_peptides),
    ALL(dim_regions),
    dim_sources[source_name] = "Google Trends",
    NOT ISBLANK(fact_search_interest[region_id]),
    CROSSFILTER(fact_search_interest[date_id], dim_dates[date_id], BOTH)
)

MaxDateGT_Region =
CALCULATE(
    MAX(dim_dates[date]),
    ALL(dim_peptides),
    ALL(dim_regions),
    dim_sources[source_name] = "Google Trends",
    NOT ISBLANK(fact_search_interest[region_id]),
    CROSSFILTER(fact_search_interest[date_id], dim_dates[date_id], BOTH)
)

Region Baseline Avg =
VAR MinDate = [MinDateGT_Region]
RETURN
CALCULATE(
    AVERAGE(fact_search_interest[interest_score]),
    dim_sources[source_name] = "Google Trends",
    FILTER(ALL(dim_dates), dim_dates[date] < MinDate + 90)
)

Region Current Avg =
VAR MaxDate = [MaxDateGT_Region]
RETURN
CALCULATE(
    AVERAGE(fact_search_interest[interest_score]),
    dim_sources[source_name] = "Google Trends",
    FILTER(ALL(dim_dates), dim_dates[date] > MaxDate - 90)
)

Region Growth % =
DIVIDE([Region Current Avg] - [Region Baseline Avg], [Region Baseline Avg])
```

Use `Region Growth %` (not `Growth %`) anywhere the report breaks growth out
by `dim_regions[region_name]` — that's KPI 9.4 on Page 1 and the regional
bar chart on Page 3.

**Expected, ranked descending:** Scotland **47.14%**, Wales **44.37%**,
England **41.01%**, Northern Ireland **29.23%**.

### 3.8 Event Rank by Article Count (Page 4 support measure)

```dax
Event Rank by Article Count =
RANKX(
    ALLSELECTED(fact_events),
    CALCULATE(SUM(fact_events[related_article_count]))
)
```

Ranks each row of `fact_events` by `related_article_count` within whatever
is currently selected. Used as an explicit visual-level filter (`Event Rank
by Article Count` ≤ 15) on the Page 4 events table instead of a plain
Top N visual filter, so the rank itself can also be shown as a column.

---

## 4. Report pages

Create 4 report pages (right-click the page tab area → rename each).

### Page 1 — Overview

- 4 **Card** visuals: `Growth %` (unfiltered, label it "Overall UK Search
  Interest Growth"), `YoY Growth %`, and two more showing the *name* of the
  top peptide/region — for the peptide one, add a **Table** visual with
  `dim_peptides[peptide_name]` + `Growth %`, sort descending by `Growth %`,
  and use a **Top N** visual filter (Top 1). For the region one, use
  `dim_regions[region_name]` + **`Region Growth %`** (not `Growth %` — see
  §3.7, plain `Growth %` returns -100% for every region). Convert each to a
  KPI-style card via **Format → General → Layout** if you want a
  single-number look, or just leave as a 1-row table.
- 1 **Line chart**: X-axis `dim_dates[date]`, Y-axis
  `AVERAGE(fact_search_interest[interest_score])` filtered to Google Trends
  (add a visual-level filter `dim_sources[source_name] = "Google Trends"`),
  legend by `dim_peptides[peptide_name]`.
- 1 **Slicer** on `dim_peptides[peptide_name]`, synced to affect the whole
  page.

### Page 2 — Peptide Deep Dive

- **Bar chart**: `dim_peptides[peptide_name]` on axis, `Growth %` on
  values, sorted descending.
- **Table**: `peptide_name`, `Baseline Avg`, `Current Avg`, `Growth %`.
- **Table** (the spike table from §3.4): `peptide_name`, `date`, `Peak
  Interest`, `Expected Interest`, `Spike %`, filtered to `Rank Within
  Peptide = 1`, sorted descending by `Spike %`.

### Page 3 — Regional Analysis

- **Bar chart** (or **Filled map** if you want to try Power BI's built-in UK
  map — set `dim_regions[region_name]` as the Location field, Category
  set to "State or Province"): `region_name` on axis, **`Region Growth %`**
  on values (use the region-scoped measure from §3.7, not plain `Growth %`,
  which returns -100% for every region here).
- **Bar chart**: `region_name` on axis, `Interest per Million Population` on
  values — compare the ranking to the growth chart above; note whether it
  changes.
- **Slicer** on `dim_regions[region_name]`.

### Page 4 — Cross-Source & Events Context

- **Table**: the imported cross-source-correlation query from §3.6
  (`peptide_name`, `n_weeks`, `correlation`), sorted descending.
- **Clustered column chart**: legend by `fact_events[category]`, values =
  count of rows, quarter axis via **`fact_events[YearQuarter]`** — a
  calculated column (`"Q" & FORMAT(fact_events[event_date], "Q") & " " &
  YEAR(fact_events[event_date])`), not `dim_dates`'s date hierarchy.
  Grouping by `dim_dates[quarter]` alone merges the same quarter across
  different years (Q1 2023 and Q1 2026 become one bucket), which is why
  this was pulled out as its own column on `fact_events` instead.
- **Table**: `fact_events[event_date]`, `dim_peptides[peptide_name]`,
  `category`, `title`, `related_article_count`, `source_count`, sorted
  descending by `related_article_count`. Filter with **`Event Rank by
  Article Count`** (§3.8) ≤ 15 rather than a plain Top N visual filter, so
  the rank is available to show as a column too.

---

## 5. Save and export

- Save the `.pbix` file wherever you keep working files for this project
  (e.g. a new `dashboards/` file alongside the empty `dashboards/exports/`
  folder already in the repo).
- Once you're happy with the report, use **File → Export → Export to PDF**
  (or **Export → Export to image** per page) and save the output into
  `dashboards/exports/` so the finished dashboard has a static artifact
  alongside the live `.pbix`.

If any DAX measure gives a number that doesn't match the "Expected" value
noted above, that's the fastest way to catch a mistake — recheck the
relationship or filter context for that measure before moving on.
