"""Versioned team assessments and a transparent, separate law-score overlay.

These labels are reviewer judgments, not ground truth. This module does not
train a model or change the statute-as-written rubric.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict

from .core import digest, encode, now
from .law_links import catalog

DECISIONS = {
    'misuse': 'Misuse identified',
    'no_misuse': 'No misuse identified',
}
PRIOR_STRENGTH = 6
METHOD = {
    'version': 'review-feedback-v1',
    'prior_strength': PRIOR_STRENGTH,
    'formula': '(6 * original_score + 12 * yes_reviews) / (6 + yes_reviews + no_reviews)',
    'scale': '0–12 review index, not a probability',
    'unit': 'One current team assessment per CNR and selected law profile',
    'excluded': 'Unreviewed, cleared, stale and historical non-binary reviews do not change scores.',
    'validation': 'Provisional feedback policy; neither learned nor expert-validated.',
}


class ReviewError(ValueError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def initialize(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS case_reviews (
            cnr TEXT PRIMARY KEY REFERENCES cases(cnr), revision INTEGER NOT NULL,
            payload TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS case_review_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, cnr TEXT REFERENCES cases(cnr),
            revision INTEGER NOT NULL, action TEXT NOT NULL, payload TEXT NOT NULL,
            created_at TEXT NOT NULL, UNIQUE(cnr,revision));
    ''')


def contexts(db):
    """Batch the evidence fingerprint so queue reads don't issue N+1 queries."""
    source = catalog()
    documents = defaultdict(list)
    for row in db.execute('SELECT id,cnr,sha256,status,order_date,source_url FROM documents ORDER BY id'):
        documents[row['cnr']].append({k: row[k] for k in ('id', 'sha256', 'status', 'order_date', 'source_url')})
    result = {}
    for row in db.execute('SELECT * FROM cases'):
        metadata = json.loads(row['metadata'])
        snapshot = {
            'cnr': row['cnr'], 'title': row['title'], 'court': row['court'], 'bench': row['bench'],
            'sections': json.loads(row['sections']), 'source_metadata': metadata,
            'documents': documents[row['cnr']], 'catalog_sha256': source['sha256'],
        }
        version = digest(json.dumps(snapshot, sort_keys=True, ensure_ascii=False).encode())
        result[row['cnr']] = {'evidence_version': version, 'snapshot': snapshot}
    return result


def state(db):
    current = contexts(db)
    counts, stale_counts = defaultdict(Counter), Counter()
    reviews = {}
    summary = {'reviewed': 0, 'misuse': 0, 'no_misuse': 0, 'legacy_pending': 0, 'needs_recheck': 0}
    for row in db.execute('SELECT * FROM case_reviews'):
        payload = json.loads(row['payload'])
        stale = payload['evidence_version'] != current[row['cnr']]['evidence_version']
        active = payload.get('decision') in DECISIONS
        eligible = active and not stale
        public = {k: payload.get(k) for k in ('decision', 'law_profile_ids', 'note', 'evidence_version', 'reviewed_at')}
        if payload.get('decision') and not active:
            # Preserve old records verbatim in storage; never turn unknown into no.
            public['legacy_decision'] = payload['decision']
            public['decision'] = None
            summary['legacy_pending'] += 1
        public.update(revision=row['revision'], needs_recheck=stale and active,
                      score_eligible=eligible, status='needs_recheck' if stale and active else
                      'reviewed' if active else 'unreviewed', updated_at=row['updated_at'],
                      label=DECISIONS.get(payload.get('decision'), 'Not reviewed'),
                      training_label_status='Human assessment; requires adjudication before gold use')
        reviews[row['cnr']] = public
        if active:
            if stale:
                summary['needs_recheck'] += 1
                stale_counts.update(payload['law_profile_ids'])
            else:
                summary['reviewed'] += 1
                summary[payload['decision']] += 1
            if eligible:
                for identifier in payload['law_profile_ids']:
                    counts[identifier][payload['decision']] += 1
    profiles = []
    for profile in catalog()['profiles']:
        votes = counts[profile['id']]
        yes, no = votes['misuse'], votes['no_misuse']
        adjusted = (PRIOR_STRENGTH * profile['raw_total'] + profile['raw_max'] * yes) / (PRIOR_STRENGTH + yes + no)
        profiles.append(profile | {
            'original_score': profile['raw_total'], 'adjusted_score': round(adjusted, 4),
            'adjusted_display': f'{adjusted:.1f}/12' if yes + no else f'{profile["raw_total"]}/12',
            'yes_reviews': yes, 'no_reviews': no, 'review_count': yes + no,
            'needs_recheck_count': stale_counts[profile['id']], 'feedback_method': METHOD['version'],
        })
    summary['unreviewed'] = len(current) - summary['reviewed'] - summary['needs_recheck']
    return {'reviews': reviews, 'profiles': profiles, 'summary': summary,
            'contexts': current, 'method': METHOD}


