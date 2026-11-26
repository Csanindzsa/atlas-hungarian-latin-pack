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


if __name__ == '__main__':
    unittest.main()
