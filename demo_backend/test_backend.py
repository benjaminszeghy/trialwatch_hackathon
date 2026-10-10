import io
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import duckdb
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from .app import create_app
from .collector import Collector, bns_sections
from .core import BASE, Config, PublicSource, Store, digest, now


def pdf_bytes(width=100):
    writer = PdfWriter()
    writer.add_blank_page(width=width, height=100)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


class FakeSource:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.raw = pdf_bytes()
        self.fail = False
        self.metadata_fail = False
        self.case_count = 1
        self.write()

    def write(self):
        detail = self.directory / 'details.parquet'
        orders = self.directory / 'orders.parquet'
        with duckdb.connect() as con:
            con.execute('CREATE TABLE details(cnr VARCHAR, petitioner VARCHAR, respondent VARCHAR, bench VARCHAR, acts VARCHAR)')
            # AWS order Parquets omit the hive year/bench columns. Keep this real schema behavior.
            con.execute('CREATE TABLE orders(cnr VARCHAR,decision_date VARCHAR,pdf_link VARCHAR,order_number VARCHAR,source VARCHAR,pdf_exists BOOLEAN)')
            for i in range(self.case_count):
                cnr = f'TEST{i}'
                con.execute('INSERT INTO details VALUES(?,?,?,?,?)', [cnr, f'Party {i}', 'State', 'newas', json.dumps([{'act': 'Bharatiya Nyaya Sanhita', 'section': '353(2)'}])])
                # Both representations have the same proceeding/date/order number.
                for source in ['mobile', 'web']:
                    con.execute('INSERT INTO orders VALUES(?,?,?,?,?,?)', [cnr, '2025-07-01', f'orders_{i}_{source}.pdf', '1', source, True])
            con.execute('COPY details TO ? (FORMAT PARQUET)', [str(detail)])
            con.execute('COPY orders TO ? (FORMAT PARQUET)', [str(orders)])

    def listing(self, prefix):
        if self.metadata_fail:
            raise RuntimeError('Upstream listing unavailable')
        if 'parquet_case_details' in prefix:
            return [{'key': prefix + 'case_details-mobile.parquet'}]
        if 'year=2025' in prefix:
            return [{'key': prefix + 'metadata-mobile.parquet'}]
        return []

    def parquet(self, item):
        return self.directory / ('details.parquet' if 'case_details' in item['key'] else 'orders.parquet'), True

    def download(self, url):
        if self.fail:
            raise RuntimeError('PDF source failed')
        return self.raw


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.config = Config(state_dir=self.directory / 'state', benches=['newas'],
                             start_date='2025-01-01', end_date='2025-12-31', max_pdfs_per_run=1)
        self.store = Store(self.config.state_dir)
        self.source = FakeSource(self.directory)
        self.engine = Collector(self.config, self.store, self.source)

    def tearDown(self):
        self.temp.cleanup()

    def annotate(self):
        with self.store.db() as db:
            identifier = db.execute('SELECT id FROM documents LIMIT 1').fetchone()[0]
            db.execute('INSERT INTO annotations VALUES(?,?,?,?)', (identifier, 'human', '{"law_role":"pending"}', now()))
        return identifier

    def test_incremental_idempotence_and_annotation_preservation(self):
        first = self.engine.refresh()
        self.assertEqual(first['status'], 'success')
        self.assertEqual(first['stats']['new_document_records'], 1)
        identifier = self.annotate()
        self.assertIn('mobile', self.store.row(identifier)['source_url'])
        second = self.engine.refresh()
        self.assertEqual(second['stats']['new_cases'], 0)
        self.assertEqual(second['stats']['pdfs_downloaded'], 0)
        self.source.case_count = 2
        self.source.write()
        third = self.engine.refresh()
        self.assertEqual(third['stats']['new_cases'], 1)
        self.assertEqual(third['stats']['new_document_records'], 1)
        self.assertEqual(self.store.status(self.config)['human_annotations'], 1)

    def test_seed_rerun_preserves_fresh_metadata_pdf_and_review_version(self):
        self.engine.refresh()
        identifier = self.annotate()
        row = self.store.row(identifier)
        corpus = self.directory / 'corpus'
        corpus.mkdir()
        (corpus / 'seed.pdf').write_bytes(self.source.raw)
        cases = [{'cnr': 'TEST0', 'title': 'Old title', 'court': 'Bombay High Court',
                  'bench': 'newas', 'metadata_bns_targets': '353'}]
        (corpus / 'case-candidates.json').write_text(json.dumps(cases))
        old = {'document_id': identifier, 'order_metadata': {'order_number': '1'},
               'pdf_sha256': row['sha256']}
        metadata = self.directory / 'raw.json'
        metadata.write_text(json.dumps([old]))
        item = {'document_id': identifier, 'cnr': 'TEST0', 'decision_date': row['order_date'],
                'source_url': row['source_url'], 'local_pdf': 'seed.pdf',
                'pdf_sha256': row['sha256'], 'pages': [{'page': 1, 'text': ''}]}
        (corpus / 'documents.jsonl').write_text(json.dumps(item) + '\n')
        (corpus / 'review-seeds.json').write_text(json.dumps([{'document_id': identifier, 'note': 'Old review'}]))
        self.store.save_pdf(identifier, pdf_bytes(200), [{'page': 1, 'text': ''}])
        self.assertEqual(self.store.seed(corpus, metadata)['seed_documents_added'], 0)
        self.assertEqual(self.store.row(identifier)['sha256'], digest(pdf_bytes(200)))
        with TestClient(create_app(self.config, scheduler=False, collector=self.engine)) as client:
            case = client.get('/api/cases/TEST0').json()
            self.assertEqual(case['title'], 'Party 0 v State')
            self.assertFalse(case['ai_review_seeds'][0]['matches_current_pdf'])
            self.assertEqual(len(case['human_annotations']), 1)

    def test_changed_pdf_retains_evidence_versions_and_labels(self):
        self.engine.refresh()
        identifier = self.annotate()
        old = self.store.row(identifier)
        self.source.raw = pdf_bytes(width=200)
        with self.store.db() as db:
            db.execute("UPDATE documents SET downloaded_at='2000-01-01T00:00:00+00:00'")
        result = self.engine.refresh()
        self.assertEqual(result['stats']['existing_pdfs_rechecked'], 1)
        self.assertNotEqual(old['sha256'], self.store.row(identifier)['sha256'])
        self.assertTrue((self.store.root / old['pdf_path']).exists())
        with self.store.db() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM document_versions').fetchone()[0], 2)
            self.assertEqual(db.execute('SELECT payload FROM annotations').fetchone()[0], '{"law_role":"pending"}')
        with TestClient(create_app(self.config, scheduler=False, collector=self.engine)) as client:
            self.assertEqual(len(client.get(f'/api/documents/{identifier}/versions').json()['items']), 2)
            self.assertEqual(digest(client.get(f'/api/documents/{identifier}/pdf?sha256={old["sha256"]}').content), old['sha256'])

    def test_failed_pdf_is_visible_and_retried(self):
        self.source.fail = True
        first = self.engine.refresh()
        self.assertEqual(first['status'], 'partial')
        self.assertEqual(self.store.status(self.config)['documents_pending'], 1)
        self.source.fail = False
        second = self.engine.refresh()
        self.assertEqual(second['stats']['new_document_records'], 0)
        self.assertEqual(self.store.status(self.config)['documents_ready'], 1)

    def test_source_failure_does_not_claim_freshness_or_delete_data(self):
        self.engine.refresh()
        before = self.store.status(self.config)
        self.source.metadata_fail = True
        self.assertEqual(self.engine.refresh()['status'], 'failed')
        after = self.store.status(self.config)
        self.assertEqual(after['last_metadata_check_completed_at'], before['last_metadata_check_completed_at'])
        self.assertEqual(after['documents_ready'], 1)

    def test_pdf_budget_creates_visible_backlog(self):
        self.source.case_count = 3
        self.source.write()
        first = self.engine.refresh()
        self.assertEqual(first['stats']['new_document_records'], 3)
        self.assertEqual(first['stats']['pdfs_downloaded'], 1)
        self.assertEqual(first['stats']['pending_documents_total'], 2)
        self.engine.refresh()
        self.assertEqual(self.store.status(self.config)['documents_pending'], 1)

    def test_bns_identity_rejects_bnss_and_neighbor_sections(self):
        self.assertEqual(bns_sections([{'act': 'BNSS', 'section': '353'}], ['353']), [])
        self.assertEqual(bns_sections([{'act': 'BNS', 'section': '3530'}], ['353']), [])
        self.assertEqual(bns_sections([{'act': 'BNS', 'section': '353(2)'}], ['353']), ['353'])

    def test_api_search_pdf_text_and_local_admin(self):
        self.engine.refresh()
        identifier = self.annotate()
        with TestClient(create_app(self.config, scheduler=False, collector=self.engine)) as client:
            result = client.get('/api/cases?section=353&q=Party')
            self.assertEqual(result.json()['total'], 1)
            self.assertEqual(client.get('/api/cases?section=152').json()['total'], 0)
            self.assertEqual(client.get('/api/cases/TEST0').json()['human_annotations'][0]['reviewer'], 'human')
            pdf = client.get(f'/api/documents/{identifier}/pdf')
            self.assertEqual(pdf.headers['content-type'], 'application/pdf')
            self.assertTrue(pdf.content.startswith(b'%PDF'))
            self.assertEqual(client.get(f'/api/documents/{identifier}/text').json()['pages'][0]['page'], 1)
            self.assertEqual(client.get('/api/documents/invalid/pdf').status_code, 404)
            self.assertEqual(client.post('/api/refresh', headers={'Origin': 'https://example.com'}).status_code, 403)
            with patch.dict('os.environ', {'TRIALWATCH_ADMIN_TOKEN': 'test-secret'}):
                self.assertEqual(client.post('/api/refresh').status_code, 401)
                with patch.object(self.engine, 'launch', return_value=True):
                    self.assertEqual(client.post('/api/refresh', headers={'Authorization': 'Bearer test-secret'}).status_code, 202)

    def test_singleflight_and_cross_process_lock(self):
        started, finish = threading.Event(), threading.Event()
        original = self.source.listing
        def listing(prefix):
            started.set()
            finish.wait(5)
            return original(prefix)
        with patch.object(self.source, 'listing', side_effect=listing):
            self.assertTrue(self.engine.launch())
            self.assertTrue(started.wait(2))
            self.assertFalse(self.engine.launch())
            self.assertEqual(Collector(self.config, self.store, self.source).refresh()['status'], 'busy')
            finish.set()
            self.engine._thread.join(5)
            self.assertFalse(self.engine.running)

    def test_scheduler_sets_next_check_and_stops(self):
        with patch.object(self.engine, 'launch') as launch, patch.object(self.engine.stop, 'wait', return_value=True):
            self.engine.schedule()
            launch.assert_called_once()
            self.assertIsNotNone(self.engine.next_check_at)

    def test_source_cache_reuses_only_matching_object_and_valid_hash(self):
        source = PublicSource(self.store)
        raw = (self.directory / 'details.parquet').read_bytes()
        item = {'key': 'metadata/example.parquet', 'etag': 'v1', 'modified': now(), 'size': len(raw)}
        with patch.object(source, 'download', return_value=raw) as download:
            path, changed = source.parquet(item)
            self.assertTrue(changed)
            self.assertFalse(source.parquet(item)[1])
            self.assertEqual(download.call_count, 1)
            path.write_bytes(b'corrupt')
            self.assertTrue(source.parquet(item)[1])
            self.assertEqual(download.call_count, 2)
            self.assertTrue(source.parquet(item | {'etag': 'v2'})[1])
            self.assertEqual(download.call_count, 3)
        with self.assertRaises(ValueError):
            source.download('https://example.com/private.pdf')


if __name__ == '__main__':
    unittest.main()
