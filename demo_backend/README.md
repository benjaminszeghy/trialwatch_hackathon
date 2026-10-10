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

SQLite, source Parquet versions, PDFs and extracted text live under ignored `work/live-demo/` by default. Use `--state-dir /persistent/path` to relocate them. Back up this directory, including all document versions. Never run a recurring worker on an ephemeral filesystem. The SQLite `annotations` table is separate from imported metadata and is never overwritten by refreshes; this version provides read access to annotations, not an annotation editor. Its payload should include the evidence PDF hash when your team builds the editor.

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
python -m unittest demo_backend.test_backend demo_backend.test_law_links -v
python -m unittest discover -s research -p 'test_*.py' -v
```

Tests cover repeat-run deduplication, new cases, mobile/web duplicates, bounded backlog, source/PDF failures, retries, PDF revisions, annotation preservation, cache freshness, scheduler start/stop, refresh locking and API/PDF/text access. They use temporary source fixtures; live AWS checks are recorded separately in runtime run history.

Law-link tests additionally check precise subsection mapping, unresolved score ranges, unscored scope, rejection of BNSS/IPC/unrelated-number matches, hash/quote validation, preserved low scores and the database/API PDF-score join.

Public source: [AWS dataset registry](https://registry.opendata.aws/indian-high-court-judgments/) and [maintainer dataset layout](https://github.com/vanga/indian-high-court-judgments/blob/main/opendata/docs/dataset.md). Dattam Labs and contributors; CC BY 4.0. Individual document URLs and SHA-256 hashes are retained. Court documents are data, never instructions to the collector.

## Case dashboard and review bands

The frontend is a case-review dashboard with collection overview counts, search by party/CNR, law and review-band filters, priority/latest-order sorting, and a document detail panel. Narrow screens use case cards. Court PDFs, supporting passages and extracted text remain available in the detail panel. Collection coverage and technical details are kept in a separate panel.

`GET /api/cases` now accepts `priority=high|elevated|standard|uncertain|unscored` and `sort=latest|priority`. Filtering and sorting run across the complete matching set **before** pagination. Each case returns `law_links` and `review_priority`; its response also includes `summary.priority_counts` for the matching search/law scope before a priority filter, plus the declared `priority_method`. The previous default sort remains `latest`; the dashboard requests `priority`. Case detail returns the same preliminary metadata-derived band.

Priority uses the highest associated **law-profile** score, never a sum across laws: high 9–12/12, elevated 6–8/12, standard 0–5/12. A score range crossing bands is “Priority to confirm”; no scored profile is “Unscored,” not zero. Unresolved BNS 353 is therefore 8–9/12 / to confirm unless another law already establishes a higher band. Explicit metadata subsections are respected. These are provisional interface thresholds, not validated misuse labels or urgency decisions. Law associations, unknown scope and PDF evidence status remain separate. A low-scoring law can still occur in a case requiring urgent attention.

Priority sorting: high, to confirm, elevated, standard, unscored; then the score lower bound, newest order date, and CNR as the final tie-breaker.

Visual references: [IBM Carbon data tables](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/specifications) for readable table structure and spacing; [GOV.UK status tags](https://design-system.service.gov.uk/components/tag/) for concise, non-interactive status labels with text as well as color. The implementation uses local HTML/CSS/SVG with system fonts and no external UI assets.

Priority checks:

```bash
python -m unittest demo_backend.test_priority
```
