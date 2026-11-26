"""Reversible Atlas 7.4.01 Hungarian/Latin data builder; no activation changes."""
from __future__ import annotations
from pathlib import Path
import copy, hashlib, json, re, unicodedata, xml.etree.ElementTree as ET
from collections import defaultdict

ROOT=Path(__file__).resolve().parent
SOURCE_HASH='c2ea07cfb3df0996e1cfc3c97b58a5d9929e7f3aa66cc771ae91d37ae1e1a59c'
SOURCE=ROOT.parent/'originals/resources.assets'
EXPORTS=ROOT.parent/'textassets/resources.assets'
IDS={'ui':9858,'structures':10550,'words':13228,'latin_order':12714}
FOLD=str.maketrans('áéíóöőúüűÁÉÍÓÖŐÚÜŰ','aeiooouuuAEIOOOUUU')

def hashfile(path):
    with Path(path).open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()

def fold_hu(text): return unicodedata.normalize('NFC',text).translate(FOLD)

def xmltext(root):
    # short_empty_elements=False: the app's XmlTextReader loops call Read() after an element start and take
    # the next node's Value; a self-closing <m /> makes that Read() land on whitespace/the next element,
    # which shifted the Latin-ordering list and crashed readStructuresList (runtime FormatException).
    # The shipped files always use <m></m> for empty elements, so keep that form.
    return '<?xml version="1.0" encoding="utf-8"?>\n'+ET.tostring(root,encoding='unicode',short_empty_elements=False)

def validate_translations(source, targets):
    keys=[r['key'] for r in source]; got=[r['key'] for r in targets]
    if len(got)!=len(set(got)) or set(got)!=set(keys): raise ValueError('Missing/duplicate/extra term translations')
    result={}
    for r in targets:
        text=r.get('hu','')
        if not isinstance(text,str) or not text.strip() or text!=unicodedata.normalize('NFC',text): raise ValueError('Empty/non-NFC translation')
        if any(x in text for x in ('#','\x00')): raise ValueError('Program delimiter in term translation')
        result[r['key']]=text
    return result

def resolve_catalogs(terms, ui, changes):
    """Apply explicit QA deltas without erasing the inspected baseline."""
    resolved_terms=copy.deepcopy(terms); resolved_ui=copy.deepcopy(ui)
    tmap={r['key']:r for r in resolved_terms}; umap={r['row']:r for r in resolved_ui}
    for collection,rows,key,map_ in (('terms',changes.get('terms',[]),'key',tmap),('ui',changes.get('ui',[]),'row',umap)):
        seen=set()
        for change in rows:
            value=change[key]
            if value in seen or value not in map_: raise ValueError('Unknown/duplicate correction '+collection)
            seen.add(value); current=map_[value]
            if current['hu']!=change['expected_hu']: raise ValueError('Correction baseline changed')
            if collection=='ui' and current['id']!=change['id']: raise ValueError('UI correction ID mismatch')
            target=change['hu']
            if not target.strip() or target!=unicodedata.normalize('NFC',target): raise ValueError('Invalid correction text')
            current['hu']=target
    return resolved_terms,resolved_ui


def translate_ui(source_xml, targets):
    root=ET.fromstring(source_xml)
    if len(targets)!=len(root): raise ValueError('UI row coverage mismatch')
    for i,(node,row) in enumerate(zip(root,targets)):
        if row['row']!=i or row['id']!=node.attrib['id']: raise ValueError('UI key/order mismatch')
        text=row.get('hu','')
        if not text or text!=unicodedata.normalize('NFC',text): raise ValueError('Invalid UI translation')
        old=node.text or ''
        for pattern in (r'\\n',r'\{[^}]*\}',r'%[0-9.]*[sdf]',r'<[^>]+>'):
            if sorted(re.findall(pattern,old))!=sorted(re.findall(pattern,text)): raise ValueError('UI formatting token changed: '+node.attrib['id'])
        node.text=text
    return xmltext(root)

def tokens(label):
    return re.sub(r"[^\w\s\d\-']",'',label.lower()).split()

