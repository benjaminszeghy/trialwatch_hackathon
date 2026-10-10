import json
import os
import unittest
from datetime import date, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient

from . import test_backend as fixtures
from .app import create_app
from .core import Store
from .relevance import DEFAULTS, WEIGHTS, assess, order, today


def checked(**changes):
    return DEFAULTS | {'journalist_nexus': 'confirmed', 'case_stage': 'ongoing',
                       'counsel': 'available', 'interpretation': 'not_required',
                       'defence_access': 'adequate', 'custody': 'no', 'immediate_threat': 'no',
                       'deadline_status': 'none', 'opening_status': 'none',
                       'evidence_note': 'Synthetic reviewed source, pages 1–3.'} | changes


class RubricTests(unittest.TestCase):
    def test_unknowns_are_ranges_not_findings(self):
        result = assess()
        self.assertEqual(result['tier'], 'verify')
        self.assertIsNone(result['score'])
        self.assertIsNone(result['score_range'])
        self.assertEqual(result['score_display'], 'Not assessed')
        self.assertEqual(result['coverage_percent'], 0)
        self.assertEqual(sum(WEIGHTS.values()), 100)
        partial = assess(checked(counsel='unknown', interpretation='unknown', defence_access='restricted'), saved=True)
        self.assertEqual(partial['score_range'], [15, 55])
        self.assertEqual(partial['tier'], 'verify')
        self.assertEqual(partial['coverage_percent'], 60)
        full = assess(checked(), saved=True)
        self.assertEqual(full['tier'], 'routine')
        self.assertEqual(full['score'], 0)
        self.assertEqual(full['coverage_percent'], 100)

    def test_weights_tiers_and_no_double_counted_urgency(self):
        high = assess(checked(counsel='unavailable', opening_status='ready', openings=['monitoring']), saved=True)
        self.assertEqual(high['score'], 45)
        self.assertEqual(high['tier'], 'high')
        urgent = assess(checked(counsel='unavailable', interpretation='unavailable', defence_access='restricted',
                               opening_status='ready', openings=['legal_support']), saved=True)
        self.assertEqual(urgent['score'], 75)
        self.assertEqual(urgent['tier'], 'urgent')
        full = assess(checked(counsel='unavailable', interpretation='unavailable', defence_access='restricted',
                             custody='yes', immediate_threat='yes', deadline_status='scheduled',
                             next_deadline='2026-10-12', opening_status='ready', openings=['monitoring']),
                      saved=True, as_of=date(2026, 10, 10))
        self.assertEqual(full['score'], 100)
        self.assertTrue(full['urgent_override'])
        half = assess(checked(counsel='limited', interpretation='limited', opening_status='to_arrange',
                             openings=['advocacy']), saved=True)
        self.assertEqual(half['score'], 30)

    def test_date_boundaries_and_expiry(self):
        base = date(2026, 10, 10)
        for days, points, override in [(0,25,True),(7,25,True),(8,15,False),(30,15,False),(31,5,False)]:
            with self.subTest(days=days):
                r = assess(checked(deadline_status='scheduled', next_deadline=str(base+timedelta(days=days))),
                           saved=True, as_of=base)
                self.assertEqual(r['score'], points)
                self.assertEqual(r['urgent_override'], override)
                self.assertEqual(r['tier'], 'urgent' if override else 'routine')
        expired = assess(checked(deadline_status='scheduled', next_deadline='2026-10-09'), saved=True, as_of=base)
        self.assertTrue(expired['needs_recheck'])
        self.assertIsNone(expired['score_range'])
        self.assertEqual(expired['tier'], 'verify')
        closed = checked(workflow_status='closed', close_reason='Fictional team closure.',
                         deadline_status='scheduled', next_deadline=str(base+timedelta(days=8)))
        self.assertEqual(assess(closed,saved=True,as_of=base)['tier'],'closed')
        imminent=assess(closed,saved=True,as_of=base+timedelta(days=1))
        self.assertEqual(imminent['tier'],'urgent')
        self.assertTrue(imminent['reopened_for_review'])

    def test_fit_closure_and_stale_urgent_recheck(self):
        self.assertEqual(assess(checked(journalist_nexus='unknown'), saved=True)['tier'], 'verify')
        self.assertEqual(assess(checked(journalist_nexus='absent'), saved=True)['tier'], 'outside_scope')
        self.assertEqual(assess(checked(case_stage='completed'), saved=True)['tier'], 'routine')
        r = assess(checked(journalist_nexus='unknown', immediate_threat='yes'), saved=True)
        self.assertEqual(r['label'], 'Urgent verification')
        self.assertEqual(assess(checked(custody='yes', counsel='unavailable'), saved=True)['tier'], 'urgent')
        closed = checked(workflow_status='closed', close_reason='Follow-up complete in this fictional example.')
        self.assertEqual(assess(closed, saved=True)['tier'], 'closed')
        reopened = assess(closed, saved=True, stale=True)
        self.assertEqual(reopened['tier'], 'verify')
        self.assertTrue(reopened['reopened_for_review'])
        stale_urgent = assess(checked(immediate_threat='yes'), saved=True, stale=True)
        self.assertEqual(stale_urgent['label'], 'Urgent recheck')
        self.assertIsNone(stale_urgent['score'])
        self.assertEqual(stale_urgent['coverage_percent'], 0)

    def test_two_layer_sort_and_urgent_override(self):
        def item(cnr, band, tier, score):
            return {'cnr': cnr, 'latest_order_date': '2025-07-01',
                    'review_priority': {'band': band, 'score_range': [10 if band=='high' else 4]*2},
                    'trialwatch_relevance': {'tier': tier, 'score_range': [score,score]}}
        rows=[item('closed','high','closed',100),item('standard','standard','high',50),
              item('high','high','routine',0),item('urgent','standard','urgent',25),
              item('fit','high','high',50),item('outside','high','outside_scope',0)]
        self.assertEqual([r['cnr'] for r in order(rows[:], 'triage')],
                         ['urgent','fit','high','standard','closed','outside'])
        self.assertEqual([r['cnr'] for r in order(rows[:], 'trialwatch')],
                         ['urgent','fit','standard','high','closed','outside'])


