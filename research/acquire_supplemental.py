"""Two labeled official SCI supplements; not substituted for the AWS corpus."""
import json
from pypdf import PdfReader
from data_access import fetch

for name,url in [
    ('vombatkere-2022','https://api.sci.gov.in/supremecourt/2021/14059/14059_2021_1_301_35891_Order_11-May-2022.pdf'),
    ('imran-2025','https://api.sci.gov.in/supremecourt/2025/3511/3511_2025_4_1501_60508_Judgement_28-Mar-2025.pdf'),
]:
    p=fetch(url,f'supplemental/{name}.pdf',20_000_000)
    pages=[{'page':i+1,'text':q.extract_text() or ''} for i,q in enumerate(PdfReader(p).pages)]
    p.with_suffix('.pages.json').write_text(json.dumps(pages,ensure_ascii=False))
    print(name,len(pages),'pages')
