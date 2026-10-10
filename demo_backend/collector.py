from __future__ import annotations

import fcntl
import io
import json
import logging
import re
import threading
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone

from research.law_identity import act_family, has_section
from .core import BASE, PublicSource, Store, encode, now, order_key

LOG = logging.getLogger('trialwatch.collector')


def parquet_rows(paths):
    import duckdb
    if not paths:
        return
    # The bucket's year/bench/court fields can exist only in partition paths,
    # not inside the Parquet. Our content-addressed cache must restore them.
    files = [str(item[0]) for item in paths]
    provenance = {str(path): (key, dict(re.findall(r'(?:^|/)(year|court|bench)=([^/]+)', key)))
                  for path, key in paths}
    with duckdb.connect() as con:
        cursor = con.execute('SELECT * FROM read_parquet(?, union_by_name=true, filename=true, hive_partitioning=false)',
                             [files])
        names = [item[0] for item in cursor.description]
        while batch := cursor.fetchmany(2000):
            for row in batch:
                record = dict(zip(names, row))
                key, partitions = provenance[record.pop('filename')]
                record.update(partitions)
                record['_metadata_object_key'] = key
                yield record


def bns_sections(acts, targets):
    if isinstance(acts, str):
        try:
            acts = json.loads(acts)
        except ValueError:
            return []
    return sorted({section for item in (acts or []) if isinstance(item, dict)
        and act_family(item.get('act', '')) == 'BNS' for section in targets
        if has_section(item.get('section', ''), section)})


