"""Create the translation-only delta ZIP (two terminology variants), with no Atlas application distribution."""
from pathlib import Path
import json, subprocess, sys, zipfile
from pack_builder import ROOT, build_assets, hashfile, matching_ranges, make_delta, apply_delta

PACKAGE_ID = 'Atlas-Hungarian-Latin-7.4.01-v1.0'
VARIANT_LABELS = {'magyar': 'magyaros nevek (oldalsó / belső)', 'latinos': 'latinos nevek (laterális / mediális)',
                  'latinkviz': 'magyaros nevek, kvízkérdések latin névvel'}
HARD_GATES = ('full_text_inventory_completed', 'all_inventoried_text_translated', 'terminology_corrections_resolved',
              'runtime_language_search_latin_verified', 'final_code_review_ship')
SOFT_GATES = ('qualified_medical_review_completed',)


def make_manifest(variants, avs, coverage, policy=None):
    for v, av in avs.items():
        fields = av.get('additional_text_fields', 0)
        if fields <= 0 or coverage.get('complete_text_coverage') is not True or fields != coverage.get('translated_fields') or fields != coverage.get('total_fields'):
            raise ValueError('Cannot package a core-only or incomplete full-text catalog')
    av = next(iter(avs.values()))
    waived = sorted(((policy or {}).get('waivers') or {}).keys())
    return {'schema': 2, 'id': PACKAGE_ID, 'app_version': '7.4.01',
            'status': 'community translation; not medically certified' + ('; waived by project owner: ' + ', '.join(waived) if waived else ''),
            'language_slot': 'en', 'latin': 'original Latin terminology/resources preserved',
            'translated_scope': [str(av['ui_rows']) + ' ordered UI rows', str(av['structure_rows']) + ' anatomical name rows',
                                 str(av['additional_text_fields']) + ' additional catalog text fields', '4 hardcoded UI literals'],
            'first_pass_text_catalog_complete': True,
            'unverified_boundaries': ['serialized UI default strings that the app overwrites at runtime are left as shipped',
                                      'image-embedded store/branding text, audio pronunciations and videos are not translated'],
            'preferences_modified': False,
            'variants': {v: {'label': VARIANT_LABELS[v], 'files': files} for v, files in variants.items()}}


def check_policy(policy):
    gates = policy.get('required_gates', {})
    waivers = policy.get('waivers') or {}
    missing = [g for g in HARD_GATES if gates.get(g) is not True]
    soft = [g for g in SOFT_GATES if gates.get(g) is not True and not (waivers.get(g) or {}).get('waived_by')]
    if policy.get('release_allowed') is not True or missing or soft:
        raise SystemExit('RELEASE HELD: gates not satisfied: ' + ', '.join(missing + soft))


def main():
    policy_path = ROOT/'release-policy.json'
    if not policy_path.is_file():
        raise SystemExit('RELEASE HELD: release-policy.json is required.')
    policy = json.loads(policy_path.read_text(encoding='utf-8'))
    check_policy(policy)
    subprocess.run([sys.executable, '-m', 'unittest', '-v', 'test_pack', 'test_fulltext', 'test_collect_fulltext', 'test_manifest', 'test_variants'], cwd=ROOT, check=True)
    build = ROOT/'build'; dist = ROOT/'dist'; dist.mkdir(exist_ok=True)
    source = ROOT.parent/'originals/Assembly-UnityScript.dll'
    target = build/'Assembly-UnityScript.dll'
    subprocess.run(['dotnet', 'run', '--project', str(ROOT/'ManagedPatcher'), '--', str(source), str(target), str(build/'managed-verification.json')], check=True)
    ops, data = make_delta(source, target, matching_ranges(source, target))
    (build/'managed.literals').write_bytes(data)
    managed = {'path': 'Human Anatomy Atlas_Data/Managed/Assembly-UnityScript.dll', 'source_sha256': hashfile(source),
               'target_sha256': hashfile(target), 'source_size': source.stat().st_size, 'target_size': target.stat().st_size,
               'operations': ops, 'literal_file': 'managed.literals', 'literal_sha256': hashfile(build/'managed.literals')}
    apply_delta(source, build/'reconstructed.dll', managed, data)
    (build/'reconstructed.dll').unlink()
    variants, avs = {}, {}
    for v in VARIANT_LABELS:
        build_assets(v)
        vdir = build/'variants'/v
        av = json.loads((vdir/'asset-verification.json').read_text())
        entry = dict(av['entry']); entry['literal_sha256'] = hashfile(vdir/entry['literal_file'])
        variants[v] = [entry, managed]; avs[v] = av
    coverage = json.loads((build/'variants'/'magyar'/'fulltext-coverage.json').read_text())
    manifest = make_manifest(variants, avs, coverage, policy)
    (build/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    archive = dist/(PACKAGE_ID + '.zip'); prefix = PACKAGE_ID + '/'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.write(build/'manifest.json', prefix + 'manifest.json')
        z.write(build/'managed.literals', prefix + 'managed.literals')
        for v in VARIANT_LABELS:
            vdir = build/'variants'/v
            z.write(vdir/('assets-' + v + '.literals'), prefix + 'assets-' + v + '.literals')
            z.write(vdir/'terms_hu.resolved.json', prefix + 'translations/' + v + '/terms_hu.json')
        for name in ('Install-Pack.ps1', 'Install.cmd', 'Restore.cmd', 'README.hu.md'):
            z.write(ROOT/name, prefix + name)
        z.write(build/'ui_hu.resolved.json', prefix + 'translations/ui_hu.json')
        z.write(ROOT/'fulltext/merged/field-translations.json', prefix + 'translations/fulltext-fields.json')
        z.write(build/'variants'/'magyar'/'fulltext-coverage.json', prefix + 'translations/fulltext-coverage.json')
        for name in ('draft-corrections.json', 'fulltext-approved.json'):
            z.write(ROOT/'corrections'/name, prefix + 'translations/' + name)
        open_q = ROOT/'quality-review/name-accuracy/NYITOTT-KERDESEK.csv'
        z.write(open_q, prefix + 'translations/NYITOTT-KERDESEK.csv')
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None: raise ValueError('ZIP CRC verification failed')
        members = z.namelist()
        if any(n.endswith(('.exe', '.dll', '.assets')) for n in members): raise ValueError('Original application artifact accidentally included')
    result = {'zip': str(archive), 'zip_sha256': hashfile(archive), 'zip_bytes': archive.stat().st_size, 'zip_members': members,
              'variants': {v: {'assets_target_sha256': avs[v]['entry']['target_sha256'], 'core_names_changed_vs_magyar': avs[v]['variant_core_names_changed']} for v in avs},
              'managed_target_sha256': managed['target_sha256']}
    (build/'release-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != 'zip_members'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
