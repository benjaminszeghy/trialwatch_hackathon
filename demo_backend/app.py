from __future__ import annotations

import hmac
import json
import os
import re
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from .collector import Collector
from .core import ROOT, Config, parse_run
from .law_links import catalog, get_links, sync_all


def public_document(row, law_links=None):
    # No machine paths or verbose source HTML in the public response.
    return {k: row[k] for k in ['id', 'cnr', 'order_date', 'source_url', 'status', 'sha256',
        'page_count', 'first_seen', 'downloaded_at', 'error']} | {
        'pdf_url': f'/api/documents/{row["id"]}/pdf' if row['status'] == 'ready' else None,
        'text_url': f'/api/documents/{row["id"]}/text' if row['status'] == 'ready' else None,
        'laws': law_links or [], 'case_misuse_score': None}


def create_app(config=None, *, scheduler=True, collector=None):
    config = config or Config()
    engine = collector or Collector(config)
    store = engine.store
    sync_all(store)

    @asynccontextmanager
    async def lifespan(app):
        worker = None
        if scheduler:
            worker = threading.Thread(target=engine.schedule, daemon=True, name='refresh-scheduler')
            worker.start()
        yield
        engine.stop.set()
        if worker:
            worker.join(timeout=2)

    app = FastAPI(title='TrialWatch BNS collector', version='0.1.0', lifespan=lifespan)
    app.state.collector = engine
    if config.cors_origins:
        app.add_middleware(CORSMiddleware, allow_origins=config.cors_origins,
                           allow_methods=['GET'], allow_headers=['Content-Type'])

    @app.get('/', response_class=HTMLResponse)
    def demo():
        return (Path(__file__).parent / 'demo.html').read_text()

    @app.get('/api/status')
    def status():
        return store.status(config) | {'refresh_running': engine.running,
            'scheduler_enabled': scheduler, 'next_check_at': engine.next_check_at}

    @app.get('/api/cases')
    def cases(q: str = Query('', max_length=200), section: str | None = None,
              limit: int = Query(25, ge=1, le=200), offset: int = Query(0, ge=0)):
        clauses, args = [], []
        if q:
            clauses.append('(c.title LIKE ? OR c.cnr LIKE ?)')
            args.extend(['%' + q + '%'] * 2)
        if section:
            if section not in config.sections:
                raise HTTPException(400, 'Section outside configured BNS scope')
            clauses.append('EXISTS (SELECT 1 FROM json_each(c.sections) WHERE value=?)')
            args.append(section)
        where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
        with store.db() as db:
            total = db.execute('SELECT COUNT(*) FROM cases c' + where, args).fetchone()[0]
            rows = db.execute('''SELECT c.cnr,c.title,c.court,c.bench,c.sections,c.first_seen,
                MAX(d.order_date) AS latest_order_date,COUNT(d.id) AS documents,
                SUM(CASE WHEN d.status='ready' THEN 1 ELSE 0 END) AS documents_ready
                FROM cases c LEFT JOIN documents d ON c.cnr=d.cnr''' + where +
                ' GROUP BY c.cnr ORDER BY latest_order_date DESC,c.cnr LIMIT ? OFFSET ?',
                [*args, limit, offset]).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item['sections'] = json.loads(item['sections'])
            item['law_profiles'] = [p for p in catalog()['profiles'] if p['parent_section'] in item['sections']]
            item['law_score_basis'] = 'Case metadata association; per-document evidence is available in case detail'
            item['review_status'] = 'Human legal review pending; metadata is not a charge finding'
            result.append(item)
        return {'total': total, 'offset': offset, 'limit': limit, 'items': result}

    @app.get('/api/cases/{cnr}')
    def case(cnr: str):
        with store.db() as db:
            row = db.execute('SELECT * FROM cases WHERE cnr=?', (cnr,)).fetchone()
            if not row:
                raise HTTPException(404, 'Case not found')
            docs = db.execute('SELECT * FROM documents WHERE cnr=? ORDER BY order_date,id', (cnr,)).fetchall()
            annotations = db.execute('''SELECT a.* FROM annotations a JOIN documents d ON
                a.document_id=d.id WHERE d.cnr=?''', (cnr,)).fetchall()
            seeds = db.execute('''SELECT s.payload,d.sha256 FROM seed_reviews s JOIN documents d ON
                s.document_id=d.id WHERE d.cnr=?''', (cnr,)).fetchall()
            document_links = {r['id']: get_links(db, r['id']) for r in docs}
        seed_items = []
        for r in seeds:
            item = json.loads(r['payload'])
            item['matches_current_pdf'] = item.get('evidence_pdf_sha256') == r['sha256']
            seed_items.append(item)
        return {'cnr': cnr, 'title': row['title'], 'court': row['court'], 'bench': row['bench'],
                'metadata_bns_sections': json.loads(row['sections']),
                'source_metadata': json.loads(row['metadata']),
                'documents': [public_document(r, document_links[r['id']]) for r in docs],
                'ai_review_seeds': seed_items,
                'seed_status': 'AI-assisted snapshot notes, not human gold; not generated by refresh',
                'human_annotations': [dict(r) | {'payload': json.loads(r['payload'])} for r in annotations]}

    @app.get('/api/documents')
    def documents(section: str | None = None, status: str | None = 'ready',
                  limit: int = Query(25, ge=1, le=200), offset: int = Query(0, ge=0)):
        clauses, args = [], []
        if section:
            if section not in config.sections:
                raise HTTPException(400, 'Section outside configured BNS scope')
            clauses.append('EXISTS (SELECT 1 FROM document_law_links l WHERE l.document_id=d.id AND l.section=?)')
            args.append(section)
        if status:
            if status not in ('ready', 'pending', 'error'):
                raise HTTPException(400, 'Invalid document status')
            clauses.append('d.status=?')
            args.append(status)
        where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
        with store.db() as db:
            total = db.execute('SELECT COUNT(*) FROM documents d' + where, args).fetchone()[0]
            rows = db.execute('''SELECT d.*,c.title FROM documents d JOIN cases c USING(cnr)''' + where +
                ' ORDER BY d.order_date DESC,d.id LIMIT ? OFFSET ?', [*args, limit, offset]).fetchall()
            result = [public_document(r, get_links(db, r['id'])) | {'title': r['title']} for r in rows]
        return {'total': total, 'offset': offset, 'limit': limit, 'items': result}

    @app.get('/api/documents/{identifier}')
    def document_record(identifier: str):
        if not re.fullmatch(r'[a-f0-9]{20}', identifier):
            raise HTTPException(404, 'Document not found')
        row = store.row(identifier)
        if not row:
            raise HTTPException(404, 'Document not found')
        with store.db() as db:
            links = get_links(db, identifier)
        return public_document(row, links)

    def document(identifier):
        if not re.fullmatch(r'[a-f0-9]{20}', identifier):
            raise HTTPException(404, 'Document not found')
        row = store.row(identifier)
        if not row:
            raise HTTPException(404, 'Document not found')
        if row['status'] != 'ready':
            raise HTTPException(409, 'Document is queued or failed; see status and error')
        return row

    def version(row, sha256):
        if not sha256:
            return row
        if not re.fullmatch(r'[a-f0-9]{64}', sha256):
            raise HTTPException(404, 'PDF version not found')
        with store.db() as db:
            r = db.execute('SELECT * FROM document_versions WHERE document_id=? AND sha256=?',
                           (row['id'], sha256)).fetchone()
        if not r:
            raise HTTPException(404, 'PDF version not found')
        return dict(row) | dict(r)

    @app.get('/api/documents/{identifier}/versions')
    def versions(identifier: str):
        document(identifier)
        with store.db() as db:
            rows = db.execute('SELECT sha256,saved_at FROM document_versions WHERE document_id=? ORDER BY saved_at',
                              (identifier,)).fetchall()
        return {'items': [dict(r) | {'pdf_url': f'/api/documents/{identifier}/pdf?sha256={r["sha256"]}',
                                    'text_url': f'/api/documents/{identifier}/text?sha256={r["sha256"]}'} for r in rows]}

    @app.get('/api/documents/{identifier}/pdf')
    def pdf(identifier: str, sha256: str | None = None):
        row = document(identifier)
        row = version(row, sha256)
        return FileResponse(store.root / row['pdf_path'], media_type='application/pdf',
                            headers={'Content-Disposition': 'inline; filename="' + identifier + '.pdf"'})

    @app.get('/api/documents/{identifier}/text')
    def text(identifier: str, sha256: str | None = None):
        row = version(document(identifier), sha256)
        return {'document_id': identifier, 'sha256': row['sha256'], 'source_url': row['source_url'],
                'pages': json.loads((store.root / row['text_path']).read_text())}

    @app.get('/api/runs')
    def runs(limit: int = Query(20, ge=1, le=100)):
        with store.db() as db:
            rows = db.execute('SELECT * FROM runs ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
        return {'items': [parse_run(row) for row in rows]}

    @app.get('/api/laws')
    def laws():
        return json.loads((ROOT / 'outputs/law-scores.json').read_text())

    @app.post('/api/refresh', status_code=202)
    def refresh(request: Request):
        token = os.environ.get('TRIALWATCH_ADMIN_TOKEN')
        if token:
            if not hmac.compare_digest(request.headers.get('authorization', ''), 'Bearer ' + token):
                raise HTTPException(401, 'Admin bearer token required')
        else:
            host = request.client.host if request.client else ''
            hostname = urlparse(str(request.url)).hostname
            origin = request.headers.get('origin')
            if host not in ('127.0.0.1', '::1', 'testclient') or hostname not in ('127.0.0.1', 'localhost', '::1', 'testserver'):
                raise HTTPException(403, 'Manual refresh is local-only; configure TRIALWATCH_ADMIN_TOKEN for remote use')
            if origin and origin != str(request.base_url).rstrip('/'):
                raise HTTPException(403, 'Refresh requires same origin')
        return {'accepted': engine.launch(), 'message': 'Refresh queued, or existing refresh still running'}

    return app
