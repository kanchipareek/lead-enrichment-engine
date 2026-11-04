# decisions

---

## setup

**28 Sep — narrow fields table, not wide columns.**
Every field needs value + source + timestamp. If I'd
put enrichment as columns on `companies` that's 3 columns per field and it's a
mess by field 10. So: `company_fields`, one row per field per company. More
joins, but I can add a field without touching the schema. Worth it.

**28 Sep — stdlib only, SQL first.**
No pandas, no requests. Two reasons: nothing to install / nothing to break, and
every transformation lives in a .sql file in git so I can point at the exact rule
that produced any number. A Python loop full of logic is invisible in review; a
SQL file isn't. More typing. Fine.

## clean

**29 Sep — domain is the identity, name is the fallback.**
`COALESCE(normalized_domain, 'name:' || normalized_name)`. Domains are
near-unique, names aren't. I planted Linear/LinearB in my own data to prove it —
0.92 similar, totally different companies. Name only matters when there's no
domain. Known gap, saying it out loud: a company with two domains stays split.

**29 Sep — auto-merge at 0.92, same-domain at 0.5.**
Picked 0.92 as "high enough to trust", then it immediately bit me — it flagged
Linear vs LinearB for silent merge. Two different companies. Killed the
auto-merge line on the spot; everything fuzzy goes to a human now. Rule I'm
keeping: a probability score never merges anything by itself. Evidence or a human.
Result: 12 candidates flagged, all 12 rejected, 0 bad merges.

**29 Sep — failures are nulls.**
Fetch fails, or the page doesn't say something → the value is empty. I didn't
guess. Sounds obvious; it's the thing that makes everything downstream
trustworthy.

## enrich

**2 Oct — GitHub matching, in tiers, never on a name alone.**
Org logins almost never match company names (Baseten's org is `basetenlabs`). So
I record *how* I matched: exact (login == name), verified (fuzzy match, but the
org's own site matches my domain), manual (found by hand), none.
Search proposed 71 lookalikes. Domain-verify promoted 31. I reviewed the other
40 — rejected all 40, every one an impersonator. Then recovered 18 real ones by
hand. 179 matched, 39 none.
Fixing my own wording here: the "exact" tier *is* name-equality. What I actually
mean is no *fuzzy* match ever got accepted on a name alone.

**2 Oct — GitHub token with zero permissions.**
Had accidentally ticked admin scopes while setting it up. Public search needs no
permissions at all, so the token now has none. Caught before it ever ran.

**5 Oct — model swap: gemini-2.5-flash → gemini-3.8-flash.**
2.5-flash 404s on every call — retired for new keys. Only the model string changed.

**5 Oct — paid tier.**
Free tier was a dead end: 503 "high demand" across 3.8/3.7/3.5, then 429 quota,
and Batch API 400s without billing.free tier didn't work and paid just did.

**5 Oct — one request per company.**
All fields in one prompt. 218 calls instead of ~900, more context per call, and
provenance stays clean. Bigger single prompt, don't care.

**5 Oct — the prompt is allowed to say "unknown".**
Forbid outside knowledge, require a source page + a verbatim quote for every
field, make "unknown" a valid answer. Checked it: 154/154 citations traced, 0
fields missing a quote, 0 invented. The model refusing to answer when the page is
quiet is the whole point.

**5 Oct — scoring must not *disqualify* on a missing audience.**
Most dev-tools/AI companies sell to businesses; killing a lead because the page
didn't say so is dumb. So `sells_to = unknown` is never a disqualifier.
Correction (7 Oct): I called it "neutral" before and that was wrong. It's not
disqualified, but it *does* lose the 30-point business weight. That's a penalty,
not neutral. Anthropic is the proof — it loses those 30 points and lands in
neither list. Whether 30 is the right number is a job for the ground-truth check,
not a guess.

**5 Oct — always report the baseline next to the agreement.**
My eval set is a curated tech list, ~90% "accept". So "84% agreement" sounds bad
but the dumb baseline is 100%. I report both, every time. Honest weak number beats
a flattering meaningless one.

## score

**6 Oct — thresholds 60 → 70 / 80.**
At 60 a company cleared the bar on category + one signal, and 81% of everything
qualified. That's not an ICP, that's the whole list. Looked at the score
distribution, saw a pile-up right at 60/65, moved the line above it. Now 59 / 68
(27% / 31%).
Being honest: the *weights* are still guesses. I tuned the threshold against the
distribution, and that isn't validation. Needs ground-truth labels.

## emails

**6 Oct — cheapest contacts first.**
Crawl pages I already have → GitHub → Apollo only for gaps. And the target person
depends on the ICP: SaaS wants Head of Growth, dev-tools wants the technical
founder first.

**6 Oct — stopped fighting the providers.**
Gemini credit ran out (402), Groq blocked me (Cloudflare 1010) then started
404ing and crashing on SSL. I could keep burning days on it. Instead: bank the
waterfall, write the limits down. The system degrading gracefully when a provider
dies is a better story than a nicer coverage number.

## audits / corrections

**7 Oct — how many qualified accounts can I actually reach?**
Ran it: 25 of 127 (20%). Dev-tools 9/68, SaaS 16/59. 142 contacts total. So most
qualified accounts have nobody to email. Real weakness, going in the README as-is,
not buried.

**7 Oct — fixed the crawl numbers.**
Was quoting "199 fetched, 196 usable, 19 empty, 24 failures" — doesn't add up,
because it mixed per-company and per-page counts. Real numbers, per attempt:
564 attempts = 540 ok + 24 failed, across 23 companies. State it that way from
now on.


### 2026-10-07 — Devtools threshold 80 → 70, on evidence
**Why.** The ground-truth eval showed precision 1.00 but recall 0.34 — the threshold
of 80 excluded 19 genuine dev-tools targets, all scoring 60-75. Lowering it to 70
raises recall to 0.69 with no precision loss. The earlier raise to 80 was a
heuristic ("81% feels too many"); the labels contradicted it.
**Caveat.** The eval sample is stratified and the labels are rule-derived, so this
is a consistency check against the ICP definition, not a human-fit eval. A
human-judgement pass is the next step.
