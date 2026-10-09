"""Checks for provenance, unknown preservation and family/text leakage controls."""
import csv, hashlib, json, unittest
from pathlib import Path
from data_access import ROOT

OUT = ROOT / 'outputs' / 'bns-training-starter'

class BnsCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs = [json.loads(x) for x in (OUT / 'documents.jsonl').read_text().splitlines()]
        cls.cases = json.loads((OUT / 'case-candidates.json').read_text())
        cls.reviews = json.loads((OUT / 'review-seeds.json').read_text())
        cls.byid = {d['document_id']: d for d in cls.docs}
        cls.bycnr = {c['cnr']: c for c in cls.cases}

    def test_collection_identity_and_scope(self):
        self.assertEqual(len(self.docs), 177)
        self.assertEqual(len(self.bycnr), 107)
        self.assertEqual(len(self.byid), 177)
        self.assertEqual(sum(len(d['pages']) for d in self.docs), 500)
        self.assertEqual(len({d['pdf_sha256'] for d in self.docs}), 174)
        self.assertTrue(all(d['court'] == 'Bombay High Court' for d in self.docs))
        self.assertTrue(all('2024-01-01' <= d['decision_date'] <= '2025-12-31' for d in self.docs))

    def test_quotes_and_hashes(self):
        for r in self.reviews:
            d, e = self.byid[r['document_id']], r['evidence']
            p = next(p for p in d['pages'] if p['page'] == e['page'])
            self.assertEqual(p['text'][e['raw_char_start']:e['raw_char_end']], e['quote'])
            import re
            self.assertEqual(p['normalized_text'][e['normalized_char_start']:e['normalized_char_end']], re.sub(r'\s+', ' ', e['quote']).strip())
            self.assertEqual(e['pdf_sha256'], d['pdf_sha256'])
            self.assertEqual(e['source_url'], d['source_url'])
        manifest = json.loads((OUT / 'acquisition-manifest.json').read_text())
        for d in manifest:
            self.assertEqual(hashlib.sha256((ROOT / d['pdf_path']).read_bytes()).hexdigest(), d['pdf_sha256'])

    def test_no_invented_gold_or_splits(self):
        for d in self.docs:
            self.assertFalse(d['metadata_is_label'])
            self.assertEqual(d['split'], 'unassigned')
            self.assertTrue(all(v is None for v in d['human_labels'].values()))
        for c in self.cases:
            self.assertIsNone(c['human_abuse_label'])
            self.assertIsNone(c['human_law_role_label'])
            self.assertEqual(c['journalist_status'], 'unknown')

    def test_known_families_and_duplicate_text_share_groups(self):
        families = [
            ['HCBM010319502025', 'HCBM010375472025'],
            ['HCBM010286912025', 'HCBM010287052025'],
            ['HCBM010555262024', 'HCBM010555272024'],
            ['HCBM010558742025', 'HCBM010558762025'],
        ]
        for family in families:
            self.assertEqual(len({self.bycnr[c]['leakage_group_id'] for c in family}), 1)
        for field in ['pdf_sha256', 'normalized_text_sha256']:
            byhash = {}
            for d in self.docs:
                byhash.setdefault(d[field], set()).add(d['leakage_group_id'])
            self.assertTrue(all(len(groups) == 1 for groups in byhash.values()))

    def test_metadata_conflict_and_bns_bnss_distinction(self):
        c = self.bycnr['HCBM010407652025']
        self.assertEqual(c['review_status'], 'IPC/BNS metadata conflict')
        self.assertEqual(c['text_confirmed_bns_targets'], '')
        self.assertEqual(self.bycnr['HCBM010075992025']['text_confirmed_bns_targets'], '')
        self.assertEqual(self.bycnr['HCBM010409232025']['text_confirmed_bns_targets'], '356(1); 356(2); 356(3)')
        self.assertFalse(any('BNSS' in c['text_confirmed_bns_targets'] for c in self.cases))

    def test_csv_round_trip_preserves_blank_labels(self):
        for stem, size in [('case-candidates', 107), ('annotation-template', 16)]:
            with (OUT / (stem + '.csv')).open(encoding='utf-8-sig', newline='') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            self.assertEqual(len(rows), size)
            self.assertTrue(all(None not in r for r in rows))
            for r in rows:
                for key, value in r.items():
                    if key.startswith('human_'): self.assertEqual(value, '')
            with (OUT / (stem + '.csv')).open(encoding='utf-8-sig', newline='') as f:
                matrix = list(csv.reader(f))
            self.assertTrue(all(len(r) == len(matrix[0]) for r in matrix))

if __name__ == '__main__': unittest.main()
