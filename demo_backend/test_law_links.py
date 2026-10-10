import json
import unittest

from fastapi.testclient import TestClient

from .app import create_app
from .law_links import build_links, catalog, text_references
from . import test_backend as fixtures


class LawReferenceTests(unittest.TestCase):
    def link(self, section, text='', metadata=None, review=None):
        return build_links([section], metadata or {'acts': [{'act': 'BNS', 'section': section}]},
            [{'page': 1, 'text': text}], review, pdf_sha256='current-pdf', source_catalog=catalog())[0]

    def test_low_score_is_preserved_and_never_becomes_case_probability(self):
        for section in ['221', '356']:
            link = self.link(section)
            self.assertEqual(link['raw_score_range'], [4, 4])
            self.assertEqual(link['association_status'], 'metadata_only')
            self.assertFalse(link['human_verified'])

    def test_353_parent_does_not_pick_highest_subsection(self):
        link = self.link('353')
        self.assertEqual(link['raw_score_range'], [8, 9])
        self.assertEqual(link['scope_status'], 'scope_unresolved')
        self.assertEqual(len(link['profiles']), 2)

    def test_act_bound_charge_reference_resolves_subsection(self):
        link = self.link('353', 'The offences are punishable under Section 353(1)(b) of the Bharatiya Nyaya Sanhita, 2023.')
        self.assertEqual(link['association_status'], 'text_reference_candidate')
        self.assertEqual(link['document_sections'], ['353(1)(b)'])
        self.assertEqual(link['raw_score_range'], [8, 8])
        self.assertEqual(link['evidence'][0]['page'], 1)
        self.assertFalse(link['evidence'][0]['human_verified'])

    def test_bnss_ipc_years_and_unrelated_numbers_are_not_bns_charges(self):
        for text in ['Section 353 of the Bharatiya Nagarik Suraksha Sanhita (BNSS)',
                     'Section 353 of the Indian Penal Code; a separate reference to BNS.',
                     'Order dated 3/5/2023. The BNS is discussed.', 'Section 3530 of the BNS']:
            self.assertEqual(text_references([{'page': 1, 'text': text}]), [], text)

    def test_unscored_subsections_do_not_inherit_another_profile(self):
        for section, token in [('353', '353(3)'), ('356', '356(4)'), ('196', '196(1)(c)')]:
            link = self.link(section, f'Offences under Section {token} of the BNS.')
            self.assertEqual(link['profiles'], [])
            self.assertIsNone(link['raw_score_range'])
            self.assertEqual(link['scope_status'], 'unscored_scope')

    def test_metadata_and_document_subsection_disagreement_is_visible(self):
        link = self.link('353', 'Offences under Section 353(2) of the BNS.',
                         {'acts': [{'act': 'BNS', 'section': '353(1)'}]})
        self.assertTrue(link['metadata_document_subsection_disagreement'])
        self.assertEqual(link['raw_score_range'], [9, 9])

    def test_ai_seed_requires_current_hash_and_exact_supporting_passage(self):
        quote = 'offences punishable under Sections 152 of the BNS'
        seed = {'page': 1, 'quote': quote, 'verified_target_sections': ['152'],
                'role': 'operative charge recorded', 'evidence_pdf_sha256': 'current-pdf'}
        self.assertEqual(self.link('152', quote, review=seed)['association_status'], 'ai_review_charge_recorded')
        self.assertEqual(self.link('152', '', review=seed)['association_status'], 'metadata_only')
        self.assertEqual(self.link('152', quote, review=seed | {'evidence_pdf_sha256': 'old-pdf'})['association_status'], 'text_reference_candidate')


class DatabaseLinkTests(unittest.TestCase):
    setUp = fixtures.BackendTests.setUp
    tearDown = fixtures.BackendTests.tearDown
    annotate = fixtures.BackendTests.annotate
    def test_persistent_view_and_api_pair_pdf_with_profile_and_status(self):
        self.engine.refresh()
        with self.store.db() as db:
            rows = db.execute('SELECT * FROM document_pdf_law_scores').fetchall()
            self.assertEqual({r['law_score_raw'] for r in rows}, {9})  # Fixture metadata explicitly lists 353(2).
            self.assertTrue(all(r['is_case_misuse_score'] == 0 for r in rows))
            identifier = rows[0]['document_id']
            self.assertTrue(rows[0]['pdf_storage_path'].endswith('.pdf'))
        with TestClient(create_app(self.config, scheduler=False, collector=self.engine)) as client:
            result = client.get('/api/documents?section=353').json()
            self.assertEqual(result['total'], 1)
            doc = result['items'][0]
            self.assertIsNone(doc['case_misuse_score'])
            self.assertEqual(doc['laws'][0]['score_display'], '9/12')
            self.assertEqual(doc['laws'][0]['association_status'], 'metadata_only')
            self.assertEqual(client.get('/api/documents/' + identifier).json()['laws'][0]['section'], '353')
            self.assertEqual(client.get(doc['pdf_url']).status_code, 200)

    def test_updated_pdf_and_case_metadata_refresh_links_without_editing_annotations(self):
        self.engine.refresh()
        identifier = self.annotate()
        self.store.save_pdf(identifier, fixtures.pdf_bytes(300), [{'page': 1, 'text': 'Offences under Section 353(2) of the BNS.'}])
        with TestClient(create_app(self.config, scheduler=False, collector=self.engine)) as client:
            self.assertEqual(client.get('/api/documents/' + identifier).json()['laws'][0]['raw_score_range'], [9, 9])
        self.store.case('TEST0', 'Party 0', 'Court', 'newas', ['356'], {'acts': [{'act': 'BNS', 'section': '356(2)'}]})
        with self.store.db() as db:
            links = [json.loads(r[0]) for r in db.execute('SELECT payload FROM document_law_links WHERE document_id=?', (identifier,))]
            self.assertEqual([l['section'] for l in links], ['356'])
            self.assertEqual(links[0]['raw_score_range'], [4, 4])
            self.assertEqual(db.execute('SELECT COUNT(*) FROM annotations').fetchone()[0], 1)


if __name__ == '__main__':
    unittest.main()
