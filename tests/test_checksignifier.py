import importlib.util, pathlib, unittest
p=pathlib.Path(__file__).resolve().parents[1]/'research'/'checksignifier.py'
spec=importlib.util.spec_from_file_location('checksignifier',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class T(unittest.TestCase):
 def test_urls(self):
  self.assertEqual(len(m.pdf_urls({'documents':[{'url':'https://example.org/a.pdf'},{'pdf_url':'https://example.org/b.pdf'}]})),2)
 def test_three_tiers(self):
  for r in [{},{'currently_detained':'yes'},{'currently_detained':'yes','immediate_safety_risk':'yes'}]:
   self.assertIn(m.assess(r)[0]['Priority Tier'],['Tier 1 - URGENT','Tier 2 - HIGH','Tier 3 - ROUTINE'])
 def test_unknown_not_violation(self):
  r=m.assess({'pdf_url':'https://example.org/a.pdf'})[0]
  self.assertEqual(r['Procedural Signal Score'],0)
  self.assertEqual(r['Counsel Present'],'Unknown')
 def test_override(self):
  r=m.assess({'pdf_url':'https://example.org/a.pdf','evidence':[{'domain':'procedural','element':'counsel_denied','assessment':'alleged_concern','quote':'sample','source_url':'https://example.org/a.pdf','urgent_override':True}]})[0]
  self.assertEqual(r['Priority Tier'],'Tier 1 - URGENT')
if __name__=='__main__':unittest.main()

class ClosureTests(unittest.TestCase):
 def review(self):
  return {'decision':'close_no_further_action','reviewer':'TrialWatch reviewer','reviewed_at':'2026-10-10','rationale':'Documents reviewed; no further action currently warranted','evidence_reference':'https://example.org/review.pdf'}
 def test_valid_human_closure(self):
  row=m.assess({'case_id':'A','human_review':self.review()})[0]
  self.assertEqual(row['Priority Tier'],'Tier 4 - CLOSED')
  self.assertEqual(row['Closure Validation'],'VALID_HUMAN_CLOSURE')
 def test_no_auto_closure(self):
  self.assertEqual(m.assess({})[0]['Priority Tier'],'Tier 3 - ROUTINE')
 def test_missing_review_data_cannot_close(self):
  review=self.review();review.pop('rationale')
  self.assertNotEqual(m.assess({'human_review':review})[0]['Priority Tier'],'Tier 4 - CLOSED')
 def test_detained_cannot_close(self):
  row=m.assess({'currently_detained':'yes','human_review':self.review()})[0]
  self.assertNotEqual(row['Priority Tier'],'Tier 4 - CLOSED')
  self.assertEqual(row['Closure Validation'],'BLOCKED_ACTIVE_DETENTION')
 def test_urgent_flag_cannot_close(self):
  row=m.assess({'human_review':self.review(),'evidence':[{'urgent_override':True} ]})[0]
  self.assertNotEqual(row['Priority Tier'],'Tier 4 - CLOSED')
