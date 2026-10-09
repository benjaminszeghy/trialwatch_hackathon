"""Audit saved BNS PDFs and optionally live URLs; build a clickable PDF index.

CSV exports and original evidence records are read only. Live checks use curl's
normal TLS verification, two workers, HTTPS only, and a 25-second request limit.
"""
import argparse
import hashlib
import io
import json
import subprocess
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from pypdf import PdfReader
from data_access import ROOT

OUT = ROOT / 'outputs' / 'bns-training-starter'
GITHUB = 'https://github.com/benjaminszeghy/trialwatch_hackathon/blob/KaiScrapper/outputs/bns-training-starter/'
RAW = 'https://raw.githubusercontent.com/benjaminszeghy/trialwatch_hackathon/refs/heads/KaiScrapper/outputs/bns-training-starter/'


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def local_check(record, path, expected_pages):
    data = path.read_bytes()
    reader = PdfReader(io.BytesIO(data))
    count = len(reader.pages)
    result = {
        'local_pdf_present': True,
        'local_pdf_magic_valid': data.startswith(b'%PDF-'),
        'local_hash_matches': sha256(data) == record['pdf_sha256'],
        'actual_page_count': count,
        'page_count_matches': count == expected_pages,
    }
    return result, reader


def live_check(record):
    # Keep fresh remote bytes separate; never overwrite the research snapshot.
    with tempfile.TemporaryDirectory(prefix='bns-access-check-') as folder:
        path = Path(folder) / 'response.pdf'
        result = subprocess.run([
            'curl', '--silent', '--show-error', '--location', '--max-time', '25',
            '--proto', '=https', '--proto-redir', '=https',
            '--output', str(path), '--write-out', '%{http_code}\n%{content_type}\n%{url_effective}',
            record['source_url'],
        ], capture_output=True, text=True, timeout=30)
        lines = result.stdout.splitlines()
        status = int(lines[0]) if lines and lines[0].isdigit() else None
        data = path.read_bytes() if path.exists() else b''
        return {
            'http_status': status, 'content_type': lines[1] if len(lines) > 1 else None,
            'effective_url': lines[2] if len(lines) > 2 else None,
            'curl_exit_code': result.returncode,
            'remote_pdf_magic_valid': data.startswith(b'%PDF-'),
            'remote_hash_matches_snapshot': sha256(data) == record['pdf_sha256'] if data else False,
            'error': result.stderr.strip() or None,
        }


