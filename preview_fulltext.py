"""Apply validated translated fields to an IN-MEMORY copy and inspect real XML.
Default refuses incomplete catalogs. --allow-partial is an explicit offline QA preview.
No installed files or original assets are ever overwritten by this command.
"""
from pathlib import Path
from collections import defaultdict
import argparse,hashlib,json
from fulltext_tools import edit_xml_fields

ROOT=Path(__file__).resolve().parent

def hashfile(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def apply_fulltext_fields(env,catalog,fields,*,require_complete=True,output_directory=None):
    catalog_bykey={r['key']:r for r in catalog}
    if len(catalog_bykey)!=len(catalog) or not set(fields)<=set(catalog_bykey):raise ValueError('Unknown/duplicate catalog fields')
    if require_complete and set(fields)!=set(catalog_bykey):raise ValueError('Full-text field coverage is incomplete')
    grouped=defaultdict(list)
    for key in fields:
        record=catalog_bykey[key]
        if record['asset_file']!='resources.assets':raise ValueError('Unsupported asset-file scope')
        grouped[record['path_id']].append(record)
    objects={o.path_id:o for o in env.objects}; changed=[];checked=set();scripts={}
    for pid,entries in sorted(grouped.items()):
        if pid not in objects or objects[pid].type.name!='TextAsset':raise ValueError('Catalog object identity mismatch')
        hashes={e['source_sha256'] for e in entries}
        if len(hashes)!=1:raise ValueError('Inconsistent source script hashes')
        obj=objects[pid];data=obj.read();old=data.m_Script
        new=edit_xml_fields(old,entries,fields,expected_script_hash=next(iter(hashes)))
        if new!=old:
            data.m_Script=new;data.save();changed.append(pid);scripts[pid]=new
        checked.update(e['key'] for e in entries)
        if output_directory:
            dest=Path(output_directory);dest.mkdir(parents=True,exist_ok=True)
            (dest/(str(pid)+'.xml')).write_text(new,encoding='utf-8')
    if checked!=set(fields):raise ValueError('Some translated fields were not exercised')
    report={'edited_assets':len(changed),'changed_path_ids':changed,'checked_fields':len(checked),
        'total_catalog_fields':len(catalog),'complete_catalog_coverage':checked==set(catalog_bykey),
        'all_untargeted_XML_fields_preserved':True,'installed_app_modified':False,'medical_certification':False}
    return report,scripts

def main():
    p=argparse.ArgumentParser();p.add_argument('--allow-partial',action='store_true');a=p.parse_args()
    import UnityPy
    f=ROOT/'fulltext';cov=json.loads((f/'merged/coverage.json').read_text())
    catalog_path=f/'source_catalog.json'
    if hashfile(catalog_path)!=cov['source_catalog_sha256']:raise ValueError('Catalog changed after collection')
    source=ROOT.parent/'originals/resources.assets';original=hashfile(source)
    if original!='c2ea07cfb3df0996e1cfc3c97b58a5d9929e7f3aa66cc771ae91d37ae1e1a59c':raise ValueError('Wrong source asset')
    fields=json.loads((f/'merged/field-translations.json').read_text());catalog=json.loads(catalog_path.read_text())
    env=UnityPy.load(str(source));out=ROOT/'build/fulltext-preview'
    before={o.path_id:hashlib.sha256(o.get_raw_data()).hexdigest() for o in env.objects}
    report,scripts=apply_fulltext_fields(env,catalog,fields,require_complete=not a.allow_partial,output_directory=out)
    # ObjectReader.read can retain its original reader after save(); prove changes
    # through a real serialized-copy reload rather than re-reading that cache.
    out.mkdir(parents=True,exist_ok=True)
    serialized=out/'resources.assets';serialized.write_bytes(env.file.save())
    reopened=UnityPy.load(str(serialized));after={o.path_id:o for o in reopened.objects}
    if set(after)!=set(before):raise ValueError('Serialized object identities changed')
    changed={pid for pid,o in after.items() if hashlib.sha256(o.get_raw_data()).hexdigest()!=before[pid]}
    if changed!=set(scripts):raise ValueError('Unexpected serialized object changes')
    for pid,new in scripts.items():
        if after[pid].read().m_Script!=new:raise ValueError('Serialized TextAsset round-trip failed')
    if hashfile(source)!=original:raise ValueError('Original asset changed')
    report.update({'scope':'OFFLINE serialized-copy verification, not a runtime rendering test','source_sha256_before':original,'source_sha256_after':hashfile(source),'serialized_textassets_roundtripped':len(scripts),'untouched_object_payloads_verified':len(before)-len(changed),'serialized_copy_sha256':hashfile(serialized)})
    (out/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='changed_path_ids'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
