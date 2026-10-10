"""Evidence-aware TrialWatch relevance, separate from law concern and labels."""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .core import encode, now
from .feedback import ReviewError, contexts

TIERS = {'urgent': 'Tier 1 · Urgent', 'high': 'Tier 2 · High', 'routine': 'Tier 3 · Routine',
         'verify': 'Needs verification', 'closed': 'Tier 4 · Closed review',
         'outside_scope': 'Outside journalist pilot'}
WEIGHTS = {'counsel': 25, 'interpretation': 15, 'defence_access': 15, 'urgency': 25, 'opening': 20}
METHOD = {
    'version': 'trialwatch-relevance-v1', 'weights': WEIGHTS, 'scale': '0–100 review index',
    'thresholds': {'urgent': '75–100', 'high': '45 to below 75', 'routine': '0 to below 45'},
    'unknowns': 'Unknown facts contribute a range, never a confirmed zero. Crossing tiers needs verification.',
    'eligibility': 'Verify journalist/reporting connection and court stage; not all BNS candidates involve journalists.',
    'urgent_override': 'Immediate safety threat, deadline within 7 days, or custody with unavailable counsel.',
    'sorting': 'Urgent needs first; then law-concern band and TrialWatch relevance. Closed/out-of-pilot reviews last.',
    'closure': 'Reviewer decision with a reason; low scores, disposal and a no-misuse label never close a review.',
    'validation': 'Provisional team rubric, not official TrialWatch policy or probability of successful intervention.',
    'sources': ['https://cfj.org/trialwatch/', 'https://cfj.org/monitor/'],
}
OPENINGS = {'monitoring': 'Trial monitoring', 'legal_support': 'Legal-support review',
            'interpretation': 'Interpretation follow-up', 'advocacy': 'Evidence / advocacy review'}
DEFAULTS = {'journalist_nexus': 'unknown', 'case_stage': 'unknown', 'counsel': 'unknown',
            'interpretation': 'unknown', 'defence_access': 'unknown', 'custody': 'unknown',
            'immediate_threat': 'unknown', 'deadline_status': 'unknown', 'next_deadline': None,
            'opening_status': 'unknown', 'openings': [], 'workflow_status': 'active',
            'evidence_note': '', 'close_reason': ''}


def today():
    return datetime.now(ZoneInfo('Asia/Kolkata')).date()


class RelevanceInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    journalist_nexus: Literal['confirmed', 'absent', 'unknown'] = 'unknown'
    case_stage: Literal['ongoing', 'reopened', 'appeal', 'completed', 'unknown'] = 'unknown'
    counsel: Literal['unavailable', 'limited', 'available', 'unknown'] = 'unknown'
    interpretation: Literal['unavailable', 'limited', 'available', 'not_required', 'unknown'] = 'unknown'
    defence_access: Literal['restricted', 'adequate', 'unknown'] = 'unknown'
    custody: Literal['yes', 'no', 'unknown'] = 'unknown'
    immediate_threat: Literal['yes', 'no', 'unknown'] = 'unknown'
    deadline_status: Literal['scheduled', 'none', 'unknown'] = 'unknown'
    next_deadline: date | None = None
    opening_status: Literal['ready', 'to_arrange', 'none', 'unknown'] = 'unknown'
    openings: list[Literal['monitoring', 'legal_support', 'interpretation', 'advocacy']] = Field(default_factory=list, max_length=4)
    workflow_status: Literal['active', 'closed'] = 'active'
    evidence_note: str = Field('', max_length=2000)
    close_reason: str = Field('', max_length=1000)
    expected_revision: int = Field(0, ge=0)
    evidence_version: str = Field(pattern=r'^[a-f0-9]{64}$')

    @model_validator(mode='after')
    def consistent(self):
        if (self.deadline_status == 'scheduled') != (self.next_deadline is not None):
            raise ValueError('Set a date only for a scheduled hearing or filing deadline.')
        if self.next_deadline and self.next_deadline < today():
            raise ValueError('Update the next deadline: the supplied date is already past in India.')
        if self.opening_status in ('ready', 'to_arrange') and not self.openings:
            raise ValueError('Select an intervention opening for a ready or to-arrange opportunity.')
        if self.opening_status in ('none', 'unknown') and self.openings:
            raise ValueError('Select ready or to arrange before listing an intervention opening.')
        facts = self.model_dump(mode='json')
        checked = any(facts[k] != v for k, v in DEFAULTS.items() if k not in ('evidence_note', 'close_reason', 'openings'))
        if checked and len(self.evidence_note.strip()) < 10:
            raise ValueError('Add a source note supporting your confirmed entries (at least 10 characters).')
        if self.workflow_status == 'closed':
            if len(self.close_reason.strip()) < 10:
                raise ValueError('Explain why the TrialWatch review is being closed (at least 10 characters).')
            if urgency(facts, today())[2]:
                raise ValueError('Resolve the active urgent flags before closing this review.')
        return self


