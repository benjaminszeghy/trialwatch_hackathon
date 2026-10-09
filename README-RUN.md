# JiwonScrapper — executable Excel-producing scraper

This program **runs** on court judgment URLs or a folder of downloaded PDF/HTML/TXT judgments and **automatically creates** `output/TrialWatch_Case_Review.xlsx`. It is not only an Excel template.

## Install (Mac, from the repository root)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-scraper.txt
```

## Verify that Excel generation works immediately (synthetic sample, NOT real cases)

```bash
python -m scraper.jiwon_scraper --demo --output output
```

Open `output/TrialWatch_Case_Review.xlsx`.

## Scrape real public judgment URLs

Create `urls.txt` with one direct HTTPS PDF, HTML or TXT document URL per line, then:

```bash
python -m scraper.jiwon_scraper --urls urls.txt --output output
```

## Process real downloaded judgments

Put court judgment PDF/HTML/TXT files in `judgments/`, then:

```bash
python -m scraper.jiwon_scraper --files judgments --output output
```

The generated Excel workbook includes **Case Matches**, **Law Scores**, **Field Guide**, **Fetch Errors**, **START HERE**. CSV and JSON exports and extracted text files are also generated. One row is a document + *mention* of a law, **not** a verified charge or an individual criminal case. Law scores are user-provided structural metrics, not probabilities of misuse. Blank manual-review fields are intentional.

**Scope/limitations:** URL-list or local-file ingestion, not automatic search across all Indian courts. Public pages may block automated access, and image-only PDFs need OCR. Use only authorized public documents; comply with website terms and request limits. No GitHub push is performed by this archive.

## Add to your GitHub branch

Copy the `scraper/`, `data/law_scores.csv`, `tests/`, `requirements-scraper.txt` and this README into your existing repo; don't overwrite teammates' work. Then in your repo:

```bash
git switch JiwonScrapper
git add scraper data/law_scores.csv tests requirements-scraper.txt README-RUN.md
git commit -m "Add runnable judgment scraper with automatic Excel export"
git push -u origin JiwonScrapper
```

`git push` requires GitHub authorization. Do not commit `.venv`, `output`, credentials or private files.
