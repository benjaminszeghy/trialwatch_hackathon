"""Public, unsigned S3 retrieval with a local cache and provenance manifest."""
from pathlib import Path
import hashlib, json, time, urllib.parse, urllib.request, threading
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'work' / 'court-data'
CACHE.mkdir(parents=True, exist_ok=True)
MANIFEST = CACHE / 'manifest.json'
NS = {'s': 'http://s3.amazonaws.com/doc/2006-03-01/'}
LOCK=threading.Lock()

def fetch(url, name=None, limit=150_000_000):
    dest = CACHE / (name or hashlib.sha256(url.encode()).hexdigest())
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        last = None
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'TrialWatch-research-pilot/0.1'})
                with urllib.request.urlopen(req, timeout=25) as response:
                    if int(response.headers.get('Content-Length', 0)) > limit:
                        raise ValueError('Object exceeds declared download limit')
                    data = response.read(limit + 1)
                    if len(data) > limit:
                        raise ValueError('Object exceeds download limit')
                    dest.write_bytes(data)
                break
            except Exception as exc:
                last = exc
                if attempt == 2: raise
                time.sleep(1 + attempt)
    with LOCK:
        records = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
        records[url] = {'path': str(dest.relative_to(ROOT)), 'bytes': dest.stat().st_size,
                        'sha256': hashlib.sha256(dest.read_bytes()).hexdigest(),
                        'accessed_date': '2026-10-09'}
        MANIFEST.write_text(json.dumps(records, indent=2))
    return dest

def base(bucket):
    return f'https://{bucket}.s3.ap-south-1.amazonaws.com/'

def objects(bucket, prefix, delimiter=None, max_pages=10):
    query = {'list-type': '2', 'prefix': prefix, 'max-keys': '1000'}
    if delimiter: query['delimiter'] = delimiter
    out = []
    for page in range(max_pages):
        url = base(bucket) + '?' + urllib.parse.urlencode(query)
        path = fetch(url, f'lists/{bucket}-{hashlib.sha256(url.encode()).hexdigest()[:16]}.xml')
        root = ET.fromstring(path.read_bytes())
        for el in root.findall('s:Contents', NS):
            out.append({'key': el.findtext('s:Key', namespaces=NS),
                        'size': int(el.findtext('s:Size', namespaces=NS)),
                        'last_modified': el.findtext('s:LastModified', namespaces=NS)})
        for el in root.findall('s:CommonPrefixes', NS):
            out.append({'prefix': el.findtext('s:Prefix', namespaces=NS)})
        token = root.findtext('s:NextContinuationToken', namespaces=NS)
        if not token: return out
        query['continuation-token'] = token
    raise RuntimeError(f'Pagination exceeded {max_pages} pages for {prefix}')

def s3get(bucket, key, limit=150_000_000):
    return fetch(base(bucket) + urllib.parse.quote(key, safe='/='), f'{bucket}/{key}', limit)

if __name__ == '__main__':
    import sys
    print(json.dumps(objects(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv)>3 else None), indent=2))
