from data_access import *
from pypdf import PdfReader
import subprocess

URLS={
 'ipc':'https://www.indiacode.nic.in/bitstream/123456789/4219/1/THE-INDIAN-PENAL-CODE-1860.pdf',
 'bns':'https://www.indiacode.nic.in/indiacode/bitstream/123456789/20062/1/a202345.pdf',
 'uapa':'https://www.mha.gov.in/sites/default/files/A1967-37_0.pdf',
 'it':'https://www.indiacode.nic.in/bitstream/123456789/13116/1/it_act_2000_updated.pdf',
 'osa':'https://www.mha.gov.in/sites/default/files/2022-10/OSA1923_02092022%5B1%5D.pdf',
 'crpc':'https://www.indiacode.nic.in/bitstream/123456789/15272/1/the_code_of_criminal_procedure,_1973.pdf',
 'bnss':'https://www.mha.gov.in/sites/default/files/2024-04/250884_2_english_01042024.pdf',
}
for name,url in URLS.items():
    dest=CACHE/f'statutes/{name}.pdf';dest.parent.mkdir(parents=True,exist_ok=True)
    if name=='ipc' and (CACHE/'ipc-official.pdf').exists(): dest.write_bytes((CACHE/'ipc-official.pdf').read_bytes())
    if not dest.exists():
        try: subprocess.run(['curl','-fLsS','--max-time','20',url,'-o',str(dest)],check=True)
        except subprocess.CalledProcessError as exc:
            print(name,'download failed',str(exc),flush=True);continue
    p=fetch(url,f'statutes/{name}.pdf',20_000_000)
    pages=[{'page':i+1,'text':pg.extract_text() or ''} for i,pg in enumerate(PdfReader(p).pages)]
    (CACHE/f'statutes/{name}.json').write_text(json.dumps(pages,indent=2))
    (CACHE/f'statutes/{name}.txt').write_text('\n\n'.join(f'PAGE {x["page"]}\n{x["text"]}' for x in pages))
    print(name,'pages',len(pages),'bytes',p.stat().st_size,flush=True)
