from data_access import *
from pypdf import PdfReader
docs=json.loads((CACHE/'sc_documents.json').read_text())
for r in docs:
    key=r['key'].replace('.pdf','_EN.pdf') if not r['key'].endswith('_EN.pdf') else r['key']
    r['key']=key;r['source_url']=base('indian-supreme-court-judgments')+urllib.parse.quote(key,safe='/=')
    try:
        p=s3get('indian-supreme-court-judgments',key,25_000_000)
        pages=[{'page':i+1,'text':pg.extract_text() or ''} for i,pg in enumerate(PdfReader(p).pages)]
        out=p.with_suffix('.pages.json');out.write_text(json.dumps(pages))
        p.with_suffix('.txt').write_text('\n\n'.join(f'PAGE {x["page"]}\n{x["text"]}' for x in pages))
        r['pages_json']=str(out.relative_to(ROOT));r['page_count']=len(pages);r['retrieval_status']='success';r.pop('error',None)
    except Exception as exc: r['retrieval_status']='failed';r['error']=str(exc)
    print(r['case_id'],r['retrieval_status'],r.get('page_count'),flush=True)
(CACHE/'sc_documents.json').write_text(json.dumps(docs,indent=2))
