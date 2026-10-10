# TrialWatch — recurring BNS collector and local API

This is the demo backend. The original `research/acquire_bns.py` remains the fixed-snapshot research acquisition script. This backend makes **fresh public AWS metadata checks**, keeps state between runs, queues unseen orders, and serves the collection to a website. It does not automate NJDG or require its CAPTCHA session.

## Run the demo today

From the repository root, with Python **3.12+** and **curl** installed:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r demo_backend/requirements.txt
python -m demo_backend seed
python -m demo_backend serve --port 8000 --interval 120
```

Open **http://127.0.0.1:8000**. Interactive API documentation is at **http://127.0.0.1:8000/docs**. The seed step imports the included 107 candidate CNRs / 177 order records without making network requests; repeating it adds no duplicates. Then the server checks AWS immediately and every 120 seconds while it remains running. The usual default is one hour. Stop with Ctrl-C. Starting again resumes the same SQLite database and PDF backlog. The page polls the API every five seconds; this page polling is separate from the collection schedule.

The first fresh check downloads source Parquets and can take several minutes. You can present the seeded cases immediately and show the check's progress. A repeat check normally reuses verified unchanged Parquets. An unchanged source will produce **zero new cases**, correctly: the demo never fabricates activity. Keep the server running during the presentation. A laptop sleep or stopped process pauses collection.

## Update behavior and scope

Defaults: **BNS 152, 196, 299, 353, 356 and 221**, Bombay High Court, `newas`, `hcaurdb`, `hcbgoa`, `kolhcdb`, order dates from 1 July 2024 to today's machine date. The year range expands with the calendar. This is a limited pilot, not all courts or all BNS cases. Edit `config.example.json` to change scope and pass `--config PATH` **before** the command:

```sh
python -m demo_backend --config demo_backend/config.example.json serve
python -m demo_backend --config demo_backend/config.example.json refresh
```

Every refresh lists current S3 objects without a cached listing; compares ETag, last modification and byte count; verifies cached hashes; downloads and validates changed Parquets; binds sections to the named Act; joins candidate CNRs with dated orders; and deduplicates mobile/web order representations using CNR + decision date + order number, with a filename fallback. It discovers **all in-scope orders**, rather than only the old earliest/latest endpoints. BNS metadata is still only a retrieval signal: older IPC prosecutions can be mislabeled in it. Offence/FIR dates and operative Act require human verification.

Downloads are bounded to **12 PDFs per run**, newest pending orders first, with two concurrent downloads. Pending/error counts are visible. Up to two previously saved PDFs are rechecked when at least seven days old and the download budget has spare capacity. A revised PDF is stored under a new hash; its old PDF/text version and human annotations remain available. New pending documents can delay revision rechecks. Scanned pages without text remain empty; there is no OCR in this demo.

Source listings and downloads use verified public HTTPS, curl timeouts/size limits and atomic files. No AWS credentials are used. An OS file lock prevents overlapping refreshes, including a separately launched CLI worker. Failed source checks do not delete data or advance the last completed check. PDF failures produce a partial run and remain queued for retry. Missing metadata partitions fail visibly; cases disappearing upstream are retained as previously collected records. Collection totals are cumulative; `candidate_cnrs_in_window` in each run is the current retrieval frame.

## API for your teammate's website

| Route | Purpose |
|---|---|
| `GET /api/status` | Counts, scope, running state, last completed check, source modification date, latest order date |
| `GET /api/cases?q=Farah&section=353&limit=25&offset=0` | Search/filter/paginate proceedings |
| `GET /api/cases/{cnr}` | Document links, source metadata, separate AI seed notes and human annotations |
| `GET /api/documents?section=353&status=ready` | PDFs with associated law profiles, scores, subsection scope and evidence status |
| `GET /api/documents/{id}` | One PDF's source/local links, law profiles and association evidence |
| `GET /api/documents/{id}/pdf` | Saved PDF, served with `application/pdf` |
| `GET /api/documents/{id}/text` | Page-level extracted text and source hash |
| `GET /api/documents/{id}/versions` | Saved evidence versions; PDF/text links accept `?sha256=...` |
| `GET /api/runs` | Refresh history, statistics and errors |
| `GET /api/laws` | Original provisional law-profile JSON, unchanged by collection |
| `POST /api/refresh` | Start one background check; does not start a second concurrent check |

For a local frontend on another port, put its exact origin (for example `http://localhost:3000`) in `cors_origins` in your config. Read-only GET requests are allowed from those origins. Integrate with:

