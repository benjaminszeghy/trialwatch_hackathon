"""One queue index built from two distinct, auditable inputs."""
from collections import Counter

BANDS = {'urgent':'Immediate review', 'high':'Focus first', 'review':'Review',
         'monitor':'Monitor', 'verify':'Check evidence', 'closed':'Closed review',
         'outside_scope':'Referral'}
METHOD = {'version':'combined-review-v1', 'weights':{'law_concern':0.5,'trialwatch_fit':0.5},
          'formula':'0.5 × highest associated law index /12 ×100 + 0.5 × case fit index',
          'bands':{'high':'60–100','review':'40 to below 60','monitor':'Below 40'},
          'overrides':'Verified urgent needs come first. A current fit No caps non-urgent priority at 39; no automatic closure.',
          'uncertainty':'Missing scores contribute a range; ranges crossing a band require an evidence check.',
          'validation':'Provisional demo review index, not misuse probability, established legal abuse or official intake policy.'}


def band(score):
    return 'high' if score >= 60 else 'review' if score >= 40 else 'monitor'


def assess(law, relevance):
    raw_law=law.get('score_range')
    law_range=[v/12*100 for v in raw_law] if raw_law else [0,100]
    if law.get('has_unscored_scope'):
        law_range[1]=100
    fit_range=relevance.get('score_range') or [0,100]
    score=[round((law_range[i]+fit_range[i])/2,1) for i in (0,1)]
    fit_review=relevance.get('fit_review',{})
    rejected=fit_review.get('score_eligible') and fit_review.get('decision')=='no'
    if relevance.get('urgent_override'):
        key='urgent'
    elif relevance['tier'] in ('closed','outside_scope'):
        key=relevance['tier']
    elif rejected:
        score=[min(v,39) for v in score];key='monitor'
    elif relevance.get('needs_recheck') or raw_law is None or band(score[0])!=band(score[1]):
        key='verify'
    else:
        key=band(score[0])
    number=score[0] if score[0]==score[1] else None
    display=(f'{score[0]:g}' if number is not None else f'{score[0]:g}–{score[1]:g}')+'/100'
    return {'band':key,'label':BANDS[key], 'score':number,'score_range':score,'score_display':display,
            'law_score_range':raw_law,'law_score_display':law['score_display'] if not law.get('has_unscored_scope') else 'Scope partly unscored',
            'law_normalized_range':[round(v,1) for v in law_range],
            'fit_score_range':relevance.get('score_range'),'fit_score_display':relevance['score_display'],
            'fit_rejected':bool(rejected),'urgent_override':bool(relevance.get('urgent_override')),
            'method_version':METHOD['version'],'is_probability':False,'method':METHOD}


def summarize(items):
    counts=Counter(c['case_priority']['band'] for c in items)
    return {'total':len(items),'counts':{k:counts[k] for k in BANDS},
            'reviewed':sum(c['case_review'].get('score_eligible',False) or c['trialwatch_relevance'].get('fit_review',{}).get('score_eligible',False) for c in items)}


def order(items):
    items.sort(key=lambda c:c['cnr'])
    items.sort(key=lambda c:c.get('latest_order_date') or '',reverse=True)
    ranks={'urgent':0,'high':1,'review':2,'verify':3,'monitor':4,'outside_scope':5,'closed':6}
    items.sort(key=lambda c:(0 if c['case_priority']['urgent_override'] else 2 if c['case_priority']['fit_rejected'] or c['case_priority']['band'] in ('closed','outside_scope') else 1,
                             ranks[c['case_priority']['band']],-c['case_priority']['score_range'][0]))
    return items
