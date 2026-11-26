import unittest,tempfile,json,hashlib
from pathlib import Path
from collect_fulltext import collect_jobs,load_complete_fulltext

class CollectorTests(unittest.TestCase):
    def fixture(self,p):
        f=p/'fulltext';(f/'jobs').mkdir(parents=True);(f/'translations').mkdir()
        units=[{'unit_id':'a','en':'Bone','keys':['x','y']},{'unit_id':'b','en':'Nerve','keys':['z']}]
        (f/'translation_units.json').write_text(json.dumps(units))
        (f/'source_catalog.json').write_text(json.dumps([{'key':'x','en':'Bone'},{'key':'y','en':'Bone'},{'key':'z','en':'Nerve'}]))
        (f/'translations/auto-core.json').write_text('[]')
        jobs=[]
        for name,u in zip(('alpha','beta'),units):
            path=f/'jobs'/(name+'.json');path.write_text(json.dumps([u]));jobs.append({'job_id':name,'input':str(path),'output':str(f/'translations'/(name+'.json')),'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        (f/'jobs/index.json').write_text(json.dumps({'jobs':jobs}))
        (f/'translations/alpha.json').write_text(json.dumps([{'unit_id':'a','hu':'Csont'}]))
        return f
    def test_explicit_completed_subset_fans_out_without_polling_others(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);f=self.fixture(p);(f/'translations/beta.json').write_text('ACTIVE-WORKER-INVALID-JSON')
            result=collect_jobs(p,['alpha']);self.assertEqual(result['fields'],{'x':'Csont','y':'Csont'})
            self.assertEqual(result['coverage']['pending_jobs'],['beta']);self.assertFalse(result['coverage']['complete_text_coverage'])
    def test_complete_coverage_and_hash_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);f=self.fixture(p);(f/'translations/beta.json').write_text(json.dumps([{'unit_id':'b','hu':'Ideg'}]))
            self.assertTrue(collect_jobs(p,['alpha','beta'])['coverage']['complete_text_coverage'])
            (f/'jobs/alpha.json').write_text('[]');self.assertRaises(ValueError,collect_jobs,p,['alpha'])
    def test_complete_bundle_revalidates_receipts_and_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);f=self.fixture(p);(f/'translations/beta.json').write_text(json.dumps([{'unit_id':'b','hu':'Ideg'}]))
            result=collect_jobs(p,['alpha','beta']);merged=f/'merged';merged.mkdir()
            for name,value in [('coverage.json',result['coverage']),('field-translations.json',result['fields']),('translated-units.json',result['targets'])]:
                (merged/name).write_text(json.dumps(value))
            cat,fields,cov=load_complete_fulltext(p)
            self.assertEqual(fields,{'x':'Csont','y':'Csont','z':'Ideg'})
            (merged/'field-translations.json').write_text(json.dumps({'x':'Changed','y':'Csont','z':'Ideg'}))
            self.assertRaises(ValueError,load_complete_fulltext,p)
    def test_incomplete_bundle_is_not_buildable(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);f=self.fixture(p);merged=f/'merged';merged.mkdir()
            result=collect_jobs(p,['alpha']);(merged/'coverage.json').write_text(json.dumps(result['coverage']))
            self.assertRaises(ValueError,load_complete_fulltext,p)
    def test_incomplete_worker_output_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);f=self.fixture(p);(f/'translations/alpha.json').write_text('[]')
            self.assertRaises(ValueError,collect_jobs,p,['alpha'])

if __name__=='__main__':unittest.main()