```js
const response = await fetch('http://127.0.0.1:8000/api/cases?section=353');
const { items } = await response.json();
// PDF/text links are relative: prefix them with the API's base URL.
```

Manual refresh is restricted to the local machine and same origin by default. If you later expose it remotely, set `TRIALWATCH_ADMIN_TOKEN` in the server environment and call it from a trusted backend with `Authorization: Bearer ...`. Never put that token in public frontend code. CORS alone is not authentication. The demo page's local refresh button does not contain an admin token.

## Persistent state and later deployment

SQLite, source Parquet versions, PDFs and extracted text live under ignored `work/live-demo/` by default. Use `--state-dir /persistent/path` to relocate them. Back up this directory, including all document versions. Never run a recurring worker on an ephemeral filesystem. The SQLite `annotations` table is separate from imported metadata and is never overwritten by refreshes; document annotations remain separate from the case-assessment editor below. Case assessments and their PDF hashes live in the new `case_reviews` and `case_review_events` tables and are never overwritten by collection.

For today use **one server process**. The integrated scheduler works only while that process runs. For later hosting, run an API process with `serve --no-scheduler` and one persistent worker with `worker`; both need the same persistent directory. Put the API behind HTTPS and a reverse proxy before public deployment. No cloud deployment or external scheduler has been configured by this change.

```sh
# Separate-process form, in two terminals:
python -m demo_backend --state-dir /persistent/path serve --no-scheduler
python -m demo_backend --state-dir /persistent/path worker
```

## Meaning of freshness and labels

**Last checked** is when this collector completed its metadata/document pass. **Source last modified** is the latest S3 metadata-object timestamp seen. **Latest order** is a court-order date in the accumulated collection. They are deliberately separate. Upstream publication may lag the court, and collection cannot make unpublished cases appear sooner.

The status API also separates **case-detail metadata** (where Act/section matches come from) from **order metadata**. A freshly published order file does not make an older case-detail table current. Cases without matching Acts in the case-detail dimension cannot enter this BNS retrieval frame yet. The demo displays the case-detail timestamp so this coverage lag stays visible.

No ML model is trained or run by this worker. Newly collected documents are candidates for Act/charge/conduct extraction and legal annotation. AI-assisted review seeds remain attached only to the original snapshot documents, clearly separated from human labels, and include their evidence PDF hash plus a `matches_current_pdf` flag. Bail, disposal and the law-profile score do not supply abuse labels. The Supreme Court reference collection and the law-score rubric remain static reference material; automatic collection here concerns High Court BNS candidates only.

## PDF → law → score validation

The website now receives the PDF **and** its associated laws and scores in the same document response. These links are persisted in SQLite's `law_profiles` and `document_law_links` tables. The `document_pdf_law_scores` SQL view provides one PDF/law-profile row with local PDF storage/API path, source URL, PDF hash, raw/12 and display/100 scores, rubric version/date, scope and association status. A PDF with several laws or unresolved BNS 353 subsections can have several rows; never add those scores into a case risk score. The API explicitly returns `case_misuse_score: null`.

The original law rubric is unchanged: BNS 152 **10/12**, 196(1)(a)-(b) **11/12**, 299 **8/12**, 353(1) **8/12**, 353(2) **9/12**, 356(1)-(2) **4/12**, and 221 **4/12**. Acquisition targets these six parent sections, **not a minimum score**. Thus not every collected PDF relates to a high-scoring law. The rubric is an unvalidated statute-as-written index, not an estimated probability of misuse.

The association field distinguishes `metadata_only`, `text_reference_candidate`, `ai_review_charge_recorded`, `target_not_confirmed_in_review` and `metadata_conflict`. Automatic references require an Act-bound section list and a supporting page passage. They are still candidates for human checks, since a legal citation or another defendant's charge need not be the operative charge of this proceeding. No detected text reference means unknown, not absent. Existing AI seed reviews are accepted only when their PDF hash and supporting quote match; they remain non-gold.

