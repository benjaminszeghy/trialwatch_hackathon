"""Clearly separated official-source candidates found in the Claude collaboration."""
from data_access import ROOT, fetch
from pathlib import Path
from pypdf import PdfReader
import json, hashlib, re

OUT = ROOT / 'outputs' / 'bns-training-starter' / 'supplements'
OUT.mkdir(exist_ok=True)
SOURCES = [
    ('imran-pratapgarhi-2025', 'BNS interpretation benchmark',
     'https://api.sci.gov.in/supremecourt/2025/3511/3511_2025_4_1501_60508_Judgement_28-Mar-2025.pdf',
     'Fixed Supreme Court interpretation reference from the earlier pilot; not an HC training-family observation.'),
    ('pawan-khera-2026', 'supplemental target-charge candidate',
     'https://api.sci.gov.in/supremecourt/2026/25523/25523_2026_3_62_70689_Judgement_30-Apr-2026.pdf',
     'Claude identified BNS parent 353 and 356 in the charge narrative. Independently inspect the stored passages; outside the Bombay 2024–2025 frame.'),
    ('ranveer-allahbadia-2025', 'supplemental target-charge candidate',
     'https://api.sci.gov.in/supremecourt/2025/8375/8375_2025_3_47_59435_Order_18-Feb-2025.pdf',
     'Claude identified BNS 196 and 299 in one of several FIRs. Record of Proceedings/interim order; multiple FIRs need connected-family grouping.'),
    ('ruchika-mitra-2026', 'supplemental target-charge candidate',
     'https://delhihighcourt.nic.in/app/showFileJudgment/60915012026CRLMM3472026_125440.pdf',
     'Claude identified BNS 356(2) in a private dispute. Settlement-based quashing is not an abuse label; speech and dispute type need separate review.'),
    ('vombatkere-bns-152-challenge-2025', 'constitutional-challenge reference; not a charge case',
     'https://api.sci.gov.in/officereport/2025/37157/37157_2025_2025-08-08_1607@1.pdf',
     'Office report about a constitutional challenge to BNS 152. This must not be counted as a defendant charged under 152.'),
    ('ashish-dave-2026', 'BNS case outside the six target sections',
     'https://api.sci.gov.in/supremecourt/2025/68616/68616_2025_2_34_68884_FinalOrder_27-Feb-2026.pdf',
     'Claude identified BNS 308(2), 318(4), 351(2), and a media-employment context. Reference for a possible future expansion; not a current target-law positive.')
]

def main():
    results = []
    for id, kind, url, note in SOURCES:
        row = {'document_id': id, 'kind': kind, 'source_url': url, 'note': note,
            'selection': 'purposive official-source supplement; separate from the AWS retrieval frame',
            'human_labels': None, 'review_status': 'downloaded text; independent human/legal check pending'}
        try:
            p = fetch(url, 'bns-supplements/' + id + '.pdf', 20_000_000)
            data = p.read_bytes()
            assert data.startswith(b'%PDF')
            (OUT / (id + '.pdf')).write_bytes(data)
            pages = [{'page': i + 1, 'text': page.extract_text() or ''} for i, page in enumerate(PdfReader(p).pages)]
            (OUT / (id + '.pages.json')).write_text(json.dumps(pages, ensure_ascii=False))
            row.update({'retrieval_status': 'success', 'pdf_sha256': hashlib.sha256(data).hexdigest(),
                        'page_count': len(pages), 'pdf_file': id + '.pdf', 'pages_file': id + '.pages.json'})
            passages = []
            # Retrieval-only snippets, not automatic legal findings.
            for page in pages:
                for match in re.finditer(r'\bBNS\b|Bharatiya|FIR\s*No|F\.I\.R', page['text'], re.I):
                    start, end = max(0, match.start() - 200), min(len(page['text']), match.end() + 550)
                    passages.append({'page': page['page'], 'char_start': start, 'char_end': end,
                        'quote': page['text'][start:end], 'status': 'retrieval snippet; human support check required'})
            row['retrieval_passages'] = passages
        except Exception as exc:
            row.update({'retrieval_status': 'failed', 'error': str(exc)})
        results.append(row)
        print(id, row['retrieval_status'], row.get('page_count'), flush=True)
    (OUT / 'manifest.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == '__main__': main()
