# Data contract — what Projects 2-5 can rely on

Project 1 owns one SQLite database. Later projects read it; they do not rebuild
it. This file is the interface: what exists, what each thing means, and what you
can depend on.

## The tables

| Table | One row = | Key columns |
|---|---|---|
| `raw_sources` | one raw input row | `source_name`, `raw_name`, `raw_domain`, `normalized_name`, `normalized_domain`, `dedupe_group` |
| `companies` | a deduplicated company | `id`, `name`, `domain` |
| `merge_log` | one raw row merged into a company | `raw_source_id`, `company_id`, `match_method`, `match_score` |
| `match_candidates` | a fuzzy pair awaiting review | `raw_source_id_a`, `raw_source_id_b`, `similarity_score`, `decision` |
| `company_fields` | one enriched fact | `company_id`, `field_name`, `field_value`, `source`, `source_url`, `collected_at` |
| `crawl_log` | one crawl attempt | `company_id`, `url`, `ok`, `status`, `fetched_at` |
| `contacts` | one person at a company | `company_id`, `name`, `title`, `email`, `email_source` |
| `contact_candidates` | one candidate email per contact | `contact_id`, `email`, `pattern`, `reliability`, `status` |
| `icp_configs` | one (config, feature) weight | `config_name`, `feature`, `weight` |
| `icp_thresholds` | the cut-off per config | `config_name`, `threshold` |
| `icp_scores` | one company x one config | `company_id`, `config_name`, `score`, `qualified`, `reason` |

## The enriched fields (`company_fields.field_name`)

A closed set, in three families:

**Extracted from the company's own website (AI, each with a quote):**
`extracted_what_they_do`, `extracted_category`, `extracted_sells_to`,
`extracted_tech_signals`, `extracted_size_signal` — plus the raw page text
(`homepage_text`, `homepage_title`, `about_text`, `product_text`, `careers_text`)
and `extraction_json` (the full model response).

**Matched from GitHub (exact numbers, no AI):**
`github_org`, `github_match`, `github_repo_count`, `github_total_stars`,
`github_top_repo`, `github_top_repo_stars`, `github_last_push`,
`github_last_release`, `github_org_blog`, `github_rejected_org`.

**Value sets:**
- `extracted_category` ∈ dev_tools, ai_infra, data_infra, horizontal_saas,
  vertical_saas, fintech, security, other, unknown
- `extracted_sells_to` ∈ businesses, consumers, both, unknown

## Provenance — never trust a value without its source

Every `company_fields` row carries `source` (which stage produced it),
`source_url` (the page it came from), and `collected_at` (when).

- A field with **no row at all** = we never found it — not a guess.
- A field with **no `source_url`** = it wasn't read off a page — not a guess.
- A **failed** read lives in `crawl_log` (`ok = 0`), never silently filled.

## Qualification state

`icp_scores.qualified` is 1 when `score >= threshold` (from `icp_thresholds`)
for that `config_name`. `icp_scores.reason` records which features fired.
Two configs: `generic_b2b_saas`, `devtools_ai_infra`.

## Stable vs free to change

**Stable — don't break these:** the table names, the `field_name` set, the
`icp_scores.qualified` flag, and the `source` / `source_url` provenance columns.

**Free to change (Project 1 internals):** scoring weights (`icp_configs`),
thresholds (`icp_thresholds`), crawl logic, the email waterfall.

## How to consume it

```python
import sqlite3
db = sqlite3.connect("data/lead_enrichment.db")
rows = db.execute("""
    SELECT c.name, s.config_name, s.score, s.reason
    FROM icp_scores s JOIN companies c ON c.id = s.company_id
    WHERE s.qualified = 1
""").fetchall()
