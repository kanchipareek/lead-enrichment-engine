# lead-enrichment-engine

A SQLite-first lead enrichment and qualification pipeline that turns messy company
lists into deduplicated, enriched, ICP-scored accounts and ranked contact/email
candidates — all in one database file.

This is Project 1 of five in a GTM engineering portfolio. The plan is one machine:
clean the data, find the signal, research the account, qualify it, write the
outreach, catch the replies, measure what happened. This repo is the first half —
everything up to deciding who is worth contacting. The other four projects read
this database instead of building their own.

**Stack:** Python + SQLite, standard library only. No pandas, no requests, no ORM.
Every transformation is a `.sql` file in git, so when a number looks wrong I can
point at the exact rule that produced it.

## Architecture

             ┌───────────────────────┐
             │   Raw company lists   │
             │   CSV / YC / ATS ...  │
             └───────────┬───────────┘
                         │
             ┌───────────▼───────────┐
             │     CLEAN + DEDUPE    │
             │ normalize -> identity │
             │ exact -> fuzzy review │
             └───────────┬───────────┘
                         │
             ┌───────────▼───────────┐
             │        ENRICH         │
             │  website -> GitHub    │
             │  crawl -> LLM extract │
             └───────────┬───────────┘
                         │
             ┌───────────▼───────────┐
             │      ICP SCORING      │
             │  2 configs + weights  │
             │ threshold -> accounts │
             └───────────┬───────────┘
                         │
             ┌───────────▼───────────┐
             │    CONTACT + EMAIL    │
             │  people -> candidates │
             │  ranking -> output    │
             └───────────┬───────────┘
                         │
                         ▼
             ┌───────────────────────┐
             │  SQLite data contract │
             │  accounts . contacts  │
             │  signals  . scores    │
             └───────────┬───────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
     Project 2      Project 3      Projects 4-5

One file is the source of truth.

**Tables:** `raw_sources`, `companies`, `merge_log`, `match_candidates`,
`company_fields`, `crawl_log`, `contacts`, `contact_runs`, `contact_candidates`,
`icp_configs`, `icp_thresholds`, `scoring_eval`.

**Views (computed on read):** `company_features`, `company_scores`, `qualified`,
`disqualified`, `email_waterfall`, `best_email`, `field_quality`, `crawl_failures`.
Scoring is **not** stored in the `icp_scores` table (it exists in the schema but is
not populated) — read the `qualified` view.

Enrichment is stored narrow (one row per field per company) so every value carries
value + source + source_url + timestamp.

## Project structure

