"""Source-backed initial fit assessment and independent Yes/No feedback.

This is a transparent evidence rubric + feedback reranker, not a trained
misuse classifier. Missing details earn no evidence points; they do not prove
absence. Human labels are never manufactured from system assessments.
"""
from __future__ import annotations

from contextlib import nullcontext
import json
import re
from collections import defaultdict
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .core import encode, now
from .feedback import ReviewError, contexts

VERSION = 'trialwatch-fit-v1'
METHOD = {
    'version': VERSION,
    'weights': {'journalism': 35, 'expression': 15, 'support': 25, 'opening': 15, 'freshness': 10},
    'scale': '0–100 evidence-supported fit index, not a probability',
    'missing': 'No evidence points for missing facts; no finding that a need or journalist connection is absent.',
    'feedback': 'Same-law current reviews shift new candidates by at most 15 points. A current case Yes adds 20 points with a floor of 45; No sets fit to 0. No never closes a case or suppresses a verified urgent flag.',
    'peer_formula': '15 × (yes − no) / (4 + yes + no), excluding the current CNR; one vote per CNR even with several matching laws.',
    'freshness_guard': 'Automatic fit scores based on orders more than 30 days old or an unknown date are capped at 74; an old order cannot alone create an urgent tier.',
    'ranking': 'Reviewer No cases move after active candidates in the default two-layer queue, except independently verified urgent needs.',
    'labels': 'Human fit labels remain separate from human misuse labels and automatic predictions. No neural model is retrained.',
}

class FitInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    decision: Literal['yes', 'no']
    note: str = Field('', max_length=1500)
    expected_revision: int = Field(0, ge=0)
    evidence_version: str = Field(pattern=r'^[a-f0-9]{64}$')