def empty_review():
    return {'decision': None, 'law_profile_ids': [], 'note': '', 'revision': 0,
            'status': 'unreviewed', 'needs_recheck': False, 'score_eligible': False,
            'label': 'Not reviewed'}


def overlay_links(links, feedback):
    lookup = {p['id']: p for p in feedback['profiles']}
    result = []
    for law in links:
        profiles = [lookup[p['id']] for p in law['profiles']]
        scores = [p['adjusted_score'] for p in profiles]
        active = any(p['review_count'] for p in profiles)
        low, high = (min(scores), max(scores)) if scores else (None, None)
        display = 'Not scored' if low is None else (
            (f'{low:g}' if low == high else f'{low:g}–{high:g}') + '/12' if not active else
            (f'{low:.1f}' if low == high else f'{low:.1f}–{high:.1f}') + '/12')
        result.append(law | {'feedback_profiles': profiles,
                            'feedback_score_range': [low, high] if scores else None,
                            'feedback_score_display': display,
                            'has_feedback': active})
    return result


def eligible_profiles(db, cnr):
    """Offer only scored scopes associated with this case; never fill unknowns."""
    from .law_links import get_links
    from .priority import case_laws
    row = db.execute('SELECT sections,metadata FROM cases WHERE cnr=?', (cnr,)).fetchone()
    links = case_laws(json.loads(row['sections']), json.loads(row['metadata']))
    for doc in db.execute('SELECT id FROM documents WHERE cnr=?', (cnr,)):
        links.extend(get_links(db, doc['id']))
    return list({p['id']: p for law in links for p in law['profiles']}.values())


def write_review(store, cnr, data, *, clear=False):
    """Atomic revision check + replacement: edits never add a second vote."""
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        current = contexts(db).get(cnr)
        if current is None:
            raise ReviewError(404, 'Case not found')
        old = db.execute('SELECT * FROM case_reviews WHERE cnr=?', (cnr,)).fetchone()
        revision = old['revision'] if old else 0
        if data['expected_revision'] != revision:
            raise ReviewError(409, 'This review was changed in another window. Reload the case before saving.')
        if not clear and data['evidence_version'] != current['evidence_version']:
            raise ReviewError(409, 'Case evidence changed. Reload and check the current documents before saving.')
        decision = None if clear else data['decision']
        if not clear and decision not in DECISIONS:
            raise ReviewError(422, 'Assessment must be yes or no.')
        identifiers = sorted(set(data.get('law_profile_ids', []))) if not clear else []
        note = data.get('note', '').strip() if not clear else ''
        if not clear:
            ready = [d for d in current['snapshot']['documents'] if d['status'] == 'ready']
            if not ready:
                raise ReviewError(422, 'Read an available court document before recording a yes/no assessment.')
            candidates = {p['id'] for p in eligible_profiles(db, cnr)}
            if set(identifiers) - candidates:
                raise ReviewError(422, 'Selected law profile is not associated with this case or its scored scope.')
            if decision in ('misuse', 'no_misuse') and candidates and not identifiers:
                raise ReviewError(422, 'Select the law or subsection you verified in the documents.')
        payload = {
            'decision': decision, 'law_profile_ids': identifiers, 'note': note,
            'evidence_version': current['evidence_version'], 'snapshot': current['snapshot'],
            'reviewed_at': now(), 'reviewer_scope': 'Local team assessment; no individual identity verification',
            'method_version': METHOD['version'],
        }
        if old:
            previous = json.loads(old['payload'])
            fields = ('decision', 'law_profile_ids', 'note', 'evidence_version')
            if all(previous.get(k) == payload[k] for k in fields):
                return state(db)
        stamp = now()
        db.execute('INSERT INTO case_reviews VALUES(?,?,?,?) ON CONFLICT(cnr) DO UPDATE SET '
                   'revision=excluded.revision,payload=excluded.payload,updated_at=excluded.updated_at',
                   (cnr, revision + 1, encode(payload), stamp))
        db.execute('INSERT INTO case_review_events(cnr,revision,action,payload,created_at) VALUES(?,?,?,?,?)',
                   (cnr, revision + 1, 'clear' if clear else 'save', encode(payload), stamp))
        return state(db)


def export_labels(db):
    """Current, evidence-versioned judgments for subsequent adjudication/training."""
    feedback = state(db)
    items = []
    for row in db.execute('SELECT * FROM case_reviews ORDER BY cnr'):
        public = feedback['reviews'][row['cnr']]
        if not public['score_eligible']:
            continue
        payload = json.loads(row['payload'])
        items.append({'cnr': row['cnr'], 'revision': row['revision'], **payload,
                      'suggested_split_group': row['cnr'],
                      'label_status': 'Unadjudicated human assessment, not gold',
                      'family_group_verified': False})
    return {'items': items, 'total': len(items), 'exported_at': now(), 'method': METHOD,
            'training_note': 'Group related proceedings and orders before splitting. Keep reviews and law '
                             'feedback out of predictive inputs; no model is retrained by this API.'}
