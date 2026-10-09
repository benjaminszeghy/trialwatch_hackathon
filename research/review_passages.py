from data_access import *
import re
docs=json.loads((CACHE/'sc_documents.json').read_text())
queries={'2007 INSC 378':r'mens rea|intention.*essential', '2021 INSC 213':r'intention|ingredient|quash',
 '1957 INSC 32':r'deliberate and malicious|aggravated', '1962 INSC 17':r'violence|public disorder',
 '2015 INSC 257':r'vague|struck down', '2016 INSC 427':r'Exceptions|public good',
 '2021 INSC 688':r'Chapter III|Chapter IV|Section 13|43D', '2020 INSC 682':r'intent|mens rea'}
out=[]
for r in docs:
    pages=json.loads((ROOT/r['pages_json']).read_text())
    pattern=queries.get(r['case_id'])
    if not pattern: continue
    passages=[]
    for page in pages:
        text=' '.join(page['text'].split())
        m=re.search(pattern,text,re.I)
        if m: passages.append({'page':page['page'],'quote':text[max(0,m.start()-120):m.end()+550]})
    out.append({'case_id':r['case_id'],'title':r['title'],'source_url':r['source_url'],'passages':passages[:8]})
(CACHE/'sc_review_passages.json').write_text(json.dumps(out,indent=2))
for r in out:
    print(r['case_id'],r['title'])
    for p in r['passages'][:3]: print('PAGE',p['page'],p['quote'])
for name,secs in {'uapa':['2','13','14','43D'],'osa':['3','5'],'bns':['221','299','356']}.items():
    pages=json.loads((CACHE/f'statutes/{name}.json').read_text())
    for sec in secs:
        print('STATUTE',name,sec)
        for p in pages:
            if p['page']<4:continue
            m=re.search(r'(?m)^\s*'+sec+r'\.',p['text'])
            if m: print('PAGE',p['page'], ' '.join(p['text'][m.start():m.start()+2100].split()))
