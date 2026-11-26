"""Assemble an installable pack folder for runtime testing (no ZIP, no release-gate bypass of the ZIP builder).

Uses the already-built variant deltas in build/variants/* and the managed patch in build/.
"""
import json, shutil
from pathlib import Path
from pack_builder import ROOT, hashfile, matching_ranges, make_delta, apply_delta
from build_release import make_manifest, VARIANT_LABELS

build = ROOT/'build'; out = build/'stage-pack'
shutil.rmtree(out, ignore_errors=True); out.mkdir()
source = ROOT.parent/'originals/Assembly-UnityScript.dll'; target = build/'Assembly-UnityScript.dll'
ops, data = make_delta(source, target, matching_ranges(source, target))
(out/'managed.literals').write_bytes(data)
managed = {'path': 'Human Anatomy Atlas_Data/Managed/Assembly-UnityScript.dll', 'source_sha256': hashfile(source), 'target_sha256': hashfile(target),
           'source_size': source.stat().st_size, 'target_size': target.stat().st_size, 'operations': ops, 'literal_file': 'managed.literals',
           'literal_sha256': hashfile(out/'managed.literals')}
apply_delta(source, build/'reconstructed.dll', managed, data); (build/'reconstructed.dll').unlink()
variants, avs = {}, {}
for v in VARIANT_LABELS:
    vdir = build/'variants'/v
    av = json.loads((vdir/'asset-verification.json').read_text())
    shutil.copy2(vdir/av['entry']['literal_file'], out/av['entry']['literal_file'])
    entry = dict(av['entry']); entry['literal_sha256'] = hashfile(out/entry['literal_file'])
    variants[v] = [entry, managed]; avs[v] = av
coverage = json.loads((build/'variants'/'magyar'/'fulltext-coverage.json').read_text())
(out/'manifest.json').write_text(json.dumps(make_manifest(variants, avs, coverage), ensure_ascii=False, indent=2), encoding='utf-8')
for name in ('Install-Pack.ps1', 'Install.cmd', 'Restore.cmd', 'README.hu.md'):
    shutil.copy2(ROOT/name, out/name)
print(json.dumps({'stage': str(out), 'files': sorted(p.name for p in out.iterdir()),
                  'targets': {v: variants[v][0]['target_sha256'] for v in variants}, 'managed': managed['target_sha256']}, indent=1))
