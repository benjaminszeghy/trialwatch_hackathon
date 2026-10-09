"""Build a provenance-preserving BNS annotation corpus from downloaded orders."""
import hashlib, json, re
from collections import Counter, defaultdict
from pathlib import Path
from data_access import ROOT
from bns_review_seeds import SEEDS, STARTER_DOCS

SRC = ROOT / 'work' / 'bns-corpus'
OUT = ROOT / 'outputs' / 'bns-training-starter'
OUT.mkdir(parents=True, exist_ok=True)

def norm(text):
    return re.sub(r'\s+', ' ', text).strip()

def hash_text(text):
    return hashlib.sha256(text.encode()).hexdigest()

def main():
    docs = json.loads((SRC / 'documents.json').read_text())
    cases = json.loads((SRC / 'retrieval_frame.json').read_text())
    pages = {}
    byid = {d['document_id']: d for d in docs}
    bycnr = defaultdict(list)
    for d in docs:
        d['decision_date'] = d['decision_date'][:10]
        bycnr[d['cnr']].append(d)
        if d['retrieval_status'] == 'success':
            assert hashlib.sha256((ROOT / d['pdf_path']).read_bytes()).hexdigest() == d['pdf_sha256']
            pages[d['document_id']] = json.loads((ROOT / d['pages_path']).read_text())
            d['normalized_text_sha256'] = hash_text('\n'.join(norm(p['text']) for p in pages[d['document_id']]))
    reviews = []
    for s in SEEDS:
        d = byid[s['document_id']]
        p = next(p for p in pages[d['document_id']] if p['page'] == s['page'])
        text, quote = norm(p['text']), norm(s['quote'])
        start = text.find(quote)
        assert start >= 0, f'Unsupported quote: {s["document_id"]} p{s["page"]}: {quote}'
        # Store actual raw character offsets as well as normalized offsets.
        tokens = list(re.finditer(r'\S+', p['text']))
        pos, charmap = 0, []
        for i, token in enumerate(tokens):
            if i: charmap.append(token.start() - 1)
            charmap.extend(range(token.start(), token.end()))
        raw_start, raw_end = charmap[start], charmap[start + len(quote) - 1] + 1
        assert norm(p['text'][raw_start:raw_end]) == quote
        evidence = {'source_url': d['source_url'], 'document_id': d['document_id'],
            'pdf_sha256': d['pdf_sha256'], 'page': p['page'],
            'normalized_char_start': start, 'normalized_char_end': start + len(quote),
            'raw_char_start': raw_start, 'raw_char_end': raw_end,
            'quote': p['text'][raw_start:raw_end], 'source_type': s['source_type']}
        reviews.append({**s, 'cnr': d['cnr'], 'evidence': evidence,
            'annotation_status': 'AI-assisted text review; independent human/legal check pending',
            'applicability_validation': 'document assertion only; offence dates and transition rules require review'})
    review_by_doc = {r['document_id']: r for r in reviews}
    review_by_case = defaultdict(list)
    for r in reviews: review_by_case[r['cnr']].append(r)

    # Leakage groups are deliberately broader than verified FIR families. Shared
    # administrative PDFs may join unrelated proceedings; do not call that a FIR.
    parent = {r['cnr']: r['cnr'] for r in cases}
    def find(x):
        if parent[x] != x: parent[x] = find(parent[x])
        return parent[x]
    def union(a, b):
        a, b = find(a), find(b)
        parent[max(a, b)] = min(a, b)
    identities = defaultdict(set)
    for d in docs:
        if d.get('pdf_sha256'): identities['pdf:' + d['pdf_sha256']].add(d['cnr'])
        if d.get('normalized_text_sha256'): identities['text:' + d['normalized_text_sha256']].add(d['cnr'])
    for r in reviews:
        if r.get('family_key'): identities['family:' + r['family_key']].add(r['cnr'])
    # Same named petitioner may have more than one proceeding. Group conservatively
    # for splitting, without claiming their FIRs or legal outcomes are identical.
    for c in cases:
        identities['petitioner:' + norm(c['petitioner']).upper()].add(c['cnr'])
        for linked in c.get('linked_cases') or []:
            if isinstance(linked, dict):
                cnr = linked.get('cnr') or linked.get('cnr_no')
                if cnr in parent: union(c['cnr'], cnr)
    for members in identities.values():
        members = sorted(members)
        for member in members[1:]: union(members[0], member)
    groups = {cnr: 'leakage-' + hash_text(find(cnr))[:12] for cnr in parent}
    candidates = []
    for c in cases:
        cd = bycnr[c['cnr']]
        rr = review_by_case[c['cnr']]
        positives = [r for r in rr if r['verified_target_sections']]
        target = sorted({x for r in positives for x in r['verified_target_sections']}, key=lambda x: (int(re.match(r'\d+', x)[0]), x))
        role = ('operative BNS target recorded; human check pending' if positives else
                'IPC/BNS metadata conflict' if any(r['role'] == 'IPC/BNS metadata conflict' for r in rr) else
                'reviewed; target charge not established' if rr else 'metadata-only; charge review pending')
        families = sorted({r['family_key'] for r in rr if r.get('family_key')})
        candidates.append({'cnr': c['cnr'], 'title': f'{c["petitioner"]} v {c["respondent"]}',
            'court': 'Bombay High Court', 'bench': c['bench'], 'case_type': c['case_type'],
            'metadata_bns_targets': '; '.join(x[4:] for x in c['law_hits'] if x.startswith('BNS:')),
            'text_confirmed_bns_targets': '; '.join(target), 'review_status': role,
            'documents_downloaded': len(cd), 'maximum_document_pages': max(d.get('page_count', 0) for d in cd),
            'first_order_date': min(d['decision_date'] for d in cd), 'last_order_date': max(d['decision_date'] for d in cd),
            'verified_family_key': '; '.join(families),
            'family_review_status': 'AI-assisted link; human check pending' if families else 'unresolved',
            'leakage_group_id': groups[c['cnr']], 'journalist_status': 'unknown',
            'human_abuse_label': None, 'human_law_role_label': None, 'split': 'unassigned',
            'evidence_refs': '; '.join(r['document_id'] + ':p' + str(r['page']) for r in rr),
            'source_urls': '\n'.join(d['source_url'] for d in cd),
            'notes': ' | '.join(r['note'] for r in rr) or 'Metadata hit is only a retrieval candidate.'})
    # Reviewed positive first; challenging counterexamples second; unreviewed last.
    start_cnrs = [byid[doc]['cnr'] for doc in STARTER_DOCS]
    candidates.sort(key=lambda c: (start_cnrs.index(c['cnr']) if c['cnr'] in start_cnrs else 1000,
        0 if c['text_confirmed_bns_targets'] else 1, -c['maximum_document_pages'], c['cnr']))
    (OUT / 'case-candidates.json').write_text(json.dumps(candidates, ensure_ascii=False, indent=2))
    (OUT / 'review-seeds.json').write_text(json.dumps(reviews, ensure_ascii=False, indent=2))

    records = []
    for d in docs:
        records.append({'document_id': d['document_id'], 'cnr': d['cnr'], 'title': d['title'],
            'court_level': 'HC', 'court': d['court'], 'bench': d['bench'], 'decision_date': d['decision_date'],
            'source_url': d['source_url'], 'pdf_sha256': d.get('pdf_sha256'),
            'normalized_text_sha256': d.get('normalized_text_sha256'),
            'local_pdf': 'pdfs/' + d['document_id'] + '.pdf',
            'metadata_bns_targets': d['metadata_target_sections'],
            'metadata_is_label': False, 'selection': d['selection'],
            'retrieval_status': d['retrieval_status'], 'leakage_group_id': groups[d['cnr']],
            'split': 'unassigned',
            'pages': [{**p, 'normalized_text': norm(p['text'])} for p in pages.get(d['document_id'], [])],
            'human_labels': {'law_role': None, 'bns_charged_sections': None, 'charge_evidence': None,
                'fir_number': None, 'fir_date': None, 'police_station': None,
                'offence_date': None, 'charge_bearer': None, 'charge_status': None,
                'dispute_type': None, 'document_type': None,
                'conduct_evidence': None, 'journalist_status': None, 'expression_nexus': None,
                'procedure_type': None, 'reasoning_evidence': None, 'element_states': None,
                'reviewer_id': None, 'reviewed_date': None}})
    (OUT / 'documents.jsonl').write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in records) + '\n')
    (OUT / 'acquisition-manifest.json').write_text(json.dumps(docs, ensure_ascii=False, indent=2))

    # A small first sheet includes positive examples, metadata mistakes and unknowns.
    annotation_rows = []
    for id in STARTER_DOCS:
        d, r = byid[id], review_by_doc[id]
        annotation_rows.append({'document_id': id, 'cnr': d['cnr'], 'title': d['title'],
            'decision_date': d['decision_date'], 'metadata_targets': '; '.join(d['metadata_target_sections']),
            'ai_seed_role': r['role'], 'ai_text_confirmed_targets': '; '.join(r['verified_target_sections']),
            'seed_page': r['page'], 'seed_quote': r['evidence']['quote'],
            'human_law_role': None, 'human_bns_sections': None, 'human_charge_evidence_page': None,
            'human_fir_number': None, 'human_fir_date': None, 'human_police_station': None,
            'human_charge_bearer': None, 'human_dispute_type': None, 'human_document_type': None,
            'human_charge_evidence_quote': None, 'human_conduct_evidence_page': None,
            'human_conduct_evidence_quote': None, 'human_expression_nexus': None,
            'human_journalist_status': None, 'human_procedure_type': None, 'reviewer_id': None,
            'reviewed_date': None, 'leakage_group_id': groups[d['cnr']], 'source_url': d['source_url'], 'notes': r['note']})
    (OUT / 'annotation-template.json').write_text(json.dumps(annotation_rows, ensure_ascii=False, indent=2))
    stats = {'retrieval_cnrs': len(cases), 'document_records': len(docs),
        'distinct_pdf_hashes': len({d.get('pdf_sha256') for d in docs}),
        'pdf_page_records': sum(d.get('page_count', 0) for d in docs),
        'documents_with_at_least_3_pages': sum(d.get('page_count', 0) >= 3 for d in docs),
        'ai_reviewed_documents': len(reviews),
        'cnrs_with_text_confirmed_target': sum(bool(c['text_confirmed_bns_targets']) for c in candidates),
        'text_confirmed_counts_by_parent_section': {s: sum(any(re.match(r'\d+', x)[0] == s for x in c['text_confirmed_bns_targets'].split('; ') if x) for c in candidates) for s in ['152','196','299','353','356','221']},
        'annotation_starter_documents': len(annotation_rows), 'human_gold_labels': 0,
        'leakage_groups': len(set(groups.values())), 'all_splits_unassigned': True,
        'review_counts': dict(Counter(c['review_status'] for c in candidates)),
        'scope': 'Four Bombay benches; recorded 2024–2025 order window; BNS target metadata retrieval only',
        'is_journalist_only': False, 'is_representative_sample': False}
    (OUT / 'summary.json').write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))

if __name__ == '__main__': main()
