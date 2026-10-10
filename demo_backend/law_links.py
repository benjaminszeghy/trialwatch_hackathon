"""Join PDF candidates to the existing law rubric without scoring cases.

Text matches are review candidates, not charge findings. Metadata, document text
and AI-assisted snapshot review remain separate evidence types.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR_VERSION = 'law-link-v1'
SCORE_MEANING = 'Provisional statute-as-written review index; not a case misuse score or probability'
ACT = re.compile(r'\b(?:Bharatiya|Bhartiya|Bharatiy\s*a|Bh\s*aratiya|Bhar\s*tiya)\s+'
                 r'Nyay\s*a?\s+Sanhita\b|\bB\.?\s*N\.?\s*S\.?\b', re.I)
SECTION = re.compile(r'(?<![A-Za-z0-9])(\d{1,3})((?:\s*\(\s*[A-Za-z0-9]+\s*\))*)(?![A-Za-z0-9])')
CHARGE = re.compile(r'offen[cs]e|punishable|registered|\bFIR\b|charge|prosecut', re.I)
CLAUSE = re.compile(r'(?:sections?|u\s*/\s*s\.?)\s+(\d[\dA-Za-z\s(),./&;\-]{0,400}?)\s+of\s+(?:the\s+)?$', re.I)


def normalized(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def section_tokens(value):
    """Return precise numeric sections + bracketed subsections; reject word soup."""
    value = str(value or '')
    tokens = []
    for match in SECTION.finditer(value):
        tokens.append(match.group(1) + re.sub(r'\s+', '', match.group(2)))
    return sorted(set(tokens))


def text_references(pages):
    result = []
    for page in pages:
        text = normalized(page.get('text', ''))
        for act in ACT.finditer(text):
            prefix = text[max(0, act.start() - 450):act.start()]
            clause = CLAUSE.search(prefix)
            if not clause:
                continue
            values = clause.group(1)
            leftover = SECTION.sub('', values)
            leftover = re.sub(r'\band\b|\bread\b|\bwith\b|r\s*/\s*w', '', leftover, flags=re.I)
            if re.search(r'[A-Za-z0-9]', leftover):
                continue  # Do not cross another Act, quotation or unrelated sentence.
            start = max(0, act.start() - 450) + clause.start()
            quote = text[start:act.end()]
            role = 'charge_context_candidate' if CHARGE.search(text[max(0, start - 150):start]) else 'law_mention_candidate'
            result.append({'sections': section_tokens(values), 'page': page['page'],
                           'quote': quote, 'basis': 'automatic Act-bound text reference',
                           'role': role, 'human_verified': False})
    return result


@lru_cache(maxsize=2)
def _read_catalog(path, mtime_ns):
    raw = Path(path).read_bytes()
    data = json.loads(raw)
    profiles = []
    for law in data['laws']:
        if law['era'] != 'BNS':
            continue
        for hit in law['metadata_parent_hits']:
            profiles.append({
                'id': law['id'], 'name': law['name'], 'act': 'BNS', 'parent_section': hit.split(':')[1],
                'raw_total': law['raw_total'], 'raw_max': law['raw_max'], 'score_100': law['score_100'],
                'rubric_version': data['rubric_version'], 'score_as_of': data['as_of'],
                'validation_status': law['coding_status'], 'score_meaning': SCORE_MEANING,
                'profile_scope': law['name'].split(' — ')[0], 'notes': law['notes'],
                'components': {k: v['rating'] for k, v in law['components'].items()},
                'sources': law['sources']})
    return {'profiles': profiles, 'sha256': hashlib.sha256(raw).hexdigest(),
            'as_of': data['as_of'], 'version': data['rubric_version']}


def catalog(path=ROOT / 'outputs/law-scores.json'):
    path = Path(path).resolve()
    return _read_catalog(str(path), path.stat().st_mtime_ns)


def resolve_profiles(section, references, source_catalog):
    profiles = [p for p in source_catalog['profiles'] if p['parent_section'] == section]
    specific = [r for r in references if r.startswith(section + '(')]
    numbers = {re.match(r'\d+\((\d+)\)', r).group(1) for r in specific
               if re.match(r'\d+\((\d+)\)', r)}
    unresolved = not specific or section in references
    uncovered = []
    if section == '353':
        if not unresolved:
            profiles = [p for p in profiles if p['id'].rsplit('-', 1)[-1] in numbers]
        uncovered = sorted(numbers - {'1', '2'})
    elif section == '356':
        uncovered = sorted(numbers - {'1', '2'})
        if not unresolved and not numbers.intersection({'1', '2'}):
            profiles = []
    elif section == '196':
        # Only the expression/harmony limbs (1)(a)-(b) are in the current rubric.
        outside = [r for r in specific if r.startswith('196(1)(c)') or re.match(r'196\((?:[3-9]|\d{2,})\)', r)]
        inside = [r for r in specific if r.startswith(('196(1)(a)', '196(1)(b)'))]
        uncovered = outside
        if outside and not inside and not unresolved and '196(1)' not in references:
            profiles = []
        unresolved = unresolved or '196(1)' in references or ('196(2)' in references and not inside)
    status = 'scope_unresolved' if unresolved and section in ('196', '353', '356') else 'profile_match_candidate'
    if uncovered:
        status = 'partly_unscored_scope' if profiles else 'unscored_scope'
    return profiles, status, uncovered


def build_links(sections, case_metadata, pages, review, *, pdf_sha256, source_catalog):
    from research.law_identity import act_family
    acts = case_metadata.get('acts') or case_metadata.get('case_metadata', {}).get('acts') or []
    if isinstance(acts, str):
        try:
            acts = json.loads(acts)
        except ValueError:
            acts = []
    references = text_references(pages)
    seed = review if review and review.get('evidence_pdf_sha256') == pdf_sha256 else None
    # Verify a seed's cited passage before accepting its stronger review status.
    if seed:
        page = next((p for p in pages if p['page'] == seed.get('page')), None)
        if not page or normalized(seed.get('quote', '')) not in normalized(page.get('text', '')):
            seed = None
    links = []
    for section in sections:
        metadata_refs = sorted({token for act in acts if isinstance(act, dict) and act_family(act.get('act', '')) == 'BNS'
                                for token in section_tokens(act.get('section', ''))
                                if token == section or token.startswith(section + '(')})
        evidence = [r for r in references if any(s == section or s.startswith(section + '(') for s in r['sections'])]
        doc_refs = sorted({s for r in evidence for s in r['sections'] if s == section or s.startswith(section + '(')})
        basis = 'metadata_only'
        seed_refs = []
        if seed:
            seed_refs = [s for s in seed.get('verified_target_sections', []) if s == section or s.startswith(section + '(')]
            if seed_refs and seed.get('role') == 'operative charge recorded':
                basis = 'ai_review_charge_recorded'
                evidence = [{'sections': seed_refs, 'page': seed['page'], 'quote': seed['quote'],
                             'basis': 'AI-assisted snapshot review', 'role': seed['role'], 'human_verified': False}]
                doc_refs = sorted(seed_refs)
            elif seed.get('role') == 'IPC/BNS metadata conflict':
                basis = 'metadata_conflict'
                evidence = [{'page': seed['page'], 'quote': seed['quote'], 'basis': 'AI-assisted snapshot review',
                             'role': seed['role'], 'human_verified': False}]
                doc_refs = []
            elif seed.get('role') != 'operative charge recorded':
                basis = 'target_not_confirmed_in_review'
                doc_refs = []
            elif not seed_refs:
                basis = 'target_not_confirmed_in_review'
        elif evidence:
            basis = 'text_reference_candidate'
        profiles, scope, uncovered = resolve_profiles(section, doc_refs or metadata_refs, source_catalog)
        metadata_branches = {s.split(')')[0] + ')' for s in metadata_refs if '(' in s}
        document_branches = {s.split(')')[0] + ')' for s in doc_refs if '(' in s}
        disagreement = bool(metadata_branches and document_branches and metadata_branches.isdisjoint(document_branches))
        scores = sorted({p['raw_total'] for p in profiles})
        links.append({'act': 'BNS', 'section': section, 'association_status': basis,
            'metadata_sections': metadata_refs or [section], 'document_sections': doc_refs,
            'scope_status': scope, 'unscored_subsections': uncovered,
            'metadata_document_subsection_disagreement': disagreement,
            'profiles': profiles, 'score_display': (str(scores[0]) if len(scores) == 1 else f'{scores[0]}–{scores[-1]}') + '/12' if scores else 'Not scored for this scope',
            'raw_score_range': [min(scores), max(scores)] if scores else None,
            'score_meaning': SCORE_MEANING, 'score_role': 'associated law profile; never a document/case score',
            'human_verified': False, 'evidence_pdf_sha256': pdf_sha256, 'evidence': evidence,
            'notes': 'Metadata-only links may not appear in this order. Text/review links still need independent legal checks.'})
    return links


def sync_catalog(store, source_catalog=None):
    source_catalog = source_catalog or catalog()
    with store.db() as db:
        for p in source_catalog['profiles']:
            db.execute('''INSERT INTO law_profiles VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET parent_section=excluded.parent_section,
                raw_total=excluded.raw_total,raw_max=excluded.raw_max,score_100=excluded.score_100,
                rubric_version=excluded.rubric_version,score_as_of=excluded.score_as_of,
                catalog_sha256=excluded.catalog_sha256,payload=excluded.payload''',
                (p['id'], p['parent_section'], p['raw_total'], p['raw_max'], p['score_100'],
                 p['rubric_version'], p['score_as_of'], source_catalog['sha256'], json.dumps(p)))
    return source_catalog


def sync_document(store, identifier, source_catalog=None):
    source_catalog = source_catalog or catalog()
    with store.db() as db:
        row = db.execute('''SELECT d.*,c.sections,c.metadata AS case_metadata FROM documents d
                           JOIN cases c USING(cnr) WHERE d.id=?''', (identifier,)).fetchone()
        review = db.execute('SELECT payload FROM seed_reviews WHERE document_id=?', (identifier,)).fetchone()
    if not row:
        return []
    pages = json.loads((store.root / row['text_path']).read_text()) if row['status'] == 'ready' and row['text_path'] else []
    links = build_links(json.loads(row['sections']), json.loads(row['case_metadata']), pages,
                        json.loads(review[0]) if review else None,
                        pdf_sha256=row['sha256'], source_catalog=source_catalog)
    timestamp = datetime.now(timezone.utc).isoformat(timespec='seconds')
    with store.db() as db:
        db.execute('DELETE FROM document_law_links WHERE document_id=?', (identifier,))
        for link in links:
            db.execute('INSERT INTO document_law_links VALUES(?,?,?,?,?,?)',
                       (identifier, link['section'], json.dumps(link, ensure_ascii=False),
                        row['sha256'], source_catalog['sha256'], timestamp))
    return links


def sync_all(store):
    source_catalog = sync_catalog(store)
    with store.db() as db:
        identifiers = [r[0] for r in db.execute('SELECT id FROM documents')]
    for identifier in identifiers:
        sync_document(store, identifier, source_catalog)
    return audit(store)


def get_links(db, identifier):
    rows = db.execute('''SELECT l.*,d.sha256,c.sections,c.metadata AS case_metadata
        FROM document_law_links l JOIN documents d ON d.id=l.document_id
        JOIN cases c USING(cnr) WHERE l.document_id=? ORDER BY l.section''', (identifier,)).fetchall()
    source_catalog = catalog()
    if rows and any(r['pdf_sha256'] != r['sha256'] or r['catalog_sha256'] != source_catalog['sha256'] for r in rows):
        # A concurrent refresh may publish a new PDF before its derived links.
        # Fall back to current metadata until evidence has been reprocessed.
        links = build_links(json.loads(rows[0]['sections']), json.loads(rows[0]['case_metadata']), [], None,
                            pdf_sha256=rows[0]['sha256'], source_catalog=source_catalog)
        for link in links:
            link['association_status'] = 'evidence_stale_pending_recheck'
        return links
    return [json.loads(r['payload']) for r in rows]


def audit(store):
    with store.db() as db:
        missing = db.execute('''SELECT COUNT(*) FROM documents d WHERE NOT EXISTS
            (SELECT 1 FROM document_law_links l WHERE l.document_id=d.id)''').fetchone()[0]
        rows = db.execute('''SELECT d.id,d.status,l.section,l.payload FROM documents d
                            JOIN document_law_links l ON l.document_id=d.id''').fetchall()
        counts = {r[0]: r[1] for r in db.execute('SELECT status,COUNT(*) FROM documents GROUP BY status')}
        linked_ready = {r['id'] for r in rows if r['status'] == 'ready'}
        ready = [r for r in rows if r['status'] == 'ready']
        evidence_docs = {r['id'] for r in ready if json.loads(r['payload'])['association_status'] in
                         ('ai_review_charge_recorded', 'text_reference_candidate')}
        metadata_only_docs = {r['id'] for r in ready if json.loads(r['payload'])['association_status'] == 'metadata_only'}
        evidence_rows = Counter(json.loads(r['payload'])['association_status'] for r in ready)
        section_counts = []
        for section in sorted({r['section'] for r in rows}, key=int):
            options = [json.loads(r[0]) for r in db.execute('SELECT payload FROM law_profiles WHERE parent_section=?', (section,))]
            subset = [r for r in ready if r['section'] == section]
            section_counts.append({'section': section, 'profiles': [{'id': p['id'], 'raw_total': p['raw_total'], 'raw_max': p['raw_max'], 'score_100': p['score_100']} for p in options],
                                   'saved_pdf_records_linked_by_metadata': len(subset),
                                   'text_or_ai_review_candidates': sum(json.loads(r['payload'])['association_status'] in ('ai_review_charge_recorded','text_reference_candidate') for r in subset)})
    return {'checked_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'document_records': sum(counts.values()), 'saved_pdf_records': counts.get('ready', 0),
            'pending_or_failed_records': sum(v for k, v in counts.items() if k != 'ready'),
            'documents_without_any_law_link': missing, 'saved_pdf_records_with_law_links': len(linked_ready),
            'saved_pdfs_with_any_text_or_ai_review_candidate': len(evidence_docs),
            'saved_pdfs_with_at_least_one_metadata_only_link': len(metadata_only_docs),
            'saved_pdf_law_link_status_counts': dict(evidence_rows), 'law_summary': section_counts,
            'score_meaning': SCORE_MEANING,
            'validation_limit': 'Automated association audit plus prior AI-assisted review; not human gold. Counts overlap across laws/statuses.'}
