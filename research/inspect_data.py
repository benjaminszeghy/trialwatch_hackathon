from data_access import *
import sys
sys.path.insert(0, str(ROOT/'work'/'deps'))
import duckdb

HC='indian-high-court-judgments'; SC='indian-supreme-court-judgments'
catalog={
 'hc_bombay_details': objects(HC,'metadata/parquet_case_details/court=27_1/'),
 'hc_hp_details': objects(HC,'metadata/parquet_case_details/court=2_5/'),
 'hc_bombay_2025': objects(HC,'metadata/parquet/year=2025/court=27_1/'),
 'sc_metadata': objects(SC,'metadata/parquet/'),
}
(CACHE/'catalog.json').write_text(json.dumps(catalog,indent=2))
print('Catalog counts', {k:len(v) for k,v in catalog.items()})
for label in ['hc_hp_details','hc_bombay_2025','sc_metadata']:
    candidates=[x for x in catalog[label] if x.get('key','').endswith('.parquet')]
    choice= min(candidates,key=lambda x:x['size']) if label!='sc_metadata' else next(x for x in candidates if 'year=2021/' in x['key'])
    p=s3get(SC if label=='sc_metadata' else HC,choice['key'])
    c=duckdb.connect()
    cur=c.execute('SELECT * FROM read_parquet(?) LIMIT 2',[str(p)])
    names=[x[0] for x in cur.description]
    rows=cur.fetchall()
    print(label,'FILE',choice,'COLUMNS',names,'ROWS',c.execute('SELECT count(*) FROM read_parquet(?)',[str(p)]).fetchone()[0])
    for row in rows:
        print(json.dumps(dict(zip(names,[str(v)[:1600] for v in row])),ensure_ascii=False))

p=s3get(HC, next(x['key'] for x in catalog['hc_bombay_details'] if 'bench=newas/' in x['key']))
c=duckdb.connect()
cur=c.execute("SELECT * FROM read_parquet(?) WHERE acts IS NOT NULL LIMIT 3",[str(p)])
names=[x[0] for x in cur.description]
for row in cur.fetchall():
    print('BOMBAY DETAIL',json.dumps(dict(zip(names,[str(v)[:2500] for v in row])),ensure_ascii=False))
