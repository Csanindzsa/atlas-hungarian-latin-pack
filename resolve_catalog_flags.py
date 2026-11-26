"""Narrow language checks only: preserve source clinical-risk review unchanged."""
from pathlib import Path
from collections import Counter
from decimal import Decimal
import hashlib,json,re
ROOT=Path(__file__).resolve().parent;F=ROOT/'fulltext'
load=lambda p:json.loads(p.read_text())
digest=lambda s:hashlib.sha256(s.encode()).hexdigest()
old={e['unit_id']:e for e in load(F/'wave1-language-resolutions.json')['entries']}
sources={e['unit_id']:e for e in load(F/'translation_units.json')}
targets={e['unit_id']:e for e in load(F/'merged/translated-units.json')}
coverage=load(F/'merged/coverage.json')
numeric={'5aaed2c04d58894713765e145c87b7f9250458151883b3be6cd4624389ecd192','d4f025457a769520f29584f45b5c650c331ebe5d7a2f9c42c089ee6ec0b4a309','1849dea4f3d6af1b49e394b3e1e20f7e7b11c610864f5c7da0c55fa7d6d18fba'}
negative={'b5973148a74b89e9b39963e01a6f76ede7e064f03fbab8f370a696f2987c0368','e488659becf30e7647d48634d63c6d979ca553d4f31264e17008639043cdbba1'}
unchanged={'798778bc0dd6dff69e9a23f1e68b198d779e0d1787b690297382a7c463128b70':'COPD','a69b41704f190a61a8b2331c6b423f81a00b883ada117116d3684188fb345f5a':'4. Circulus arteriosus cerebri (Willisii)'}
rows=[]
for w in coverage['warnings']:
    ident=w['unit_id'];en=sources[ident]['en'];hu=targets[ident]['hu']
    if ident in old:
        entry=old[ident]
        if entry['en_sha256']!=digest(en) or entry['hu_sha256']!=digest(hu) or {c['flag'] for c in entry['checks']}!=set(w['flags']):raise ValueError('Prior language check is stale')
        rows.append(entry);continue
    checks=[]
    for flag in w['flags']:
        if ident=='d45a413dcfa833b8770daebb4a05d841245abfc1938964fc2ac89116588461fe' and flag=='numeric-content-changed':
            # Not a localization equivalence: a separately verified source error was corrected.
            proposals=load(ROOT/'quality-review/source-corrections/proposals.json')['items']
            proposal=next(x for x in proposals if x['unit_id']==ident)
            approval=next(x for x in load(ROOT/'corrections/fulltext-approved.json')['entries'] if x['unit_id']==ident)
            proof=next(x for x in load(ROOT/'quality-review/source-corrections/root-evidence-check.json')['proposals'] if x['unit_id']==ident)
            if approval.get('approved') is not True or not proof['any_live_supporting_quote_verified'] or digest(hu)!=proposal['proposal']['corrected_full_hu_sha256_utf8']:
                raise ValueError('Sourced numeric correction lacks an exact reviewed target')
            if Counter(re.findall(r'\d+',en))-Counter(re.findall(r'\d+',hu))!=Counter({'20':1}) or Counter(re.findall(r'\d+',hu))-Counter(re.findall(r'\d+',en)):
                raise ValueError('Unexpected additional numeric change')
            checks.append({'flag':flag,'decision':'explicit-evidence-backed-source-correction-not-language-equivalence','reason':'Removed the unsupported20-fold vibration-frequency statement; replaced with qualitative pressure transmission. Five-topic root readback contains the supporting quotes. No exact replacement multiplier asserted. Full record and professional review remain uncertified.','evidence_receipt':'quality-review/source-corrections/root-evidence-check.json'})
        elif ident in numeric and flag=='numeric-content-changed':
            en_nums=Counter(Decimal(x.replace(',','')) for x in re.findall(r'\d+(?:,\d{3})*(?:\.\d+)?',en))
            hu_nums=Counter(Decimal(x.replace(' ','').replace(',','.')) for x in re.findall(r'\d+(?: \d{3})*(?:,\d+)?',hu))
            if en_nums!=hu_nums:raise ValueError('Actual quantity mismatch')
            checks.append({'flag':flag,'decision':'numeric-values-equivalent-under-explicit-EN-HU-locales','reason':'Decimal point/comma and thousands comma/space localization only. All parsed numeric quantities match. Underlying anatomy claims remain unreviewed.'})
        elif ident in negative and flag=='negation-needs-review':
            if 'No one knows' not in en or 'Senki sem tudja' not in hu:raise ValueError('Reviewed negation changed')
            checks.append({'flag':flag,'decision':'negative-clause-preserved','source_clause':'No one knows','target_clause':'Senki sem tudja','reason':'The lexical detector missed Hungarian sem. Clinical claim not certified.'})
        elif ident in unchanged and flag=='unchanged-text-needs-Latin-or-proper-name-review':
            if en!=hu or hu!=unchanged[ident]:raise ValueError('Reviewed proper name changed')
            checks.append({'flag':flag,'decision':'native-Latin-or-international-acronym-retained','reason':'Required native Latin proper anatomy label or COPD acronym retained; not English prose fallback.'})
        else:raise ValueError('New warning requires substantive inspection')
    rows.append({'unit_id':ident,'en_sha256':digest(en),'hu_sha256':digest(hu),'checks':checks,'medically_certified':False})
report={'scope':'Hash-bound language checks plus separately evidenced, explicit source-correction exceptions; NOT anatomical or clinical certification','reviewed_units':len(rows),'checks':sum(len(x['checks']) for x in rows),'source_correction_exceptions':sum(c['decision']=='explicit-evidence-backed-source-correction-not-language-equivalence' for x in rows for c in x['checks']),'entries':rows,'medical_release_gate_cleared':False}
(F/'catalog-language-resolutions.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='entries'},ensure_ascii=False))
