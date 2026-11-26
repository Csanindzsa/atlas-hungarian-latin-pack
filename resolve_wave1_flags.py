"""Record narrow language-equivalence checks for inspected wave-1 warnings.
This does not clear medical/specialist review or change any translation.
"""
from pathlib import Path
import json,re,hashlib
ROOT=Path(__file__).resolve().parent
F=ROOT/'fulltext'
coverage=json.loads((F/'merged/coverage.json').read_text())
units={x['unit_id']:x for x in json.loads((F/'translation_units.json').read_text())}
translations={x['unit_id']:x for x in json.loads((F/'merged/translated-units.json').read_text())}
negations={
 '3a3e6f9ef35324578565fa470deb3ff7e9a643731db5bd4e9ae3dfb464b2f9f5':('No one knows','Senki sem ismeri'),
 '97813cd830ab0eeb0863f2fe3458c5ba415f40b6477983954fc4946f3fc31f24':('may not appear until middle age or later','csak középkorban vagy később jelentkezhetnek'),
 'b99f2705b34e631ad1d29c72daa82530230154df4f411329300e0b540f841442':('not as often as viruses','ritkábban, mint a vírusok'),
 'ad31f3643bfc2464f7f9f2b24f76f6250cdfb423fac1e711e08721fbb1c29196':('or not at all','vagy teljesen el is maradhatnak')}
unchanged={'HPV','Trichomoniasis','Angina','HIV/AIDS','Lupus','Melanoma','Hepatitis A','Hepatitis B','Hepatitis C','H1N1'}
roman={'I':1,'II':2,'III':3,'IV':4}
rows=[]
for warning in coverage['warnings']:
    ident=warning['unit_id'];en=units[ident]['en'];hu=translations[ident]['hu'];checks=[]
    for flag in warning['flags']:
        if flag=='numeric-content-changed':
            a=re.search(r'\b([1-4])(?:st|nd|rd|th)\b',en);b=re.match(r'(IV|III|II|I)\. ',hu)
            if not a or not b or int(a.group(1))!=roman[b.group(1)] or len(re.findall(r'\d+',en))!=1 or re.search(r'\d',hu):raise ValueError('Unreviewed numeric warning')
            checks.append({'flag':flag,'decision':'ordinal-value-equivalence-checked','reason':'English Arabic ordinal and Hungarian Roman ordinal have the same value; no anatomical index was changed.'})
        elif flag=='unchanged-text-needs-Latin-or-proper-name-review':
            if en!=hu or en not in unchanged:raise ValueError('Unreviewed unchanged text')
            checks.append({'flag':flag,'decision':'conventional-medical-name-or-abbreviation-retained','reason':'Retained conventional Latin/international medical name or acronym, not untranslated English prose. Hungarian display-style and clinical review remain separate.'})
        elif flag=='negation-needs-review':
            if ident not in negations:raise ValueError('New negation warning needs inspection')
            a,b=negations[ident]
            if a not in en or b not in hu:raise ValueError('Reviewed negation clause changed')
            checks.append({'flag':flag,'decision':'meaningful-negative-clause-preserved','source_clause':a,'target_clause':b,'reason':'The generic keyword detector missed a Hungarian sem/comparative/temporal construction; root inspected the corresponding complete source and target paragraphs.'})
        else:raise ValueError('Unknown review warning')
    rows.append({'unit_id':ident,'en_sha256':hashlib.sha256(en.encode()).hexdigest(),'hu_sha256':hashlib.sha256(hu.encode()).hexdigest(),'checks':checks,'medically_certified':False})
report={'scope':'Only the inspected first-wave language-equivalence warnings; does not validate underlying medical claims','reviewed_units':len(rows),'checks':sum(len(x['checks']) for x in rows),'entries':rows,'medical_release_gate_cleared':False}
(F/'wave1-language-resolutions.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='entries'},ensure_ascii=False))