For BNS 353 with no resolved subsection, return both profile candidates and an **8–9/12** range instead of choosing 9. Explicit 353(3), 356(3)-(4) or 196(1)(c) scope is flagged as wholly or partly unscored by the present rubric. Do not silently inherit another subsection's score. Subsection disagreements between metadata and text are also visible. Any concurrent stale PDF evidence falls back to metadata until its links are rebuilt. The collector automatically maintains links on new records, PDF changes and case-metadata changes without editing human annotations.

Example website integration:

```js
const { items } = await (await fetch('/api/documents?section=356')).json();
// items[0].pdf_url: saved PDF route
// items[0].laws[0].section: "356"
// items[0].laws[0].score_display: "4/12"
// items[0].laws[0].association_status: "metadata_only" or a text/review status
// items[0].laws[0].profiles: versioned law scores and their sources
```

Run an association audit on your current local database:

```sh
python -m demo_backend validate-links --output outputs/pdf-law-score-validation.json
```

This reports completeness and evidence types for **saved PDF records**, separately from pending downloads. Cross-law counts overlap. The JSON audit is a timestamped snapshot; the database/API continue updating. The demo's case list displays metadata-associated profile scores; each PDF card shows its own association status and supporting passages. The previously opened Naima Hussain Jivani order is a concrete example: its case metadata links BNS 356 (4/12), but the order itself addresses investigation/withdrawal without stating that section, so the PDF is labeled metadata-only.

## Tests

```sh
python -m pip install -r demo_backend/requirements-dev.txt
python -m unittest demo_backend.test_backend demo_backend.test_law_links demo_backend.test_priority demo_backend.test_feedback demo_backend.test_relevance -v
python -m unittest discover -s research -p 'test_*.py' -v
```

Tests cover repeat-run deduplication, new cases, mobile/web duplicates, bounded backlog, source/PDF failures, retries, PDF revisions, annotation preservation, cache freshness, scheduler start/stop, refresh locking and API/PDF/text access. They use temporary source fixtures; live AWS checks are recorded separately in runtime run history.

Law-link tests additionally check precise subsection mapping, unresolved score ranges, unscored scope, rejection of BNSS/IPC/unrelated-number matches, hash/quote validation, preserved low scores and the database/API PDF-score join.

