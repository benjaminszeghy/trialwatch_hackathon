import json
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from . import test_backend as fixtures
from .app import create_app
from .core import Store
from .feedback import state


class FeedbackTests(unittest.TestCase):
    setUp = fixtures.BackendTests.setUp
    tearDown = fixtures.BackendTests.tearDown

    def client(self):
        return TestClient(create_app(self.config, scheduler=False, collector=self.engine))

    def payload(self, client, decision='misuse', cnr='TEST0', profiles=None, note='Reviewed the record.'):
        case = client.get('/api/cases/' + cnr).json()
        return {'decision': decision, 'law_profile_ids': ['BNS-353-2'] if profiles is None else profiles,
                'note': note, 'expected_revision': case['case_review']['revision'],
                'evidence_version': case['review_evidence_version']}

    def score(self, client, identifier='BNS-353-2'):
        return next(p for p in client.get('/api/feedback').json()['profiles'] if p['id'] == identifier)

    def test_yes_no_replacement_clear_and_persistence(self):
        self.engine.refresh()
        with self.client() as client:
            original = client.get('/api/laws').json()
            yes = client.put('/api/cases/TEST0/review', json=self.payload(client)).json()
            self.assertEqual(yes['case_review']['revision'], 1)
            self.assertAlmostEqual(self.score(client)['adjusted_score'], 66 / 7, places=4)
            self.assertEqual(self.score(client)['review_count'], 1)
            same = client.put('/api/cases/TEST0/review', json=self.payload(client))
            self.assertEqual(same.json()['case_review']['revision'], 1)
            self.assertEqual(self.score(client)['review_count'], 1)
            no = client.put('/api/cases/TEST0/review', json=self.payload(client, 'no_misuse')).json()
            self.assertEqual(no['case_review']['revision'], 2)
            self.assertEqual(self.score(client)['yes_reviews'], 0)
            self.assertEqual(self.score(client)['no_reviews'], 1)
            self.assertAlmostEqual(self.score(client)['adjusted_score'], 54 / 7, places=4)
            self.assertEqual(no['review_priority']['band'], 'elevated')
            self.assertEqual(client.get('/api/cases?priority=elevated').json()['total'], 1)
            self.assertEqual(client.get('/api/cases?priority=high').json()['total'], 0)
            self.assertEqual(client.get('/api/cases?limit=1').json()['summary']['priority_counts']['elevated'], 1)
            self.assertEqual(no['documents'][0]['laws'][0]['raw_score_range'], [9, 9])
            self.assertEqual(no['documents'][0]['laws'][0]['feedback_score_range'], [7.7143, 7.7143])
            self.assertEqual(client.get('/api/laws').json(), original)
            with Store(self.config.state_dir).db() as db:
                self.assertEqual(state(db)['reviews']['TEST0']['decision'], 'no_misuse')
                self.assertEqual(db.execute('SELECT COUNT(*) FROM case_review_events').fetchone()[0], 2)
            clear = client.request('DELETE', '/api/cases/TEST0/review', json={'expected_revision': 2}).json()
            self.assertIsNone(clear['case_review']['decision'])
            self.assertEqual(self.score(client)['adjusted_score'], 9)
            self.assertEqual(client.get('/api/reviews/export').json()['total'], 0)

    def test_new_order_invalidates_assessment_without_deleting_its_history(self):
        self.engine.refresh()
        with self.client() as client:
            client.put('/api/cases/TEST0/review', json=self.payload(client))
            self.store.document('TEST0', 'new-order', '2025-08-01', 'https://example.invalid/new-order.pdf', {})
            review = client.get('/api/cases/TEST0').json()['case_review']
            self.assertTrue(review['needs_recheck'])
            self.assertEqual(review['decision'], 'misuse')
            self.assertEqual(self.score(client)['review_count'], 0)
            self.assertEqual(client.get('/api/cases?review=needs_recheck').json()['total'], 1)
            with self.store.db() as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM case_review_events').fetchone()[0], 1)

    def test_only_yes_no_are_accepted_and_legacy_unknowns_stay_unreviewed(self):
        self.engine.refresh()
        with self.client() as client:
            response = client.put('/api/cases/TEST0/review', json=self.payload(client, 'insufficient', profiles=[]))
            self.assertEqual(response.status_code, 422)
            self.assertEqual(client.get('/api/cases?review=insufficient').status_code, 400)
            # Simulate a record written by the previous version, without modifying it.
            from .feedback import contexts
            from .core import now
            with self.store.db() as db:
                context = contexts(db)['TEST0']
                legacy = {'decision': 'insufficient', 'law_profile_ids': [], 'note': 'Old uncertain review',
                          **context, 'reviewed_at': now()}
                db.execute('INSERT INTO case_reviews VALUES(?,?,?,?)', ('TEST0', 1, json.dumps(legacy), now()))
            review = client.get('/api/cases/TEST0').json()['case_review']
            self.assertIsNone(review['decision'])
            self.assertFalse(review['score_eligible'])
            self.assertEqual(review['legacy_decision'], 'insufficient')
            self.assertEqual(client.get('/api/cases?review=unreviewed').json()['total'], 1)
            self.assertEqual(client.get('/api/status').json()['case_reviews']['reviewed'], 0)
            self.assertEqual(self.score(client)['adjusted_score'], 9)
            self.assertEqual(client.get('/api/reviews/export').json()['total'], 0)
            with self.store.db() as db:
                self.assertEqual(json.loads(db.execute('SELECT payload FROM case_reviews').fetchone()[0])['decision'], 'insufficient')
            saved = client.put('/api/cases/TEST0/review', json=self.payload(client, 'no_misuse'))
            self.assertEqual(saved.status_code, 200)
            self.assertEqual(saved.json()['case_review']['revision'], 2)
            self.assertEqual(self.score(client)['no_reviews'], 1)

    def test_new_pdf_metadata_and_catalog_evidence_changes_require_recheck(self):
        self.engine.refresh()
        with self.client() as client:
            client.put('/api/cases/TEST0/review', json=self.payload(client))
            self.engine.refresh()  # unchanged polling must not invalidate the label
            self.assertFalse(client.get('/api/cases/TEST0').json()['case_review']['needs_recheck'])
            old = self.payload(client)
            document = client.get('/api/cases/TEST0').json()['documents'][0]
            self.store.save_pdf(document['id'], fixtures.pdf_bytes(200), [{'page': 1, 'text': 'Changed evidence'}])
            stale = client.get('/api/cases/TEST0').json()
            self.assertTrue(stale['case_review']['needs_recheck'])
            self.assertEqual(self.score(client)['adjusted_score'], 9)
            self.assertEqual(client.get('/api/reviews/export').json()['total'], 0)
            self.assertEqual(client.put('/api/cases/TEST0/review', json=old).status_code, 409)
            updated = client.put('/api/cases/TEST0/review', json=self.payload(client)).json()
            self.assertEqual(updated['case_review']['revision'], 2)
            self.assertFalse(updated['case_review']['needs_recheck'])
            self.store.case('TEST0', 'Party 0 v State', 'Bombay High Court', 'newas', ['353'],
                            {'acts': [{'act': 'BNS', 'section': '353(2)'}], 'new_fact': True})
            self.assertTrue(client.get('/api/cases/TEST0').json()['case_review']['needs_recheck'])
            client.put('/api/cases/TEST0/review', json=self.payload(client))
            from .law_links import catalog
            changed = catalog() | {'sha256': 'f' * 64}
            with patch('demo_backend.feedback.catalog', return_value=changed):
                self.assertTrue(client.get('/api/cases/TEST0').json()['case_review']['needs_recheck'])

    def test_multilaw_manual_attribution_does_not_vote_on_other_laws(self):
        self.engine.refresh()
        self.store.case('TEST0', 'Party 0 v State', 'Court', 'newas', ['299', '353'],
                        {'acts': [{'act': 'BNS', 'section': '299,353'}]})
        with self.client() as client:
            options = client.get('/api/cases/TEST0').json()['review_law_options']
            self.assertEqual({p['id'] for p in options}, {'BNS-299', 'BNS-353-1', 'BNS-353-2'})
            self.assertEqual(client.put('/api/cases/TEST0/review', json=self.payload(client, profiles=[])).status_code, 422)
            self.assertEqual(client.put('/api/cases/TEST0/review', json=self.payload(client, profiles=['BNS-152'])).status_code, 422)
            result = client.put('/api/cases/TEST0/review', json=self.payload(client, profiles=['BNS-299', 'BNS-299']))
            self.assertEqual(result.status_code, 200)
            self.assertEqual(self.score(client, 'BNS-299')['review_count'], 1)
            self.assertEqual(self.score(client, 'BNS-353-1')['review_count'], 0)
            self.assertEqual(self.score(client)['review_count'], 0)

    def test_conflicting_revision_does_not_overwrite_saved_review(self):
        self.engine.refresh()
        with self.client() as client:
            a, b = self.payload(client), self.payload(client, 'no_misuse')
            self.assertEqual(client.put('/api/cases/TEST0/review', json=a).status_code, 200)
            self.assertEqual(client.put('/api/cases/TEST0/review', json=b).status_code, 409)
            self.assertEqual(client.request('DELETE', '/api/cases/TEST0/review', json={'expected_revision': 0}).status_code, 409)
            self.assertEqual(self.score(client)['yes_reviews'], 1)
            self.assertEqual(self.score(client)['no_reviews'], 0)

    def test_export_snapshots_and_pdf_feed_share_current_scores(self):
        self.engine.refresh()
        with self.client() as client:
            client.put('/api/cases/TEST0/review', json=self.payload(client))
            export = client.get('/api/reviews/export').json()
            self.assertEqual(export['total'], 1)
            label = export['items'][0]
            self.assertFalse(label['family_group_verified'])
            self.assertIn('not gold', label['label_status'])
            self.assertTrue(label['snapshot']['documents'][0]['sha256'])
            self.assertEqual(label['law_profile_ids'], ['BNS-353-2'])
            docs = client.get('/api/documents').json()['items']
            one = client.get('/api/documents/' + docs[0]['id']).json()
            self.assertEqual(one['laws'][0]['feedback_score_range'], docs[0]['laws'][0]['feedback_score_range'])
            self.assertIsNone(one['case_misuse_score'])
            self.assertEqual(client.get('/api/cases?review=misuse').json()['total'], 1)
            self.assertEqual(client.get('/api/cases?review=bad').status_code, 400)

    def test_local_write_and_export_guards_and_input_limits(self):
        self.engine.refresh()
        with self.client() as client:
            data = self.payload(client)
            self.assertEqual(client.put('/api/cases/TEST0/review', json=data, headers={'origin': 'https://external.test'}).status_code, 403)
            with patch.dict(os.environ, {'TRIALWATCH_ADMIN_TOKEN': 'test-secret'}):
                self.assertEqual(client.put('/api/cases/TEST0/review', json=data).status_code, 401)
                self.assertEqual(client.get('/api/reviews/export').status_code, 401)
                self.assertEqual(client.put('/api/cases/TEST0/review', json=data,
                                           headers={'authorization': 'Bearer test-secret'}).status_code, 200)
            self.assertEqual(client.put('/api/cases/TEST0/review', json=data | {'note': 'x' * 1501}).status_code, 422)
            self.assertEqual(client.put('/api/cases/TEST0/review', json=data | {'decision': 'legal'}).status_code, 422)
            self.assertEqual(client.put('/api/cases/TEST0/review', json=data | {'extra': True}).status_code, 422)
            self.assertEqual(client.put('/api/cases/MISSING/review', json=data).status_code, 404)
        with TestClient(create_app(self.config, scheduler=False, collector=self.engine),
                        base_url='http://public.test', client=('203.0.113.10', 1)) as remote:
            self.assertEqual(remote.put('/api/cases/TEST0/review', json=data).status_code, 403)
            self.assertEqual(remote.get('/api/reviews/export').status_code, 403)

    def test_no_document_no_false_certainty_and_unknown_scope_not_zero(self):
        self.store.case('TEST0', 'Pending case', 'Court', 'newas', ['353'],
                        {'acts': [{'act': 'BNS', 'section': '353(3)'}]})
        with self.client() as client:
            case = client.get('/api/cases/TEST0').json()
            self.assertEqual(case['review_law_options'], [])
            self.assertEqual(client.put('/api/cases/TEST0/review', json=self.payload(client, profiles=[])).status_code, 422)
            result = client.put('/api/cases/TEST0/review', json=self.payload(client, 'insufficient', profiles=[]))
            self.assertEqual(result.status_code, 422)
            self.assertEqual(client.get('/api/cases/TEST0').json()['review_priority']['band'], 'unscored')
            self.assertEqual(self.score(client)['adjusted_score'], 9)

    def test_two_case_votes_are_bounded_and_replaceable(self):
        self.source.case_count = 2
        self.source.write()
        self.engine.refresh()
        self.engine.refresh()
        with self.client() as client:
            client.put('/api/cases/TEST0/review', json=self.payload(client))
            client.put('/api/cases/TEST1/review', json=self.payload(client, 'no_misuse', cnr='TEST1'))
            self.assertEqual(self.score(client)['review_count'], 2)
            self.assertEqual(self.score(client)['adjusted_score'], 66 / 8)
            client.put('/api/cases/TEST1/review', json=self.payload(client, cnr='TEST1'))
            self.assertEqual(self.score(client)['review_count'], 2)
            self.assertEqual(self.score(client)['adjusted_score'], 78 / 8)
            self.assertTrue(0 <= self.score(client)['adjusted_score'] <= 12)


if __name__ == '__main__':
    unittest.main()
