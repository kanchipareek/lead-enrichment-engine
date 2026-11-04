# STAR story — Project 1 (lead enrichment engine)

**Situation.** I assembled 230 company rows from four sources and planted duplicates and lookalike pairs to test the cleaner.

**Task.** Build a pipeline that cleans the list, enriches each company from its
own website and GitHub, scores it against two ICP definitions, and finds
contacts — with every value traceable to a source and nothing invented.

**Action.** One SQLite database, every transformation in a committed `.sql` file.
The decisions that mattered: domain (not name) decides identity, so nothing
auto-merges on a similarity score; enrichment is stored narrow, so every field
carries its source and timestamp; the extractor must return the exact quote for
every fact, or the field stays `unknown`; and two ICP configs with different
weights instead of one filter. When my scoring eval returned perfect precision,
I checked how I'd labelled it — and found the labels used the same rules as the
score. So I renamed it a rule-consistency check, documented the limits, and
named the real test.

**Result.** 230 messy rows → 218 clean companies (12 duplicates resolved, 0
false merges, 5 planted traps all caught) 199 companies enriched; 154 facts verified in a 50-company sample. 138 qualified accounts
(59 SaaS / 79 dev tools), 142 contacts. And the honest gap: only 25 of the 138
qualified accounts have a contact yet — which is what the next project is for.
