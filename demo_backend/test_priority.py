import unittest

from fastapi.testclient import TestClient

from . import test_backend as fixtures
from .app import create_app
from .priority import case_laws, review_priority


class PriorityTests(unittest.TestCase):
    def test_boundaries_are_review_bands_not_case_scores(self):
        for score, band in [(0, 'standard'), (5, 'standard'), (6, 'elevated'),
                            (8, 'elevated'), (9, 'high'), (12, 'high')]:
            result = review_priority([{'raw_score_range': [score, score], 'profiles': ['scored']}])
            self.assertEqual(result['band'], band)
            self.assertFalse(result['is_case_misuse_score'])
            self.assertFalse(result['human_verified'])

    def test_unresolved_353_is_not_automatically_high(self):
        result = review_priority(case_laws(['353'], {'acts': [{'act': 'BNS', 'section': '353'}]}))
        self.assertEqual(result['band'], 'uncertain')
        self.assertEqual(result['score_range'], [8, 9])

    def test_law_scores_are_never_added(self):
        links = case_laws(['299', '356'], {'acts': [{'act': 'BNS', 'section': '299,356(2)'}]})
        result = review_priority(links)
        self.assertEqual(result['score_range'], [8, 8])
        self.assertEqual(result['band'], 'elevated')
        links += case_laws(['196'], {'acts': [{'act': 'BNS', 'section': '196(1)(a)'}]})
        self.assertEqual(review_priority(links)['score_range'], [11, 11])

    def test_unscored_scope_is_unknown_not_standard(self):
        links = case_laws(['353'], {'acts': [{'act': 'BNS', 'section': '353(3)'}]})
        result = review_priority(links)
        self.assertEqual(result['band'], 'unscored')
        self.assertIsNone(result['score_range'])
        self.assertTrue(result['has_unscored_scope'])


class PriorityApiTests(unittest.TestCase):
    setUp = fixtures.BackendTests.setUp
    tearDown = fixtures.BackendTests.tearDown

    def populate(self):
        for cnr, section in [('HIGH', '152'), ('ELEVATED', '299'), ('LOW', '356(2)'),
                             ('UNKNOWN', '353'), ('HIGH353', '353(2)'), ('UNSCORED', '353(3)')]:
            self.store.case(cnr, 'Party ' + cnr, 'Court', 'newas', [section.split('(')[0]],
                            {'acts': [{'act': 'BNS', 'section': section}]})

    def test_priority_sort_filter_summary_and_pagination_cover_full_result_set(self):
        self.populate()
        with TestClient(create_app(self.config, scheduler=False, collector=self.engine)) as client:
            result = client.get('/api/cases?sort=priority&limit=2&offset=2').json()
            self.assertEqual(result['total'], 6)
            self.assertEqual([r['cnr'] for r in result['items']], ['UNKNOWN', 'ELEVATED'])
            self.assertEqual(result['summary']['priority_counts'],
                             {'high': 2, 'elevated': 1, 'standard': 1, 'uncertain': 1, 'unscored': 1})
            high = client.get('/api/cases?priority=high&limit=1').json()
            self.assertEqual(high['total'], 2)
            self.assertEqual(high['summary']['total'], 6)
            scoped = client.get('/api/cases?section=353&priority=high').json()
            self.assertEqual(scoped['total'], 1)
            self.assertEqual(scoped['items'][0]['law_links'][0]['raw_score_range'], [9, 9])
            self.assertEqual(scoped['items'][0]['review_priority']['band'], 'high')
            detail = client.get('/api/cases/UNKNOWN').json()
            self.assertEqual(detail['review_priority']['band'], 'uncertain')
            self.assertEqual(client.get('/api/cases?q=LOW').json()['summary']['priority_counts']['standard'], 1)

    def test_invalid_filter_or_sort_is_rejected(self):
        with TestClient(create_app(self.config, scheduler=False, collector=self.engine)) as client:
            self.assertEqual(client.get('/api/cases?priority=urgent').status_code, 400)
            self.assertEqual(client.get('/api/cases?sort=misuse').status_code, 400)


if __name__ == '__main__':
    unittest.main()