class Collector:
    def __init__(self, config, store=None, source=None):
        self.config = config
        self.store = store or Store(config.state_dir)
        self.source = source or PublicSource(self.store)
        self._launch_lock = threading.Lock()
        self._thread = None
        self.stop = threading.Event()
        self.next_check_at = None

    def launch(self):
        with self._launch_lock:
            if self._thread and self._thread.is_alive():
                return False
            self._thread = threading.Thread(target=self.refresh, daemon=True, name='court-refresh')
            self._thread.start()
            return True

    @property
    def running(self):
        return bool(self._thread and self._thread.is_alive())

    def schedule(self):
        from datetime import datetime, timedelta, timezone
        while not self.stop.is_set():
            self.launch()
            self.next_check_at = (datetime.now(timezone.utc) +
                timedelta(seconds=self.config.interval_seconds)).isoformat(timespec='seconds')
            if self.stop.wait(self.config.interval_seconds):
                break

    def refresh(self):
        # An OS lock also excludes a simultaneous CLI worker / second server.
        with (self.store.root / 'refresh.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return {'status': 'busy'}
            with self.store.db() as db:
                db.execute("UPDATE runs SET status='interrupted',finished_at=?,error='Previous process stopped before completion' WHERE status='running'", (now(),))
                cursor = db.execute('INSERT INTO runs(started_at,status,scope) VALUES(?,?,?)',
                                    (now(), 'running', encode(self.config.scope())))
                run_id = cursor.lastrowid
            stats = {'metadata_objects_checked': 0, 'metadata_objects_changed': 0,
                     'candidate_cnrs_in_window': 0, 'new_cases': 0, 'new_document_records': 0,
                     'pdfs_downloaded': 0, 'pdf_failures': 0, 'existing_pdfs_rechecked': 0}
            status, error = 'success', None
            try:
                self.ingest(stats, run_id)
            except Exception as exc:
                LOG.exception('Refresh %s failed', run_id)
                status, error = 'failed', str(exc)[:1000]
            if status == 'success' and stats['pdf_failures']:
                status = 'partial'
            with self.store.db() as db:
                db.execute('UPDATE runs SET finished_at=?,status=?,stats=?,error=? WHERE id=?',
                           (now(), status, encode(stats), error, run_id))
            LOG.info('Refresh %s %s: %s', run_id, status, encode(stats))
            return {'id': run_id, 'status': status, 'stats': stats, 'error': error}

    def progress(self, run_id, stats):
        with self.store.db() as db:
            db.execute('UPDATE runs SET stats=? WHERE id=?', (encode(stats), run_id))

    def ingest(self, stats, run_id):
        config = self.config
        detail_paths, order_paths = [], []
        for bench in config.benches:
            prefix = f'metadata/parquet_case_details/court={config.court}/bench={bench}/'
            items = [r for r in self.source.listing(prefix)
                     if r['key'].rsplit('/', 1)[-1] == 'case_details-mobile.parquet']
            if not items:
                raise RuntimeError('Required case-details partition missing: ' + prefix)
            for item in items:
                path, changed = self.source.parquet(item)
                detail_paths.append((path, item['key']))
                stats['metadata_objects_checked'] += 1
                stats['metadata_objects_changed'] += int(changed)
            for year in range(date.fromisoformat(config.start_date).year, config.end.year + 1):
                prefix = f'metadata/parquet/year={year}/court={config.court}/bench={bench}/'
                for item in self.source.listing(prefix):
                    if item['key'].rsplit('/', 1)[-1] not in ('metadata.parquet', 'metadata-mobile.parquet'):
                        continue
                    path, changed = self.source.parquet(item)
                    order_paths.append((path, item['key']))
                    stats['metadata_objects_checked'] += 1
                    stats['metadata_objects_changed'] += int(changed)
            self.progress(run_id, stats)
        if not order_paths:
            raise RuntimeError('No order metadata found in configured scope')

        candidates = {}
        for row in parquet_rows(detail_paths):
            sections = bns_sections(row.get('acts'), config.sections)
            cnr = row.get('cnr')
            if sections and cnr:
                candidates[str(cnr)] = (row, sections)
        options = {}
        for row in parquet_rows(order_paths):
            cnr = str(row.get('cnr') or '')
            day = str(row.get('decision_date') or '')[:10]
            pdf = row.get('pdf_link')
            bench = str(row.get('bench') or '')
            year = str(row.get('year') or '')
            if cnr not in candidates or not pdf or not day:
                continue
            if not config.start_date <= day <= config.end.isoformat():
                continue
            # Metadata is external input: reject links/paths and unexpected partitions.
            if not re.fullmatch(r'[a-zA-Z0-9_.-]+\.pdf', str(pdf)) or bench not in config.benches:
                continue
            if not year.isdigit() or row.get('pdf_exists') is False:
                continue
            key = f'data/pdf/year={year}/court={config.court}/bench={bench}/{pdf}'
            url = BASE + urllib.parse.quote(key, safe='/=')
            logical = order_key(cnr, day, row.get('order_number'), url)
            old = options.get(logical)
            # Prefer mobile, then stable URL tie-break. Deduplicate web/mobile orders.
            priority = (str(row.get('source')) == 'mobile', url)
            if old is None or priority > old[0]:
                options[logical] = (priority, cnr, day, url, row)

        in_window = {o[1] for o in options.values()}
        stats['candidate_cnrs_in_window'] = len(in_window)
        for cnr in sorted(in_window):
            row, sections = candidates[cnr]
            title = f"{row.get('petitioner') or 'Unknown petitioner'} v {row.get('respondent') or 'Unknown respondent'}"
            stats['new_cases'] += int(self.store.case(cnr, title, config.court_name,
                str(row.get('bench') or ''), sections, row))
        for logical, (_, cnr, day, url, row) in sorted(options.items()):
            _, added = self.store.document(cnr, logical, day, url, row)
            stats['new_document_records'] += int(added)
        self.progress(run_id, stats)

        with self.store.db() as db:
            # Scope-local backlog, newest first. Existing annotations are never updated.
            rows = db.execute("SELECT id,cnr FROM documents WHERE status!='ready' ORDER BY order_date DESC,id").fetchall()
        pending = [r['id'] for r in rows if r['cnr'] in in_window][:config.max_pdfs_per_run]
        cutoff = (datetime.now(timezone.utc) - timedelta(days=config.pdf_recheck_days)).isoformat(timespec='seconds')
        with self.store.db() as db:
            old = db.execute("SELECT id,cnr FROM documents WHERE status='ready' AND downloaded_at<? ORDER BY downloaded_at,id", (cutoff,)).fetchall()
        rechecks = [r['id'] for r in old if r['cnr'] in in_window][:min(2, config.max_pdfs_per_run - len(pending))]
        stats['existing_pdfs_rechecked'] = len(rechecks)
        with ThreadPoolExecutor(max_workers=2) as pool:
            for success in pool.map(self.retrieve, pending + rechecks):
                stats['pdfs_downloaded'] += int(success)
                stats['pdf_failures'] += int(not success)
                self.progress(run_id, stats)
        with self.store.db() as db:
            stats['pending_documents_total'] = db.execute("SELECT COUNT(*) FROM documents WHERE status!='ready'").fetchone()[0]
        stats['metadata_checked_at'] = now()

    def retrieve(self, identifier):
        from pypdf import PdfReader
        row = self.store.row(identifier)
        try:
            raw = self.source.download(row['source_url'])
            if not raw.startswith(b'%PDF'):
                raise ValueError('Response is not a PDF')
            reader = PdfReader(io.BytesIO(raw))
            if len(reader.pages) > 500:
                raise ValueError('PDF exceeds 500-page extraction budget')
            pages = [{'page': i + 1, 'text': page.extract_text() or ''}
                     for i, page in enumerate(reader.pages)]
            self.store.save_pdf(identifier, raw, pages)
            return True
        except Exception as exc:
            with self.store.db() as db:
                # Keep any successfully downloaded version; human evidence stays intact.
                db.execute("UPDATE documents SET status=CASE WHEN sha256 IS NULL THEN 'error' ELSE 'ready' END,error=? WHERE id=?",
                           (str(exc)[:500], identifier))
            LOG.warning('Document %s failed: %s', identifier, exc)
            return False