def initialize(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS case_fit_features (
            cnr TEXT PRIMARY KEY REFERENCES cases(cnr), evidence_version TEXT NOT NULL,
            method_version TEXT NOT NULL, payload TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS case_fit_reviews (
            cnr TEXT PRIMARY KEY REFERENCES cases(cnr), revision INTEGER NOT NULL,
            payload TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS case_fit_review_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, cnr TEXT REFERENCES cases(cnr),
            revision INTEGER NOT NULL, action TEXT NOT NULL, payload TEXT NOT NULL,
            created_at TEXT NOT NULL, UNIQUE(cnr,revision));
    """)


# Require an apparent connection to a case participant. A bare word in a cited
# precedent, 'State counsel' or a routine translation direction isn't a gap.
ROLE = r'(?:applicant|petitioner|accused|defendant|complainant|respondent)'
PATTERNS = {
    'journalism': rf'\b{ROLE}\b[^.;\n]{{0,100}}\b(?:journalist|reporter|editor|news correspondent)\b',
    'expression': rf'\b{ROLE}\b[^.;\n]{{0,180}}\b(?:posted|published|uploaded|reported|speech|article|social media|video|news)\b',
    'counsel': rf'\b{ROLE}\b[^.;\n]{{0,100}}(?:unrepresented|without (?:a |any )?(?:lawyer|counsel)|denied[^.;\n]{{0,45}}(?:counsel|legal aid))',
    'interpretation': rf'\b{ROLE}\b[^.;\n]{{0,100}}(?:denied[^.;\n]{{0,45}}(?:interpreter|interpretation)|no interpreter|interpreter[^.;\n]{{0,35}}(?:unavailable|not provided))',
    'access': rf'\b{ROLE}\b[^.;\n]{{0,120}}(?:denied access to|not supplied with|not provided with)[^.;\n]{{0,60}}(?:evidence|documents|records)',
    'pending': r'\b(?:stand over to|list (?:this|the) (?:matter|application|petition)|investigation is (?:ongoing|in progress)|trial is pending|notice (?:is )?issued|returnable on)\b',
    'disposed': r'\b(?:application|petition|appeal|proceeding|matter)[^.;\n]{0,55}\b(?:disposed of|dismissed|allowed)\b',
}


def extract(store, db, cnr, context):
    docs = db.execute("SELECT * FROM documents WHERE cnr=? AND status='ready' ORDER BY order_date DESC,id", (cnr,)).fetchall()
    signals, scanned, available = {}, 0, 0
    latest_stage = None
    for doc in docs:
        if not doc['text_path']:
            continue
        try:
            pages = json.loads((store.root / doc['text_path']).read_text())
        except (OSError, ValueError):
            continue
        doc_stage = []
        for page in pages:
            raw = page.get('text', '')
            scanned += bool(raw.strip())
            if raw.strip():
                available += 1
            for key, pattern in PATTERNS.items():
                if key in signals and key not in ('pending', 'disposed'):
                    continue
                match = re.search(pattern, raw, re.I)
                if not match:
                    continue
                quote = raw[max(0, match.start()-60):match.end()+150].strip()
                # Keep exact substrings for independent quote validation.
                evidence = {'topic': key, 'quote': quote, 'page': page['page'],
                            'document_id': doc['id'], 'order_date': doc['order_date'],
                            'pdf_sha256': doc['sha256'],
                            'pdf_url': f'/api/documents/{doc["id"]}/pdf?sha256={doc["sha256"]}',
                            'status': 'System-extracted candidate; not human verified'}
                if key in ('pending', 'disposed'):
                    doc_stage.append((key, evidence))
                else:
                    signals.setdefault(key, evidence)
        if latest_stage is None and pages:
            # Older orders cannot turn a newer disposed application into pending.
            latest_stage = 'disposed' if any(k == 'disposed' for k, _ in doc_stage) else 'pending' if doc_stage else 'unknown'
            for key, evidence in doc_stage:
                if key == latest_stage:
                    signals[key] = evidence
                    break
    return {'signals': signals, 'pages_scanned': scanned, 'documents_ready': len(docs),
            'text_available': bool(available), 'latest_order_date': max((d['order_date'] or '' for d in docs), default='') or None,
            'order_stage': latest_stage or 'unknown',
            'sections': context['snapshot']['sections'], 'extracted_at': now()}


def base_assessment(features, *, as_of):
    signals = features['signals']
    journalism = 35 if 'journalism' in signals else 15 if 'expression' in signals else 0
    expression = 15 if 'expression' in signals else 5 if any(s in features['sections'] for s in ('152', '196', '299', '353', '356')) else 0
    support = sum(points for key, points in [('counsel', 10), ('interpretation', 7.5), ('access', 7.5)] if key in signals)
    # This is a potential reading/monitoring route, never confirmed present-day
    # capacity. A disposed High Court application isn't a closed criminal case.
    opening = 15 if features['order_stage'] == 'pending' else 5 if features['text_available'] else 0
    latest = features.get('latest_order_date')
    age = max(0, (as_of - date.fromisoformat(latest)).days) if latest else None
    freshness = 10 if age is not None and age <= 30 else 5 if age is not None and age <= 90 else 0
    factors = [
        {'key': 'journalism', 'label': 'Journalist / reporting link', 'points': journalism, 'max': 35,
         'status': 'Participant role mentioned; verify' if 'journalism' in signals else 'Expression activity mentioned; profession unknown' if 'expression' in signals else 'No link identified in available text'},
        {'key': 'expression', 'label': 'Expression-law connection', 'points': expression, 'max': 15,
         'status': 'Activity in document' if 'expression' in signals else 'Law metadata only' if expression else 'No supported connection'},
        {'key': 'support', 'label': 'Documented support gaps', 'points': support, 'max': 25,
         'status': 'Candidate gap passages found' if support else 'Counsel, interpreter and access gaps not established'},
        {'key': 'opening', 'label': 'Potential opening to act', 'points': opening, 'max': 15,
         'status': 'Pending application at order date; current status unverified' if features['order_stage'] == 'pending' else 'Evidence review possible; current court stage unverified'},
        {'key': 'freshness', 'label': 'Source freshness', 'points': freshness, 'max': 10,
         'status': f'Latest order {age} days old' if age is not None else 'Order date unavailable'},
    ]
    score = sum(f['points'] for f in factors)
    # Generic speech prosecutions and missing identity cannot become urgent.
    if 'journalism' not in signals:
        score = min(score, 40)
    if age is None or age > 30:
        score = min(score, 74)
    reasons = [f['status'] for f in factors]
    return {'base_score': score, 'factors': factors, 'reasons': reasons,
            'recommendation': 'Potential TrialWatch fit' if 'journalism' in signals else 'Reporting connection to verify' if 'expression' in signals else 'Limited fit evidence',
            'evidence': list(signals.values()), 'missing': [k for k in ('journalism', 'counsel', 'interpretation', 'access') if k not in signals],
            'pages_scanned': features['pages_scanned'], 'documents_ready': features['documents_ready'],
            'method_version': VERSION, 'is_probability': False, 'as_of': str(as_of),
            'current_status_verified': False, 'source': 'Automatic document assessment' if features['text_available'] else 'Automatic metadata assessment'}


def state(store, db, evidence_contexts, *, as_of):
    cached = {r['cnr']: r for r in db.execute('SELECT * FROM case_fit_features')}
    records = {r['cnr']: r for r in db.execute('SELECT * FROM case_fit_reviews')}
    reviews, items = {}, {}
    votes = defaultdict(dict)
    for cnr, context in evidence_contexts.items():
        row = records.get(cnr)
        payload = json.loads(row['payload']) if row else {}
        current = bool(payload.get('decision')) and payload.get('evidence_version') == context['evidence_version']
        reviews[cnr] = {'decision': payload.get('decision'), 'note': payload.get('note', ''),
                        'revision': row['revision'] if row else 0, 'updated_at': row['updated_at'] if row else None,
                        'needs_recheck': bool(payload.get('decision')) and not current, 'score_eligible': current}
        if current:
            for section in context['snapshot']['sections']:
                votes[section][cnr] = payload['decision']
    for cnr, context in evidence_contexts.items():
        row = cached.get(cnr)
        if row and row['evidence_version'] == context['evidence_version'] and row['method_version'] == VERSION:
            features = json.loads(row['payload'])
        else:
            features = extract(store, db, cnr, context)
            db.execute('INSERT INTO case_fit_features VALUES(?,?,?,?,?) ON CONFLICT(cnr) DO UPDATE SET evidence_version=excluded.evidence_version,method_version=excluded.method_version,payload=excluded.payload,updated_at=excluded.updated_at',
                       (cnr, context['evidence_version'], VERSION, encode(features), now()))
        auto = base_assessment(features, as_of=as_of)
        peers = {key: value for section in context['snapshot']['sections'] for key, value in votes[section].items() if key != cnr}
        yes, no = sum(v == 'yes' for v in peers.values()), sum(v == 'no' for v in peers.values())
        shift = 15 * (yes - no) / (4 + yes + no)
        score = max(0, min(100, auto['base_score'] + shift))
        review = reviews[cnr]
        if review['score_eligible']:
            score = min(100, max(45, score + 20)) if review['decision'] == 'yes' else 0
        elif 'journalism' not in features['signals']:
            score = min(score, 40)
        if auto['factors'][-1]['points'] != 10:
            score = min(score, 74)
        score = round(score, 1)
        tier = 'urgent' if score >= 75 else 'high' if score >= 45 else 'routine'
        label = 'Confirmed fit' if review['score_eligible'] and review['decision'] == 'yes' else 'Not relevant · reviewer' if review['score_eligible'] else auto['recommendation']
        auto.update(score=score, score_display=f'{score:g}/100', tier=tier, label=label, feedback=review,
                    peer_feedback={'yes': yes, 'no': no, 'score_shift': round(shift, 2)},
                    evidence_version=context['evidence_version'], method=METHOD)
        items[cnr] = auto
    return items


def save(store, cnr, data, *, clear=False, connection=None):
    with (nullcontext(connection) if connection is not None else store.db()) as db:
        if connection is None:
            db.execute('BEGIN IMMEDIATE')
        context = contexts(db).get(cnr)
        if context is None:
            raise ReviewError(404, 'Case not found')
        old = db.execute('SELECT * FROM case_fit_reviews WHERE cnr=?', (cnr,)).fetchone()
        revision = old['revision'] if old else 0
        if data.expected_revision != revision:
            raise ReviewError(409, 'TrialWatch fit feedback changed. Reload before saving.')
        if not clear and data.evidence_version != context['evidence_version']:
            raise ReviewError(409, 'Case evidence changed. Reload before saving fit feedback.')
        if not clear and not any(d['status'] == 'ready' for d in context['snapshot']['documents']):
            raise ReviewError(422, 'Read an available court document before recording fit feedback.')
        payload = {'decision': None if clear else data.decision, 'note': '' if clear else data.note.strip(),
                   'evidence_version': context['evidence_version'], 'snapshot': context['snapshot'],
                   'method_version': VERSION, 'reviewer_scope': 'Local team feedback; not individually authenticated',
                   'reviewed_at': now()}
        prior = json.loads(old['payload']) if old else {}
        if old and all(prior.get(k) == payload[k] for k in ('decision', 'note', 'evidence_version')):
            return
        stamp = now()
        db.execute('INSERT INTO case_fit_reviews VALUES(?,?,?,?) ON CONFLICT(cnr) DO UPDATE SET revision=excluded.revision,payload=excluded.payload,updated_at=excluded.updated_at',
                   (cnr, revision+1, encode(payload), stamp))
        db.execute('INSERT INTO case_fit_review_events(cnr,revision,action,payload,created_at) VALUES(?,?,?,?,?)',
                   (cnr, revision+1, 'clear' if clear else 'save', encode(payload), stamp))


def export(db):
    current = contexts(db)
    items = []
    for row in db.execute('SELECT * FROM case_fit_reviews ORDER BY cnr'):
        p = json.loads(row['payload'])
        if p['decision'] and p['evidence_version'] == current[row['cnr']]['evidence_version']:
            items.append({'cnr': row['cnr'], 'revision': row['revision'], **p,
                          'label_task': 'trialwatch_fit', 'label_status': 'Unadjudicated human feedback',
                          'family_group_verified': False, 'suggested_split_group': row['cnr']})
    return {'items': items, 'total': len(items), 'method': METHOD, 'exported_at': now()}
