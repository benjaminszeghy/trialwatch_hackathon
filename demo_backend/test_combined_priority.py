import unittest
from unittest.mock import patch
from io import BytesIO
from pypdf import PdfReader
from fastapi.testclient import TestClient
from . import test_backend as fixtures
from .app import create_app
from .combined_priority import assess, order
from .feedback import ReviewError


def result(law_score=12,fit_score=50,**changes):
    law={'score_range':None if law_score is None else [law_score,law_score],'score_display':'Not scored' if law_score is None else str(law_score)+'/12'}
    fit={'tier':'high','score_range':[fit_score,fit_score],'score_display':str(fit_score)+'/100','fit_review':{},**changes}
    return assess(law,fit)


class CombinedTests(unittest.TestCase):
    def test_blend_and_boundary(self):
        self.assertEqual(result(12,20)['score'],60)
        self.assertEqual(result(12,20)['band'],'high')
        self.assertEqual(result(6,30)['band'],'review')
        self.assertEqual(result(6,29)['band'],'monitor')
        self.assertFalse(result()['is_probability'])

    def test_unknown_is_range_and_needs_check(self):
        r=result(None,20)
        self.assertEqual(r['score_range'],[10,60]);self.assertEqual(r['band'],'verify')
        mixed=assess({'score_range':[6,6],'score_display':'6/12','has_unscored_scope':True},{'tier':'high','score_range':[30,30],'score_display':'30/100'})
        self.assertEqual(mixed['score_range'],[40,65]);self.assertEqual(mixed['band'],'verify')
        self.assertEqual(result(12,60,needs_recheck=True)['band'],'verify')

    def test_no_does_not_hide_urgent_or_close(self):
        vote={'score_eligible':True,'decision':'no'}
        self.assertEqual(result(12,70,fit_review=vote)['score'],39)
        self.assertEqual(result(12,70,fit_review=vote)['band'],'monitor')
        self.assertEqual(result(12,70,fit_review=vote,urgent_override=True)['band'],'urgent')
        self.assertEqual(result(12,70,tier='closed')['band'],'closed')

    def test_order_respects_urgent_then_active_then_negative(self):
        items=[{'cnr':key,'case_priority':p,'latest_order_date':'2025-01-01'} for key,p in [('negative',result(12,70,fit_review={'score_eligible':True,'decision':'no'})),('monitor',result(4,10)),('high',result(12,20)),('urgent',result(1,0,urgent_override=True))]]
        self.assertEqual([c['cnr'] for c in order(items)],['urgent','high','monitor','negative'])


