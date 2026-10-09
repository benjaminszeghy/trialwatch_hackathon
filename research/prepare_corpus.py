from data_access import *
import sys, re
sys.path.insert(0,str(ROOT/'work'/'deps'))
import duckdb
from law_identity import metadata_hits
from concurrent.futures import ThreadPoolExecutor

HC='indian-high-court-judgments'; SC='indian-supreme-court-judgments'
CAT=json.loads((CACHE/'catalog.json').read_text())
YEARS=[1957,1962,1997,2007,2015,2016,2020,2021,2022,2024,2025,2026]
BENCHES=['newas','hcaurdb','hcbgoa','kolhcdb']
tasks=[(SC,x['key']) for x in CAT['sc_metadata'] if any(f'year={y}/' in x['key'] for y in YEARS)]
tasks += [(HC,x['key']) for x in CAT['hc_bombay_details'] if any(f'bench={b}/' in x['key'] for b in BENCHES)]
with ThreadPoolExecutor(max_workers=3) as pool:
    paths=list(pool.map(lambda t:s3get(*t),tasks))
print('downloaded metadata files',len(paths),flush=True)
c=duckdb.connect()
sc=[str(p) for p in paths if SC in str(p)]
hc=[str(p) for p in paths if HC in str(p)]
c.execute('CREATE TABLE sc AS SELECT * FROM read_parquet(?, union_by_name=true)',[sc])
c.execute('CREATE TABLE hc AS SELECT * FROM read_parquet(?, union_by_name=true)',[hc])
cur=c.execute('SELECT * FROM hc')
names=[x[0] for x in cur.description]
rows=[dict(zip(names,r)) for r in cur.fetchall()]
(CACHE/'hc_case_details.json').write_text(json.dumps(rows,default=str,ensure_ascii=False))
sc_count=c.execute('SELECT count(*) FROM sc').fetchone()[0]
(CACHE/'corpus_inventory.json').write_text(json.dumps({
    'hc_case_detail_rows':len(rows),'hc_unique_cnr':len({r['cnr'] for r in rows}),
    'sc_metadata_rows_inspected':sc_count,'sc_metadata_years':YEARS,'hc_benches':BENCHES,
    'court':'Bombay High Court, S3 court=27_1',
    'source_metadata_files':[str(p.relative_to(ROOT)) for p in paths],
    'note':'Counts from the cached metadata snapshot, not population denominators.'},indent=2)+'\n')
print('HC rows',len(rows),'SC rows',sc_count,flush=True)
keywords=['MANZAR','BILAL AHMED','SHREYA','RAMJI LAL','SUBRAMANIAN SWAMY','THWAHA','AMISH','PATRICIA','VOMBATKERE','KEDAR NATH','JAVED HAJAM','IMRAN PRATAPGARHI','ARNAB']
cur=c.execute('SELECT title,path,year,decision_date,case_id FROM sc')
names=[x[0] for x in cur.description]
matches=[dict(zip(names,r)) for r in cur.fetchall() if any(k in str(r[0]).upper() for k in keywords)]
(CACHE/'sc_candidates.json').write_text(json.dumps(matches,default=str,indent=2))
print('SC selected titles',json.dumps(matches,default=str),flush=True)
targets={'IPC':['124A','153A','295A','505','499','500','186'], 'BNS':['152','196','299','353','356','221'], 'UAPA':['13'],'IT':['66A','67'],'OSA':['3','5']}
counts={}
selected=[]
for r in rows:
    hits=metadata_hits(r.get('acts'))
    if hits:
        r['law_hits']=sorted(set(hits)); selected.append(r)
        for law in set(hits): counts[law]=counts.get(law,0)+1
(CACHE/'hc_eligible_cases.json').write_text(json.dumps(selected,default=str,ensure_ascii=False,indent=2))
print('HC law hits',counts,flush=True)
for r in selected[:3]: print('HC SAMPLE',json.dumps(r,default=str,ensure_ascii=False)[:5000],flush=True)
