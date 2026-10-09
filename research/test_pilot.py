"""Regression checks for identity, evidence provenance, arithmetic and honest outputs."""
import copy
import hashlib
import json
import unittest
from pathlib import Path
from data_access import ROOT, CACHE
from evidence_review import reviews, quote
from law_identity import act_family, has_section, metadata_hits
from law_catalog import LAWS, CRITERIA
from scoring import score, sensitivity, tied_rank_bands

class IdentityTests(unittest.TestCase):
    def test_letter_variants_and_boundaries(self):
        for text in ['153-A','153 A','153(A)','153 (A)','153A, 505(1)(b)']:
            self.assertTrue(has_section(text,'153A'),text)
        for text in ['153AA','1153A','153B']:
            self.assertFalse(has_section(text,'153A'),text)
        self.assertTrue(has_section('505(1)(b) r/w 34','505'))
        for text in ['67A','67B','67(b)','67 (B)','167']:
            self.assertFalse(has_section(text,'67'),text)
        self.assertTrue(has_section('67, 66E','67'))

    def test_act_bound_sections(self):
        self.assertEqual(act_family('Bharatiya Nagarik Suraksha Sanhita (BNSS)'),None)
        self.assertEqual(act_family('Criminal Procedure Code (Cr.PC)'),None)
        self.assertEqual(act_family('Indian Penal Code (I.P.C)'), 'IPC')
        self.assertEqual(act_family('The Unlawful Activities(Prevention) Act'),'UAPA')
        self.assertEqual(metadata_hits([{'act':'Criminal Procedure Code','section':'152, 196, 221'}]),[])
        self.assertEqual(metadata_hits([{'act':'Indian Penal Code','section':'153-A,505(2)'},
                                        {'act':'Information Technology Act','section':'67(b)'}]),['IPC:153A','IPC:505'])
        self.assertIsNone(act_family('Indian Penal Code and Bharatiya Nyaya Sanhita'))

class ScoreTests(unittest.TestCase):
    def test_arithmetic_unknown_and_bad_weights(self):
        self.assertEqual(score([0]*6),0)
        self.assertEqual(score([2]*6),100)
        self.assertEqual(score([1]*6),50)
        self.assertIsNone(score([2,2,None,2,2,2]))
        with self.assertRaises(ValueError):score([3])
        with self.assertRaises(ValueError):score([1],[0])
        with self.assertRaises(ValueError):score([1],[float('nan')])
        with self.assertRaises(ValueError):score([1,2],[1])

    def test_rank_ties_and_reproducible_sensitivity(self):
        self.assertEqual(tied_rank_bands([90,90,50]),[(1,2),(1,2),(3,3)])
        a=sensitivity([[2,1,0],[0,1,2]],runs=100,seed=7)
        self.assertEqual(a,sensitivity([[2,1,0],[0,1,2]],runs=100,seed=7))
        for r in a:self.assertEqual(len(r['leave_one_criterion_out']),3)

class EvidenceTests(unittest.TestCase):
    def test_all_curated_spans_verified_and_missing_not_distance(self):
        rev,matrices=reviews()
        self.assertGreaterEqual(len(rev),12)
        for m in matrices:
            self.assertIsNone(m['ccd_numeric'])
            for e in m['elements']:
                if e['state']=='not assessed in this pilot':self.assertIsNone(e['evidence'])
        d=json.loads((CACHE/'hc_documents.json').read_text())[0]
        with self.assertRaises(ValueError):quote(d,1,'THIS TEXT IS NOT IN THE JUDGMENT')

    def test_bail_target_and_act_conflict_are_separate(self):
        rev,_=reviews();byid={e['id']:e for e in rev}
        self.assertEqual(byid['hc-act-conflict']['excluded_metadata_hits'],['BNS:152','BNS:353'])
        self.assertEqual(byid['hc-farah-deeba']['case_family_key'],byid['hc-linked-bail-proceeding']['case_family_key'])
        self.assertIn('FIR/prosecution was not quashed',byid['hc-bail-not-fir-quashing']['summary'])

class ArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result=json.loads((ROOT/'outputs/law-scores.json').read_text())
        cls.frame=json.loads((CACHE/'hc_sampling_frame.json').read_text())

    def test_output_scores_and_no_invented_outcome_rates(self):
        rows=self.result['laws'];self.assertEqual(len(rows),19)
        for row in rows:
            if row['era']=='Invalid':
                self.assertIsNone(row['score_100']);continue
            p=[row['components'][c['id']]['rating'] for c in CRITERIA]
            self.assertEqual(row['raw_total'],sum(p))
            self.assertEqual(row['score_100'],round(score(p)))
            self.assertIsNone(row['historical_panel']['rate_of_abuse'])
            self.assertIsNone(row['historical_panel']['quashing_rate'])
            for scenario in row.get('alternative_scenarios',[]):
                self.assertEqual(scenario['raw_total'],sum(scenario['profile']))
                self.assertEqual(scenario['score_100'],round(score(scenario['profile'])))

    def test_union_denominator_and_shared_parent(self):
        rows={r['id']:r for r in self.result['laws']}
        union=sum(bool({'IPC:499','IPC:500'}.intersection(r['law_hits'])) for r in self.frame)
        self.assertEqual(rows['IPC-499-500']['historical_panel']['metadata_cnr_count'],union)
        self.assertEqual(rows['IPC-505-1']['historical_panel']['metadata_cnr_count'],
                         rows['IPC-505-2']['historical_panel']['metadata_cnr_count'])
        self.assertEqual(len(self.frame),len({r['cnr'] for r in self.frame}))
        for r in self.frame:self.assertEqual(r['law_hits'],metadata_hits(r.get('acts')))

    def test_cached_source_hashes(self):
        manifest=json.loads((ROOT/'outputs/source-manifest.json').read_text())
        checked=0
        for r in manifest.values():
            if 'sha256' not in r:continue
            p=ROOT/r['path'];self.assertTrue(p.exists(),str(p))
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),r['sha256'])
            checked+=1
        self.assertGreater(checked,50)

if __name__=='__main__':unittest.main()
