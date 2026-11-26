"""Terminology variants. 'magyar' = house style (oldalsó/belső/külső). 'latinos' = laterális/mediális where native Latin says lateralis/medialis.

Both are accepted by the course; the user picks one at install time. Only the direction adjective changes;
structure identity, IDs and Latin are untouched. The change is Latin-driven: a Hungarian word is replaced only
when every native Latin name of that structure carries the matching Latin adjective and no conflicting one
(e.g. "belső" for internus is never touched).
"""
import re

VARIANTS = ('magyar', 'latinos')
LAT = re.compile(r'\blateral(?:is|e|es|ia)\b', re.I)
MED = re.compile(r'\bmedial(?:is|e|es|ia)\b', re.I)
INT = re.compile(r'\b(?:intern(?:us|a|um|i|ae)|extern(?:us|a|um|i|ae))\b', re.I)
# Hungarian direction adjectives (standalone words only, any case) -> latinos form
HU_LAT = re.compile(r'\b(Oldalsó|oldalsó|Külső|külső)\b(?! ?boka)')
HU_MED = re.compile(r'\b(Belső|belső)\b(?! ?boka)')


def _swap(word, target):
    return target.capitalize() if word[0].isupper() else target


EN_LAT = re.compile(r'\blateral\b', re.I)
EN_MED = re.compile(r'\bmedial\b', re.I)
EN_INT = re.compile(r'\b(?:internal|external|inner|outer)\b', re.I)


def latinos_name(hu, latin_names, english=''):
    """Return the laterális/mediális form of a core name, or hu unchanged when evidence is not unanimous.

    Native Latin decides; the English name is used only when the structure has no native Latin at all.
    """
    names = [n for n in latin_names if n]
    if not names and english:
        # map English to pseudo-Latin evidence
        if EN_INT.search(english):
            return hu
        names = [('lateralis ' if EN_LAT.search(english) else '') + ('medialis' if EN_MED.search(english) else '')]
        if not names[0].strip():
            return hu
    if not names or any(INT.search(n) for n in names):
        return hu
    out = hu
    if all(LAT.search(n) for n in names) and not any(MED.search(n) for n in names):
        hits = HU_LAT.findall(out)
        if len(hits) == 1:
            out = HU_LAT.sub(lambda m: _swap(m.group(1), 'laterális'), out, count=1)
    if all(MED.search(n) for n in names) and not any(LAT.search(n) for n in names):
        hits = HU_MED.findall(out)
        if len(hits) == 1:
            out = HU_MED.sub(lambda m: _swap(m.group(1), 'mediális'), out, count=1)
    # Hungarian article: "az" only before a vowel; laterális/mediális start with a consonant
    out = re.sub(r'\b(A|a)z (laterális|mediális)\b', r'\1 \2', out)
    return out


def apply_variant(terms, latin_by_key, variant, english_by_key=None):
    """terms: [{'key','hu'}]; returns (new_terms, {key: (old, new)})."""
    if variant not in VARIANTS:
        raise ValueError('Unknown variant ' + str(variant))
    if variant == 'magyar':
        return [dict(t) for t in terms], {}
    out, changed = [], {}
    for t in terms:
        new = latinos_name(t['hu'], sorted(latin_by_key.get(t['key'], ())), (english_by_key or {}).get(t['key'], ''))
        if new != t['hu']:
            changed[t['key']] = (t['hu'], new)
        out.append({**t, 'hu': new})
    return out, changed


def apply_variant_to_fields(fields, changed):
    """Carry core-name variant changes into catalog label fields that repeat a core name verbatim."""
    if not changed:
        return dict(fields), 0
    pairs = sorted(((old, new) for old, new in changed.values()), key=lambda p: -len(p[0]))
    out, n = {}, 0
    for key, value in fields.items():
        new_value = value
        for old, new in pairs:
            if value == old or value == old + '.':
                new_value = new + value[len(old):]
            elif value.startswith(old + ', ') or value.startswith(old + ' ('):
                new_value = new + value[len(old):]
            elif value.endswith(': ' + old + '.'):
                new_value = value[:-len(old) - 1] + new + '.'
            if new_value != value:
                break
        if new_value != value:
            n += 1
        out[key] = new_value
    return out, n
