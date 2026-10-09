# JiwonScrapper — TrialWatch Legal Tripwire

An initial, **URL-driven public-document collector** for historical case research. It accepts a user-supplied list of public HTTPS judgment URLs (HTML, PDF with extractable text, or TXT), extracts text, identifies *mentions* of selected Indian legal provisions, attaches the supplied law-level scores, and exports CSV/JSON with excerpts and source provenance.

It **does not** discover URLs automatically, search the full Indian High Court corpus, confirm criminal charges, classify a prosecution as abusive, or assess procedural fairness. These are follow-on modules. This prototype has not been validated against the live court sites.

## Setup (Mac Terminal, from repository root)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-scraper.txt
cp urls.example.txt urls.txt
# Edit urls.txt: add one authorized public HTTPS judgment URL per line
python -m scraper.jiwon_scraper --urls urls.txt --output output
```

Outputs:
- `output/case_matches.csv` and `.json`: one row per **document × matched provision**
- `output/texts/*.txt`: extracted source text
- `output/errors.json`: fetch and parse failures

A matched mention is not necessarily a charged offence. The source may discuss precedents, quote unrelated provisions, or use ambiguous shorthand. Always manually verify the statute, alleged conduct, date, court, outcome, and source context. Unmatched documents are saved as text but do not generate match rows. A blank CSV means no matching mentions, not that no cases exist.

## Law score source

`data/law_scores.csv` transcribes the user-supplied 2026-10-09 law scores. They are *law-level reference scores*, not case-specific determinations or verified legal advice. `IT-66A` is flagged as invalid with no numeric score. BNS 353(1) and 353(2) are matched separately; parent-only references are intentionally left unclassified. `IT-67` is the first-conviction reference scenario; `OSA-3` uses the specified defence/code branch, not a universal case-level score. IPC↔BNS mapping is not automatically inferred.

## Responsible collection

Use public URLs that permit automated access; review site terms and robots instructions. Keep the default 2-second delay or raise it. Do not evade CAPTCHA, login requirements, or rate limits. Prefer official bulk/open datasets for large-scale research. No personally identifying case facts should be treated as proof of misconduct. This prototype does not perform OCR on scanned PDFs.

## Git integration

Create or switch to your own `JiwonScrapper` branch. Copy these files into the team repo; avoid overwriting existing `data/` files. Commit the scraper and rubric, not the generated `output/` or secret credentials.

## Excel output (new)

Run from repository root:

```bash
python -m pip install -r requirements-scraper.txt
python -m scraper.jiwon_scraper --urls urls.txt --output output --excel
```

Creates `output/TrialWatch_Case_Review.xlsx` with **Case Matches**, **Law Scores**, **Field Guide**, **Fetch Errors**, and **START HERE** tabs. The workbook includes blank reviewer-only columns for case metadata, verified charges, journalism nexus, detention, bail, procedural concerns, outcome, and citations. **Blank is unknown, not a negative finding.** Case Matches are document/provision mentions, not confirmed charges or unique defendants. Law scores are supplied project inputs, not automatically inferred case-abuse scores.

For an offline demonstration without contacting external websites, create the empty workbook template with `python -m scraper.create_template`.
