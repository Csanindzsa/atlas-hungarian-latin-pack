import unittest
from variants import latinos_name, apply_variant, apply_variant_to_fields


class VariantTests(unittest.TestCase):
    def test_latin_driven_swap(self):
        self.assertEqual(latinos_name('Oldalsó combcsont körüli ér', ['A. circumflexa femoris lateralis']), 'Laterális combcsont körüli ér')
        self.assertEqual(latinos_name('Belső vaskosizom', ['M. vastus medialis']), 'Mediális vaskosizom')
        self.assertEqual(latinos_name('Háromfejű karizom, belső fej', ['M. triceps brachii, caput mediale']), 'Háromfejű karizom, mediális fej')

    def test_internal_external_never_touched(self):
        self.assertEqual(latinos_name('Belső csípőér', ['A. iliaca interna']), 'Belső csípőér')
        self.assertEqual(latinos_name('Külső fül', ['Auris externa']), 'Külső fül')
        # mixed evidence: medialis AND interna -> unchanged
        self.assertEqual(latinos_name('Belső x', ['A. x medialis', 'V. x interna']), 'Belső x')

    def test_conflicting_or_ambiguous_evidence_unchanged(self):
        self.assertEqual(latinos_name('Oldalsó x', ['A. x lateralis', 'A. x medialis']), 'Oldalsó x')
        self.assertEqual(latinos_name('Oldalsó belső oldalsó', ['lateralis']), 'Oldalsó belső oldalsó')  # two candidates -> skip
        self.assertEqual(latinos_name('Belső boka melletti nyáktömlő', [], 'Calcaneal (of medial malleolus) bursa'), 'Belső boka melletti nyáktömlő')

    def test_english_fallback_only_without_latin(self):
        self.assertEqual(latinos_name('C03 Hátsó ág, oldalsó ág', [], 'C03 Dorsal ramus, lateral branch'), 'C03 Hátsó ág, laterális ág')
        self.assertEqual(latinos_name('Belső fül', [], 'Inner ear'), 'Belső fül')

    def test_article(self):
        self.assertEqual(latinos_name('Az oldalsó félkörös ívjárat csontos ampullája', ['Ampulla ossea lateralis']), 'A laterális félkörös ívjárat csontos ampullája')

    def test_magyar_is_identity_and_fields_follow(self):
        terms = [{'key': 1, 'hu': 'Oldalsó köteg'}]
        same, ch = apply_variant(terms, {1: {'Fasciculus lateralis'}}, 'magyar')
        self.assertEqual((same, ch), (terms, {}))
        new, ch = apply_variant(terms, {1: {'Fasciculus lateralis'}}, 'latinos')
        self.assertEqual(new[0]['hu'], 'Laterális köteg')
        fields, n = apply_variant_to_fields({'a': 'Oldalsó köteg, jobb', 'b': 'Válassza ki: Oldalsó köteg.', 'c': 'Az oldalsó köteg ágai futnak.'}, ch)
        self.assertEqual(fields, {'a': 'Laterális köteg, jobb', 'b': 'Válassza ki: Laterális köteg.', 'c': 'Az oldalsó köteg ágai futnak.'})
        self.assertEqual(n, 2)
        with self.assertRaises(ValueError):
            apply_variant(terms, {}, 'english')

    def test_latin_quiz_prompts(self):
        from variants import latin_quiz_prompt
        lat = [{'M. vastus lateralis'}, {'M. vastus lateralis'}]
        self.assertEqual(latin_quiz_prompt('Select the right or left vastus lateralis.', lat),
                         'Válassza ki a jobb vagy bal oldali képletet: M. vastus lateralis.')
        self.assertEqual(latin_quiz_prompt('Select the left superior lobe.', [{'Lobus superior'}]),
                         'Válassza ki a bal oldali képletet: Lobus superior.')
        # sub-parts collapse to the base name
        self.assertEqual(latin_quiz_prompt('Select any part of the right or left internal carotid artery.',
                                           [{'A. carotis interna'}, {'A. carotis interna, pars cervicalis'}]),
                         'Válassza ki a jobb vagy bal oldali képlet bármely részét: A. carotis interna.')

    def test_latin_quiz_keeps_hungarian_when_information_would_be_lost(self):
        from variants import latin_quiz_prompt
        self.assertIsNone(latin_quiz_prompt('Select the right or left S4 spinal nerve.', [{'N. spinalis'}]))
        self.assertIsNone(latin_quiz_prompt('Select the second rib.', [{'Costa vera'}]))
        self.assertIsNone(latin_quiz_prompt('Select any of the cerebellar arteries.', [{'A. cerebelli superior'}, {'A. cerebelli inferior posterior'}]))
        self.assertIsNone(latin_quiz_prompt('Select any of the lumbricals.', [{'M. lumbricalis'}, set()]))
        self.assertIsNone(latin_quiz_prompt('Select the occipital vein.', [{'V. occipitalis'}], latin_is_exclusive=False))
        self.assertIsNotNone(latin_quiz_prompt('Select one of the ureters.', [{'Ureter'}], latin_is_exclusive=False))

    def test_latin_quiz_variant_keeps_names(self):
        terms = [{'key': 1, 'hu': 'Oldalsó köteg'}]
        same, ch = apply_variant(terms, {1: {'Fasciculus lateralis'}}, 'latinkviz')
        self.assertEqual((same, ch), (terms, {}))

    def test_latin_quiz_whole_bone_with_landmarks(self):
        from variants import apply_latin_quiz
        cat = [{'key': 'k', 'category': 'quiz_prompts', 'en': 'Select the right or left temporal bone.'}]
        latin = {'1': {'Os temporale'}, '2': {'Meatus acusticus internus'}, '3': {'Os temporale'}}
        english = {'1': 'Temporal, L#dummy', '2': 'Internal auditory (acoustic) meatus, L#', '3': 'Temporal bone (cut)#'}
        _, ch = apply_latin_quiz({'k': 'hu'}, cat, {'k': ['1', '2']}, latin, {'1': 10, '2': 11, '3': 12}, english)
        self.assertEqual(ch['k'][1], 'Válassza ki a jobb vagy bal oldali képletet: Os temporale.')
        # a qualifier in parentheses that the Latin would drop keeps the Hungarian prompt
        cat[0]['en'] = 'Select the right or left semispinalis capitis (lateral fascicle).'
        latin = {'1': {'M. semispinalis capitis'}, '3': {'M. semispinalis capitis'}}
        english = {'1': 'Semispinalis capitis (lateral fascicle), L#', '3': 'Semispinalis capitis (medial fascicle), L#'}
        _, ch = apply_latin_quiz({'k': 'hu'}, cat, {'k': ['1']}, latin, {'1': 10, '3': 12}, english)
        self.assertEqual(ch, {})

    def test_numbered_latin(self):
        from variants import numbered_latin
        self.assertEqual(numbered_latin('Select the seventh cervical vertebra.', 'Vertebra cervicalis'), 'Vertebra cervicalis VII')
        self.assertEqual(numbered_latin('Select the 3rd metacarpal.', 'Os metacarpi'), 'Os metacarpi III')
        self.assertEqual(numbered_latin('Select the 1st distal phalanx (pollex).', 'Phalanx distalis'), 'Phalanx distalis digiti I manus')
        self.assertEqual(numbered_latin('Select a second molar.', 'Dens molaris'), 'Dens molaris secundus')
        self.assertIsNone(numbered_latin('Select a third premolar.', 'Dens premolaris'))
        self.assertIsNone(numbered_latin('Select the eighth cervical vertebra.', 'Vertebra cervicalis'))
        self.assertIsNone(numbered_latin('Select the 2nd distal phalanx.', 'Phalanx distalis'))  # hand or foot unknown


if __name__ == '__main__':
    unittest.main()