def sort_label(label):
    # Existing A-Z buttons group accented Hungarian vowels with their base letters.
    folded=fold_hu(label).lower()
    group=folded[0] if folded and 'a'<=folded[0]<='z' else '\uf8ff'
    return group,folded,label

def build_structure_documents(source_xml, latin_xml, rows, translations):
    source=ET.fromstring(source_xml); latin=ET.fromstring(latin_xml)
    if len(source)!=len(rows) or len(latin)!=len(rows): raise ValueError('Positional map length mismatch')
    translated=[]
    for i,(node,row) in enumerate(zip(source,rows)):
        if row['row']!=i or row['id']!=node.attrib['id']: raise ValueError('Structure row mismatch')
        label=translations[row['base_id']]
        if row['side']: label+=', '+{'L':'bal','R':'jobb','left side':'bal oldal','right side':'jobb oldal'}[row['side']]
        new=copy.deepcopy(node); new.text=label+row['suffix']; translated.append((i,label,new))
    translated.sort(key=lambda x:(sort_label(x[1]),x[0]))
    structures=ET.Element(source.tag,source.attrib); ordering=ET.Element(latin.tag,latin.attrib)
    index=defaultdict(set)
    for new_row,(old_row,label,node) in enumerate(translated):
        structures.append(node); ordering.append(copy.deepcopy(latin[old_row]))
        for order,word in enumerate(tokens(label)):
            index[word].add((order,new_row)); index[fold_hu(word)].add((order,new_row))
    words=ET.Element('words')
    for word,refs in sorted(index.items()):
        w=ET.SubElement(words,'w',{'n':word})
        for order,idx in sorted(refs): ET.SubElement(w,'i',{'o':str(order)}).text=str(idx)
    # Legacy readWords emits a word only when the NEXT <w> begins.
    ET.SubElement(words,'w',{'n':'\uf8ff'})
    stats={'structure_rows':len(structures),'search_words':len(index),'search_references':sum(map(len,index.values())),
           'latin_join_preserved':True,'old_row_for_new_row':[x[0] for x in translated]}
    return {'structures':xmltext(structures),'latin_order':xmltext(ordering),'words':xmltext(words)},stats

def make_delta(source_path,target_path,copy_ranges):
    """Build seek/copy + literal operations; ranges are (source,target,length)."""
    source_path=Path(source_path); target_path=Path(target_path)
    ops=[]; literals=bytearray(); cursor=0
    def add(kind,offset,length):
        if not length: return
        if ops and ops[-1][0]==kind and ops[-1][1]+ops[-1][2]==offset: ops[-1][2]+=length
        else: ops.append([kind,offset,length])
    with source_path.open('rb') as src,target_path.open('rb') as dst:
        size=target_path.stat().st_size
        for old,new,length in sorted(copy_ranges,key=lambda r:r[1]):
            if min(old,new,length)<0 or new<cursor or new+length>size: raise ValueError('Overlapping/invalid delta ranges')
            dst.seek(cursor); gap=dst.read(new-cursor); add('data',len(literals),len(gap)); literals.extend(gap)
            src.seek(old); dst.seek(new)
            if src.read(length)!=dst.read(length): raise ValueError('COPY range content mismatch')
            add('copy',old,length); cursor=new+length
        dst.seek(cursor); gap=dst.read(); add('data',len(literals),len(gap)); literals.extend(gap)
    return ops,bytes(literals)

def matching_ranges(source_path, target_path, block=64, stride=16):
    """Bounded byte matching for the small managed DLL; never use on giant assets."""
    import zlib
    old=Path(source_path).read_bytes(); new=Path(target_path).read_bytes()
    if max(len(old),len(new))>4*1024*1024: raise ValueError('Use object ranges for large assets')
    buckets=defaultdict(list)
    for pos in range(0,len(old)-block+1,stride):
        key=zlib.adler32(old[pos:pos+block])
        if len(buckets[key])<8: buckets[key].append(pos)
    result=[]; pos=0
    while pos+block<=len(new):
        candidates=buckets.get(zlib.adler32(new[pos:pos+block]),())
        best=None
        for start in candidates:
            if old[start:start+block]!=new[pos:pos+block]: continue
            length=block
            while start+length+4096<=len(old) and pos+length+4096<=len(new) and old[start+length:start+length+4096]==new[pos+length:pos+length+4096]: length+=4096
            while start+length<len(old) and pos+length<len(new) and old[start+length]==new[pos+length]: length+=1
            if best is None or length>best[2]: best=(start,pos,length)
        if best: result.append(best); pos+=best[2]
        else: pos+=1
    return result


