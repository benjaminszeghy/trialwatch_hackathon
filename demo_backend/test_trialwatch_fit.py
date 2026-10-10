import json
import unittest
from datetime import date
from unittest.mock import patch

from fastapi.testclient import TestClient
from . import test_backend as fixtures
from .app import create_app
from .core import Store, now
from .trialwatch_fit import base_assessment, extract
from .feedback import contexts
from .test_relevance import checked


class FitTests(unittest.TestCase):
    setUp = fixtures.BackendTests.setUp
    tearDown = fixtures.BackendTests.tearDown

    def client(self):
        return TestClient(create_app(self.config, scheduler=False, collector=self.engine))

    def payload(self, client, decision='yes', cnr='TEST0'):
        c=client.get('/api/cases/'+cnr).json()
        return {'decision':decision,'note':'Fictional QA assessment.',
                'expected_revision':c['trialwatch_relevance']['fit_review']['revision'],
                'evidence_version':c['review_evidence_version']}

    def test_initial_assessment_without_a_human_vote(self):
        self.engine.refresh()
        with self.client() as client:
            c=client.get('/api/cases/TEST0').json();r=c['trialwatch_relevance']
            self.assertEqual(r['assessment_source'],'automatic')
            self.assertEqual(r['automatic_assessment']['label'],'Limited fit evidence')
            self.assertEqual(r['score'],5)
            self.assertEqual(r['facts']['counsel'],'unknown')
            self.assertIsNone(r['fit_review']['decision'])
            self.assertIsNone(c['case_review']['decision'])
            self.assertEqual(client.get('/api/trialwatch-fit/export').json()['total'],0)
            self.assertEqual(client.get('/api/cases').json()['relevance_review_summary']['automatically_assessed'],1)

    def test_yes_no_edit_clear_persist_and_separate_misuse(self):
        self.engine.refresh()
        with self.client() as client:
            original=client.get('/api/feedback').json()
            url='/api/cases/TEST0/trialwatch-fit'
            p=self.payload(client)
            yes=client.put(url,json=p).json()['trialwatch_relevance']
            self.assertEqual(yes['score'],45);self.assertEqual(yes['tier'],'high')
            self.assertEqual(yes['fit_review']['revision'],1)
            self.assertEqual(client.get('/api/cases?fit_review=unreviewed').json()['total'],0)
            self.assertEqual(client.get('/api/cases?fit_review=yes').json()['total'],1)
            self.assertEqual(client.get('/api/cases?fit_review=not_sure').status_code,400)
            repeat=client.put(url,json=self.payload(client)).json()
            self.assertEqual(repeat['trialwatch_relevance']['fit_review']['revision'],1)
            no=client.put(url,json=self.payload(client,'no')).json()['trialwatch_relevance']
            self.assertEqual(no['score'],0);self.assertEqual(no['tier'],'routine')
            self.assertEqual(no['facts']['workflow_status'],'active')
            self.assertEqual(client.get('/api/feedback').json(),original)
            labels=client.get('/api/trialwatch-fit/export').json()['items']
            self.assertEqual(labels[0]['decision'],'no')
            self.assertEqual(labels[0]['label_task'],'trialwatch_fit')
            clear=client.request('DELETE',url,json={'expected_revision':2}).json()['trialwatch_relevance']
            self.assertEqual(clear['score'],5)
            self.assertEqual(client.get('/api/trialwatch-fit/export').json()['total'],0)
        with Store(self.config.state_dir).db() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM case_fit_review_events').fetchone()[0],3)
        with self.client() as client:
            self.assertEqual(client.get('/api/cases/TEST0').json()['trialwatch_relevance']['fit_review']['revision'],3)

    def test_peer_votes_change_ranking_once_per_case_and_replace(self):
        self.source.case_count=2;self.source.write();self.engine.refresh();self.engine.refresh()
        with self.client() as client:
            url='/api/cases/TEST0/trialwatch-fit'
            client.put(url,json=self.payload(client))
            r=client.get('/api/cases/TEST1').json()['trialwatch_relevance']['automatic_assessment']
            self.assertEqual(r['peer_feedback']['yes'],1)
            self.assertEqual(r['score'],8)
            client.put(url,json=self.payload(client,'no'))
            r=client.get('/api/cases/TEST1').json()['trialwatch_relevance']['automatic_assessment']
            self.assertEqual(r['peer_feedback'],{'yes':0,'no':1,'score_shift':-3.0})
            self.assertEqual(r['score'],2)
            client.request('DELETE',url,json={'expected_revision':2})
            self.assertEqual(client.get('/api/cases/TEST1').json()['trialwatch_relevance']['score'],5)

    def test_negative_fit_moves_behind_active_cases_without_closing(self):
        self.source.case_count=2;self.source.write();self.engine.refresh();self.engine.refresh()
        with self.client() as client:
            client.put('/api/cases/TEST0/trialwatch-fit',json=self.payload(client,'no'))
            queue=client.get('/api/cases?sort=triage').json()['items']
            self.assertEqual([c['cnr'] for c in queue],['TEST1','TEST0'])
            self.assertEqual(queue[1]['trialwatch_relevance']['facts']['workflow_status'],'active')

    def test_multiple_matching_sections_do_not_double_count_peer(self):
        self.source.case_count=2;self.source.write();self.engine.refresh();self.engine.refresh()
        with self.store.db() as db:
            db.execute("UPDATE cases SET sections=?",(json.dumps(['353','196']),))
        with self.client() as client:
            client.put('/api/cases/TEST0/trialwatch-fit',json=self.payload(client))
            r=client.get('/api/cases/TEST1').json()['trialwatch_relevance']['automatic_assessment']
            self.assertEqual(r['peer_feedback']['yes'],1)
            self.assertEqual(r['peer_feedback']['score_shift'],3)

    def test_changed_source_invalidates_feedback_and_refreshes_auto(self):
        self.engine.refresh()
        with self.client() as client:
            client.put('/api/cases/TEST0/trialwatch-fit',json=self.payload(client))
            self.store.document('TEST0','extra','2025-08-01','https://example.invalid/extra.pdf',{})
            c=client.get('/api/cases/TEST0').json()['trialwatch_relevance']
            self.assertTrue(c['fit_review']['needs_recheck'])
            self.assertEqual(client.get('/api/cases?fit_review=needs_recheck').json()['total'],1)
            self.assertEqual(client.get('/api/cases?fit_review=unreviewed').json()['total'],1)
            self.assertFalse(c['fit_review']['score_eligible'])
            self.assertEqual(c['score'],5)
            self.assertEqual(client.get('/api/trialwatch-fit/export').json()['total'],0)
        with self.store.db() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM case_fit_review_events').fetchone()[0],1)

    def test_invalid_decisions_conflicts_and_writer_guard(self):
        self.engine.refresh()
        with self.client() as client:
            url='/api/cases/TEST0/trialwatch-fit';p=self.payload(client)
            self.assertEqual(client.put(url,json=p|{'decision':'unsure'}).status_code,422)
            self.assertEqual(client.put(url,json=p|{'evidence_version':'0'*64}).status_code,409)
            self.assertEqual(client.put(url,json=p).status_code,200)
            self.assertEqual(client.put(url,json=p|{'decision':'no'}).status_code,409)
            self.assertEqual(client.put(url,json=self.payload(client),headers={'origin':'https://elsewhere.example'}).status_code,403)
            with patch.dict('os.environ',{'TRIALWATCH_ADMIN_TOKEN':'test-key'}):
                self.assertEqual(client.get('/api/trialwatch-fit/export').status_code,401)
                self.assertEqual(client.get('/api/trialwatch-fit/export',headers={'authorization':'Bearer test-key'}).status_code,200)

    def test_no_fit_vote_preserves_verified_urgent_need(self):
        self.engine.refresh()
        with self.client() as client:
            c=client.get('/api/cases/TEST0').json()
            facts=checked(counsel='unavailable',custody='yes')
            client.put('/api/cases/TEST0/relevance',json=facts|{'expected_revision':0,'evidence_version':c['review_evidence_version']})
            r=client.put('/api/cases/TEST0/trialwatch-fit',json=self.payload(client,'no')).json()['trialwatch_relevance']
            self.assertEqual(r['tier'],'urgent')
            self.assertTrue(r['urgent_override'])
            self.assertEqual(r['automatic_assessment']['score'],0)

    def test_exact_quotes_and_role_aware_gap_extraction(self):
        self.engine.refresh()
        raw='The applicant is a journalist. The applicant was denied legal aid. State counsel appeared. The applicant was denied access to documents. List the matter for further hearing.'
        with self.store.db() as db:
            doc=db.execute('SELECT * FROM documents').fetchone()
        (self.store.root/doc['text_path']).write_text(json.dumps([{'page':1,'text':raw}]))
        with self.store.db() as db:
            f=extract(self.store,db,'TEST0',contexts(db)['TEST0'])
        self.assertIn('journalism',f['signals']);self.assertIn('counsel',f['signals'])
        self.assertIn('access',f['signals']);self.assertNotIn('interpretation',f['signals'])
        for q in f['signals'].values():self.assertIn(q['quote'],raw)
        a=base_assessment(f,as_of=date(2026,10,10))
        self.assertGreater(a['base_score'],45)
        self.assertFalse(a['current_status_verified'])

    def test_bare_keywords_and_missing_details_do_not_create_needs(self):
        self.engine.refresh()
        raw='State counsel appeared. The judgment in a journalist case was cited. Translation of this order shall be supplied.'
        with self.store.db() as db:doc=db.execute('SELECT * FROM documents').fetchone()
        (self.store.root/doc['text_path']).write_text(json.dumps([{'page':1,'text':raw}]))
        with self.store.db() as db:f=extract(self.store,db,'TEST0',contexts(db)['TEST0'])
        self.assertEqual(f['signals'],{})
        a=base_assessment(f,as_of=date(2026,10,10))
        self.assertEqual(a['base_score'],10)
        self.assertEqual(next(v for v in a['factors'] if v['key']=='support')['points'],0)
        self.assertIn('counsel',a['missing'])

    def test_newer_disposal_does_not_close_criminal_case_or_use_old_pending(self):
        self.engine.refresh()
        with self.store.db() as db:doc=db.execute('SELECT * FROM documents').fetchone()
        (self.store.root/doc['text_path']).write_text(json.dumps([{'page':1,'text':'List the matter for further hearing.'}]))
        self.store.document('TEST0','later','2025-08-01','https://example.invalid/later.pdf',{})
        with self.store.db() as db:new=db.execute("SELECT * FROM documents WHERE logical_key='later'").fetchone()
        self.store.save_pdf(new['id'],fixtures.pdf_bytes(200),[{'page':1,'text':'The application is disposed of.'}])
        with self.store.db() as db:f=extract(self.store,db,'TEST0',contexts(db)['TEST0'])
        self.assertEqual(f['order_stage'],'disposed')
        self.assertNotIn('pending',f['signals'])
        with self.client() as client:
            self.assertEqual(client.get('/api/cases/TEST0').json()['trialwatch_relevance']['facts']['workflow_status'],'active')

    def test_cached_features_reused_and_clock_freshness_recomputed(self):
        self.engine.refresh()
        with self.client() as client:
            client.get('/api/cases/TEST0')
            with patch('demo_backend.trialwatch_fit.extract',side_effect=AssertionError('Cache miss')):
                self.assertEqual(client.get('/api/cases/TEST0').status_code,200)
        f={'signals':{},'sections':['353'],'text_available':True,'order_stage':'unknown','latest_order_date':'2026-10-09','pages_scanned':1,'documents_ready':1}
        self.assertEqual(base_assessment(f,as_of=date(2026,10,10))['base_score'],20)
        self.assertEqual(base_assessment(f,as_of=date(2027,10,10))['base_score'],10)
