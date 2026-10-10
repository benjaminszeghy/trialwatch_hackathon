# CheckSignifier v4 — Four-tier TrialWatch queue

Takes Benny's JSON (`cases` array or list of records) containing PDF URLs. Optionally downloads HTTPS PDFs and extracts text; **does not automatically interpret PDFs or determine rights violations**. Structured, source-attributed `evidence` objects are needed for signal scoring. Generates a ranked Excel workbook plus JSON report.

## Priority tiers

| Tier | Criteria | TrialWatch action |
|---|---|---|
| Tier 1 — URGENT | Score >=75 or source-attributed urgent escalation | Immediate human review |
| Tier 2 — HIGH | Score 45–74 | Priority investigation |
| Tier 3 — ROUTINE | Score 0–44, not closed | Monitor and verify unknowns |
| Tier 4 — CLOSED | **Explicit human-reviewed closure only**, regardless of score | Archive; reopen if material new evidence |

Score = 45% urgency + 30% procedural concerns + 25% legal concerns. Thresholds are operational heuristics, not calibrated legal probabilities. Tier 4 is a **disposition**, not an inference that the case was fair. Missing evidence must never automatically trigger closure.

## Human-reviewed closure JSON

```json
{
  "case_id": "EXAMPLE-REVIEWED",
  "pdf_url": "https://example.org/order.pdf",
  "human_review": {
    "decision": "close_no_further_action",
    "reviewer": "TrialWatch reviewer",
    "reviewed_at": "2026-10-10",
    "rationale": "Documented reason why no further action is warranted",
    "evidence_reference": "https://example.org/order.pdf"
  }
}
```

Closure is rejected if reviewer, date, rationale, or evidence reference is missing, or if input explicitly indicates ongoing detention, immediate safety risk, or an urgent evidence flag. This is a safeguard, **not** a replacement for human approval or legal review. A high score can be closed only through a deliberate review decision, and new material evidence should trigger reopening. Tier 4 rows are retained at the bottom of the Excel queue for auditability.

## Install and run

```bash
python3 -m pip install artifact-tool pypdf
python3 research/checksignifier.py --input examples/benny_output.json --out outputs/checksignifier.xlsx
python3 research/checksignifier.py --input path/to/benny_actual.json --out outputs/checksignifier.xlsx --fetch-pdfs
python3 -m unittest discover -s tests -p 'test_checksignifier.py' -v
```

The example PDF URLs are placeholders. For scanned PDFs, OCR is not included. For remote URLs, only fetch trusted domains and review network security before production deployment. The score is not a legal conclusion; all evidence assertions require source and human verification.
