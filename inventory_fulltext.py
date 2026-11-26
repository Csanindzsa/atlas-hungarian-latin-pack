"""Inventory additional English text; does not translate or patch anything.
This is a first-pass TextAsset catalog, NOT proof of all user-visible text coverage.
"""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json,re,xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
OUT=ROOT/'fulltext'
OUT.mkdir(exist_ok=True)
inv=json.loads((BASE/'inventory.json').read_text())
schema=json.loads((BASE/'localization_schema.json').read_text())
paths=defaultdict(list)
for p in json.loads((BASE/'resource_paths.json').read_text()): paths[p['m_PathID']].append(p['resource_path'])
records=[]; seen=set(); unmapped=[]

def add(asset,node,route,field,category):
    text=node.text if field=='text' else node.attrib.get(field[1:])
    if text is None or not text.strip(): return
    identity=(asset['file'],asset['path_id'],route,field)
    if identity in seen: return
    seen.add(identity)
    records.append({'key':':'.join(map(str,identity)),'asset_file':asset['file'],'path_id':asset['path_id'],
        'resource_paths':paths[asset['path_id']],'node_route':route,'tag':node.tag,'field':field,
        'category':category,'en':text,'source_sha256':asset['sha256']})

def walk(node,route='0'):
    yield node,route
    for i,c in enumerate(node): yield from walk(c,route+'.'+str(i))

for asset in inv['textassets']:
    try: root=ET.parse(asset['extracted']).getroot()
    except ET.ParseError: continue
    resource_paths=paths[asset['path_id']]
    english=any('/en/' in p or p.endswith('_en') for p in resource_paths)
    foreign=any(re.search(r'/(fr|de|it|es|ja)/|_(fr|de|it|es|ja)$',p) for p in resource_paths)
    group=(resource_paths[0].split('/')[0] if resource_paths else '')
    for node,route in walk(root):
        if node.tag=='en' and root.tag=='definition': add(asset,node,route,'text','definitions')
        if node.tag=='nih_en':
            add(asset,node,route,'text','health_descriptions'); add(asset,node,route,'@disease','health_titles')
        if english:
            if group=='landmarks' and node.tag=='node':
                for field in ('@name','@text'): add(asset,node,route,field,'landmarks')
            elif group=='quiz':
                if node.tag=='prompt': add(asset,node,route,'text','quiz_prompts')
                if node.tag=='qv':
                    for field in ('@full','@short'): add(asset,node,route,field,'quiz_titles')
            elif group=='actionanimations':
                if node.tag in ('region','action','view'): add(asset,node,route,'@name','action_labels')
            elif group=='animations':
                for field in ('@short','@full','@name','@title','@description'): add(asset,node,route,field,'animation_labels')
                if node.tag=='text': add(asset,node,route,'text','animation_descriptions')
            elif group=='in_app_store':
                for field in ('@title','@description','@name'): add(asset,node,route,field,'store_labels')
                if node.tag=='text': add(asset,node,route,'text','store_descriptions')
        if root.tag=='quickviews' and group!='quiz' and not foreign:
            if node.tag=='qv':
                for field in ('@full','@short'): add(asset,node,route,field,'shared_quickview_labels')
    if root.tag not in ('l','quickviews','definition','t','r','animations','descriptions','actions','structures','ui','mapping','words','xcptns'):
        unmapped.append({'path_id':asset['path_id'],'root':root.tag,'paths':resource_paths})

unique={}
for r in records: unique.setdefault(r['en'],[]).append(r['key'])
summary={'status':'first-pass inventory; incomplete coverage audit',
    'additional_text_fields':len(records),'unique_additional_strings':len(unique),
    'source_word_count':sum(len(r['en'].split()) for r in records),
    'counts_by_category':dict(sorted(Counter(r['category'] for r in records).items())),
    'already_handled_core':{'ui_rows':241,'structure_name_rows':4643},
    'unclassified_xml_assets':unmapped,
    'remaining_inventory_boundaries':['Serialized MonoBehaviour/GUIText strings outside TextAssets','Text embedded in textures/images','Audio and video narration/subtitles','Runtime-generated and managed-assembly hardcoded strings','Other localized data fields outside current allowlist'],
    'forbidden_to_translate':['Latin terminology','IDs and quiz answer references','Timeline/camera/visibility command data','File/resource paths','Program suffixes and numeric data'],
    'not_medically_reviewed':True}
(OUT/'source_catalog.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'unique_strings.json').write_text(json.dumps([{'en':k,'keys':v} for k,v in unique.items()],ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'inventory-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k!='unclassified_xml_assets'},ensure_ascii=False,indent=2))
