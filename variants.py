"""Terminology variants. 'magyar' = house style (oldalsó/belső/külső). 'latinos' = laterális/mediális where native Latin says lateralis/medialis.

Both are accepted by the course; the user picks one at install time. Only the direction adjective changes;
structure identity, IDs and Latin are untouched. The change is Latin-driven: a Hungarian word is replaced only
when every native Latin name of that structure carries the matching Latin adjective and no conflicting one
(e.g. "belső" for internus is never touched).
"""
import re

VARIANTS = ('magyar', 'latinos', 'latinkviz')
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
    if variant in ('magyar', 'latinkviz'):  # latinkviz keeps the magyar names; only quiz prompts change
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


# --- Latin quiz variant -------------------------------------------------------------------------
# Quiz questions are "<prompt> + correct structure IDs". For the Latin-practice variant the prompt
# names the structure by its native Latin name (from the app's own Latin layer for the answer IDs).
# Fixed Hungarian frames + "colon + Latin" avoid inflecting Latin words. If the answers do not map
# to exactly one Latin name (or one name plus its own sub-parts), the Hungarian prompt is kept.
_FRAMES = [
    (r'^Selec?t? the right or left .*, or any of its branches\.?$', 'Válassza ki a jobb vagy bal oldali képletet vagy annak bármely ágát: {L}.'),
    (r'^Selec?t? any part of the right or left ', 'Válassza ki a jobb vagy bal oldali képlet bármely részét: {L}.'),
    (r'^Selec?t? any branch of the right or left ', 'Válassza ki a jobb vagy bal oldali képlet bármely ágát: {L}.'),
    (r'^Selec?t? the right or left ', 'Válassza ki a jobb vagy bal oldali képletet: {L}.'),
    (r'^Selec?t? any (part|region|lobe|leaflet|cusp) of (the|a|an) ', 'Válassza ki a következő képlet bármely részét: {L}.'),
    (r'^Selec?t? (one of the|any of the|any of|an?|any) ', 'Válassza ki a következő képletek egyikét: {L}.'),
    (r'^Selec?t? the ', 'Válassza ki a következő képletet: {L}.'),
]


def single_latin(names):
    """One Latin name, or a base name whose other names are its own parts ('A. x' + 'A. x, r. y')."""
    names = sorted({n.strip() for n in names if n and n.strip()})
    if len(names) == 1:
        return names[0]
    if names:
        base = min(names, key=len)
        if all(n == base or n.startswith(base + ',') for n in names):
            return base
    return None


_ORDINAL = re.compile(r'\b(\d+(st|nd|rd|th)?|[CTLS]\d+|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth)\b', re.I)
_GROUP = re.compile(r'^Selec?t? (one of the|any of the|any of|an?|any) ', re.I)


def latin_quiz_prompt(english_prompt, answer_latin_sets, latin_is_exclusive=True):
    """answer_latin_sets: one set of native Latin names per answer ID. Returns the new prompt or None.

    Returns None (keep the Hungarian prompt) whenever the Latin name would lose information:
    level numbers / ordinals the Latin does not carry, or a Latin name that other, non-answer
    structures also use (latin_is_exclusive=False) in a question about one specific structure.
    """
    if not answer_latin_sets or any(not s for s in answer_latin_sets):
        return None
    if re.search(r'\bany structure of\b', english_prompt, re.I):
        return None
    name = single_latin(set().union(*answer_latin_sets))
    if not name:
        return None
    if _ORDINAL.search(english_prompt) and not re.search(r'\d|\b[IVX]+\b', name):
        return None
    if not latin_is_exclusive and not _GROUP.match(english_prompt.strip()):
        return None
    text = english_prompt.strip()
    side = re.search(r'\b(right|left)\b(?! or)', text, re.I)
    if side and not re.search(r'\bright or left\b', text, re.I):
        hu_side = 'jobb' if side.group(1).lower() == 'right' else 'bal'
        return 'Válassza ki a ' + hu_side + ' oldali képletet: ' + name + '.'
    for pattern, frame in _FRAMES:
        if re.match(pattern, text, re.I):
            return frame.format(L=name)
    return None


def apply_latin_quiz(fields, catalog, answers_by_key, latin_by_structure_id, base_by_structure_id=None):
    """fields: key->hu. catalog: source_catalog entries. answers_by_key: field key -> [structure IDs].
    base_by_structure_id: structure ID -> canonical name key, used to detect Latin names shared with
    structures outside the answer set."""
    users = {}
    for sid, names in latin_by_structure_id.items():
        for n in names:
            users.setdefault(n, set()).add((base_by_structure_id or {}).get(sid, sid))
    out, changed = dict(fields), {}
    for e in catalog:
        if e['category'] != 'quiz_prompts':
            continue
        ids = answers_by_key.get(e['key'], [])
        sets = [set(latin_by_structure_id.get(i, ())) for i in ids]
        name = single_latin(set().union(*sets)) if sets and all(sets) else None
        answer_bases = {(base_by_structure_id or {}).get(i, i) for i in ids}
        exclusive = bool(name) and users.get(name, set()) <= answer_bases
        new = latin_quiz_prompt(e['en'], sets, exclusive)
        if new:
            changed[e['key']] = (out[e['key']], new)
            out[e['key']] = new
    return out, changed
