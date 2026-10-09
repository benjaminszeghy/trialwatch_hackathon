"""Transparent arithmetic and assumption sensitivity; no outcome-trained model."""
import math
import random

def score(values, weights=None):
    if not values: raise ValueError('At least one criterion is required')
    if any(v is None for v in values): return None
    if any(v not in (0,1,2) for v in values): raise ValueError('Ratings must be 0, 1, 2 or unknown')
    weights = weights if weights is not None else [1.0]*len(values)
    if len(weights)!=len(values) or any(not math.isfinite(w) or w<0 for w in weights) or sum(weights)<=0:
        raise ValueError('Weights must be finite, nonnegative, and have positive total')
    return 100*sum(v*w for v,w in zip(values,weights))/(2*sum(weights))

def tied_rank_bands(scores):
    """Best/worst positions occupied by a tie, using a small numerical tolerance."""
    return [(1+sum(x>s+1e-9 for x in scores), sum(x>=s-1e-9 for x in scores)) for s in scores]

def sensitivity(profiles, runs=10000, seed=20261009):
    rng=random.Random(seed)
    n=len(profiles); m=len(profiles[0])
    simulated=[[] for _ in profiles]; ranks=[[] for _ in profiles]
    for _ in range(runs):
        weights=[rng.uniform(0.5,1.5) for _ in range(m)]
        values=[score(p,weights) for p in profiles]
        bands=tied_rank_bands(values)
        for i,(v,b) in enumerate(zip(values,bands)):
            simulated[i].append(v); ranks[i].append(b)
    out=[]
    for i,p in enumerate(profiles):
        vals=sorted(simulated[i]); lo=int((runs-1)*.05); hi=int((runs-1)*.95)
        leave=[]
        for j in range(m):
            w=[1.0]*m;w[j]=0
            values=[score(q,w) for q in profiles]
            leave.append({'omitted_index':j,'score_100':round(values[i],1),
                          'rank_band':tied_rank_bands(values)[i]})
        out.append({'weight_score_p05_p95':[round(vals[lo],1),round(vals[hi],1)],
            'weight_rank_envelope':[min(b[0] for b in ranks[i]),max(b[1] for b in ranks[i])],
            'leave_one_criterion_out':leave})
    return out

def correlations(profiles):
    """Descriptive Pearson correlations of coding columns, not independent evidence."""
    columns=list(zip(*profiles));out=[]
    for a in columns:
        row=[]
        for b in columns:
            am=sum(a)/len(a);bm=sum(b)/len(b)
            numerator=sum((x-am)*(y-bm) for x,y in zip(a,b))
            denom=math.sqrt(sum((x-am)**2 for x in a)*sum((y-bm)**2 for y in b))
            row.append(round(numerator/denom,3) if denom else None)
        out.append(row)
    return out