def apply_delta(source_path,output_path,entry,literals):
    source_path=Path(source_path); output_path=Path(output_path)
    if source_path.resolve()==output_path.resolve(): raise ValueError('Never write delta over source')
    if hashfile(source_path)!=entry['source_sha256']: raise ValueError('Source hash mismatch')
    size=0
    with source_path.open('rb') as src,output_path.open('wb') as dst:
        for kind,offset,length in entry['operations']:
            if min(offset,length)<0: raise ValueError('Invalid operation bounds')
            if kind=='copy': src.seek(offset); data=src.read(length)
            elif kind=='data': data=literals[offset:offset+length]
            else: raise ValueError('Invalid delta operation')
            if len(data)!=length: raise ValueError('Truncated delta/source')
            dst.write(data); size+=length
    if size!=entry['target_size'] or hashfile(output_path)!=entry['target_sha256']:
        output_path.unlink(missing_ok=True); raise ValueError('Target hash mismatch')

def variant_inputs():
    """Native Latin and English per core term key, used only to derive the 'latinos' terminology variant."""
    latin=defaultdict(set)
    occ=ROOT/'quality-review/name-accuracy/run-01/structure-occurrences.json'
    for r in json.loads(occ.read_text()): latin[int(r['key'])].update(x for x in r['native_latin'] if x)
    english={r['key']:r['en'] for r in json.loads((ROOT/'terms_source.json').read_text())}
    return latin,english

