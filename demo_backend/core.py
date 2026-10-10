from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import subprocess
import tempfile
import urllib.parse
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://indian-high-court-judgments.s3.ap-south-1.amazonaws.com/'
NS = {'s': 'http://s3.amazonaws.com/doc/2006-03-01/'}


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def encode(value):
    return json.dumps(value, ensure_ascii=False, default=str)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


@dataclass
class Config:
    state_dir: Path = field(default_factory=lambda: ROOT / 'work/live-demo')
    court: str = '27_1'
    court_name: str = 'Bombay High Court'
    benches: list[str] = field(default_factory=lambda: ['newas', 'hcaurdb', 'hcbgoa', 'kolhcdb'])
    sections: list[str] = field(default_factory=lambda: ['152', '196', '299', '353', '356', '221'])
    start_date: str = '2024-07-01'
    end_date: str | None = None  # Dynamic today, so next year's partition is discovered.
    interval_seconds: int = 3600
    max_pdfs_per_run: int = 12
    pdf_recheck_days: int = 7
    cors_origins: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.state_dir = Path(self.state_dir).expanduser().resolve()
        for value in [self.court, *self.benches]:
            if not re.fullmatch(r'[a-zA-Z0-9_]+', value):
                raise ValueError('Invalid court or bench identifier')
        if not self.benches or not self.sections or any(not re.fullmatch(r'\d+', s) for s in self.sections):
            raise ValueError('Nonempty benches and numeric BNS sections required')
        if date.fromisoformat(self.start_date) > self.end:
            raise ValueError('Invalid date window')
        if self.interval_seconds < 30 or not 1 <= self.max_pdfs_per_run <= 100 or self.pdf_recheck_days < 1:
            raise ValueError('Interval must be >=30 seconds; PDF budget must be 1–100')

    @property
    def end(self):
        return date.fromisoformat(self.end_date) if self.end_date else date.today()

    @classmethod
    def load(cls, path=None, state_dir=None):
        values = json.loads(Path(path).read_text()) if path else {}
        if state_dir:
            values['state_dir'] = state_dir
        return cls(**values)

    def scope(self):
        return {'court': self.court_name, 'court_code': self.court, 'benches': self.benches,
                'act': 'BNS', 'sections': self.sections, 'order_date_from': self.start_date,
                'order_date_to': self.end.isoformat(), 'pdf_budget_per_run': self.max_pdfs_per_run}


