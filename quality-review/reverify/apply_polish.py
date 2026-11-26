"""Append root-verified Hungarian polish fixes to corrections/fulltext-approved.json (hash-guarded)."""
import json, re, hashlib
from pathlib import Path

P = Path(__file__).resolve().parents[2]
H = lambda s: hashlib.sha256(s.encode()).hexdigest()
units = {u['unit_id']: u for u in json.loads((P/'fulltext/translation_units.json').read_text())}
cur = {t['unit_id']: t['hu'] for t in json.loads((P/'fulltext/merged/translated-units.json').read_text())}
path = P/'corrections/fulltext-approved.json'
doc = json.loads(path.read_text())
entries = {e['unit_id']: e for e in doc['entries']}

# worker-output baseline (what expected_hu_sha256 guards) for units that have no entry yet
worker = {}
for f in sorted((P/'fulltext/translations').glob('*.json')):
    if any(t in f.name for t in ('notes', 'chunk', 'part', 'check', 'validation', 'evidence', 'sources', 'auto-core')):
        continue
    for t in json.loads(f.read_text()):
        worker.setdefault(t['unit_id'], t['hu'])
for t in json.loads((P/'fulltext/translations/auto-core.json').read_text()) if (P/'fulltext/translations/auto-core.json').exists() else []:
    worker.setdefault(t['unit_id'], t['hu'])

fixes = []  # (uid, old, new, reason)
def plan(uid, old, new, reason):
    fixes.append((uid, old, new, reason))

for uid, hu in cur.items():
    # 1. English-form direction adverbs inside Hungarian prose
    for m in re.finditer(r'medial felől lateral felé|\b(medial|lateral) felé', hu):
        s = m.group(0)
        new = {'medial felől lateral felé': 'medialis felől lateralis irányba', 'medial felé': 'medialis irányba', 'lateral felé': 'lateralis irányba'}[s]
        plan(uid, s, new, 'Hungarian grammar: English adverb form "medial/lateral felé" replaced by "medialis/lateralis irányba"; direction unchanged.')
    # 2. decimal point -> decimal comma in measurements
    for m in re.finditer(r'(?<![\d.])(\d+)\.(\d+)(?!\.)(?=\s*(?:–\d+(?:[.,]\d+)?\s*)?(?:cm|mm|m\b|hüvelyk|liter|l\b|kg|g\b|mérföld|%|láb))', hu):
        plan(uid, m.group(0), m.group(1) + ',' + m.group(2), 'Hungarian number format: decimal comma; value unchanged.')
    if '(.5 hüvelyk)' in hu:
        plan(uid, '(.5 hüvelyk)', '(0,5 hüvelyk)', 'Hungarian number format; value unchanged.')
    # 3. article before "5."
    if re.match(r'Válassza ki a 5\.', hu):
        plan(uid, 'Válassza ki a 5.', 'Válassza ki az 5.', 'Hungarian article: "az" before a vowel-initial numeral (öt).')
    # 4. "legfeljebb" (= at most) misused for "most superior"
    if 'ez helyezkedik el a legfeljebb;' in hu:
        plan(uid, 'ez helyezkedik el a legfeljebb;', 'ez helyezkedik el legfelül;', 'Meaning fix: "legfeljebb" means "at most"; EN "most superior of the lobes" = "legfelül".')

applied = 0
by_uid = {}
for uid, old, new, reason in fixes:
    by_uid.setdefault(uid, []).append((old, new, reason))
for uid, items in by_uid.items():
    hu = cur[uid]
    # make each old unique: widen with context when needed
    reps = []
    tmp = hu
    for old, new, reason in items:
        if tmp.count(old) != 1:
            i = tmp.find(old)
            # widen to a unique window
            for w in range(8, 80, 4):
                cand = tmp[max(0, i - w):i + len(old)]
                if tmp.count(cand) == 1:
                    new = cand[:-len(old)] + new; old = cand; break
            else:
                raise SystemExit('cannot make unique: ' + uid + ' ' + old)
        tmp = tmp.replace(old, new, 1)
        reps.append({'old': old, 'new': new})
    reason = ' '.join(sorted({r for _, _, r in items}))
    if uid in entries:
        entries[uid]['replacements'].extend(reps)
        entries[uid]['reason'] += ' | Root polish pass: ' + reason
    else:
        base = worker.get(uid)
        if base is None or base != hu:
            raise SystemExit('baseline unknown/changed for ' + uid)
        e = {'unit_id': uid, 'approved': True, 'kind': 'root-language-polish', 'source_en_sha256': H(units[uid]['en']),
             'expected_hu_sha256': H(base), 'replacements': reps, 'reason': reason,
             'evidence': [{'path': 'quality-review/reverify/root_checks.py', 'note': 'mechanical hit, root-read in context'}],
             'medical_certification': False}
        doc['entries'].append(e); entries[uid] = e
    applied += len(reps)
doc['revision'] = doc.get('revision', 1) + 1
path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n')
print('units', len(by_uid), 'replacements', applied)
