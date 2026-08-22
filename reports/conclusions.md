# UK Peptides Interest — Research Conclusions

Analysis of UK search interest, page-view activity, scientific publication
activity, and news/media activity for 9 research peptides
(BPC-157, TB-500, Retatrutide, Semaglutide, Ipamorelin, GHK-Cu, Epitalon,
Tesamorelin, CJC-1295) across 2023–2026, structured around the research
questions defined in the project brief (`claude/agents/orchestrator.md`).

All figures below were computed by running `sql/07_kpis.sql`,
`sql/05_cross_source_comparison.sql`, and `sql/06_events_exploration.sql`
directly against the live `peptides_uk` database
(9 peptides, 4 UK regions, 209 weekly dates, 3,292 search-interest rows,
334 events).

---

## Is UK interest increasing?

**Yes, substantially.** Comparing the first 90 days of data against the
last 90 days (Google Trends only — the one source on a consistent 0–100
relative scale; Wikipedia pageviews are excluded from growth KPIs as a
non-comparable scale):

- **Overall growth: +389.85%** (average interest score 3.19 → 15.62).
- **Year-over-year growth (2025 → 2026): +182.29%** (4.58 → 12.94).

Both metrics point the same direction and neither is a rounding artifact —
the underlying averages more than tripled in a single year and are nearly
5x higher comparing the very start to the very end of the dataset.

## Which peptides are driving it?

Per-peptide growth %, first 90 vs. last 90 days:

| Peptide | Baseline avg | Current avg | Growth % |
|---|---|---|---|
| Retatrutide | 0.12 | 83.15 | 70,580.77% |
| GHK-Cu | 0.06 | 6.31 | 10,623.08% |
| Tesamorelin | 0.12 | 6.92 | 5,784.62% |
| TB-500 | 0.03 | 1.62 | 5,392.31% |
| CJC-1295 | 0.03 | 1.54 | 5,130.77% |
| Epitalon | 0.09 | 0.92 | 946.15% |
| BPC-157 | 0.76 | 3.92 | 413.02% |
| Ipamorelin | 1.26 | 4.46 | 252.77% |
| Semaglutide | 26.24 | 31.77 | 21.09% |