def main():
    args = argparse.ArgumentParser()
    args.add_argument('--live', action='store_true', help='Check every HC and supplemental source URL')
    options = args.parse_args()
    checked_at = datetime.now(timezone.utc).isoformat()
    docs = [json.loads(line) for line in (OUT / 'documents.jsonl').read_text().splitlines()]
    cases = json.loads((OUT / 'case-candidates.json').read_text())
    seeds = {r['document_id']: r for r in json.loads((OUT / 'review-seeds.json').read_text())}
    records = []
    for doc in docs:
        path = OUT / doc['local_pdf']
        checks, reader = local_check(doc, path, len(doc['pages']))
        checks['extracted_page_text_matches_snapshot'] = all(
            (page.extract_text() or '') == saved['text']
            for page, saved in zip(reader.pages, doc['pages'])
        )
        url = doc['source_url']
        checks['source_url_is_clean_https'] = (
            urlsplit(url).scheme == 'https' and not any(c.isspace() or c == '\\' for c in url)
        )
        local_pdf = doc['local_pdf']
        records.append({
            'document_id': doc['document_id'], 'cnr': doc['cnr'], 'title': doc['title'],
            'decision_date': doc['decision_date'], 'page_count': len(doc['pages']),
            'pdf_sha256': doc['pdf_sha256'], 'source_url': url,
            'local_pdf': local_pdf, 'github_pdf_url': GITHUB + local_pdf,
            'github_download_url': RAW + local_pdf,
            'ai_review_role': seeds.get(doc['document_id'], {}).get('role', 'not text-reviewed'),
            'human_review_status': 'independent human review pending',
            'local_checks': checks, 'live_check': None,
        })
    supplements = []
    for doc in json.loads((OUT / 'supplements' / 'manifest.json').read_text()):
        local_pdf = 'supplements/' + doc['pdf_file']
        checks, _ = local_check(doc, OUT / local_pdf, doc['page_count'])
        supplements.append({
            'document_id': doc['document_id'], 'source_url': doc['source_url'],
            'pdf_sha256': doc['pdf_sha256'], 'local_pdf': local_pdf,
            'github_pdf_url': GITHUB + local_pdf, 'kind': doc['kind'],
            'local_checks': checks, 'live_check': None,
        })
    if options.live:
        items = records + supplements
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {pool.submit(live_check, row): row for row in items}
            for count, future in enumerate(as_completed(futures), 1):
                row = futures[future]
                try:
                    row['live_check'] = future.result()
                except Exception as exc:
                    row['live_check'] = {'error': str(exc), 'http_status': None}
                if count % 25 == 0 or count == len(items):
                    print(f'Live sources checked: {count}/{len(items)}', flush=True)
    source_cells = [url for case in cases for url in case['source_urls'].splitlines()]
    summary = {
        'hc_document_records': len(records), 'hc_candidate_cnrs': len(cases),
        'hc_unique_pdf_hashes': len({r['pdf_sha256'] for r in records}),
        'hc_actual_pages': sum(r['local_checks']['actual_page_count'] for r in records),
        'hc_local_pdf_checks_passed': sum(all(r['local_checks'].values()) for r in records),
        'hc_documents_under_three_pages': sum(r['page_count'] < 3 for r in records),
        'supplemental_documents': len(supplements),
        'supplemental_local_checks_passed': sum(all(r['local_checks'].values()) for r in supplements),
        'candidate_url_cells_match_document_urls': Counter(source_cells) == Counter(r['source_url'] for r in records),
        'live_check_performed': options.live,
        'hc_live_http_200': sum((r['live_check'] or {}).get('http_status') == 200 for r in records) if options.live else None,
        'hc_live_hash_matches': sum((r['live_check'] or {}).get('remote_hash_matches_snapshot', False) for r in records) if options.live else None,
        'supplemental_live_http_200': sum((r['live_check'] or {}).get('http_status') == 200 for r in supplements) if options.live else None,
        'supplemental_live_hash_matches': sum((r['live_check'] or {}).get('remote_hash_matches_snapshot', False) for r in supplements) if options.live else None,
    }
    report = {'checked_at_utc': checked_at, 'summary': summary, 'documents': records, 'supplements': supplements}
    (OUT / 'document-access-audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    lines = [
        '# Open the BNS documents', '',
        'Each row below is one saved PDF. Click **Open PDF** for GitHub preview or **Download** for the original saved bytes. The AWS source is retained separately for provenance.', '',
        'The case CSV has one row per CNR and can contain two source URLs separated by a newline. Copy one URL at a time; backslashes, `&#x20;` and CSV quotation marks are formatting, not part of the URL. A CSV does not guarantee clickable hyperlinks.', '',
        '**Scope:** 107 candidate CNR proceedings; 177 document records; 174 distinct PDFs. These are not all independent prosecutions or journalist cases. Human labels remain blank.', '',
        f'Access and byte-integrity audit: `{checked_at}`. [Detailed checks](document-access-audit.json). Live access is a point-in-time observation.', '',
        '| CNR | Order date | Pages | PDF | Saved bytes | Original source |',
        '|---|---|---:|---|---|---|',
    ]
    case_order = {c['cnr']: i for i, c in enumerate(cases)}
    for row in sorted(records, key=lambda r: (case_order[r['cnr']], r['decision_date'], r['document_id'])):
        lines.append(f'| {row["cnr"]} | {row["decision_date"]} | {row["page_count"]} | [Open PDF]({row["github_pdf_url"]}) | [Download]({row["github_download_url"]}) | [AWS source]({row["source_url"]}) |')
    lines.extend(['', '## Separate reference documents', '',
        'These six documents are not part of the 107-CNR AWS sampling denominator.', '',
        '| Reference | Purpose | PDF |', '|---|---|---|'])
    for row in supplements:
        lines.append(f'| {row["document_id"]} | {row["kind"]} | [Open PDF]({row["github_pdf_url"]}) |')
    lines.extend(['', '## What the example links contain', '',
        'For Ashraf Naseem Khan (HCBM070353582025), the 4 July 2025 document is a one-page adjournment/interim-protection order without a charge list. The 8 September 2025 document has three pages and records BNS 353(1)(b)/353(2), a social-media allegation and anticipatory bail. Its observations are expressly limited to bail. These are two orders in one proceeding; bail is not an abuse label.', '',
        'The corpus has 130 documents under three pages. Some are informative, others lack charge or conduct facts. It is suitable for acquisition review and extraction annotation; it is not an already-labelled abuse-classifier training set.', ''])
    (OUT / 'document-index.md').write_text('\n'.join(lines))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
