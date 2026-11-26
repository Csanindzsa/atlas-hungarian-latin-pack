"""Validate explicitly completed jobs and expand units to exact original field keys.
Never polls active worker files; --jobs must name jobs whose completion was received.
"""
from pathlib import Path
import argparse,hashlib,json
from collections import Counter
from fulltext_tools import materialize_fields,apply_unit_corrections

ROOT=Path(__file__).resolve().parent

def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def collect_jobs(root,completed):
    root=Path(root).resolve();f=root/'fulltext'; index=load(f/'jobs/index.json')
    jobs={j['job_id']:j for j in index['jobs']}
    if len(completed)!=len(set(completed)) or not set(completed)<=set(jobs):raise ValueError('Unknown/duplicate completed-job IDs')
    units=load(f/'translation_units.json');byid={u['unit_id']:u for u in units}
    if len(byid)!=len(units):raise ValueError('Duplicate source units')
    catalog=load(f/'source_catalog.json');byfield={e['key']:e for e in catalog}
    if len(byfield)!=len(catalog):raise ValueError('Duplicate source fields')
    seen=set()
    for unit in units:
        for key in unit['keys']:
            if key in seen or key not in byfield or byfield[key]['en']!=unit['en']:raise ValueError('Source unit/field identity mismatch')
            seen.add(key)
    if seen!=set(byfield):raise ValueError('Source unit catalog is incomplete')
    targets=load(f/'translations/auto-core.json'); accepted=[]
    for name in completed:
        j=jobs[name];source=f/'jobs'/(name+'.json');output=f/'translations'/(name+'.json')
        if Path(j['input']).resolve()!=source.resolve() or Path(j['output']).resolve()!=output.resolve():raise ValueError('Job paths do not match their identities')
        if sha(source)!=j['input_sha256']:raise ValueError('Job source hash changed')
        requested=load(source);translated=load(output)
        source_ids=[u['unit_id'] for u in requested];target_ids=[u.get('unit_id') for u in translated]
        if len(source_ids)!=len(set(source_ids)) or len(target_ids)!=len(set(target_ids)) or set(source_ids)!=set(target_ids):raise ValueError('Incomplete or duplicate worker output: '+name)
        for unit in requested:
            if byid.get(unit['unit_id'])!=unit:raise ValueError('Job no longer matches original unit catalog')
        targets.extend(translated);accepted.append({'job_id':name,'units':len(translated),'input_sha256':sha(source),'output_sha256':sha(output)})
    target_ids=[t['unit_id'] for t in targets]
    if len(target_ids)!=len(set(target_ids)) or not set(target_ids)<=set(byid):raise ValueError('Conflicting or unknown translated units')
    chosen=[byid[i] for i in target_ids]
    correction_path=root/'corrections/fulltext-approved.json'
    if correction_path.exists():targets=apply_unit_corrections(units,targets,load(correction_path))
    fields,warnings=materialize_fields(chosen,targets)
    pending=[j['job_id'] for j in index['jobs'] if j['job_id'] not in completed]
    coverage={'scope':'First-pass TextAsset catalog only; not all app-visible media/hardcoded text',
              'completed_jobs':list(completed),'pending_jobs':pending,'accepted_job_receipts':accepted,
              'translated_units':len(target_ids),'total_units':len(units),'translated_fields':len(fields),'total_fields':len(catalog),
              'complete_text_coverage':set(target_ids)==set(byid),'warnings':warnings,
              'warning_counts':dict(Counter(flag for w in warnings for flag in w['flags'])),
              'source_catalog_sha256':sha(f/'source_catalog.json'),'translation_units_sha256':sha(f/'translation_units.json'),
              'draft_corrections_sha256':sha(correction_path) if correction_path.exists() else None,
              'medical_certification':False,'release_authorized':False}
    if not pending and not coverage['complete_text_coverage']:raise ValueError('All jobs selected but translation units remain missing')
    return {'targets':targets,'fields':fields,'coverage':coverage}

def load_complete_fulltext(root):
    """Fail closed: rebuild receipts and fanout before allowing a full asset build."""
    root=Path(root).resolve();f=root/'fulltext';merged=f/'merged'
    cov=load(merged/'coverage.json')
    if cov.get('complete_text_coverage') is not True or cov.get('pending_jobs')!=[]:
        raise ValueError('Full-text bundle is incomplete')
    verified=collect_jobs(root,cov.get('completed_jobs',[]))
    if not verified['coverage']['complete_text_coverage']:raise ValueError('Missing complete-job receipts')
    if cov!=verified['coverage']:raise ValueError('Full-text coverage receipts changed; recollect')
    fields=load(merged/'field-translations.json');targets=load(merged/'translated-units.json')
    if fields!=verified['fields'] or targets!=verified['targets']:raise ValueError('Merged translations do not match validated job outputs')
    return load(f/'source_catalog.json'),fields,cov


def main():
    p=argparse.ArgumentParser();p.add_argument('--jobs',nargs='+',required=True);a=p.parse_args()
    result=collect_jobs(ROOT,a.jobs);out=ROOT/'fulltext/merged';out.mkdir(exist_ok=True)
    for name,data in [('translated-units.json',result['targets']),('field-translations.json',result['fields']),('coverage.json',result['coverage'])]:
        temp=out/(name+'.new');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(out/name)
    report={k:v for k,v in result['coverage'].items() if k not in ('warnings','accepted_job_receipts')}
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