```
lead-enrichment-engine/
├── data/
│   ├── raw/                      # raw source CSVs
│   ├── eval/                     # eval artifacts
│   ├── processed/                # processed output
│   ├── raw_companies.csv         # the raw company list
│   ├── eval_set.csv
│   ├── eval_labels.csv
│   ├── idempotency_snapshot.json
│   └── lead_enrichment.db        # the SQLite database
├── scripts/                      # pipeline + eval + audit scripts
│   ├── run_sql.py                # executes a .sql file
│   ├── import_raw.py             # load raw CSVs
│   ├── show_schema.py            # print tables / columns
│   ├── crawl.py                  # polite website crawler
│   ├── crawl_summary.py          # crawl stats
│   ├── github_find.py            # GitHub org search
│   ├── github_verify.py          # domain-evidence verification
│   ├── github_resolve.py         # match decisions
│   ├── github_homepage_links.py  # footer audit
│   ├── github_stats.py           # repo stats
│   ├── manual_orgs.py            # hand-found org pairs
│   ├── resolve_matches.py        # duplicate review loop
│   ├── coverage_stats.py         # site / GitHub coverage
│   ├── make_eval_set.py          # build the 50-company eval set
│   ├── label_eval.py             # hand-label helper
│   ├── extract.py                # LLM extraction
│   ├── extract_batch.py          # batch attempt (parked)
│   ├── eval_extraction.py        # extraction eval
│   ├── list_models.py            # list live models
│   ├── test_call.py              # API probe
│   ├── make_view.py              # data-quality views
│   ├── audit_values.py           # per-field audit
│   ├── check_idempotency.py      # idempotency snapshot
│   ├── test_idempotency.py       # re-run diff
│   ├── score_report.py           # scoring report + breakdown
│   ├── score_distribution.py     # score histogram
│   ├── make_scoring_eval.py      # sampling for the scoring check
│   ├── label_scoring.py          # labelling loop
│   ├── label_blind.py            # blind labelling (no score shown)
│   ├── eval_scoring.py           # scoring check
│   ├── apply_labels.py           # rule-based labels
│   ├── audit_coverage.py         # reach measurement
│   ├── extract_contacts.py       # contact extraction
│   ├── generate_candidates.py    # email waterfall
│   └── test_groq.py              # Groq probe
├── sql/                          # every transformation, in order
│   ├── schema.sql
│   ├── 01_normalize.sql
│   ├── 02_exact_dedupe.sql
│   ├── 03_near_dupe_queue.sql
│   ├── 04_canonicalize.sql
│   ├── 05_prefix_queue.sql
│   ├── 06_crawl_log.sql
│   └── 07_score.sql
├── src/
│   ├── init_db.py                # create the database from sql/schema.sql
│   ├── config.py                 # settings from env vars (secrets never committed)
│   ├── log.py                    # structured logging
│   ├── retry.py                  # bounded backoff + rate limiter
│   └── schemas.py                # typed value contracts for extracted fields
├── tests/
│   └── test_core.py              # unit tests (retry, schemas)
├── docs/
│   └── CONTRACT.md               # the stable data contract for Projects 2-5
├── run.py                        # one command: runs the whole pipeline in order
├── .env.example                  # template for API keys (real .env is gitignored)
├── .gitignore
├── decisions.md
└── README.md
```

## Sample output

```
$ python scripts/score_report.py

qualified per config:
  devtools_ai_infra: 79
  generic_b2b_saas:  59

company     config              score  qualified
------------------------------------------------
Vercel      devtools_ai_infra     100  yes
Linear      devtools_ai_infra     100  yes
Databricks  devtools_ai_infra     100  yes
Supabase    devtools_ai_infra      95  yes
Stripe      generic_b2b_saas      100  yes
Notion      generic_b2b_saas       95  yes
Anthropic   devtools_ai_infra      70  yes

why Vercel scored 100 (devtools_ai_infra):
  +35 cat_dev_tools  +25 has_tech_signals  +20 active_github
  +15 stars_500  +5 sells_to_business  = 100
```

## Numbers

| Step | Result |
|---|---|
| raw rows in | 230 (4 sources, duplicates and traps planted on purpose) |
| companies out | 218 (12 duplicates resolved, 0 false merges on my own traps) |
| crawl | 564 attempts = 540 ok + 24 failed, across 23 companies |
| GitHub orgs | 179 matched (130 exact, 31 verified, 18 by hand); 39 with none |
| AI extraction | 199/199 extracted; 154/154 citations traced to source text |
| qualified | 59 (generic B2B SaaS) / 79 (dev tools + AI infra) = 138 unique accounts |
| reach | 25 of 138 qualified accounts have a contact (18%) |
| contacts | 142 people across 29 companies |

The raw list is messy on purpose. I planted 12 duplicates and 5 lookalike pairs
(Linear vs LinearB, Clay vs Clayton, ...) because a pipeline that has never been
attacked is not trustworthy. It caught all 5 traps and rejected all 12 fuzzy
candidates. A test that never fails teaches you nothing.

## How to run

```bash
# one command runs the whole pipeline in order:
python run.py

# or step by step:
python src/init_db.py
python scripts/import_raw.py data/raw_companies.csv
python scripts/run_sql.py sql/01_normalize.sql      # then 02 ... 06 in order
python scripts/resolve_matches.py                   # human review of fuzzy pairs
python scripts/crawl.py
python scripts/github_find.py && python scripts/github_verify.py
python scripts/github_stats.py
python scripts/extract.py
python scripts/run_sql.py sql/07_score.sql
python scripts/extract_contacts.py
python scripts/generate_candidates.py

# tests:
python -m unittest discover tests
```

