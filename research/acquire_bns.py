"""Bounded BNS-only acquisition from the recorded Bombay AWS metadata snapshot.

This is a retrieval corpus, not a labelled abuse dataset. Two endpoint orders per
CNR are selected without reading their outcome. Every attempted URL is retained.
"""
from data_access import ROOT, CACHE, base, s3get
import sys, json, hashlib, urllib.parse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, str(ROOT / 'work' / 'deps'))
import duckdb
from pypdf import PdfReader

OUT = ROOT / 'work' / 'bns-corpus'
OUT.mkdir(exist_ok=True)
HC = 'indian-high-court-judgments'
TARGETS = ['152', '196', '299', '353', '356', '221']

def main():
    frame = json.loads((CACHE / 'hc_sampling_frame.json').read_text())
    frame = [r for r in frame if any(x == 'BNS:' + s for s in TARGETS for x in r['law_hits'])]
    paths = sorted((CACHE / HC / 'metadata' / 'parquet').glob('year=*/court=27_1/bench=*/metadata-mobile.parquet'))
    paths = [p for p in paths if any('year=' + str(y) in str(p) for y in [2024, 2025])]
    assert paths, 'Recorded order metadata is required'
    con = duckdb.connect()
    cur = con.execute('SELECT * FROM read_parquet(?, union_by_name=true)', [[str(p) for p in paths]])
    names = [x[0] for x in cur.description]
    bycnr = {}
    for row in cur.fetchall():
        r = dict(zip(names, row))
        if r['pdf_link'] and r['decision_date']:
            bycnr.setdefault(r['cnr'], []).append(r)
    selected = []
    for case in sorted(frame, key=lambda r: r['cnr']):
        # Deduplicate metadata representations of the same PDF before selection.
        options = {str(o['year']) + '/' + str(o['bench']) + '/' + o['pdf_link']: o
                   for o in bycnr.get(case['cnr'], [])}
        ordered = sorted(options.values(), key=lambda o: (str(o['decision_date']), o['pdf_link']))
        endpoints = ordered[:1] + (ordered[-1:] if len(ordered) > 1 else [])
        for o in endpoints:
            key = f'data/pdf/year={o["year"]}/court=27_1/bench={o["bench"]}/{o["pdf_link"]}'
            url = base(HC) + urllib.parse.quote(key, safe='/=')
            selected.append({'document_id': hashlib.sha256(url.encode()).hexdigest()[:20],
                'cnr': case['cnr'], 'title': f'{case["petitioner"]} v {case["respondent"]}',
                'court': 'Bombay High Court', 'bench': o['bench'],
                'decision_date': str(o['decision_date']), 'source_url': url, 'key': key,
                'metadata_target_sections': [x[4:] for x in case['law_hits'] if x.startswith('BNS:')],
                'metadata_order_count': len(ordered), 'case_metadata': case,
                'order_metadata': o, 'selection': 'earliest/latest available order in fixed 2024–2025 window'})
    (OUT / 'retrieval_frame.json').write_text(json.dumps(frame, ensure_ascii=False, indent=2))
    (OUT / 'selected_orders.json').write_text(json.dumps(selected, ensure_ascii=False, default=str, indent=2))
    print(json.dumps({'candidate_cnrs': len(frame), 'selected_orders': len(selected)}), flush=True)
    def retrieve(item):
        try:
            p = s3get(HC, item['key'], 20_000_000)
            raw = p.read_bytes()
            if not raw.startswith(b'%PDF'): raise ValueError('Not a PDF')
            reader = PdfReader(p)
            pages = [{'page': i + 1, 'text': page.extract_text() or ''} for i, page in enumerate(reader.pages)]
            dest = OUT / (item['document_id'] + '.pages.json')
            dest.write_text(json.dumps(pages, ensure_ascii=False))
            item.update({'retrieval_status': 'success', 'pdf_path': str(p.relative_to(ROOT)),
                'pdf_sha256': hashlib.sha256(raw).hexdigest(), 'pdf_bytes': len(raw),
                'pages_path': str(dest.relative_to(ROOT)), 'page_count': len(pages),
                'text_characters': sum(len(x['text']) for x in pages)})
        except Exception as exc:
            item.update({'retrieval_status': 'failed', 'error': str(exc)})
        print(item['cnr'], item['decision_date'], item['retrieval_status'], item.get('page_count'), flush=True)
        return item
    with ThreadPoolExecutor(max_workers=2) as pool:
        docs = list(pool.map(retrieve, selected))
    (OUT / 'documents.json').write_text(json.dumps(docs, ensure_ascii=False, default=str, indent=2))
    summary = {'candidate_cnrs': len(frame), 'attempted_documents': len(docs),
        'retrieved_documents': sum(r['retrieval_status'] == 'success' for r in docs),
        'page_count': sum(r.get('page_count', 0) for r in docs),
        'metadata_section_counts': {s: sum('BNS:' + s in r['law_hits'] for r in frame) for s in TARGETS},
        'snapshot': 'Existing four-bench Bombay case-details joined to 2024–2025 order metadata',
        'selection_unit': 'CNR proceeding; not necessarily an independent FIR',
        'metadata_only_is_not_charge_confirmation': True}
    (OUT / 'acquisition_summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary), flush=True)

if __name__ == '__main__': main()
