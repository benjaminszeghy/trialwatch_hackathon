from data_access import *
import sys, re, hashlib
sys.path.insert(0,str(ROOT/'work'/'deps'))
import duckdb
from pypdf import PdfReader
from concurrent.futures import ThreadPoolExecutor

HC='indian-high-court-judgments'; SC='indian-supreme-court-judgments'
BENCHES=['newas','hcaurdb','hcbgoa','kolhcdb']
cases=json.loads((CACHE/'hc_eligible_cases.json').read_text())
order_objs=[]
for year in [2024,2025]:
    order_objs += [x for x in objects(HC,f'metadata/parquet/year={year}/court=27_1/')
                   if x['key'].endswith('metadata-mobile.parquet') and any(f'bench={b}/' in x['key'] for b in BENCHES)]
with ThreadPoolExecutor(max_workers=3) as pool:
    paths=list(pool.map(lambda x:s3get(HC,x['key']),order_objs))
c=duckdb.connect()
cur=c.execute('SELECT * FROM read_parquet(?,union_by_name=true)',[[str(p) for p in paths]])
names=[x[0] for x in cur.description]; orders=[dict(zip(names,r)) for r in cur.fetchall()]
bycnr={}
for r in orders:
    bycnr.setdefault(r['cnr'],[]).append(r)
frame=[r for r in cases if r['cnr'] in bycnr and r.get('judicial_section')=='Criminal']
laws=sorted({law for r in frame for law in r['law_hits']})
sample={}
for law in laws:
    matching=sorted([r for r in frame if law in r['law_hits']],key=lambda r:hashlib.sha256(r['cnr'].encode()).hexdigest())
    for r in matching[:4]: sample[r['cnr']]=r
(CACHE/'hc_sampling_frame.json').write_text(json.dumps(frame,ensure_ascii=False,default=str,indent=2))
print('HC frame',len(frame),'law counts',{law:sum(law in r['law_hits'] for r in frame) for law in laws},'sample',len(sample),flush=True)

def extract(p):
    pages=[{'page':i+1,'text':page.extract_text() or ''} for i,page in enumerate(PdfReader(p).pages)]
    out=p.with_suffix('.pages.json'); out.write_text(json.dumps(pages,ensure_ascii=False))
    p.with_suffix('.txt').write_text('\n\n'.join(f'PAGE {r["page"]}\n{r["text"]}' for r in pages))
    return str(out.relative_to(ROOT)),len(pages)

selected=[]
for r in sample.values():
    # Prefer the latest order in the fixed 2024-2025 observation window.
    options=sorted(bycnr[r['cnr']],key=lambda o:str(o['decision_date']),reverse=True)
    o=next((o for o in options if o.get('is_final')),options[0])
    key=f'data/pdf/year={o["year"]}/court=27_1/bench={o["bench"]}/{o["pdf_link"]}'
    item={'court_level':'HC','cnr':r['cnr'],'title':f'{r["petitioner"]} v {r["respondent"]}',
          'law_hits':r['law_hits'],'decision_date':str(o['decision_date']), 'key':key,
          'source_url':base(HC)+urllib.parse.quote(key,safe='/='),'case_type':r['case_type'],
          'case_metadata':r,'order_metadata':o}
    try:
        p=s3get(HC,key,20_000_000); item['pages_json'],item['page_count']=extract(p)
        item['retrieval_status']='success'
    except Exception as exc: item['retrieval_status']='failed';item['error']=str(exc)
    selected.append(item)
    print('HC',r['cnr'],r['law_hits'],item['retrieval_status'],flush=True)
(CACHE/'hc_documents.json').write_text(json.dumps(selected,ensure_ascii=False,default=str,indent=2))

candidates=json.loads((CACHE/'sc_candidates.json').read_text())
ids=['1957 INSC 32','1962 INSC 17','2007 INSC 378','2015 INSC 257','2016 INSC 427','2020 INSC 400','2020 INSC 682','2021 INSC 213','2021 INSC 688']
scdocs=[]
for r in candidates:
    if r['case_id'] not in ids: continue
    key=f'data/pdf/year={r["year"]}/english/{r["path"]}_EN.pdf'
    item={**r,'court_level':'SC','key':key,'source_url':base(SC)+urllib.parse.quote(key,safe='/=')}
    try:
        p=s3get(SC,key,25_000_000);item['pages_json'],item['page_count']=extract(p);item['retrieval_status']='success'
    except Exception as exc: item['retrieval_status']='failed';item['error']=str(exc)
    scdocs.append(item)
    print('SC',r['case_id'],item['retrieval_status'],flush=True)
(CACHE/'sc_documents.json').write_text(json.dumps(scdocs,default=str,indent=2))
