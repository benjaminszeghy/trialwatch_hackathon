import unittest
from scraper.jiwon_scraper import detect_laws, load_scores

class LawDetectionTests(unittest.TestCase):
    def test_specific_subsections(self):
        self.assertEqual(set(detect_laws('Section 353(2) of the BNS')), {'BNS-353-2'})
    def test_no_parent_353_guess(self):
        self.assertEqual(detect_laws('BNS section 353'), {})
    def test_66a_flag(self):
        self.assertIn('IT-66A', detect_laws('Section 66A of the IT Act'))
        self.assertEqual(load_scores()['IT-66A']['score'], '')
    def test_no_unrelated_section(self):
        self.assertEqual(detect_laws('Section 152 of the Civil Procedure Code'), {})

if __name__ == '__main__':
    unittest.main()
