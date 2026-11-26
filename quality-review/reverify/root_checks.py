"""Root-side mechanical defect hunt over every full-text unit (EN vs current HU).

Each check is a cheap signal; hits are triaged by hand in root-triage.json.
"""
import json, re, collections
from pathlib import Path

P = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
units = {u['unit_id']: u for u in json.loads((P/'fulltext/translation_units.json').read_text())}
cur = {t['unit_id']: t['hu'] for t in json.loads((P/'fulltext/merged/translated-units.json').read_text())}

# (english regex, hungarian regex) pairs: if EN count > HU count, the concept may be dropped or inverted.
PAIRS = {
    'superior': (r'\bsuperior(ly)?\b|\bupper\b|\babove\b', r'felső|felett|fölött|felfelé|feljebb|superior|cranial|kraniális|felül'),
    'inferior': (r'\binferior(ly)?\b|\blower\b|\bbelow\b', r'alsó|alatt|lefelé|lejjebb|inferior|caudal|kaudális|alul'),
    'anterior': (r'\banterior(ly)?\b|\bfront\b|\bventral\b', r'elülső|elől|előre|elé|előtt|anterior|ventrális|ventralis|hasi|mellső'),
    'posterior': (r'\bposterior(ly)?\b|\bback of\b|\bbehind\b|\bdorsal\b', r'hátsó|hátul|hátra|mögött|mögé|posterior|dorzális|dorsalis|háti|hát'),
    'medial': (r'\bmedial(ly)?\b', r'belső|mediális|medialis|középvonal|befelé|közép'),
    'lateral': (r'\blateral(ly)?\b', r'oldalsó|külső|laterális|lateralis|oldal|kifelé'),
    'left': (r'\bleft\b', r'\bbal\b|bal |balra|baloldal|bal-'),
    'right': (r'\bright\b', r'jobb'),
    'proximal': (r'\bproximal(ly)?\b', r'proximális|proximalis|közelebbi|törzshöz közel|kezdeti|közeli'),
    'distal': (r'\bdistal(ly)?\b', r'disztális|distalis|távolabbi|távoli|vég'),
    'deep': (r'\bdeep\b', r'mély'),
    'superficial': (r'\bsuperficial\b', r'felületes|felszíni|felszínes'),
    'artery': (r'\barter(y|ies|ial)\b', r'artéri|verőér|arteri|ütőér|\bér\b|erek|aorta'),
    'vein': (r'\bvein|venous\b|\bvenae?\b', r'vén|visszér|gyűjtőér|vena|venae|\bér\b|erek'),
    'nerve': (r'\bnerves?\b|\bnervous\b', r'ideg|nervus|nervi|beidegz'),
    'flex': (r'\bflex(ion|es|ing|or|ors)?\b', r'hajlít|hajlító|flexi|flexor|behajlít'),
    'extend': (r'\bextend(s|ing)?\b|\bextension\b|\bextensors?\b', r'feszít|nyújt|extenzi|extensor'),
    'abduct': (r'\babduct(s|ion|ing|or|ors)?\b', r'távolít|abdukci|abductor|távolító'),
    'adduct': (r'\badduct(s|ion|ing|or|ors)?\b', r'közelít|addukci|adductor|közelítő'),
    'pronat': (r'\bpronat(e|es|ion|ing|or)\b', r'borint|pronáci|pronator|befelé forgat'),
    'supinat': (r'\bsupinat(e|es|ion|ing|or)\b', r'kifelé forgat|szupináci|supinator|kiforgat|szupinál'),
    'elevat': (r'\belevat(e|es|ion|ing|or)\b', r'emel|eleváci'),
    'depress': (r'\bdepress(es|ion|ing|or)?\b', r'süllyeszt|lesüllyeszt|lefelé|depresszi|depressor|nyom'),
    'rotate': (r'\brotat(e|es|ion|ing|or|ors)\b', r'forgat|forgás|rotáci|rotator|fordít'),
    'not': (r"\bnot\b|\bno\b|\bnever\b|\bwithout\b|n't\b|\bnone\b|\bneither\b|\bnor\b|\bcannot\b", r'\bnem\b|\bnincs|\bsem\b|nélkül|\bsoha|\bne\b|hiány|képtelen|\bnélkül'),
}
EN_STOP = set('''the and of to in is are with for from by on at as or that this which be its it into these those their they than was were has have can may also
when where while most more such other each both only between through during after before about over under within without upon'''.split())

def nums(s):
    return sorted(re.findall(r'\d+(?:[.,]\d+)?', s.replace('\u2009', '')))

def count(rx, s):
    return len(re.findall(rx, s, re.I))

findings = []
for uid, u in units.items():
    en, hu = u['en'], cur[uid]
    f = []
    # numbers (normalize decimal comma)
    ne = [x.replace(',', '.') for x in nums(en)]; nh = [x.replace(',', '.') for x in nums(hu)]
    if collections.Counter(ne) != collections.Counter(nh):
        f.append(('numbers', ne, nh))
    for name, (ren, rhu) in PAIRS.items():
        ce, ch = count(ren, en), count(rhu, hu)
        if ce and ch == 0:
            f.append(('missing-' + name, ce, ch))
    # opposite-pair inversions: EN has only A, HU has only B
    for a, b in (('superior', 'inferior'), ('anterior', 'posterior'), ('medial', 'lateral'), ('left', 'right'),
                 ('flex', 'extend'), ('abduct', 'adduct'), ('pronat', 'supinat'), ('elevat', 'depress'), ('deep', 'superficial'),
                 ('proximal', 'distal')):
        ea, eb = count(PAIRS[a][0], en), count(PAIRS[b][0], en)
        ha, hb = count(PAIRS[a][1], hu), count(PAIRS[b][1], hu)
        if ea and not eb and hb and not ha:
            f.append(('INVERSION ' + a + '->' + b, ea, hb))
    # untranslated English: runs of 3+ English stopword-y words
    words = re.findall(r"[A-Za-z']+", hu)
    eng = [w for w in words if w.lower() in EN_STOP and w.lower() not in ('a', 'is', 'be', 'on', 'at', 'in')]
    if len(eng) >= 2:
        f.append(('english-residue', eng[:8], None))
    # length ratio (omission/addition)
    le, lh = len(en.split()), len(hu.split())
    if le >= 12 and (lh / le < 0.55 or lh / le > 1.6):
        f.append(('length-ratio', le, lh))
    # line structure
    if en.count('\n') != hu.count('\n'):
        f.append(('newline-count', en.count('\n'), hu.count('\n')))
    if f:
        findings.append({'unit_id': uid, 'group': u['group'], 'flags': [list(x) for x in f]})

c = collections.Counter(fl[0].split()[0] if fl[0].startswith('INVERSION') else fl[0] for x in findings for fl in x['flags'])
(OUT/'root-checks.json').write_text(json.dumps({'counts': dict(c), 'units_flagged': len(findings), 'findings': findings}, ensure_ascii=False, indent=1))
print(len(units), 'units;', len(findings), 'flagged'); print(json.dumps(dict(c.most_common()), indent=0))