def initialize(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS case_relevance (
            cnr TEXT PRIMARY KEY REFERENCES cases(cnr), revision INTEGER NOT NULL,
            payload TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS case_relevance_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, cnr TEXT REFERENCES cases(cnr),
            revision INTEGER NOT NULL, action TEXT NOT NULL, payload TEXT NOT NULL,
            created_at TEXT NOT NULL, UNIQUE(cnr,revision));
    ''')


def urgency(facts, as_of):
    low, potential, overrides, reasons = 0, [], [], []
    if facts['immediate_threat'] == 'yes':
        low = 25
        overrides.append('Documented immediate safety threat')
    elif facts['immediate_threat'] == 'unknown':
        potential.append(25)
    if facts['custody'] == 'yes':
        low = max(low, 20)
        reasons.append('Currently in custody')
        if facts['counsel'] == 'unavailable':
            overrides.append('In custody with unavailable / denied counsel')
    elif facts['custody'] == 'unknown':
        potential.append(20)
    if facts['deadline_status'] == 'scheduled':
        days = (date.fromisoformat(str(facts['next_deadline'])) - as_of).days
        if 0 <= days <= 7:
            low = 25
            overrides.append(f'Hearing / filing deadline in {days} day(s)')
        elif 7 < days <= 30:
            low = max(low, 15)
            reasons.append(f'Hearing / filing deadline in {days} days')
        elif days > 30:
            low = max(low, 5)
        else:
            potential.append(25)
    elif facts['deadline_status'] == 'unknown':
        potential.append(25)
    return low, max([low, *potential]), overrides, reasons


def assess(facts=None, *, as_of=None, stale=False, saved=False):
    as_of = as_of or today()
    facts = DEFAULTS | (facts or {})
    expired = facts['workflow_status'] != 'closed' and facts['deadline_status'] == 'scheduled' and \
        date.fromisoformat(str(facts['next_deadline'])) < as_of
    needs_recheck = stale or expired
    factors = []
    reasons = []
    def factor(key, label, values):
        value = values.get(facts[key])
        lo, hi = (0, WEIGHTS[key]) if value is None else (value, value)
        factors.append({'key': key, 'label': label, 'max': WEIGHTS[key], 'range': [lo, hi],
                        'assessed': value is not None, 'status': facts[key]})
        if value:
            reasons.append(label)
    factor('counsel', 'Counsel access gap', {'unavailable': 25, 'limited': 12.5, 'available': 0})
    factor('interpretation', 'Interpretation access gap', {'unavailable': 15, 'limited': 7.5, 'available': 0, 'not_required': 0})
    factor('defence_access', 'Defence / evidence access restriction', {'restricted': 15, 'adequate': 0})
    lo, hi, overrides, timing = urgency(facts, as_of)
    closed_became_urgent = facts['workflow_status'] == 'closed' and bool(overrides)
    needs_recheck = needs_recheck or closed_became_urgent
    factors.append({'key': 'urgency', 'label': 'Time sensitivity', 'max': 25, 'range': [lo, hi],
                    'assessed': lo == hi, 'status': 'urgent' if overrides else 'checked' if lo == hi else 'partial'})
    reasons.extend(timing)
    opening = {'ready': 20, 'to_arrange': 10, 'none': 0}.get(facts['opening_status'])
    factors.append({'key': 'opening', 'label': 'Practical intervention opening', 'max': 20,
                    'range': [0, 20] if opening is None else [opening, opening],
                    'assessed': opening is not None, 'status': facts['opening_status']})
    if opening:
        reasons.append('Opening: ' + ', '.join(OPENINGS[key] for key in facts['openings']))
    lower, upper = [sum(f['range'][side] for f in factors) for side in (0, 1)]
    coverage = sum(f['max'] for f in factors if f['assessed'])
    if needs_recheck:
        lower, upper, coverage = 0, 100, 0
        reasons.insert(0, 'Deadline passed: update current status' if expired else
                       'Closed review: a recorded urgent flag now requires recheck' if closed_became_urgent else
                       'Evidence changed: reassess current needs')
        for f in factors:
            f.update(range=[0, f['max']], assessed=False, status='needs_recheck')
    fit_checked = facts['journalist_nexus'] == 'confirmed' and facts['case_stage'] != 'unknown'
    def tier(score):
        return 'urgent' if score >= 75 else 'high' if score >= 45 else 'routine'
    if facts['workflow_status'] == 'closed' and not needs_recheck:
        key = 'closed'
    elif facts['journalist_nexus'] == 'absent' and not needs_recheck:
        key = 'outside_scope'
    elif overrides:
        key = 'urgent'
    elif not fit_checked or needs_recheck or tier(lower) != tier(upper):
        key = 'verify'
    else:
        key = tier(lower)
    if not fit_checked and key not in ('closed', 'outside_scope'):
        reasons.insert(0, 'Verify journalist / reporting connection and court stage')
    label = 'Urgent recheck' if key == 'urgent' and needs_recheck else \
            'Urgent verification' if key == 'urgent' and not fit_checked else TIERS[key]
    actions = {'urgent': 'Immediate review of the documented need', 'high': 'Priority investigation of support needs and intervention route',
               'routine': 'Routine monitoring and evidence collection', 'verify': 'Verify case fit, support needs and current dates',
               'closed': 'Review archived; reconsider if new evidence arrives',
               'outside_scope': 'Consider referral; this journalist pilot does not establish fit'}
    return {'tier': key, 'label': label, 'score_range': [lower, upper] if saved and not needs_recheck else None,
            'score': lower if saved and not needs_recheck and lower == upper else None,
            'score_display': 'Not assessed' if not saved else 'Recheck needed' if needs_recheck else
                             (f'{lower:g}' if lower == upper else f'{lower:g}–{upper:g}') + '/100',
            'coverage_percent': coverage, 'factors': factors, 'reasons': [*overrides, *reasons],
            'urgent_override': bool(overrides) and key == 'urgent', 'eligibility_verified': fit_checked,
            'needs_recheck': needs_recheck, 'reopened_for_review': needs_recheck and facts['workflow_status'] == 'closed',
            'action': actions[key], 'as_of': str(as_of), 'date_timezone': 'Asia/Kolkata',
            'method_version': METHOD['version'], 'is_probability': False}


def state(db, evidence_contexts=None):
    evidence_contexts = evidence_contexts or contexts(db)
    records = {r['cnr']: r for r in db.execute('SELECT * FROM case_relevance')}
    items = {}
    for cnr, context in evidence_contexts.items():
        row = records.get(cnr)
        payload = json.loads(row['payload']) if row else {}
        facts = DEFAULTS | payload.get('facts', {})
        result = assess(facts, stale=bool(row) and payload['evidence_version'] != context['evidence_version'], saved=bool(row))
        items[cnr] = result | {'revision': row['revision'] if row else 0,
                              'updated_at': row['updated_at'] if row else None, 'facts': facts,
                              'has_assessment': bool(row)}
    counts = Counter(r['tier'] for r in items.values())
    return {'items': items, 'summary': {k: counts[k] for k in TIERS}, 'method': METHOD}


def save(store, cnr, data):
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        context = contexts(db).get(cnr)
        if context is None:
            raise ReviewError(404, 'Case not found')
        old = db.execute('SELECT * FROM case_relevance WHERE cnr=?', (cnr,)).fetchone()
        revision = old['revision'] if old else 0
        if data.expected_revision != revision:
            raise ReviewError(409, 'Relevance assessment changed in another window. Reload this case.')
        if data.evidence_version != context['evidence_version']:
            raise ReviewError(409, 'Case evidence changed. Reload before assessing current needs.')
        facts = {k: v for k, v in data.model_dump(mode='json').items() if k in DEFAULTS}
        for key in ('evidence_note', 'close_reason'):
            facts[key] = facts[key].strip()
        facts['openings'] = sorted(set(facts['openings']))
        previous = json.loads(old['payload']) if old else None
        if previous and previous['facts'] == facts and previous['evidence_version'] == context['evidence_version']:
            return
        payload = {'facts': facts, **context, 'assessed_at': now(), 'method_version': METHOD['version'],
                   'reviewer_scope': 'Local team assessment; individual identity not verified'}
        stamp = now()
        db.execute('INSERT INTO case_relevance VALUES(?,?,?,?) ON CONFLICT(cnr) DO UPDATE SET '
                   'revision=excluded.revision,payload=excluded.payload,updated_at=excluded.updated_at',
                   (cnr, revision + 1, encode(payload), stamp))
        db.execute('INSERT INTO case_relevance_events(cnr,revision,action,payload,created_at) VALUES(?,?,?,?,?)',
                   (cnr, revision + 1, 'close' if facts['workflow_status'] == 'closed' else 'save', encode(payload), stamp))


def order(items, sort):
    from .priority import order_cases
    order_cases(items, 'priority')
    if sort not in ('triage', 'trialwatch'):
        return order_cases(items, sort)
    ranks = {'urgent': 0, 'high': 1, 'verify': 2, 'routine': 3, 'closed': 4, 'outside_scope': 5}
    law_ranks = {k: i for i, k in enumerate(['high', 'uncertain', 'elevated', 'standard', 'unscored'])}
    def key(item):
        r = item['trialwatch_relevance']
        end = 2 if r['tier'] in ('closed', 'outside_scope') else 0 if r['tier'] == 'urgent' else 1
        score = -(r['score_range'] or [0])[0]
        law = law_ranks[item['review_priority']['band']]
        return (end, ranks[r['tier']], score, law) if sort == 'trialwatch' else \
               (end, law if end == 1 else 0, ranks[r['tier']], score)
    items.sort(key=key)
    return items


def passages(store, cnr):
    patterns = {'Counsel': r'\b(?:counsel|advocates?|lawyer|unrepresented|legal aid)\b',
                'Interpretation': r'\b(?:interpreter|translator|interpretation|translation|language)\b',
                'Custody / dates': r'\b(?:custody|detained|hearing|listed on|next date)\b',
                'Defence access': r'\b(?:cross.exam|access to|disclos|documents supplied)'}
    result, seen = [], set()
    with store.db() as db:
        docs = db.execute("SELECT * FROM documents WHERE cnr=? AND status='ready' ORDER BY order_date DESC,id", (cnr,)).fetchall()
    for doc in docs:
        if not doc['text_path']:
            continue
        for page in json.loads((store.root / doc['text_path']).read_text()):
            text = page.get('text', '')
            for label, pattern in patterns.items():
                if label in seen:
                    continue
                match = re.search(pattern, text, re.I)
                if match:
                    seen.add(label)
                    result.append({'topic': label, 'document_id': doc['id'], 'page': page['page'],
                                   'quote': text[max(0, match.start() - 100):match.end() + 260].strip(),
                                   'pdf_sha256': doc['sha256'], 'order_date': doc['order_date'],
                                   'pdf_url': f'/api/documents/{doc["id"]}/pdf?sha256={doc["sha256"]}',
                                   'human_verified': False})
                    if len(seen) == len(patterns):
                        return result
    return result