class Store:
    def __init__(self, directory):
        self.root = Path(directory)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / 'collector.sqlite3'
        with self.db() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS cases (
                    cnr TEXT PRIMARY KEY, title TEXT, court TEXT, bench TEXT,
                    sections TEXT, metadata TEXT, first_seen TEXT, last_seen TEXT);
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY, cnr TEXT NOT NULL REFERENCES cases(cnr),
                    logical_key TEXT UNIQUE, order_date TEXT, source_url TEXT UNIQUE,
                    metadata TEXT, status TEXT DEFAULT 'pending', sha256 TEXT,
                    pdf_path TEXT, text_path TEXT, page_count INTEGER, error TEXT,
                    first_seen TEXT, last_seen TEXT, downloaded_at TEXT);
                CREATE INDEX IF NOT EXISTS documents_cnr ON documents(cnr);
                CREATE TABLE IF NOT EXISTS document_versions (
                    document_id TEXT, sha256 TEXT, pdf_path TEXT, text_path TEXT,
                    saved_at TEXT, PRIMARY KEY(document_id,sha256));
                CREATE TABLE IF NOT EXISTS annotations (
                    document_id TEXT, reviewer TEXT, payload TEXT, updated_at TEXT,
                    PRIMARY KEY(document_id,reviewer));
                CREATE TABLE IF NOT EXISTS seed_reviews (
                    document_id TEXT PRIMARY KEY, payload TEXT);
                CREATE TABLE IF NOT EXISTS source_objects (
                    key TEXT PRIMARY KEY, etag TEXT, modified TEXT, size INTEGER,
                    path TEXT, sha256 TEXT, checked_at TEXT);
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT,
                    finished_at TEXT, status TEXT, scope TEXT, stats TEXT, error TEXT);
            ''')

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def case(self, cnr, title, court, bench, sections, metadata):
        with self.db() as db:
            new = db.execute('SELECT 1 FROM cases WHERE cnr=?', (cnr,)).fetchone() is None
            db.execute('''INSERT INTO cases VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(cnr) DO UPDATE SET title=excluded.title,court=excluded.court,
                bench=excluded.bench,sections=excluded.sections,metadata=excluded.metadata,
                last_seen=excluded.last_seen''',
                (cnr, title, court, bench, encode(sorted(set(sections))), encode(metadata), now(), now()))
        return new

    def document(self, cnr, logical_key, order_date, url, metadata):
        identifier = digest(url.encode())[:20]
        with self.db() as db:
            # Preserve original snapshot identifiers when mobile/web representations change.
            old = db.execute('SELECT id FROM documents WHERE logical_key=? OR source_url=?',
                             (logical_key, url)).fetchone()
            if old:
                db.execute('UPDATE documents SET last_seen=?,metadata=? WHERE id=?',
                           (now(), encode(metadata), old['id']))
                return old['id'], False
            db.execute('''INSERT INTO documents(id,cnr,logical_key,order_date,source_url,metadata,
                       first_seen,last_seen) VALUES(?,?,?,?,?,?,?,?)''',
                       (identifier, cnr, logical_key, order_date, url, encode(metadata), now(), now()))
            return identifier, True

    def row(self, identifier):
        with self.db() as db:
            r = db.execute('SELECT * FROM documents WHERE id=?', (identifier,)).fetchone()
            return dict(r) if r else None

    def save_pdf(self, identifier, raw, pages):
        sha = digest(raw)
        folder = self.root / 'documents' / identifier
        folder.mkdir(parents=True, exist_ok=True)
        pdf, text = folder / (sha + '.pdf'), folder / (sha + '.json')
        atomic(pdf, raw)
        atomic(text, encode(pages).encode())
        relative_pdf, relative_text = str(pdf.relative_to(self.root)), str(text.relative_to(self.root))
        with self.db() as db:
            db.execute('INSERT OR IGNORE INTO document_versions VALUES(?,?,?,?,?)',
                       (identifier, sha, relative_pdf, relative_text, now()))
            db.execute('''UPDATE documents SET status='ready',sha256=?,pdf_path=?,text_path=?,
                       page_count=?,error=NULL,downloaded_at=? WHERE id=?''',
                       (sha, relative_pdf, relative_text, len(pages), now(), identifier))
        return sha

    def seed(self, corpus=ROOT / 'outputs/bns-training-starter', raw_metadata=ROOT / 'work/bns-corpus/documents.json'):
        corpus = Path(corpus)
        originals = {r['document_id']: r for r in json.loads(Path(raw_metadata).read_text())}
        cases = {r['cnr']: r for r in json.loads((corpus / 'case-candidates.json').read_text())}
        for case in cases.values():
            with self.db() as db:
                exists = db.execute('SELECT 1 FROM cases WHERE cnr=?', (case['cnr'],)).fetchone()
            if exists:
                continue  # Never replace fresher live metadata with the seed snapshot.
            self.case(case['cnr'], case['title'], case['court'], case['bench'],
                      re.findall(r'\d+', case['metadata_bns_targets']), {'snapshot_candidate': case})
        count = 0
        with (corpus / 'documents.jsonl').open() as stream:
            for line in stream:
                item = json.loads(line)
                old = originals[item['document_id']]
                with self.db() as db:
                    exists = db.execute("SELECT 1 FROM documents WHERE source_url=? AND status='ready'", (item['source_url'],)).fetchone()
                if exists:
                    continue
                order = old.get('order_metadata', {})
                logical = order_key(item['cnr'], item['decision_date'], order.get('order_number'), item['source_url'])
                identifier, _ = self.document(item['cnr'], logical, item['decision_date'],
                                              item['source_url'], old)
                if self.row(identifier)['status'] == 'ready':
                    continue
                raw = (corpus / item['local_pdf']).read_bytes()
                if digest(raw) != item['pdf_sha256']:
                    raise ValueError('Seed PDF hash mismatch: ' + identifier)
                self.save_pdf(identifier, raw, item['pages'])
                count += 1
        reviews = json.loads((corpus / 'review-seeds.json').read_text())
        if isinstance(reviews, dict):
            reviews = reviews.get('reviews', reviews.get('documents', []))
        with self.db() as db:
            for review in reviews:
                review = dict(review)
                review['evidence_pdf_sha256'] = originals[review['document_id']]['pdf_sha256']
                db.execute('INSERT OR IGNORE INTO seed_reviews VALUES(?,?)',
                           (review['document_id'], encode(review)))
                # Enrich earlier imports without replacing any snapshot evidence/labels.
                old = json.loads(db.execute('SELECT payload FROM seed_reviews WHERE document_id=?',
                                           (review['document_id'],)).fetchone()[0])
                if 'evidence_pdf_sha256' not in old:
                    old['evidence_pdf_sha256'] = review['evidence_pdf_sha256']
                    db.execute('UPDATE seed_reviews SET payload=? WHERE document_id=?',
                               (encode(old), review['document_id']))
        return {'seed_documents_added': count, 'cases': len(cases)}

    def status(self, config):
        with self.db() as db:
            scalar = lambda sql: db.execute(sql).fetchone()[0]
            last = db.execute('SELECT * FROM runs ORDER BY id DESC LIMIT 1').fetchone()
            last_ok = db.execute("SELECT finished_at FROM runs WHERE status IN ('success','partial') ORDER BY id DESC LIMIT 1").fetchone()
            result = {'cases': scalar('SELECT COUNT(*) FROM cases'),
                      'documents_ready': scalar("SELECT COUNT(*) FROM documents WHERE status='ready'"),
                      'documents_pending': scalar("SELECT COUNT(*) FROM documents WHERE status!='ready'"),
                      'human_annotations': scalar('SELECT COUNT(*) FROM annotations'),
                      'latest_order_date': scalar('SELECT MAX(order_date) FROM documents'),
                      'source_latest_modified': scalar('SELECT MAX(modified) FROM source_objects'),
                      'source_case_details_latest_modified': scalar("SELECT MAX(modified) FROM source_objects WHERE key LIKE 'metadata/parquet_case_details/%'"),
                      'source_order_metadata_latest_modified': scalar("SELECT MAX(modified) FROM source_objects WHERE key LIKE 'metadata/parquet/%'"),
                      'last_metadata_check_completed_at': last_ok[0] if last_ok else None,
                      'last_run': parse_run(last) if last else None, 'scope': config.scope(),
                      'interval_seconds': config.interval_seconds,
                      'source': BASE, 'labels': 'Metadata candidates; human legal review pending. Not training gold.'}
        return result


def parse_run(row):
    result = dict(row)
    for key in ['scope', 'stats']:
        result[key] = json.loads(result[key]) if result[key] else {}
    return result


def order_key(cnr, day, number, url):
    if number not in (None, '', 'None'):
        return f'{cnr}|{str(day)[:10]}|{number}'
    return cnr + '|' + url.rsplit('/', 1)[-1]


def atomic(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.partial-')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


class PublicSource:
    """Verified HTTPS only. Listings bypass the disk cache on every run."""
    def __init__(self, store):
        self.store = store

    def download(self, url, limit=25_000_000):
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != 'https' or parsed.netloc != urllib.parse.urlparse(BASE).netloc:
            raise ValueError('Only the public AWS court bucket is allowed')
        with tempfile.TemporaryDirectory(dir=self.store.root) as directory:
            target = Path(directory) / 'download'
            result = subprocess.run(['curl', '--silent', '--show-error', '--fail', '--location',
                '--proto', '=https', '--proto-redir', '=https', '--connect-timeout', '10',
                '--max-time', '60', '--max-filesize', str(limit), '--retry', '1',
                '--output', str(target), url], capture_output=True, text=True, timeout=135)
            if result.returncode:
                raise RuntimeError(f'Public download failed: {result.stderr.strip()[:300]}')
            if target.stat().st_size > limit:
                raise ValueError('Download exceeds limit')
            return target.read_bytes()

    def listing(self, prefix):
        query = {'list-type': '2', 'prefix': prefix, 'max-keys': '1000'}
        output = []
        for _ in range(10):
            root = ET.fromstring(self.download(BASE + '?' + urllib.parse.urlencode(query)))
            for item in root.findall('s:Contents', NS):
                output.append({'key': item.findtext('s:Key', namespaces=NS),
                    'etag': item.findtext('s:ETag', namespaces=NS),
                    'modified': item.findtext('s:LastModified', namespaces=NS),
                    'size': int(item.findtext('s:Size', namespaces=NS))})
            token = root.findtext('s:NextContinuationToken', namespaces=NS)
            if not token:
                return output
            query['continuation-token'] = token
        raise RuntimeError('Source listing exceeds pagination budget')

    def parquet(self, item):
        key = item['key']
        with self.store.db() as db:
            old = db.execute('SELECT * FROM source_objects WHERE key=?', (key,)).fetchone()
        if old and all(old[k] == item[k] for k in ['etag', 'modified', 'size']):
            path = self.store.root / old['path']
            if path.is_file() and digest(path.read_bytes()) == old['sha256']:
                with self.store.db() as db:
                    db.execute('UPDATE source_objects SET checked_at=? WHERE key=?', (now(), key))
                return path, False
        raw = self.download(BASE + urllib.parse.quote(key, safe='/='), limit=150_000_000)
        if not raw.startswith(b'PAR1') or not raw.endswith(b'PAR1'):
            raise ValueError('Source object is not a Parquet')
        # Parse before recording a new source version. Old files remain recoverable.
        import duckdb
        relative = Path('metadata') / digest(key.encode()) / (digest(raw) + '.parquet')
        path = self.store.root / relative
        atomic(path, raw)
        with duckdb.connect() as con:
            con.execute('SELECT COUNT(*) FROM read_parquet(?)', [str(path)]).fetchone()
        with self.store.db() as db:
            db.execute('''INSERT INTO source_objects VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(key) DO UPDATE SET etag=excluded.etag,modified=excluded.modified,
                size=excluded.size,path=excluded.path,sha256=excluded.sha256,checked_at=excluded.checked_at''',
                (key, item['etag'], item['modified'], item['size'], str(relative), digest(raw), now()))
        return path, True
