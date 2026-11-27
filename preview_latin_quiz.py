"""Preview the Latin-quiz prompt rewrite without building assets."""
import json, random, sys
from pathlib import Path
from pack_builder import ROOT, quiz_inputs
from variants import apply_latin_quiz

cat = json.loads((ROOT/'fulltext/source_catalog.json').read_text())
fields = json.loads((ROOT/'fulltext/merged/field-translations.json').read_text())
answers, latin, base, english = quiz_inputs(cat)
new, changed = apply_latin_quiz(fields, cat, answers, latin, base, english)
en = {e['key']: e['en'] for e in cat if e['category'] == 'quiz_prompts'}
print('prompts', len(en), 'latin', len(changed))
for w in sys.argv[1:]:
    for k in [k for k in en if w in en[k].lower()][:2]:
        print(en[k], '=>', new[k])
random.seed(7)
for k in random.sample(sorted(changed), min(15, len(changed))):
    print('  ', en[k], '=>', changed[k][1])