**Read this table carefully — the percentages and the raw scores tell
different stories.** Six peptides started from a baseline near zero, so
even a small absolute rise in search interest produces an enormous
percentage figure (Retatrutide's 70,580% growth is a ~0.12 → 83 move, not a
gradual climb). Semaglutide is the opposite case: it's the only *already
approved* peptide in the set (per `dim_peptides.approved`) and by far the
highest-volume search term throughout the whole period (baseline 26.24,
still ~2–5x every other peptide's *current* score) — its modest 21% growth
reflects an already-mainstream topic, not a lack of momentum.

**Takeaway:** Retatrutide is the standout emerging-interest story of this
dataset — it goes from statistically invisible to the single
highest-scoring peptide in the current period (current avg 83.15, above
even Semaglutide's 31.77). GHK-Cu and Tesamorelin show the next-largest
genuine emergence. Semaglutide remains the steady, high-volume anchor
peptide rather than a growth driver.

## Where in the UK is interest growing?

All four UK regions grew, with no single outlier — growth is broad-based
rather than concentrated:

| Region | Baseline avg | Current avg | Growth % |
|---|---|---|---|
| Scotland | 7.78 | 11.44 | 47.14% |
| Wales | 7.89 | 11.39 | 44.37% |
| England | 7.72 | 10.89 | 41.01% |
| Northern Ireland | 7.22 | 9.33 | 29.23% |

Scotland and Wales edge out England and Northern Ireland, but the spread is
narrow (29%–47%) compared to the peptide-level spread (21%–70,580%) —
regional variation is a secondary effect next to which peptide is being
searched for.

## Largest individual spikes

Peak interest vs. each peptide's own long-run average ("expected interest"):

| Peptide | Peak date | Peak interest | Expected interest | Spike % |
|---|---|---|---|---|
| Epitalon | 2026-01-04 | 2.0 | 0.21 | 872.84% |
| TB-500 | 2026-06-28 | 3.0 | 0.33 | 802.29% |
| CJC-1295 | 2026-07-12 | 3.0 | 0.35 | 762.77% |
| Tesamorelin | 2026-05-10 | 11.0 | 1.42 | 673.93% |
| BPC-157 | 2026-06-28 | 7.0 | 1.22 | 474.58% |
| GHK-Cu | 2026-03-08 | 9.0 | 1.65 | 443.87% |
| Retatrutide | 2026-08-02 | 89.0 | 16.63 | 435.03% |
| Ipamorelin | 2023-01-01 | 7.0 | 1.39 | 403.28% |
| Semaglutide | 2026-08-09 | 66.0 | 21.77 | 203.22% |

## Which events explain the increase?

This is the project's most important research question, but the formal
metrics for it — **Event-Associated Excess Search Lift %** and **Event
Attribution Rate %** — are explicitly out of scope for this pass (see
`sql/07_kpis.sql`'s header comment): computing them properly requires
windowing decisions (how many days pre/post an event counts as "affected")
that haven't been made yet. What the data does support, descriptively:

- Events volume is heavily concentrated in **2026**: of 334 total events
  (242 Clinical research / PubMed, 92 News/Media / GDELT), the two biggest
  quarters are **2026 Q2** (52 clinical + 51 news) and **2026 Q3** (28
  clinical + 41 news) — the News/Media category barely exists before 2026
  at all.
- That surge lines up in time with the largest search spikes: Retatrutide's
  peak (2026-08-02) and Semaglutide's peak (2026-08-09) both land right
  after the Q2/Q3 2026 event surge, and Retatrutide is also the most
  *covered* peptide by far (93 events — 2x the next-highest, BPC-157 at 54).
- The highest-attention individual events by article/source count in 2026
  are almost all Semaglutide or Retatrutide clinical-research or news
  stories (e.g. "What Is the TB-500 Peptide?" — 166 articles/143 sources;
  "Doctors are using a regulatory gap to administer an unauthorized
  peptide" — 161/142; several Retatrutide obesity-trial stories in the
  30–45 article range).

This is a plausible, time-aligned story — search interest rising alongside
a concentrated burst of clinical and media coverage in 2026 — but it is
**correlational, not the formal attribution KPI**, and should be presented
to stakeholders as such.

## What are users trying to achieve?

**Data gap.** There is no user-intent field anywhere in the schema —
`dim_peptides.primary_usage` describes what each peptide is studied for
(e.g. "gastric/tissue injury repair" for BPC-157), not what an individual
searcher was looking for. Answering this would require new data (query-log
or survey data) that doesn't exist in this project. Flagged here rather
than approximated from `primary_usage`, since doing so would silently
conflate "what the peptide does" with "why someone searched."

## Do sources agree?

Per-peptide correlation between Google Trends and Wikipedia weekly series
(the project's ">=3 independent sources" success metric — events data being
the third):

| Peptide | Correlation |
|---|---|
| GHK-Cu | 0.905 |
| Tesamorelin | 0.883 |
| Retatrutide | 0.818 |
| CJC-1295 | 0.674 |
| Ipamorelin | 0.525 |
| BPC-157 | 0.403 |
| Epitalon | 0.385 |
| Semaglutide | 0.080 |
| TB-500 | 0.078 |

Agreement varies widely. GHK-Cu, Tesamorelin, and Retatrutide show strong
agreement — both sources move together, which is reassuring for those
peptides' growth numbers. **Semaglutide and TB-500 show essentially no
correlation (0.08).** For Semaglutide specifically, the most likely
explanation is that Wikipedia page-view traffic is driven by
brand-name/media attention (e.g. Ozempic/Wegovy coverage) that doesn't
track the compound-name Google Trends series this project deliberately
uses to avoid brand-name bias — worth flagging to stakeholders as a
divergence rather than treating either source as simply "wrong."

---

## Limitations and data gaps

- **KPIs 9.6, 9.7, 9.8 are not computed** — Event-Associated Excess Search
  Lift %, Event Attribution Rate %, and Most Common User Intent are all
  out of scope for this pass (see `sql/07_kpis.sql` and
  `notebooks/01_eda_roadmap.ipynb` §9.6–9.8). 9.8 additionally has no data
  path forward without new data collection.
- **Weekly, not daily, grain.** `dim_dates` holds one row per ISO week
  (209 rows over ~4 years), so "first/last 90 days" resolves to roughly 12
  weekly observations per window, not 90 individual daily readings.
- **Growth KPIs use Google Trends only.** Wikipedia pageviews are a
  different, non-comparable scale (raw pageviews vs. 0–100 relative), so
  mixing them would distort every growth/spike figure above.
- **Small N.** 9 peptides and 4 regions means single data points can swing
  a ranking noticeably — the peptide-level percentages in particular should
  be read as directional, not precise.
- **Percentage growth from near-zero baselines is dramatic but easy to
  over-read** — see the "Which peptides are driving it?" section above for
  why Retatrutide's 70,580% and Semaglutide's 21% are not directly
  comparable signals.

## Dashboard

An interactive Power BI dashboard covering every KPI above (with live
peptide/region/date slicers) can be built by following
[`docs/power_bi_dashboard_guide.md`](../docs/power_bi_dashboard_guide.md).
Once built, export a static copy of the report into `dashboards/exports/`
alongside the live `.pbix` file.