class UnifiedReviewTests(unittest.TestCase):
    setUp=fixtures.BackendTests.setUp
    tearDown=fixtures.BackendTests.tearDown

    def client(self):
        return TestClient(create_app(self.config,scheduler=False,collector=self.engine))

    def payload(self,c,misuse='misuse',fit='yes',cnr='TEST0'):
        item=c.get('/api/cases/'+cnr).json()
        return {'misuse_decision':misuse,'fit_decision':fit,'law_profile_ids':[p['id'] for p in item['review_law_options']] if misuse else [],'note':'Fictional combined QA label.','expected_misuse_revision':item['case_review']['revision'],'expected_fit_revision':item['trialwatch_relevance']['fit_review']['revision'],'evidence_version':item['review_evidence_version']}

    def test_atomic_save_edit_clear_and_one_label_only(self):
        self.engine.refresh()
        with self.client() as c:
            url='/api/cases/TEST0/assessment'
            before=c.get('/api/cases/TEST0').json()['case_priority']['score']
            p=self.payload(c);r=c.put(url,json=p);self.assertEqual(r.status_code,200,r.text)
            after=r.json();self.assertEqual(after['case_review']['decision'],'misuse');self.assertEqual(after['trialwatch_relevance']['fit_review']['decision'],'yes');self.assertGreater(after['case_priority']['score'],before)
            r=c.put(url,json=self.payload(c)).json();self.assertEqual(r['case_review']['revision'],1);self.assertEqual(r['trialwatch_relevance']['fit_review']['revision'],1)
            one=c.put(url,json=self.payload(c,misuse=None,fit='no')).json();self.assertEqual(one['case_review']['revision'],1);self.assertEqual(one['case_review']['decision'],'misuse');self.assertEqual(one['case_priority']['band'],'monitor')
            clear=c.request('DELETE',url,json={'expected_misuse_revision':1,'expected_fit_revision':2});self.assertEqual(clear.status_code,200)
            self.assertIsNone(clear.json()['case_review']['decision']);self.assertIsNone(clear.json()['trialwatch_relevance']['fit_review']['decision']);self.assertEqual(clear.json()['case_priority']['score'],before)

    def test_conflict_or_fit_failure_rolls_back_both(self):
        self.engine.refresh()
        with self.client() as c:
            url='/api/cases/TEST0/assessment';p=self.payload(c)
            self.assertEqual(c.put(url,json=p|{'expected_fit_revision':1}).status_code,409)
            self.assertEqual(c.put(url,json=p|{'law_profile_ids':['wrong']}).status_code,422)
            self.assertEqual(c.put(url,json=p|{'evidence_version':'0'*64}).status_code,409)
            with patch('demo_backend.unified_review.save_fit',side_effect=ReviewError(409,'Simulated competing fit review')):
                self.assertEqual(c.put(url,json=p).status_code,409)
            item=c.get('/api/cases/TEST0').json();self.assertEqual(item['case_review']['revision'],0);self.assertEqual(item['trialwatch_relevance']['fit_review']['revision'],0)
            with self.store.db() as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM case_review_events').fetchone()[0],0)
            self.assertEqual(c.put(url,json=p|{'misuse_decision':None,'fit_decision':None,'law_profile_ids':[]}).status_code,422)
            self.assertEqual(c.put(url,json=p,headers={'origin':'https://elsewhere.example'}).status_code,403)

    def test_filtered_queue_summary_is_before_pagination(self):
        self.source.case_count=2;self.source.write();self.engine.refresh();self.engine.refresh()
        with self.client() as c:
            q=c.get('/api/cases?sort=combined&limit=1').json();self.assertEqual(q['queue_summary']['total'],2);self.assertEqual(len(q['items']),1)
            key=q['items'][0]['case_priority']['band'];self.assertEqual(c.get('/api/cases?queue_priority='+key).json()['total'],2)
            self.assertEqual(c.get('/api/cases?queue_priority=bad').status_code,400)

    def test_demo_isolation_pdf_export_and_reset(self):
        self.engine.refresh()
        with self.client() as c:
            live=c.get('/api/feedback').json()
            initial=c.get('/demo/api/cases?sort=combined').json()
            self.assertEqual(initial['total'],6);self.assertTrue(initial['demo_mode'])
            self.assertEqual(initial['queue_summary']['counts'],{'urgent':1,'high':1,'review':1,'monitor':1,'verify':1,'closed':1,'outside_scope':0})
            item=c.get('/demo/api/cases/DEMO-003').json()
            doc=c.get('/demo'+item['documents'][0]['pdf_url']);self.assertEqual(doc.status_code,200)
            self.assertIn('FICTIONAL DEMO',PdfReader(BytesIO(doc.content)).pages[0].extract_text())
            p={'fit_decision':'yes','expected_fit_revision':0,'expected_misuse_revision':0,'evidence_version':item['review_evidence_version']}
            r=c.put('/demo/api/cases/DEMO-003/assessment',json=p,headers={'origin':'http://testserver'});self.assertEqual(r.status_code,200,r.text)
            self.assertEqual(r.json()['case_priority']['band'],'high')
            labels=c.get('/demo/api/trialwatch-fit/export').json();self.assertEqual(labels['total'],1);self.assertTrue(labels['synthetic_demo']);self.assertFalse(labels['training_eligible'])
            self.assertEqual(c.get('/api/trialwatch-fit/export').json()['total'],0);self.assertEqual(c.get('/api/feedback').json(),live)
            self.assertEqual(c.post('/demo/api/refresh').status_code,409)
            self.assertEqual(c.post('/demo/api/demo/reset',headers={'origin':'http://testserver'}).status_code,200)
            self.assertEqual(c.get('/demo/api/trialwatch-fit/export').json()['total'],0)
            self.assertEqual(c.get('/demo/api/cases').json()['queue_summary'],initial['queue_summary'])
