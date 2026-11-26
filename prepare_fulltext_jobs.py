"""Prepare resumable, disjoint full-text translation jobs; never fabricate translations."""
from pathlib import Path
from collections import defaultdict,Counter
import hashlib,json
from pack_builder import ROOT,resolve_catalogs,validate_translations

F=ROOT/'fulltext'; jobsdir=F/'jobs'; jobsdir.mkdir(exist_ok=True)
outputs=F/'translations'; outputs.mkdir(exist_ok=True)
source=json.loads((F/'source_catalog.json').read_text())
terms0=json.loads((ROOT/'translations/terms_hu.json').read_text())
ui0=json.loads((ROOT/'translations/ui_hu.json').read_text())
terms,ui=resolve_catalogs(terms0,ui0,json.loads((ROOT/'corrections/draft-corrections.json').read_text()))
term_src=json.loads((ROOT/'terms_source.json').read_text()); validate_translations(term_src,terms)
bykey={x['key']:x['hu'] for x in terms}
lookup=defaultdict(set)
for e,t in zip(term_src,terms):
    if e['key']!=t['key']: raise ValueError('Glossary order mismatch')
    lookup[e['en']].add(t['hu'])
for s,t in zip(json.loads((ROOT/'ui_source.json').read_text()),ui): lookup[s['en']].add(t['hu'])
rows=json.loads((ROOT/'structure_rows.json').read_text())
import xml.etree.ElementTree as ET
original=ET.parse(ROOT.parent/'textassets/resources.assets/10550_structures_en.txt').getroot()
for s,row in zip(original,rows):
    text=bykey[row['base_id']]
    if row['side']:text+=', '+{'L':'bal','R':'jobb','left side':'bal oldal','right side':'jobb oldal'}[row['side']]
    lookup[(s.text or '').partition('#')[0]].add(text)
glossary=[{'en':s['en'],'hu':bykey[s['key']],'key':s['key']} for s in term_src]
(F/'draft_glossary.json').write_text(json.dumps(glossary,ensure_ascii=False,indent=2),encoding='utf-8')
units={}
for item in source:
    cat=item['category']
    group='definitions' if cat=='definitions' else ('health' if cat.startswith('health_') else 'labels-and-quizzes')
    ident=hashlib.sha256((group+'\0'+item['en']).encode()).hexdigest()
    u=units.setdefault(ident,{'unit_id':ident,'en':item['en'],'group':group,'keys':[],'categories':set(),'resource_paths':set()})
    u['keys'].append(item['key']);u['categories'].add(cat);u['resource_paths'].update(item['resource_paths'])
for u in units.values():
    u['categories']=sorted(u['categories']);u['resource_paths']=sorted(u['resource_paths'])
auto=[]; pending=defaultdict(list)
for u in units.values():
    if len(lookup.get(u['en'],()))==1:
        auto.append({'unit_id':u['unit_id'],'hu':next(iter(lookup[u['en']])),'status':'unreviewed-core-glossary-reuse'})
    else:pending[u['group']].append(u)
(F/'translation_units.json').write_text(json.dumps(list(units.values()),ensure_ascii=False,indent=2),encoding='utf-8')
(outputs/'auto-core.json').write_text(json.dumps(auto,ensure_ascii=False,indent=2),encoding='utf-8')
index=[]
for group,items in sorted(pending.items()):
    chunks=[];chunk=[];words=0
    for u in items:
        count=len(u['en'].split())
        if chunk and words+count>12000:chunks.append(chunk);chunk=[];words=0
        chunk.append(u);words+=count
    if chunk:chunks.append(chunk)
    for n,chunk in enumerate(chunks,1):
        name=f'{group}-{n:02d}'
        p=jobsdir/(name+'.json')
        if p.exists():
            prior=json.loads(p.read_text())
            if prior!=chunk: raise ValueError('Refusing to alter an existing job input')
        else:p.write_text(json.dumps(chunk,ensure_ascii=False,indent=2),encoding='utf-8')
        index.append({'job_id':name,'input':str(p),'output':str(outputs/(name+'.json')),'units':len(chunk),'source_words':sum(len(u['en'].split()) for u in chunk),'input_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
all_keys=[key for u in units.values() for key in u['keys']]
if len(all_keys)!=len(set(all_keys)) or set(all_keys)!={x['key'] for x in source}:raise ValueError('Unit field coverage mismatch')
summary={'status':'translation jobs prepared, not completed','source_fields':len(source),'translation_units':len(units),'draft_core_reused_units':len(auto),'jobs':index,'medical_certification':False}
(jobsdir/'index.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
