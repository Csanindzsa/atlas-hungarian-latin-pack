import unittest
from build_release import make_manifest, check_policy

AV = {'ui_rows': 3, 'structure_rows': 7, 'additional_text_fields': 42}
COV = {'complete_text_coverage': True, 'translated_fields': 42, 'total_fields': 42}
HARD = {g: True for g in ('full_text_inventory_completed', 'all_inventoried_text_translated', 'terminology_corrections_resolved',
                          'runtime_language_search_latin_verified', 'final_code_review_ship')}


class ManifestTests(unittest.TestCase):
    def test_scope_includes_catalog_and_does_not_claim_media(self):
        m = make_manifest({'magyar': [], 'latinos': []}, {'magyar': AV, 'latinos': AV}, COV)
        self.assertEqual(m['schema'], 2)
        self.assertEqual(set(m['variants']), {'magyar', 'latinos'})
        self.assertIn('42 additional catalog text fields', m['translated_scope'])
        self.assertTrue(m['first_pass_text_catalog_complete'])
        self.assertTrue(m['unverified_boundaries'])
        self.assertIn('not medically certified', m['status'])
        self.assertFalse(m['preferences_modified'])

    def test_core_only_or_incomplete_catalog_cannot_be_manifested(self):
        self.assertRaises(ValueError, make_manifest, {'magyar': []}, {'magyar': {'ui_rows': 3, 'structure_rows': 7}}, COV)
        self.assertRaises(ValueError, make_manifest, {'magyar': []}, {'magyar': AV}, dict(COV, complete_text_coverage=False))

    def test_policy_requires_hard_gates_and_explicit_waiver(self):
        with self.assertRaises(SystemExit):
            check_policy({'release_allowed': True, 'required_gates': HARD})  # qualified review neither done nor waived
        with self.assertRaises(SystemExit):
            check_policy({'release_allowed': True, 'required_gates': dict(HARD, final_code_review_ship=False),
                          'waivers': {'qualified_medical_review_completed': {'waived_by': 'owner'}}})
        check_policy({'release_allowed': True, 'required_gates': HARD,
                      'waivers': {'qualified_medical_review_completed': {'waived_by': 'owner'}}})
        m = make_manifest({'magyar': []}, {'magyar': AV}, COV, {'waivers': {'qualified_medical_review_completed': {'waived_by': 'owner'}}})
        self.assertIn('waived by project owner: qualified_medical_review_completed', m['status'])


if __name__ == '__main__':
    unittest.main()
