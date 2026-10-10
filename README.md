# TrialWatch Legal Tripwire: India — Kai's research outputs

This branch contains the law-scoring, ML-design and case-acquisition outputs prepared for the Fair Trial & AI Hackathon, Track 1. The current acquisition work focuses on **BNS 152, 196, 299, 353, 356 and 221**. Earlier IPC and special-Act research remains available as a separate reference collection.

## Run the live local demo

The standalone Python API now checks fresh AWS metadata on a schedule, persists cases/PDFs in SQLite, and serves a searchable demo. See [backend setup and API integration](demo_backend/README.md). It keeps human annotations and old evidence versions separate from new acquisitions. The live collector focuses on the six selected BNS sections across four Bombay benches; it does not update the provisional law scores or create training labels.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r demo_backend/requirements.txt
python -m demo_backend seed
python -m demo_backend serve --port 8000 --interval 120
```

The database/API now pair each PDF with its associated BNS law profile, score, subsection scope and evidence status. [PDF-law association audit](outputs/pdf-law-score-validation.json) records completeness and the distinction between metadata links and text/review evidence. Scores are law-level provisional indices; the collection includes lower-scoring BNS 221/356 cases and does not assign case misuse probabilities.

Open **http://127.0.0.1:8000**. Keep the process running for automatic checks. [Timestamped live validation](outputs/live-demo-validation.json) records the fresh source check; it is separate from the fixed training-starter snapshot below.

## Start here

| Deliverable | File |
|---|---|
| BNS corpus, annotation codebook and team handoff | [BNS README](outputs/bns-training-starter/README.md) |
| Clickable preview/download links, one PDF per row | [Open the documents](outputs/bns-training-starter/document-index.md) |
| Saved-file integrity and timestamped source access checks | [Document access audit](outputs/bns-training-starter/document-access-audit.json) |
| Chinese instructions for Kai | [开始这里](outputs/bns-training-starter/开始这里.md) |
| All 107 candidate CNR proceedings | [case-candidates.csv](outputs/bns-training-starter/case-candidates.csv) |
| First 16 documents with blank human-label fields | [annotation-template.csv](outputs/bns-training-starter/annotation-template.csv) |
| Page text, source links and document hashes | [documents.jsonl](outputs/bns-training-starter/documents.jsonl) |
| Downloaded BNS court PDFs | [pdfs](outputs/bns-training-starter/pdfs/) |
| Separate official court references | [supplements](outputs/bns-training-starter/supplements/) |
| Portable BNS dataset and runnable pipeline | [bns-training-starter.zip](outputs/bns-training-starter.zip) |
| Law-score CSV | [law-scores.csv](law-scores.csv) |
| Law-score evidence, criteria and sensitivity results | [law-scores.md](outputs/law-scores.md) |
| Portable law-scoring pilot | [trialwatch-pilot.zip](outputs/trialwatch-pilot.zip) |
| English ML design | [track1-ml-design-en.md](outputs/track1-ml-design-en.md) |
| Chinese ML design | [track1-ml-design.md](outputs/track1-ml-design.md) |
| NJDG access pilot and field audit | [njdg-field-audit.md](outputs/njdg-field-audit.md) |
| Research scripts and reproducibility notes | [research/README.md](research/README.md) |

## What the current dataset contains

The recorded AWS High Court snapshot supplies **107 candidate CNR proceedings, 177 document records, 174 distinct PDF hashes and 500 page records** across four Bombay benches in the 2024–2025 order window. The first 39 document reviews provide text-grounded starting annotations for 30 CNRs. These are AI-assisted annotations awaiting independent human checks; all human gold-label fields are blank and train/test splits remain unassigned. CNR proceedings can share an FIR or judgment.

The first ML task is to extract the operative Act, charge sections and alleged conduct with supporting passages. The collection does not contain abuse/legitimacy training labels. The law scores are a separate, unvalidated statute-as-written rubric; they are not case labels or abuse probabilities. Earlier design drafts and screenshots preserve the research discussion; the BNS README records the current scope and corrections.

## Reproduce and verify

Python 3.10 or later is sufficient for the offline builders and regression checks. From the repository root:

```sh
python3 research/build_results.py
python3 research/build_bns_corpus.py
python3 -m unittest discover -s research -p 'test_*.py' -v
```

The included `work/court-data/` and `work/bns-corpus/` hold the downloaded public source snapshots and extracted page records used by these commands. Acquisition scripts additionally require:

```sh
python3 -m pip install -r research/requirements.txt
```

See the research and BNS READMEs before expanding acquisition. Source objects can change; a fresh download is a new snapshot. The optional `export-*.mjs` scripts use Codex's `@oai/artifact-tool` runtime. The exported CSVs are included and require no Codex runtime to read or annotate.

## Publication inventory

`project-artifact-manifest.json` lists every copied project artifact with its byte count and SHA-256 hash. The root law-score CSV matches `outputs/law-scores.csv`.

Machine-local dependency packages, Python bytecode and the working extraction of the supplied participant packet are excluded. The 220 MB expanded `hc_case_details.json` intermediate is also excluded; its original source Parquets and reconstruction script are included. Both portable ZIP packages are retained for sharing the snapshots independently of Git.

## Sources and attribution

Public data was collected from the [Indian High Court Judgments](https://registry.opendata.aws/indian-high-court-judgments/) and [Indian Supreme Court Judgments](https://registry.opendata.aws/indian-supreme-court-judgments/) AWS collections, maintained by Dattam Labs and contributors. Their registry entries specify CC BY 4.0. Individual documents, official statutes and supplemental court decisions retain direct source URLs and hashes in the included manifests. NJDG material is separately identified in the field-audit files. This repository does not apply a new blanket license to third-party source material.