class RelevanceApiTests(unittest.TestCase):
    setUp = fixtures.BackendTests.setUp
    tearDown = fixtures.BackendTests.tearDown

    def client(self):
        return TestClient(create_app(self.config, scheduler=False, collector=self.engine))

    def payload(self, client, cnr='TEST0', **changes):
        c = client.get('/api/cases/'+cnr).json()
        return checked(**changes) | {'expected_revision': c['trialwatch_relevance']['revision'],
                                     'evidence_version': c['review_evidence_version']}

    def put(self, client, **changes):
        return client.put('/api/cases/TEST0/relevance', json=self.payload(client, **changes))

    def test_save_idempotence_restart_and_independent_law_score(self):
        self.engine.refresh()
        with self.client() as client:
            original = client.get('/api/feedback').json()
            c = client.get('/api/cases/TEST0').json()
            self.assertEqual(c['trialwatch_relevance']['score_display'], 'Not assessed')
            self.assertEqual(c['trialwatch_relevance']['facts']['counsel'], 'unknown')
            self.assertEqual(c['relevance_passages'], [])
            r = self.put(client, counsel='unavailable', opening_status='ready', openings=['monitoring'])
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()['trialwatch_relevance']['score'], 45)
            self.assertEqual(r.json()['trialwatch_relevance']['revision'], 1)
            repeat = self.put(client, counsel='unavailable', opening_status='ready', openings=['monitoring'])
            self.assertEqual(repeat.json()['trialwatch_relevance']['revision'], 1)
            self.assertEqual(client.get('/api/feedback').json(), original)
            self.assertEqual(client.get('/api/cases?trialwatch_tier=high').json()['total'], 1)
            self.assertEqual(client.get('/api/cases?trialwatch_tier=urgent').json()['total'], 0)
            self.assertEqual(client.get('/api/status').json()['trialwatch_tiers']['high'], 1)
            docs = client.get('/api/documents').json()['items']
            self.assertEqual(docs[0]['trialwatch_relevance']['score'], 45)
            self.assertEqual(client.get('/api/documents/'+docs[0]['id']).json()['trialwatch_relevance']['score'], 45)
            self.engine.refresh()
            self.assertFalse(client.get('/api/cases/TEST0').json()['trialwatch_relevance']['needs_recheck'])
        with Store(self.config.state_dir).db() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM case_relevance_events').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT revision FROM case_relevance').fetchone()[0], 1)
        with self.client() as client:
            self.assertEqual(client.get('/api/cases/TEST0').json()['trialwatch_relevance']['score'],45)

    def test_conflicts_validation_and_write_guard(self):
        self.engine.refresh()
        with self.client() as client:
            old = self.payload(client)
            self.assertEqual(client.put('/api/cases/TEST0/relevance',json=old).status_code,200)
            self.assertEqual(client.put('/api/cases/TEST0/relevance',json=old).status_code,409)
            wrong = self.payload(client) | {'evidence_version':'0'*64}
            self.assertEqual(client.put('/api/cases/TEST0/relevance',json=wrong).status_code,409)
            for changes in [dict(counsel='no'),dict(evidence_note=''),dict(evidence_note='x'*2001),
                            dict(opening_status='ready'),dict(openings=['monitoring']),
                            dict(deadline_status='scheduled'),dict(next_deadline='2001-01-01',deadline_status='scheduled'),
                            dict(workflow_status='closed',close_reason=''),
                            dict(workflow_status='closed',close_reason='Reviewed all facts.',immediate_threat='yes'),
                            dict(workflow_status='closed',close_reason='Reviewed all facts.',custody='yes',counsel='unavailable')]:
                with self.subTest(changes=changes):
                    self.assertEqual(self.put(client,**changes).status_code,422)
            payload=self.payload(client)
            self.assertEqual(client.put('/api/cases/TEST0/relevance',json=payload,
                                       headers={'Origin':'https://untrusted.example'}).status_code,403)
            with patch.dict(os.environ,{'TRIALWATCH_ADMIN_TOKEN':'fixture-secret'}):
                self.assertEqual(client.put('/api/cases/TEST0/relevance',json=payload).status_code,401)
                self.assertEqual(client.put('/api/cases/TEST0/relevance',json=payload,
                                           headers={'Authorization':'Bearer fixture-secret'}).status_code,200)
            self.assertEqual(client.get('/api/cases?trialwatch_tier=wrong').status_code,400)
            self.assertEqual(client.get('/assets/relevance.js').status_code,200)
            self.assertEqual(client.get('/assets/relevance.css').status_code,200)

    def test_closed_review_reopens_on_new_evidence_without_editing_saved_facts(self):
        self.engine.refresh()
        with self.client() as client:
            closed = self.put(client,workflow_status='closed',close_reason='Synthetic follow-up completed.')
            self.assertEqual(closed.json()['trialwatch_relevance']['tier'],'closed')
            with self.store.db() as db:
                payload_before=db.execute('SELECT payload FROM case_relevance').fetchone()[0]
            doc=closed.json()['documents'][0]['id']
            self.store.save_pdf(doc,fixtures.pdf_bytes(180),[{'page':1,'text':'Revised synthetic text.'}])
            changed=client.get('/api/cases/TEST0').json()['trialwatch_relevance']
            self.assertEqual(changed['tier'],'verify')
            self.assertTrue(changed['reopened_for_review'])
            self.assertIsNone(changed['score_range'])
            with self.store.db() as db:
                self.assertEqual(db.execute('SELECT payload FROM case_relevance').fetchone()[0],payload_before)
            active=self.put(client)
            self.assertEqual(active.json()['trialwatch_relevance']['tier'],'routine')
            self.assertEqual(active.json()['trialwatch_relevance']['revision'],2)

    def test_sorted_filtered_across_full_set_before_pagination(self):
        self.source.case_count=3
        self.source.write()
        self.config.max_pdfs_per_run=3
        self.engine.refresh()
        with self.client() as client:
            self.put(client,workflow_status='closed',close_reason='Synthetic follow-up completed.')
            client.put('/api/cases/TEST2/relevance',json=self.payload(client,'TEST2',immediate_threat='yes'))
            page=client.get('/api/cases?sort=triage&limit=1').json()
            self.assertEqual(page['items'][0]['cnr'],'TEST2')
            self.assertEqual(page['trialwatch_summary']['closed'],1)
            second=client.get('/api/cases?sort=triage&limit=1&offset=1').json()
            self.assertEqual(second['items'][0]['cnr'],'TEST1')
            self.assertEqual(client.get('/api/cases?trialwatch_tier=closed&limit=1').json()['total'],1)
            self.assertEqual(client.get('/api/cases?q=Party%202').json()['trialwatch_summary']['urgent'],1)

    def test_passages_are_exact_source_hints_never_auto_facts(self):
        self.engine.refresh()
        with self.client() as client:
            d=client.get('/api/cases/TEST0').json()['documents'][0]
            text='Counsel for the State appeared. A document translation was filed. Hearing listed on 1 December. Access to exhibits was discussed.'
            self.store.save_pdf(d['id'],fixtures.pdf_bytes(130),[{'page':1,'text':text}])
            result=client.get('/api/cases/TEST0').json()
            self.assertEqual(len(result['relevance_passages']),4)
            for p in result['relevance_passages']:
                self.assertIn(p['quote'],text)
                self.assertFalse(p['human_verified'])
                self.assertEqual(p['pdf_sha256'],result['documents'][0]['sha256'])
            self.assertEqual(result['trialwatch_relevance']['facts']['counsel'],'unknown')
            self.assertIsNone(result['trialwatch_relevance']['score'])

    def test_binary_no_does_not_close_relevance(self):
        self.engine.refresh()
        with self.client() as client:
            self.put(client,immediate_threat='yes')
            c=client.get('/api/cases/TEST0').json()
            response=client.put('/api/cases/TEST0/review',json={
                'decision':'no_misuse','law_profile_ids':['BNS-353-2'],'note':'Fictional record reviewed.',
                'expected_revision':0,'evidence_version':c['review_evidence_version']})
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['trialwatch_relevance']['tier'],'urgent')
            self.assertEqual(response.json()['trialwatch_relevance']['revision'],1)


if __name__ == '__main__':
    unittest.main()
