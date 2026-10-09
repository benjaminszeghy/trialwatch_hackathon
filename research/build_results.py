"""Build a reproducible provisional law-score report from the downloaded pilot.

No network call, classifier training, or inference of abuse prevalence occurs here.
Unsupported evidence spans fail the build rather than silently losing citations.
"""
import copy
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from data_access import ROOT, CACHE, MANIFEST
from evidence_review import reviews, norm
from law_catalog import LAWS, INVALID, CRITERIA, SOURCES
from scoring import score, sensitivity, correlations, tied_rank_bands

OUT=ROOT/'outputs'
OUT.mkdir(exist_ok=True)

def read(name): return json.loads((CACHE/name).read_text())
def write(name,obj): (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def values(row): return [row['components'][c['id']]['rating'] for c in CRITERIA]

def main():
    frame=read('hc_sampling_frame.json');hc=read('hc_documents.json');sc=read('sc_documents.json')
    assert len(frame)==len({r['cnr'] for r in frame}), 'Duplicate CNR in frame'
    assert len(hc)==len({r['cnr'] for r in hc}), 'Duplicate selected order for a CNR'
    assert all(d['retrieval_status']=='success' for d in hc+sc), 'Incomplete court download'
    evidence,matrices=reviews()
    reviews_by_cnr={}
    for item in evidence:
        if item.get('cnr'): reviews_by_cnr.setdefault(item['cnr'],[]).append(item)

    inventory=read('corpus_inventory.json')

    docs=[]
    for d in hc:
        pages=json.loads((ROOT/d['pages_json']).read_text())
        terms=[]
        for page in pages:
            # These are retrieval candidates. Party submissions and precedent quotations
            # can contain the same words as operative reasoning, so no labels are assigned.
            for term in ['quash','bail','ingredient','mens rea']:
                match=re.search(re.escape(term),page['text'],re.I)
                if match and sum(x['term']==term for x in terms)<2:
                    terms.append({'term':term,'pdf_page':page['page'],
                        'context':norm(page['text'][max(0,match.start()-160):match.start()+300]),
                        'status':'unreviewed retrieval candidate; not an outcome/element finding'})
        rev=reviews_by_cnr.get(d['cnr'],[])
        docs.append({k:d[k] for k in ['cnr','title','law_hits','decision_date','source_url','pages_json','page_count']}|
            {'review_ids':[x['id'] for x in rev],
             'verified_specific_charge_laws':sorted({law for x in rev for law in x.get('verified_charge_laws',[])}),
             'excluded_metadata_hits':sorted({law for x in rev for law in x.get('excluded_metadata_hits',[])}),
             'case_family_key':next((x['case_family_key'] for x in rev if x.get('case_family_key')),None),
             'lexical_candidates':terms,
             'unreviewed_fields':{'journalism_nexus':None,'fir_quashed':None,'charge_conduct_distance':None}})

    laws=copy.deepcopy(LAWS)+[copy.deepcopy(INVALID)]
    for row in laws:
        parents=set(row['metadata_parent_hits'])
        matching=[r for r in frame if parents.intersection(r['law_hits'])]
        selected=[d for d in docs if parents.intersection(d['law_hits'])]
        row['historical_panel']={
            'metadata_cnr_count':len(matching),'selected_pdf_count':len(selected),
            'one_page_selected_orders':sum(d['page_count']==1 for d in selected),
            'metadata_scope':sorted(parents),
            'verified_specific_charge_examples_cnr':[d['cnr'] for d in docs if row['id'] in d['verified_specific_charge_laws']],
            'known_metadata_conflicts_cnr':[d['cnr'] for d in selected if parents.intersection(d['excluded_metadata_hits'])],
            'rate_of_abuse':None,'quashing_rate':None,
            'note':'Metadata counts are retrieval denominators. Subsection rows share the parent denominator. Zero reviewed confirmations is not an absence finding.'}
        row['evidence_review_ids']=[e['id'] for e in evidence if row['id'] in e['laws']]
        if row['era']=='Invalid':continue
        row['raw_total']=sum(values(row));row['raw_max']=12
        row['score_100']=round(score(values(row)))
        for scenario in row.get('alternative_scenarios',[]):
            profile=[scenario['component_overrides'].get(c['id'],row['components'][c['id']]['rating']) for c in CRITERIA]
            scenario['raw_total']=sum(profile);scenario['score_100']=round(score(profile));scenario['profile']=profile
        for source in row['sources']:
            local=SOURCES[source['source']].get('local')
            if local:
                pages=read(local)
                assert all(1<=p<=len(pages) for p in source['pdf_pages']), 'Invalid statutory page reference'

    for era in ['IPC','BNS','Other']:
        group=[r for r in laws if r['era']==era]
        sim=sensitivity([values(r) for r in group]);ranks=tied_rank_bands([score(values(r)) for r in group])
        for row,result,rank in zip(group,sim,ranks):
            row['baseline_rank_band_within_era']=rank;row['sensitivity']=result

    profiles=[values(r) for r in laws if r['era']!='Invalid']
    n_pages=sum(d['page_count'] for d in hc)
    summary={**inventory,'observation_order_years':[2024,2025],
        'metadata_matched_cnr_frame':len(frame),'selected_hc_pdfs':len(hc),'selected_hc_pdf_pages':n_pages,
        'selected_sc_aws_pdfs':len(sc),'supplemental_official_sc_pdfs':2,
        'reviewed_hc_cnr':len(reviews_by_cnr),'curated_review_items':len(evidence),
        'one_page_hc_orders':sum(d['page_count']==1 for d in hc),
        'selection':'Lowest SHA-256(CNR) within each parent-law metadata stratum, up to four CNRs; union; latest final order in 2024-25 if available, otherwise latest order.',
        'unit':'CNR proceeding; not an independent FIR/case family, journalist, or charge.',
        'law_assignment':'Named Act in metadata; never inferred from order year. Operative PDF text can expose conflicts. Only the small reviewed subset is corrected/confirmed.',
        'gold_dataset_status':'No independent expert gold labels and no measured generalization performance.',
        'sc_selection':'Purposive doctrinal benchmarks from inspected-year metadata; not a random Supreme Court outcome sample.'}
    result={'title':'TrialWatch Legal Tripwire: India — provisional law review indices',
        'as_of':'2026-10-09','rubric_version':'0.1','summary':summary,
        'score_definition':'Statute-as-written plus linked central procedural classification. Six analyst-proposed 0-2 ratings; equal-weight sum/12*100, rounded. Higher means more review flags under THIS rubric.',
        'validation_status':'Provisional AI-assisted analyst coding; not independently legally validated; not an abuse probability or learned risk model.',
        'weight_sensitivity':{'runs':10000,'seed':20261009,'distribution':'Independent Uniform(0.5,1.5) criterion weights, normalized in the score formula.',
            'interpretation':'5th-95th percentile assumption band, not a statistical confidence interval. Rank envelopes include ties and are within era only.'},
        'criteria':CRITERIA,'sources':SOURCES,'laws':laws,
        'criterion_correlations':{'criterion_order':[c['id'] for c in CRITERIA],
            'matrix':correlations(profiles),
            'interpretation':'Descriptive correlation across the 18 coded profiles, including related IPC/BNS rows; not independent cases or a causal estimate.'},
        'claude_review':{'scope':'Two conceptual/implementation audits through the existing authorized Claude chat; not independent expert legal coding.',
            'final_result':'Arithmetic checked; requested explicit OSA 3 penalty branch and visible historical 124A status, both implemented.',
            'screenshot':'claude-score-review.png'}}
    write('law-scores.json',result)
    write('court-evidence.json',{'reviews':evidence,'element_matrices':matrices,'hc_document_index':docs,
        'sc_aws_document_index':sc,'schema_note':'Unreviewed/unknown fields remain null. Boilerplate allegation, missing record, court finding and specific alleged facts must remain distinct.'})
    write('corpus-summary.json',summary)
    raw_manifest=read('manifest.json')
    selected_urls={d['source_url'] for d in hc+sc}
    selected_urls.update(q['url'] for e in evidence for q in e['evidence'])
    selected_urls.update(s['url'] for r in laws for s in r['sources'])
    selected_urls.add(SOURCES['commencement']['url'])
    provenance={u:v for u,v in raw_manifest.items() if u in selected_urls or '/metadata/' in u}
    for u in selected_urls:
        if u not in provenance:provenance[u]={'accessed_date':'2026-10-09','access_method':'web tool; no cached-byte hash available'}
    write('source-manifest.json',provenance)
    (OUT/'law-scores.md').write_text(report(result,evidence,matrices))
    print(json.dumps({'law_rows':len(laws),'scored_rows':len(LAWS),'hc_selected':len(hc),'hc_pages':n_pages,
                      'verified_review_items':len(evidence),'output':str(OUT/'law-scores.md')},indent=2))

def report(result,evidence,matrices):
    s=result['summary'];lines=[
        '# TrialWatch Legal Tripwire: India — laws and scores',
        '', 'First build · 9 October 2026 · rubric 0.1', '',
        '**These are provisional statute-as-written review indices.** They use AI-assisted analyst coding, have not been independently legally validated, and are not probabilities that a law or prosecution is abusive. Higher scores mean more flags under the explicit rubric below.', '',
        'Historical IPC and current BNS provisions are separate. Continuing special acts form a third panel. Judicial interpretations and observed court evidence are displayed separately from the numerical index.', '',
        'The selected BNS provisions commenced on 1 July 2024 under the [official commencement notification](https://www.mha.gov.in/sites/default/files/BhartiyaNyayaSanhita_24022024.pdf). The linked IPC baseline is historical and subject to savings; this is not a claim that all later amendments, state variations or decisions have been exhaustively audited.', '',
        '## Score tables', '',
        'The six numbers in the profile are: expression reach · evaluative language · explicit mental-state gap · expression-safeguard gap · arrest/bail exposure · imprisonment severity. Each runs from 0 to 2. Raw totals are out of 12; the 0–100 display is a rounded rescaling, not additional precision.', '',
    ]
    for era,label in [('IPC','Historical IPC — repealed code, subject to savings'),('BNS','Current BNS baseline — selected provisions commenced 1 July 2024'),('Other','Continuing special statutes — selected central text')]:
        lines += ['### '+label,'','| Provision | Raw /12 | Score /100 | Six-component profile | Weight band* | Parent metadata CNRs† | PDFs selected† |','|---|---:|---:|---|---|---:|---:|']
        for row in result['laws']:
            if row['era']!=era:continue
            h=row['historical_panel'];band=row['sensitivity']['weight_score_p05_p95']
            lines.append(f"| {row['name']} | {row['raw_total']} | **{row['score_100']}** | {' / '.join(str(x) for x in values(row))} | {band[0]}–{band[1]} | {h['metadata_cnr_count']} | {h['selected_pdf_count']} |")
        lines += ['']
    inv=next(r for r in result['laws'] if r['era']=='Invalid')
    lines += ['**Alternative scenarios:** OSA 3 other-case publication branch (three-year maximum) is **9/12 → 75/100**; IT 67 subsequent conviction (five-year maximum, different bail classification) is **9/12 → 75/100**. These are declared branch changes, not additional independent laws.', '',
        f"**IT Act 66A: no score.** Struck down in its entirety in *Shreya Singhal* (2015). There are {inv['historical_panel']['metadata_cnr_count']} parent-metadata matches and {inv['historical_panel']['selected_pdf_count']} selected PDFs. These are verification leads; a metadata listing does not prove a fresh/illegal charge.", '',
        '\\* Weight bands are the 5th–95th percentiles when each weight varies from 0.5 to 1.5. They measure assumption sensitivity, not uncertainty about real-world abuse.', '',
        '† Counts refer to overlapping **CNR proceedings**, not independent cases. 505(1)/505(2) and 353(1)/353(2) share unresolved parent metadata counts; do not add these rows. IPC 499/500 uses a union, not a sum. The metadata contains verified Act errors, so these counts do not enter the score.', '',
        '## What the requested datasets actually contributed', '',
        f"The [High Court dataset](https://registry.opendata.aws/indian-high-court-judgments/) supplied {s['hc_case_detail_rows']:,} case-detail rows from four Bombay High Court bench partitions. Joining selected offence metadata to 2024–2025 order records produced a {s['metadata_matched_cnr_frame']}-CNR retrieval frame. The deterministic law-stratified union selected **{s['selected_hc_pdfs']} PDFs / {s['selected_hc_pdf_pages']} pages**, including {s['one_page_hc_orders']} one-page orders. All selected PDFs were downloaded and text-extracted.", '',
        f"The [Supreme Court dataset](https://registry.opendata.aws/indian-supreme-court-judgments/) supplied metadata from 12 selected years ({s['sc_metadata_rows_inspected']:,} rows inspected) and **{s['selected_sc_aws_pdfs']} purposively selected judgments** for doctrine. Two clearly labeled official SCI supplements cover the 2022 sedition order and current BNS interpretation. Statutory and procedural components require the linked official Act/schedule text; court outcome frequency is not a substitute for that text.", '',
        f"The evidence layer contains **{s['curated_review_items']} curated review items**, including {s['reviewed_hc_cnr']} reviewed High Court proceedings. The rest have lexical retrieval candidates, not reviewed findings. The two element matrices are demonstrations, not independently annotated gold data.", '',
        'Selection: SHA-256 of CNR within each parent-law metadata stratum, up to four per stratum, then union across strata. For each CNR, use the latest final order available within the fixed window, otherwise the latest order. This selects final/interim document type, not a desired outcome. Named Act controls the preliminary IPC/BNS identity; order date never supplies the code. FIR/offence date and operative text still require verification.', '',
        '## Important findings from the PDF review', '',
    ]
    for e in evidence:
        links=', '.join(f"[PDF p.{q['pdf_page']}]({q['url']}#page={q['pdf_page']})" for q in e['evidence'])
        lines += [f"- **{e['id']}**: {e['summary']} {links}"]
    lines += ['',
        'The two Farah Deeba CNRs link to the same identified Kalepadal FIR 178/2025. This is a concrete reason to avoid treating unique CNRs as independent prosecutions. FIR-family linkage remains incomplete for the rest of the sample.', '',
        '## Rubric and arithmetic', '',
        '`raw total = sum of six ratings; display score = round(100 × raw total / 12)`', '',
        'The ratings and equal weights are declared analyst assumptions, not fitted from quashing, bail, conviction or volume. Missing criteria would yield no point score. Invalidated 66A is excluded. The selected publication/communication limbs and penalty scenarios are stated in each law note.', '',
        '| Criterion | 0 | 1 | 2 |','|---|---|---|---|',
    ]
    for c in CRITERIA:lines.append('| '+c['label']+' | '+' | '.join(c['anchors'])+' |')
    lines += ['',
        'The mental-state component measures words present in the statutory clause. It does **not** assert strict liability. In particular, the high bare-text score for IPC 153A/BNS 196 must be read alongside the Court’s intent/context requirements. Judicial safeguards are not converted to invented numeric deductions in this build. General constitutional protections, complaint gates, sanction requirements, fines, charge bundling and enforcement conduct are not fully represented by six numbers.', '',
        'Arrest classification is not a prediction that arrest will occur; non-bailable does not mean bail is impossible. CrPC/BNSS central schedules and special-act overrides are used. State amendments and later legal-version changes need a separate audit before operational use.', '',
        '### Weight and rank sensitivity', '',
        '10,000 seeded runs use independent Uniform(0.5,1.5) criterion weights, normalized by their sum. Each criterion is also omitted in turn. Rank bands are within each panel and retain ties. The Monte Carlo bands do not cover coding disagreements or source-version errors.', '',
        '| Provision | Baseline rank range (ties) | Rank envelope over weight runs | Leave-one-out score min–max |','|---|---|---|---|',
    ]
    for row in result['laws']:
        if row['era']=='Invalid':continue
        vals=[r['score_100'] for r in row['sensitivity']['leave_one_criterion_out']]
        rank=row['baseline_rank_band_within_era'];ran=row['sensitivity']['weight_rank_envelope']
        lines.append(f"| {row['name']} | {rank[0]}–{rank[1]} | {ran[0]}–{ran[1]} | {min(vals)}–{max(vals)} |")
    corr=result['criterion_correlations']['matrix']
    lines += ['',f"Descriptive component correlations in this 18-row catalog: expression reach/evaluative language **r={corr[0][1]}**; custody/imprisonment **r={corr[4][5]}**. Related IPC/BNS profiles are not independent observations. These correlations flag potential double counting, not evidence that either criterion causes abuse. The full matrix and every omitted-criterion result are in `law-scores.json`.", '',
        '## Per-law coding and sources', '',
    ]
    for row in result['laws']:
        if row['era']=='Invalid':continue
        lines += ['### '+row['name'],'',f"**{row['raw_total']}/12 → {row['score_100']}/100.** {row['notes']}",'']
        for c in CRITERIA:
            v=row['components'][c['id']]
            lines.append(f"- **{c['label']}: {v['rating']}** — {v['reason']}")
        lines += ['', 'Official text: '+ '; '.join(f"[{r['source'].upper()} {r['provisions']}, PDF pp. {', '.join(map(str,r['pdf_pages']))}]({r['url']})" for r in row['sources'])+'.','']
    lines += ['## Element-matrix examples and remaining validation', '',
        'Each cell separates specific recorded facts, merely formulaic allegation (only when the allegation record is sufficiently complete), explicit judicial absence, and an unavailable/unassessed record. Evidence source type is separate. No numerical Charge–Conduct Distance is emitted before the element definitions and coding are reviewed.', '',
        '| Example | Element | State |','|---|---|---|',
    ]
    for m in matrices:
        for e in m['elements']:lines.append(f"| {m['id']} | {e['element']} | {e['state']} |")
    lines += ['',
        'Completed: data access, Act-bound section normalization, deterministic sampling, PDF extraction, verified-span evidence storage, editable scoring, weight/rank sensitivity and code tests. **No classifier was trained, no expert agreement statistic or model accuracy was measured, and no expert pairwise ordering was obtained.** Those results must not be fabricated from this small curated layer.', '',
        'Next validation: have legal teammates independently code the profiles and the 2–3-law element pilot, preserve disagreements, test relevance/field extraction on held-out case families, and compare ordering against independent expert pairs. Include source and time holdouts once labels exist. The current corpus is a selected High Court sample and cannot estimate population abuse prevalence, journalist targeting probability, or IPC-to-BNS causal changes.', '',
        'Claude reviewed the design and final proposed profiles in the existing authorized chat. Its final audit checked arithmetic and requested an explicit OSA 3 penalty-branch label and a visible historical 124A flag; both are incorporated. Claude expressly did not re-read the statutes in that final audit, so this is not independent expert legal validation. The implementation separately checked the linked text and schedules. See `claude-score-review.png`.', '',
        '## Deliverables', '',
        '- `law-scores.json`: all profiles, arithmetic, denominators, sources and sensitivity.',
        '- `court-evidence.json`: verified review spans, two element examples, 55-document HC index and nine AWS SC documents.',
        '- `corpus-summary.json`: scope, units and selection.',
        '- `source-manifest.json`: source URLs and cached-file SHA-256 hashes where available.',
        '- `trialwatch-pilot.zip`: code, offline text snapshot and reports; public PDF source links remain in the manifest.',
        '',
        'Dataset attribution: Indian High Court Judgments and Indian Supreme Court Judgments datasets, maintained by Dattam Labs and contributors, distributed through the AWS Registry of Open Data; see their registry pages and repositories for the stated CC BY 4.0 license. Government statutes and supplemental Supreme Court documents are separately attributed by direct source URL. All legal judgments in this report are provisional research interpretations.', '',
    ]
    return '\n'.join(lines)

if __name__=='__main__':main()
