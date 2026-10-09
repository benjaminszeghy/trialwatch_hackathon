# TrialWatch Legal Tripwire: India — first implementation

**BNS acquisition update:** `outputs/bns-training-starter/README.md` documents the new BNS-only retrieval corpus (107 candidate CNRs, 177 order records), its text-grounded review seeds, blank human-label template and separate official-source supplements. `acquire_bns.py` and `build_bns_corpus.py` implement this acquisition/annotation stage. The prior law-score outputs below remain a separate provisional rubric.

**PDF access audit:** `outputs/bns-training-starter/document-index.md` provides a clickable link per document. `audit_bns_output.py` checks the saved PDFs against hashes, page counts and extracted text, and optionally checks live source bytes with `--live`. It needs the pinned `pypdf` dependency; live checks additionally use curl. It does not modify the CSVs, annotations or source snapshot.

The deliverable is **19 version/status-specific rows: 18 scored profiles and an unscored, invalidated IT 66A entry**. Historical IPC, current BNS, and continuing special acts are kept in separate panels. Start with `outputs/law-scores.md`.

The score is a provisional **statute-as-written review index**, not a learned model or an abuse probability. Six explicit 0–2 ratings are summed out of 12 and rounded onto a 0–100 display. Every rating has a reason and a source. Court doctrine, metadata counts, incomplete evidence and weight sensitivity remain separate.

## Offline rebuild from the included snapshot

Use Python 3.10 or later. The report builder and checks use only the standard library; the acquisition scripts additionally require the pinned packages.

```sh
python3 research/build_results.py
python3 -m unittest discover -s research -p test_pilot.py -v
```

The portable package includes the required downloaded source files and extracted page JSON, so these commands make no network requests. It omits the large 106,408-row expanded JSON intermediate; its recorded source Parquets and generated inventory are included. `corpus_inventory.json` is produced from those Parquets by `prepare_corpus.py`.

## Acquisition from the two requested public datasets

No AWS credentials are required. The scripts use unsigned public HTTPS retrieval and record source SHA-256 hashes. A cold rerun needs network access.

```sh
python3 -m pip install -r research/requirements.txt
python3 research/inspect_data.py
python3 research/prepare_corpus.py
python3 research/acquire_judgments.py
python3 research/fetch_statutes.py
python3 research/acquire_supplemental.py
python3 research/build_results.py
python3 -m unittest discover -s research -p test_pilot.py -v
```

The IT Act PDF was accessible through web-tool PDF text but its direct download timed out. That source is explicitly marked web-verified without a local-byte hash; the report does not silently claim a successful download. The official linked 67/67B-proviso/77B text was checked. Other required statutory PDFs and all selected court PDFs are cached.

S3 objects can change. The included snapshot, inventory and hashes identify this build; a new acquisition is a new snapshot. Fixed curated spans deliberately fail closed if a source or extraction changes. Do not substitute a new PDF while keeping old provenance.

## Files and responsibilities

- `law_catalog.py`: six anchored criteria, editable proposed ratings, version relationships and official sources.
- `law_identity.py`: Act-bound section normalization; rejects 67A/67B when targeting 67 and prevents BNSS from being interpreted as BNS.
- `data_access.py`: bounded public downloads, caching and provenance.
- `prepare_corpus.py`: source metadata, inventory and preliminary statute matches.
- `acquire_judgments.py`: CNR join, deterministic stratified selection and page-level PDF text extraction. Supreme Court SCR files use the `_EN.pdf` suffix.
- `evidence_review.py`: explicitly curated examples and exact normalized-whitespace quotation verification; this is not independent legal gold data.
- `scoring.py`: score arithmetic, tied ranks, bounded-weight sensitivity and leave-one-criterion-out analysis.
- `build_results.py`: offline report and machine-readable outputs; no inferred abuse or quashing rates.
- `test_pilot.py`: nine regression checks for identity, arithmetic, unknown fields, court-evidence distinctions and source hashes.

## Corpus and interpretation

The selected High Court frame is a Bombay proceeding sample with 2024–2025 order dates, drawn from four bench partitions. It is not all India, not a journalist-only sample and not a set of independent FIRs. Unique CNRs can belong to the same prosecution. Metadata has verified Act errors; the counters are retrieval denominators only.

Nine AWS Supreme Court judgments provide historical doctrinal material. Two labeled official SCI supplements supply the 2022 sedition order and the 2025 BNS 196 interpretation. Statutes and central procedural schedules supply the structural components. IPC-to-BNS relationships are comparison links, not automatic legal equivalence. Assigning a substantive code requires the named law, offence/FIR date and operative record, not the judgment year.

No supervised classifier, expert agreement statistic, expert pairwise ranking, CCD accuracy or population abuse probability has been estimated. Legal reviewers should independently verify the current versions, elements and ratings. This build preserves unknowns and provides a reproducible starting point for that validation.

## Source attribution

Requested datasets:

- https://registry.opendata.aws/indian-supreme-court-judgments/
- https://registry.opendata.aws/indian-high-court-judgments/

Maintained by Dattam Labs and contributors; see registry entries and dataset repositories for CC BY 4.0 terms. Every selected judgment, official Act and supplemental decision has a direct source URL in the report/manifest. Downloaded legal documents are source material, not instructions to the program.