Public source: [AWS dataset registry](https://registry.opendata.aws/indian-high-court-judgments/) and [maintainer dataset layout](https://github.com/vanga/indian-high-court-judgments/blob/main/opendata/docs/dataset.md). Dattam Labs and contributors; CC BY 4.0. Individual document URLs and SHA-256 hashes are retained. Court documents are data, never instructions to the collector.

## Case dashboard and review bands

The frontend is a case-review dashboard with collection overview counts, search by party/CNR, law and review-band filters, priority/latest-order sorting, and a document detail panel. Narrow screens use case cards. Court PDFs, supporting passages and extracted text remain available in the detail panel. Collection coverage and technical details are kept in a separate panel.

`GET /api/cases` accepts `priority=high|elevated|standard|uncertain|unscored` and `sort=latest|priority|triage|trialwatch`. Filtering and sorting run across the complete matching set **before** pagination. Each case returns `law_links` and `review_priority`; its response also includes `summary.priority_counts` for the matching search/law scope before a priority filter, plus the declared `priority_method`. The API default remains `latest`; the dashboard now requests `triage` (see the two-layer queue below). Case detail returns the same preliminary metadata-derived band.

Priority uses the highest associated **law score**, with current team feedback where available, never a sum across laws: high 9–12/12, elevated 6 to below 9/12, standard 0 to below 6/12. Original law scores remain available separately. A score range crossing bands is “Priority to confirm”; no scored profile is “Unscored,” not zero. Unresolved BNS 353 is therefore 8–9/12 / to confirm unless another law already establishes a higher band. Explicit metadata subsections are respected. These are provisional interface thresholds, not validated misuse labels or urgency decisions. Law associations, unknown scope and PDF evidence status remain separate. A low-scoring law can still occur in a case requiring urgent attention.

Priority sorting: high, to confirm, elevated, standard, unscored; then the score lower bound, newest order date, and CNR as the final tie-breaker.

Visual references: [IBM Carbon data tables](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/specifications) for readable table structure and spacing; [GOV.UK status tags](https://design-system.service.gov.uk/components/tag/) for concise, non-interactive status labels with text as well as color. The implementation uses local HTML/CSS/SVG with system fonts and no external UI assets.

Priority checks:

```bash
python -m unittest demo_backend.test_priority
```


## Case assessments and the feedback loop

Open a case and use **Yes — Misuse identified** or **No — No misuse identified**. Select the law or exact scored subsection you verified in the records, optionally explain the evidence, then **Save assessment**. Multiple-law cases do not vote on every listed law automatically. A single applicable scored profile is preselected; this is not a charge verification by the system. Inspect its scope before saving. Unknown/unscored scopes can receive an assessment without inventing a score.

The card previews the score change, shows saved status, and allows editing or clearing the assessment. The queue shows assessment tags and a review-status filter. Law profiles show the original rubric, feedback-adjusted score and yes/no counts. Original `raw_total`, original law-score CSV/JSON, and PDF-law associations are preserved. `/api/cases` and PDF APIs carry a separate overlay; priority uses that overlay where present. The raw SQL `document_pdf_law_scores` view continues to expose the original rubric; combine it with `case_reviews` or use `/api/feedback` for current adjusted scores.

### Transparent scoring policy

For each exact scored law profile, let **b** be the original rubric score out of 12, **Y** the number of current yes assessments and **N** the number of current no assessments:

```text
feedback_adjusted_score = (6 × b + 12 × Y) / (6 + Y + N)
```

The baseline carries the weight of six assessments. Yes moves the index upward; no moves it downward; scores stay within 0–12. With no current votes, the index equals the original score. Example: BNS 299 starts at 8; one yes gives **8.6**, one no gives **6.9**. Replacing that yes with a no yields one current no vote, not two votes. Unreviewed cases, cleared assessments and stale assessments add no score vote. Historical non-binary assessments are preserved in storage but appear as unreviewed and add no vote; new assessments accept only yes or no. This weighting is an explicit experimental policy, not a learned parameter or a calibrated probability. Changing feedback cannot change the wording of a law or its underlying structural rubric.

There is **one current team assessment per CNR**, rather than one vote per click or PDF. This local pilot does not verify the identity or legal expertise of individual reviewers. Concurrent edits use `expected_revision`; an outdated browser receives HTTP 409 and must reload. Repeating the same current assessment is idempotent. Every actual change appends an audit event; clearing retains the earlier evidence and edit history.

Each assessment snapshots the case metadata, catalog hash, and all known document IDs, source URLs, dates, statuses and PDF SHA-256 hashes at review time. Changes to these inputs mark it **Needs recheck** and remove its contribution from adjusted scores and the current binary-label export. Unchanged polling does not invalidate it. Reconfirm the current evidence to reactivate it. Importing new source data never silently rewrites a review.

### API integration

| Route | Purpose |
|---|---|
| `PUT /api/cases/{cnr}/review` | Save/replace the current assessment; response is updated case detail |
| `DELETE /api/cases/{cnr}/review` | Clear the current assessment with a revision check; audit retained |
| `GET /api/feedback` | Current profile overlays, yes/no counts, summary and declared formula |
| `GET /api/reviews/export` | Current non-stale binary human assessments, their evidence snapshots and revision |
| `GET /api/cases?review=unreviewed` | Restrict queue by assessment status |

The case detail API supplies `review_evidence_version`, `case_review.revision` and `review_law_options`. Only those associated profile IDs can be selected. For unresolved BNS 353, a reviewer must choose the verified scored subsection; the API does not assume 353(2). A yes/no decision requires an available court PDF. Cases remain unreviewed while PDFs are pending. Notes are limited to 1,500 characters. Score updates are computed from persisted current assessments, so they survive restarts without a separate score-update job.

```js
const c = await (await fetch(`/api/cases/${cnr}`)).json();
const response = await fetch(`/api/cases/${cnr}/review`, {
  method: 'PUT',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    decision: 'misuse', // or 'no_misuse'
    law_profile_ids: selectedVerifiedProfileIds,
    note: reviewerNote,
    expected_revision: c.case_review.revision,
    evidence_version: c.review_evidence_version
  })
});
```

Writes and label export share the local/same-origin or server-held admin-token guard used by refresh. This is intended for the current local demo. Deploying a shared reviewer service requires real reviewer authentication, authorization and a defined adjudication process; a token is not an individual reviewer identity. Cross-origin browser writes are not enabled, and no token is embedded in the page. Notes and assessments remain in the ignored runtime database and are not included in source commits.

### What this contributes to active learning

The feature supplies an editable human-label feedback loop and a queue that can filter unreviewed or changed-evidence cases. **It does not retrain a machine-learning model.** Exported labels are explicitly **unadjudicated human assessments, not gold**; historical non-binary, cleared and stale labels are excluded from the binary export. Keep related CNR proceedings, all their orders, and revisions in the same train/test group. The export includes `family_group_verified: false`: different CNRs can still describe one prosecution, so grouping and duplicate-adjudication remain team tasks. Do not use post-review feedback scores or reviewer notes as features when predicting the labels themselves. Evaluate any future model on separately adjudicated held-out cases before using model uncertainty for acquisition.

Feedback validation uses isolated synthetic cases: yes/no monotonic updates, replacements, idempotence, clearing, persistence, law attribution, stale evidence/catalog checks, export, input limits and write guards. Browser save/reload/recheck tests also use a fictional case in a separate temporary database. No real-case assessment was added for testing.

## TrialWatch relevance and the two-layer queue

**Law concern** stays a separate law-level index out of 12, including the existing feedback overlay. **TrialWatch relevance** is a reviewer-confirmed case-level index out of 100. It describes support needs, timing and a possible route for monitoring or follow-up; it is not a misuse finding, a measure of deservingness, or an estimate of TrialWatch's capacity to secure a release. The categories reflect [TrialWatch's published monitoring and legal-support work](https://cfj.org/trialwatch/); the following weights and thresholds are our provisional team assumptions, not official TrialWatch policy.

| Factor | Anchored contribution |
|---|---|
| Access to counsel · max 25 | Unavailable/denied 25; limited access 12.5; available with no identified gap 0 |
| Interpretation · max 15 | Needed but unavailable 15; limited support 7.5; adequately provided or verified not required 0 |
| Defence/evidence access · max 15 | Documented restriction 15; checked and no restriction identified 0 |
| Time sensitivity · max 25 | Highest applicable signal: immediate safety threat or hearing/filing deadline in 0–7 days 25; current custody 20; deadline in 8–30 days 15; later deadline 5; all checked with no current signal 0 |
| Practical intervention opening · max 20 | Confirmed route 20; route still to arrange 10; checked and no current opening 0 |

Possible routes are trial monitoring, legal-support review, interpretation follow-up, or evidence/advocacy review. Listing a route does not assign resources, contact anyone, or verify that TrialWatch has agreed to take a case. A completed proceeding can still have a review/advocacy route. Journalist/reporting connection and current court stage are separate fit checks, not points. A verified absence of this connection is labeled **Outside journalist pilot**, with referral for consideration; it is not a determination about eligibility for other help.

Open a case, expand **Assess TrialWatch priority**, select only facts you checked, supply a source note (order/date/page or other current source), and save. Each unknown factor contributes **0 to its maximum** to a lower–upper score range, rather than a confirmed zero. Coverage is the percentage of rubric weight whose contribution is assessed, not model confidence. An unassessed case has no score. Missing journalist connection/stage, a range crossing tiers, changed evidence, or an expired active deadline requires verification. A keyword passage is only a reading aid: the advocate may represent the State or another defendant, and translation may concern a document rather than an interpreter. No form entry is auto-populated from those matches or from silence in an order.

| TrialWatch tier | Routing |
|---|---|
| Tier 1 · Urgent | 75–100: immediate review |
| Tier 2 · High | 45 to below 75: priority investigation |
| Tier 3 · Routine | Below 45: monitoring/evidence collection |
| Needs verification | Fit or facts unconfirmed, range crosses tiers, or an assessment needs recheck |
| Tier 4 · Closed review | Explicit reviewer decision with a reason, independent of score |

A documented immediate threat, deadline within seven days, or current custody with unavailable counsel overrides the numerical tiers and moves the case to immediate review even with a low law score. If journalist fit is unconfirmed, this is **Urgent verification**. Stale urgent flags remain visible as **Urgent recheck**, without a current numerical score. A verified non-journalist case stays outside this pilot. Closing while a current urgent override is active is rejected. A closure reopens for review on changed evidence or when its recorded future deadline becomes urgent. This updates the routing state without rewriting the saved historical facts. A no-misuse assessment, a low relevance score or completed proceedings never automatically closes a review. Dates and deadline aging use `Asia/Kolkata`; polling recomputes tiers as time passes.

The default `sort=triage` puts urgent cases first, then sorts other active cases by **law-concern band → TrialWatch tier → confirmed relevance lower bound**. Existing law-score/date ordering breaks ties. Closed/out-of-pilot reviews come last. `sort=trialwatch` emphasizes relevance tier/lower bound before law concern; `sort=priority` and `sort=latest` retain their previous behavior. The dashboard provides a separate TrialWatch-tier filter, two distinct score columns, an urgent count and assessed component breakdown in case detail.

### Relevance API and storage

| Route / field | Purpose |
|---|---|
| `PUT /api/cases/{cnr}/relevance` | Save/replace verified facts or explicitly close/reopen a review; updated case detail returned |
| `GET /api/cases?sort=triage&trialwatch_tier=urgent` | Full-set prioritization and tier filtering before pagination |
| `GET /api/cases/{cnr}` | `trialwatch_relevance`, `relevance_method`, and exact-source `relevance_passages` |
| Case/document `trialwatch_relevance` | Tier, score/range, coverage, factor breakdown, reasons, action, checked facts, revision and evidence freshness |
| `GET /api/status` | Global `trialwatch_tiers`; case list also reports scoped `trialwatch_summary` and `relevance_review_summary` |

The same case relevance accompanies its PDF responses; it is not a score calculated independently for each PDF. Law scores, PDF-law associations and the original binary misuse assessment remain separate. Relevance changes never vote on a law score or change a misuse label. The API's `case_misuse_score` remains null.

```js
const c = await (await fetch(`/api/cases/${cnr}`)).json();
const response = await fetch(`/api/cases/${cnr}/relevance`, {
  method: 'PUT', headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    ...c.trialwatch_relevance.facts,
    journalist_nexus: 'confirmed', case_stage: 'ongoing',
    counsel: 'limited',
    evidence_note: 'Checked order [date], page [n]: describe the relevant defendant and supporting facts.',
    expected_revision: c.trialwatch_relevance.revision,
    evidence_version: c.review_evidence_version
  })
});
```

Other enum fields, date/opening consistency and limits are described in `/docs`. A confirmed entry requires a source note of at least 10 characters. `deadline_status=scheduled` requires a non-past `next_deadline`; other statuses require null. `opening_status=ready|to_arrange` requires at least one listed opening; `none|unknown` requires none. `workflow_status=closed` requires a reason of at least 10 characters. Revision and evidence hashes prevent stale/concurrent writes (HTTP 409). Identical resaves are idempotent. The local/same-origin or backend-admin write guard also applies here.

`case_relevance` stores one current assessment per CNR. `case_relevance_events` retains actual edits with metadata/PDF evidence snapshots, revision, timestamp and method version. Both live only in the ignored runtime SQLite database; collection never overwrites them and source commits exclude reviewer notes. Back up that database with the PDF/text versions. The local team identity is not verified; this is not a multi-reviewer adjudication system. Related proceedings still require case-family grouping. Neither relevance facts nor future reviewer scores should become features for predicting the same human misuse labels without a deliberate leakage review.

Validation includes 11 relevance tests plus the existing 36 backend tests, 15 research tests, desktop/mobile UI review and a save/reload/invalid-closure/filter flow on a clearly fictional case in an isolated database. Real scraped cases remain unassessed. See [validation snapshot](../outputs/trialwatch-relevance-validation.json) and [fictional UI proof](../outputs/trialwatch-relevance-fictional-test.png).

### Finding scores in the dashboard

The **TrialWatch priority** panel shows tier counts, explains pending scores and offers **Assess next case**. Each case has an explicit **TrialWatch score / priority** block with a score out of 100, a tier and an **Assess priority** link that opens the scoring form. Scores that have not been assessed display a dash and “Awaiting assessment”; they never silently become zero. Narrow windows up to 920px use labeled case cards so the score cannot disappear into a horizontally scrolled table.
