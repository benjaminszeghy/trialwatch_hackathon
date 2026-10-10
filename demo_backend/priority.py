"""Transparent review bands derived from associated law profiles, not case risk."""
from collections import Counter

from .law_links import build_links, catalog

BANDS = {
    'high': 'High priority',
    'elevated': 'Elevated priority',
    'standard': 'Standard priority',
    'uncertain': 'Priority to confirm',
    'unscored': 'Unscored',
}
METHOD = {
    'version': 'law-review-bands-v2',
    'bands': {'high': {'min': 9, 'max': 12}, 'elevated': {'min': 6, 'max_exclusive': 9},
              'standard': {'min': 0, 'max_exclusive': 6}},
    'basis': 'Highest associated law score, with current team-feedback overlay when available; not a case misuse finding.',
    'uncertainty': 'A score range crossing a band boundary is Priority to confirm. Unknown scores are not zero.',
    'sorting': 'High, to confirm, elevated, standard, unscored; then score lower bound and latest order.',
    'validation': 'Provisional interface thresholds, not expert-validated or learned from outcomes.',
}


def band(score):
    return 'high' if score >= 9 else 'elevated' if score >= 6 else 'standard'


def review_priority(links):
    ranges = [law.get('feedback_score_range', law.get('raw_score_range')) for law in links
              if law.get('feedback_score_range', law.get('raw_score_range'))]
    adjusted = any(law.get('has_feedback') for law in links)
    low = max(r[0] for r in ranges) if ranges else None
    high = max(r[1] for r in ranges) if ranges else None
    key = 'unscored' if not ranges else band(low) if band(low) == band(high) else 'uncertain'
    return {
        'band': key, 'label': BANDS[key], 'score_range': [low, high] if ranges else None,
        'score_display': ('Not scored' if low is None else
                          ((f'{low:.1f}' if low == high else f'{low:.1f}–{high:.1f}') if adjusted else
                           (f'{low:g}' if low == high else f'{low:g}–{high:g}')) + '/12'),
        'score_source': 'feedback_adjusted' if adjusted else 'original_rubric',
        'has_unscored_scope': any(not l.get('profiles') or l.get('unscored_subsections') for l in links),
        'basis': METHOD['basis'], 'method_version': METHOD['version'],
        'is_case_misuse_score': False, 'human_verified': False,
    }


def case_laws(sections, metadata):
    return build_links(sections, metadata, [], None, pdf_sha256=None, source_catalog=catalog())


def summarize(items):
    counts = Counter(i['review_priority']['band'] for i in items)
    return {'total': len(items), 'priority_counts': {key: counts[key] for key in BANDS}}


def order_cases(items, sort):
    items.sort(key=lambda i: i['cnr'])
    items.sort(key=lambda i: i['latest_order_date'] or '', reverse=True)
    if sort == 'priority':
        ranks = {key: index for index, key in enumerate(['high', 'uncertain', 'elevated', 'standard', 'unscored'])}
        items.sort(key=lambda i: (ranks[i['review_priority']['band']],
                                 -(i['review_priority']['score_range'] or [0])[0]))
    return items