def build_assets(variant='magyar'):
    from variants import apply_variant, apply_variant_to_fields, VARIANTS
    if variant not in VARIANTS: raise ValueError('Unknown variant')
    from collect_fulltext import load_complete_fulltext
    from preview_fulltext import apply_fulltext_fields
    catalog,fulltext_fields,coverage=load_complete_fulltext(ROOT)
    if {e['path_id'] for e in catalog}&set(IDS.values()): raise ValueError('Full-text catalog overlaps core catalogs')
    import UnityPy
    top=ROOT/'build'; top.mkdir(exist_ok=True)
    build=top/'variants'/variant; build.mkdir(parents=True,exist_ok=True)
    if hashfile(SOURCE)!=SOURCE_HASH: raise ValueError('Wrong original resources.assets')
    terms_source=json.loads((ROOT/'terms_source.json').read_text())
    terms=json.loads((ROOT/'translations/terms_hu.json').read_text())
    ui=json.loads((ROOT/'translations/ui_hu.json').read_text())
    corrections=ROOT/'corrections/draft-corrections.json'
    if corrections.exists(): terms,ui=resolve_catalogs(terms,ui,json.loads(corrections.read_text()))
    if variant=='magyar':
        (top/'terms_hu.resolved.json').write_text(json.dumps(terms,ensure_ascii=False,indent=2),encoding='utf-8')
        (top/'ui_hu.resolved.json').write_text(json.dumps(ui,ensure_ascii=False,indent=2),encoding='utf-8')
    latin,english=variant_inputs()
    terms,variant_changes=apply_variant(terms,latin,variant,english)
    fulltext_fields,variant_field_changes=apply_variant_to_fields(fulltext_fields,variant_changes)
    translations=validate_translations(terms_source,terms)
    (build/'terms_hu.resolved.json').write_text(json.dumps(terms,ensure_ascii=False,indent=2),encoding='utf-8')
    (build/'ui_hu.resolved.json').write_text(json.dumps(ui,ensure_ascii=False,indent=2),encoding='utf-8')
    (build/'variant-changes.json').write_text(json.dumps({'variant':variant,'core_names_changed':{str(k):v for k,v in variant_changes.items()},'catalog_fields_changed':variant_field_changes},ensure_ascii=False,indent=2),encoding='utf-8')
    rows=json.loads((ROOT/'structure_rows.json').read_text())
    docs,stats=build_structure_documents((EXPORTS/'10550_structures_en.txt').read_text(),(EXPORTS/'12714_latin_en_ordering.txt').read_text(),rows,translations)
    docs['ui']=translate_ui((EXPORTS/'9858_ui_en.txt').read_text(),ui)
    env=UnityPy.load(str(SOURCE)); before={o.path_id:(o.byte_start,o.byte_size,hashlib.sha256(o.get_raw_data()).hexdigest()) for o in env.objects}
    for key,pid in IDS.items():
        obj=next(o for o in env.objects if o.path_id==pid); data=obj.read(); data.m_Script=docs[key]; data.save()
        (build/(key+'.xml')).write_text(docs[key],encoding='utf-8')
    fulltext_report,fulltext_scripts=apply_fulltext_fields(env,catalog,fulltext_fields)
    expected_changed=set(IDS.values())|set(fulltext_scripts)
    target=build/'resources.assets'; target.write_bytes(env.file.save())
    saved=UnityPy.load(str(target)); saved_objects={o.path_id:o for o in saved.objects}; changed=[]; ranges=[]
    if set(saved_objects)!=set(before): raise ValueError('Serialized object identities changed')
    for obj in saved_objects.values():
        old_offset,old_length,old_hash=before[obj.path_id]
        if hashlib.sha256(obj.get_raw_data()).hexdigest()!=old_hash: changed.append(obj.path_id)
        else: ranges.append((old_offset,obj.byte_start,obj.byte_size))
    if set(changed)!=expected_changed: raise ValueError('Unexpected changed objects')
    for key,pid in IDS.items():
        data=saved_objects[pid].read()
        if data.m_Script!=docs[key]: raise ValueError('Asset XML roundtrip mismatch')
    for pid,text in fulltext_scripts.items():
        if saved_objects[pid].read().m_Script!=text: raise ValueError('Full-text XML roundtrip mismatch')
    (build/'fulltext-coverage.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2),encoding='utf-8')
    if hashfile(SOURCE)!=SOURCE_HASH: raise ValueError('Original source was changed')
    ops,literals=make_delta(SOURCE,target,ranges)
    entry={'path':'Human Anatomy Atlas_Data/resources.assets','source_sha256':SOURCE_HASH,'target_sha256':hashfile(target),
           'source_size':SOURCE.stat().st_size,'target_size':target.stat().st_size,'operations':ops,'literal_file':'assets-'+variant+'.literals'}
    (build/entry['literal_file']).write_bytes(literals)
    # Independently reconstruct from the emitted patch, not from UnityPy's in-memory state.
    apply_delta(SOURCE,build/'reconstructed.assets',entry,literals)
    (build/'reconstructed.assets').unlink()
    target.unlink()  # 300+ MB; the verified delta reproduces it
    report={**stats,'variant':variant,'variant_core_names_changed':len(variant_changes),'variant_catalog_fields_changed':variant_field_changes,
            'ui_rows':len(ui),'canonical_terms':len(terms),'changed_asset_ids':sorted(changed),'object_count':len(before),
            'additional_text_fields':len(fulltext_fields),'additional_text_units':coverage['translated_units'],
            'fulltext_xml_assets':fulltext_report['edited_assets'],'fulltext_scope':'complete first-pass TextAsset catalog; other boundaries separately reviewed',
            'unchanged_object_count':len(before)-len(changed),'delta_operations':len(ops),'literal_bytes':len(literals),'entry':entry}
    (build/'asset-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in ('entry','old_row_for_new_row')},ensure_ascii=False))

if __name__=='__main__':
    import sys
    for v in (sys.argv[1:] or ['magyar']): build_assets(v)
