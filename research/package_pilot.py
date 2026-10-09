"""Package an allowlisted public-data snapshot and code, excluding large intermediates."""
import json
import zipfile
from pathlib import Path
from data_access import ROOT, CACHE

paths={p for p in (ROOT/'research').iterdir() if p.suffix in {'.py','.md','.txt'}}
for name in ['law-scores.md','law-scores.json','court-evidence.json','corpus-summary.json','source-manifest.json','claude-score-review.png']:
    paths.add(ROOT/'outputs'/name)
manifest=json.loads((ROOT/'outputs/source-manifest.json').read_text())
for row in manifest.values():
    if row.get('path'):paths.add(ROOT/row['path'])
for name in ['manifest.json','catalog.json','corpus_inventory.json','hc_sampling_frame.json','hc_documents.json','sc_documents.json','sc_candidates.json']:
    paths.add(CACHE/name)
for file in ['hc_documents.json','sc_documents.json']:
    for doc in json.loads((CACHE/file).read_text()):paths.add(ROOT/doc['pages_json'])
for name in ['ipc','bns','uapa','osa','crpc','bnss']:
    paths.add(CACHE/f'statutes/{name}.json')
for name in ['imran-2025','vombatkere-2022']:
    paths.add(CACHE/f'supplemental/{name}.pages.json')
dest=ROOT/'outputs/trialwatch-pilot.zip'
with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for path in sorted(paths):
        if not path.is_file():raise FileNotFoundError(path)
        z.write(path,path.relative_to(ROOT))
print('Packaged',len(paths),'files;',round(dest.stat().st_size/1e6,1),'MB;',dest)
