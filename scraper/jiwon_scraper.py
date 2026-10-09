"""Collect public judgment documents from an explicit URL list, with source provenance.

This is a document collector, not a legal opinion, general web crawler, or
live case discovery service. It does not bypass paywalls, logins or CAPTCHA.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SCORES_PATH = ROOT / "data" / "law_scores.csv"
USER_AGENT = "TrialWatchLegalTripwireResearch/0.1 (public documents; respectful request rate)"

# Conservative, provision-specific matching. Mentions are NOT evidence of charges.
PATTERNS = {
    "BNS-152": [r"\b(?:BNS|Bharatiya Nyaya Sanhita)[,\s]*(?:section|sec\.?|s\.?)?\s*152\b", r"\bsection\s+152\s+of\s+(?:the\s+)?(?:BNS|Bharatiya Nyaya Sanhita)\b"],
    "BNS-196": [r"\b(?:BNS|Bharatiya Nyaya Sanhita)[,\s]*(?:section|sec\.?|s\.?)?\s*196(?:\s*\(1\))?\b", r"\bsection\s+196\s+of\s+(?:the\s+)?(?:BNS|Bharatiya Nyaya Sanhita)\b"],
    "BNS-299": [r"\b(?:BNS|Bharatiya Nyaya Sanhita)[,\s]*(?:section|sec\.?|s\.?)?\s*299\b", r"\bsection\s+299\s+of\s+(?:the\s+)?(?:BNS|Bharatiya Nyaya Sanhita)\b"],
    "BNS-353-1": [r"\b(?:BNS|Bharatiya Nyaya Sanhita)[,\s]*(?:section|sec\.?|s\.?)?\s*353\s*\(1\)\b", r"\bsection\s+353\s*\(1\)\s+of\s+(?:the\s+)?(?:BNS|Bharatiya Nyaya Sanhita)\b"],
    "BNS-353-2": [r"\b(?:BNS|Bharatiya Nyaya Sanhita)[,\s]*(?:section|sec\.?|s\.?)?\s*353\s*\(2\)\b", r"\bsection\s+353\s*\(2\)\s+of\s+(?:the\s+)?(?:BNS|Bharatiya Nyaya Sanhita)\b"],
    "BNS-356": [r"\b(?:BNS|Bharatiya Nyaya Sanhita)[,\s]*(?:section|sec\.?|s\.?)?\s*356(?:\s*\([12]\))?\b", r"\bsection\s+356\s+of\s+(?:the\s+)?(?:BNS|Bharatiya Nyaya Sanhita)\b"],
    "BNS-221": [r"\b(?:BNS|Bharatiya Nyaya Sanhita)[,\s]*(?:section|sec\.?|s\.?)?\s*221\b", r"\bsection\s+221\s+of\s+(?:the\s+)?(?:BNS|Bharatiya Nyaya Sanhita)\b"],
    "UAPA-13": [r"\b(?:UAPA|Unlawful Activities\s*\(Prevention\)\s*Act)[,\s]*(?:section|sec\.?|s\.?)?\s*13\b", r"\bsection\s+13\s+of\s+(?:the\s+)?(?:UAPA|Unlawful Activities\s*\(Prevention\)\s*Act)\b"],
    "IT-67": [r"\b(?:IT Act|Information Technology Act)[,\s]*(?:section|sec\.?|s\.?)?\s*67(?!\s*[ABab])\b", r"\bsection\s+67\s+of\s+(?:the\s+)?(?:IT Act|Information Technology Act)\b"],
    "OSA-3": [r"\b(?:Official Secrets Act|OSA)[,\s]*(?:section|sec\.?|s\.?)?\s*3\b", r"\bsection\s+3\s+of\s+(?:the\s+)?(?:Official Secrets Act|OSA)\b"],
    "OSA-5": [r"\b(?:Official Secrets Act|OSA)[,\s]*(?:section|sec\.?|s\.?)?\s*5\b", r"\bsection\s+5\s+of\s+(?:the\s+)?(?:Official Secrets Act|OSA)\b"],
    "IT-66A": [r"\b(?:IT Act|Information Technology Act)[,\s]*(?:section|sec\.?|s\.?)?\s*66\s*A\b", r"\bsection\s+66\s*A\s+of\s+(?:the\s+)?(?:IT Act|Information Technology Act)\b"],
}
SPEECH_TERMS = ["journalist", "reporter", "editor", "newspaper", "press", "publication", "article", "speech", "protest", "activist", "social media", "tweet", "expression"]
FIELDNAMES = ["document_id", "source_url", "retrieved_at_utc", "document_title", "sha256", "law_id", "law_label", "law_score_100", "law_status", "matched_excerpt", "speech_term_hits", "requires_human_review", "review_note", "text_file"]


def load_scores(path: Path = SCORES_PATH) -> dict[str, dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return {row["law_id"]: row for row in csv.DictReader(f)}


def detect_laws(text: str) -> dict[str, str]:
    """Return first short context snippet per law; never assert charge or guilt."""
    found = {}
    for law_id, patterns in PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                start, end = max(0, match.start()-110), min(len(text), match.end()+140)
                found[law_id] = " ".join(text[start:end].split())
                break
    return found


def extract_document(content: bytes, content_type: str, url: str) -> tuple[str, str]:
    ctype = content_type.lower()
    if "pdf" in ctype or urlparse(url).path.lower().endswith(".pdf") or content.startswith(b"%PDF"):
        reader = PdfReader(io.BytesIO(content))
        # Scanned/image-only PDFs require a separate OCR workflow.
        return (" ".join(page.extract_text() or "" for page in reader.pages), "PDF judgment")
    if "html" in ctype or content.lstrip()[:100].lower().startswith((b"<!doctype html", b"<html")):
        soup = BeautifulSoup(content, "html.parser")
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()
        title = soup.title.get_text(" ", strip=True) if soup.title else "HTML judgment"
        return (soup.get_text(" ", strip=True), title)
    if "text/plain" in ctype or urlparse(url).path.lower().endswith(".txt"):
        return (content.decode("utf-8", errors="replace"), "Text judgment")
    raise ValueError(f"Unsupported document type: {content_type or 'unknown'}")


def collect(urls: list[str], output_dir: Path, delay: float, timeout: int, max_bytes: int) -> tuple[list[dict], list[dict]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    text_dir = output_dir / "texts"
    text_dir.mkdir(exist_ok=True)
    scores = load_scores()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html,application/pdf,text/plain"})
    rows, errors, seen = [], [], set()
    for index, url in enumerate(urls):
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            errors.append({"source_url": url, "error": "Only public HTTPS URLs supported"})
            continue
        if index:
            time.sleep(delay)
        try:
            with session.get(url, timeout=timeout, stream=True, allow_redirects=True) as response:
                response.raise_for_status()
                if urlparse(response.url).scheme != "https":
                    raise ValueError("Redirected away from HTTPS")
                chunks, total = [], 0
                for chunk in response.iter_content(chunk_size=65536):
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError("Document exceeds max size")
                    chunks.append(chunk)
                content = b"".join(chunks)
                text, title = extract_document(content, response.headers.get("Content-Type", ""), response.url)
            if not text.strip():
                raise ValueError("No extractable text; scanned PDF may require OCR")
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if digest in seen:
                continue
            seen.add(digest)
            doc_id = digest[:16]
            txt_path = text_dir / f"{doc_id}.txt"
            txt_path.write_text(text, encoding="utf-8")
            found = detect_laws(text)
            hits = sorted({term for term in SPEECH_TERMS if re.search(r"\b" + re.escape(term) + r"\b", text, re.IGNORECASE)})
            # Only matched documents appear in case_matches; unmatched texts still saved.
            for law_id, excerpt in found.items():
                score = scores[law_id]
                invalid = law_id == "IT-66A"
                rows.append({
                    "document_id": doc_id, "source_url": url,
                    "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                    "document_title": title, "sha256": digest, "law_id": law_id,
                    "law_label": score["label"], "law_score_100": score["score"],
                    "law_status": score["status"], "matched_excerpt": excerpt,
                    "speech_term_hits": "; ".join(hits),
                    "requires_human_review": "true",
                    "review_note": "Struck-down provision mentioned; check timing and context" if invalid else "Provision mention only; verify statute, charge, conduct and procedural facts",
                    "text_file": str(txt_path.relative_to(output_dir)),
                })
            print(f"[{index+1}/{len(urls)}] {url}: {len(found)} provision matches", file=sys.stderr)
        except (requests.RequestException, ValueError, OSError, Exception) as exc:
            errors.append({"source_url": url, "error": f"{type(exc).__name__}: {exc}"})
            print(f"ERROR {url}: {exc}", file=sys.stderr)
    return rows, errors


def collect_local(files, output_dir):
    """Extract real local PDF/HTML/TXT documents and detect law mentions."""
    output_dir.mkdir(parents=True, exist_ok=True)
    text_dir = output_dir / "texts"
    text_dir.mkdir(exist_ok=True)
    scores = load_scores()
    rows, errors, seen = [], [], set()
    for file in files:
        try:
            raw = file.read_bytes()
            ctype = {".pdf":"application/pdf", ".html":"text/html", ".htm":"text/html", ".txt":"text/plain"}[file.suffix.lower()]
            text, title = extract_document(raw, ctype, file.as_uri())
            if not text.strip():
                raise ValueError("No extractable text")
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if digest in seen: continue
            seen.add(digest)
            doc_id = digest[:16]
            (text_dir / f"{doc_id}.txt").write_text(text, encoding="utf-8")
            hits = sorted({term for term in SPEECH_TERMS if re.search(r"\b" + re.escape(term) + r"\b", text, re.IGNORECASE)})
            for law_id, excerpt in detect_laws(text).items():
                score = scores[law_id]
                rows.append({
                    "document_id":doc_id, "source_url":file.as_uri(),
                    "retrieved_at_utc":datetime.now(timezone.utc).isoformat(),
                    "document_title":file.name, "sha256":digest, "law_id":law_id,
                    "law_label":score["label"], "law_score_100":int(score["score"]) if score["score"] else "",
                    "law_status":score["status"], "matched_excerpt":excerpt,
                    "speech_term_hits":"; ".join(hits), "requires_human_review":"true",
                    "review_note": "Provision mention only; verify charges and case facts; invalid statute if IT-66A",
                    "text_file":f"texts/{doc_id}.txt"})
        except Exception as exc:
            errors.append({"source_url":str(file), "error":f"{type(exc).__name__}: {exc}"})
    return rows, errors


def main() -> None:
    parser = argparse.ArgumentParser(description="TrialWatch source-document collector")
    parser.add_argument("--urls", type=Path, help="Text file with one public HTTPS judgment URL per line")
    parser.add_argument("--files", type=Path, help="Folder containing downloaded PDF/HTML/TXT files")
    parser.add_argument("--demo", action="store_true", help="Generate and process synthetic sample documents")
    parser.add_argument("--output", type=Path, default=ROOT / "output")
    parser.add_argument("--delay", type=float, default=2.0, help="Seconds between document requests")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--max-mb", type=int, default=15)
    parser.add_argument("--no-excel", action="store_true", help="Skip automatic Excel export")
    args = parser.parse_args()
    if args.delay < 1:
        parser.error("--delay must be at least 1 second")
    if sum(bool(x) for x in (args.urls, args.files, args.demo)) != 1:
        parser.error("Specify exactly one of --urls, --files, or --demo")
    if args.demo:
        demo_dir = args.output / "demo_sources"
        demo_dir.mkdir(parents=True, exist_ok=True)
        (demo_dir / "SYNTHETIC_example_1.txt").write_text(
            "SYNTHETIC SAMPLE - NOT A REAL CASE. A journalist published an article. "
            "Section 196 of the BNS and Section 353(2) of the BNS were mentioned.", encoding="utf-8")
        (demo_dir / "SYNTHETIC_example_2.txt").write_text(
            "SYNTHETIC SAMPLE - NOT A REAL CASE. A reporter discussed Section 66A of the IT Act "
            "and Section 13 of UAPA.", encoding="utf-8")
        rows, errors = collect_local(sorted(demo_dir.glob("*.txt")), args.output)
    elif args.files:
        if not args.files.is_dir(): parser.error("--files must be an existing directory")
        files = sorted(p for p in args.files.rglob("*") if p.is_file() and p.suffix.lower() in {".pdf", ".html", ".htm", ".txt"})
        rows, errors = collect_local(files, args.output)
    else:
        urls = [line.strip() for line in args.urls.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")]
        rows, errors = collect(urls, args.output, args.delay, args.timeout, args.max_mb * 1024 * 1024)
    with (args.output / "case_matches.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    (args.output / "case_matches.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output / "errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.no_excel:
        from .excel_export import export_excel
        xlsx = export_excel(rows, errors, args.output / "TrialWatch_Case_Review.xlsx")
        print(f"Excel workbook: {xlsx}")
    print(f"Finished: {len(rows)} law mentions; {len(errors)} errors. Output: {args.output}")


if __name__ == "__main__":
    main()
