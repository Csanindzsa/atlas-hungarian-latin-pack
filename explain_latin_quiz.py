"""Explain, for quiz prompts matching a word, why the Latin rewrite was or was not applied."""
import json, re, sys
from pack_builder import ROOT, quiz_inputs
from variants import single_latin, latin_quiz_prompt, apply_latin_quiz

cat = json.loads((ROOT/'fulltext/source_catalog.json').read_text())
fields = json.loads((ROOT/'fulltext/merged/field-translations.json').read_text())
answers, latin, base, english = quiz_inputs(cat)
users = {}
for sid, names in latin.items():
    for n in names:
        users.setdefault(n, set()).add(base.get(sid, sid))
pat = re.compile(sys.argv[1], re.I)
for e in cat:
    if e['category'] != 'quiz_prompts' or not pat.search(e['en']):
        continue
    ids = answers.get(e['key'], [])
    sets = [set(latin.get(i, ())) for i in ids]
    name = single_latin(set().union(*sets)) if sets and all(sets) else None
    bases = {base.get(i, i) for i in ids}
    excl = bool(name) and users.get(name, set()) <= bases
    new = apply_latin_quiz({e['key']: fields[e['key']]}, [e], answers, latin, base, english)[1].get(e['key'], (0, None))[1]
    print('\n' + e['key'][-40:], '|', e['path_id'], '|', e['en'])
    print('   ->', new or ('KEPT: ' + fields[e['key']]))
    if not new:
        print('   ids', ids[:6], 'latin', [sorted(s) for s in sets][:6])
        print('   name', name, 'exclusive', excl, 'other users', sorted(users.get(name, set()) - bases)[:5] if name else '')