API keys (Gemini, Groq, GitHub) are read from environment variables, never from
code. Copy `.env.example` to `.env` and fill it in; `.env` is gitignored.

## The extraction eval

Before running the extraction at volume I hand-labelled 50 companies. On the 45
with usable page text: 154 fields filled, all 154 citations traced back to the
source, zero fields invented. Agreement with my own labels was 38/45 (84%) — which
is worse than a dumb "accept everything" rule (45/45).

Every disagreement had the same cause: the model said unknown for who the company
sells to, and my quick verdict proxy treated that as disqualifying. The model was
right to say unknown instead of guessing. The proxy was wrong. That finding is why
a missing audience is **not disqualified** — though it does forfeit the business
weight, so it is a stated penalty, not a free pass.

## The scoring eval — read this part carefully

This one is a **rule-consistency check, not validation.** It asks "does the scoring
agree with my own ICP definition?" — not "is my ICP right?"

60 pairs, sampled as 10 qualified + 10 near-threshold + 10 below per config:

| config | n | TP | FP | FN | TN | precision | recall |
|---|---|---|---|---|---|---|---|
| devtools_ai_infra | 30 | 20 | 0 | 9 | 1 | 1.00 | 0.69 |
| generic_b2b_saas | 30 | 10 | 0 | 0 | 20 | 1.00 | 1.00 |

Don't read too much into those 1.00s. The labels are not independent of the score:
I could see the scores while labelling, and the final labels came from the same
category logic the scorer uses. So precision and recall here measure
self-consistency, not correctness. I also tuned the threshold on these same 60
pairs, which is leakage. And n=30 per config, so with zero false positives the true
precision could be as low as ~0.89.

The first honest test of whether the ICP is right is reply and meeting data from
Project 4. That has not happened yet.

## Engineering depth

The pipeline is also built to be maintained, not just to work:

- **Structured logging** (`src/log.py`) instead of scattered prints.
- **Bounded retry with backoff and a rate limiter** (`src/retry.py`).
- **Typed value contracts** (`src/schemas.py`) validating what the extractor may return.
- **Unit tests** (`tests/`) for the retry and schema logic.
- **Config and secrets** in environment variables, with a committed `.env.example`.
- **One-command setup** (`run.py`).

## The data contract

`docs/CONTRACT.md` defines the stable interface Projects 2-5 read: the tables, the
`field_name` set, provenance columns, and the `qualified` view for qualification
state. Later projects consume these records rather than rebuilding their own model.

## Known limitations

- Scoring is a **self-consistency check, not validation** (see above).
- No holdout — the threshold was tuned on the same labels it is reported on.
- Small sample — 30 pairs per config.
- The 130 **exact** GitHub matches rest on name-equality and have **no independent
  check**; only the verified (31) and manual (18) tiers carry evidence.
- 33 companies came back `sells_to = unknown` and I have not hand-checked them.
  They lose the audience weight, so this is a real, unmeasured error source.
- Reach is thin: only 25 of 138 qualified accounts had a contact (18%). 113 have
  nobody to email yet. Closing that gap is the next job.
- Emails are predicted patterns, not verified addresses. Hunter's free tier could
  not cover ~700 candidates, so I documented the gap instead of pretending.
- Idempotency is proven on identical input only, not yet on overlapping new data.
- No integration tests at the API boundaries (fixtures/mocks).
- No CRM or workflow tooling in this project — no Clay, no n8n, no HubSpot. Those
  come in Projects 2 and 5.
- GitHub and Apollo as contact sources: skipped for now. GitHub org members are
  mostly IC engineers, and Apollo's free credits don't stretch far.

## Decisions

Every real decision, with its reason and tradeoff, is in `decisions.md`. The ones
worth reading: why domain beats name for identity, why nothing ever auto-merges on
a similarity score alone, and why failures are stored as nulls and never guessed.

## Status

Done: setup, clean, crawl, GitHub matching, AI extraction, ICP scoring, contact and
email enrichment — plus engineering depth (logging, retry, typed schemas, unit
tests, one-command setup) and the data contract for Projects 2-5.

Optional future work: blind-labelling the scoring eval, and a short demo video.

Next: Project 2 — the market signal detector.
