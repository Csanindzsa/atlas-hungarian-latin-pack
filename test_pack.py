import unittest, tempfile, json, hashlib
from pathlib import Path
import xml.etree.ElementTree as ET
from pack_builder import fold_hu, translate_ui, build_structure_documents, make_delta, apply_delta, validate_translations, resolve_catalogs

class PackTests(unittest.TestCase):
    def test_corrections_are_guarded_and_do_not_mutate_baseline(self):
        terms=[{'key':1,'hu':'Hibás'}]; ui=[{'row':0,'id':'redo','hu':'Újra'}]
        changes={'terms':[{'key':1,'expected_hu':'Hibás','hu':'Javított'}], 'ui':[{'row':0,'id':'redo','expected_hu':'Újra','hu':'Ismételt végrehajtás'}]}
        t,u=resolve_catalogs(terms,ui,changes)
        self.assertEqual(t[0]['hu'],'Javított'); self.assertEqual(terms[0]['hu'],'Hibás')
        self.assertEqual(u[0]['hu'],'Ismételt végrehajtás'); self.assertEqual(ui[0]['hu'],'Újra')
        changes['terms'][0]['expected_hu']='Más'
        self.assertRaises(ValueError,resolve_catalogs,terms,ui,changes)

    def test_fold_all_hungarian_accents(self):
        self.assertEqual(fold_hu('ÁÉÍÓÖŐÚÜŰ áéíóöőúüű'),'AEIOOOUUU aeiooouuu')
    def test_ui_duplicate_rows_preserved(self):
        src='<ui><item id="back">Back</item><item id="back">Back</item><item id="x">Hide\\nOthers</item></ui>'
        rows=[{'row':0,'id':'back','hu':'Vissza'},{'row':1,'id':'back','hu':'Vissza'},{'row':2,'id':'x','hu':'Többi\\nelrejtése'}]
        x=ET.fromstring(translate_ui(src,rows)); self.assertEqual(len(x),3); self.assertEqual(x[1].text,'Vissza')
        rows[2]['hu']='Hibás'; self.assertRaises(ValueError,translate_ui,src,rows)
    def test_missing_translation_rejected(self):
        self.assertRaises(ValueError,validate_translations,[{'key':0,'en':'Bone'}],[])
        self.assertRaises(ValueError,validate_translations,[{'key':0,'en':'Bone'}],[{'key':0,'hu':''}])
        self.assertRaises(ValueError,validate_translations,[{'key':0,'en':'Bone'}],[{'key':0,'hu':'Csont'},{'key':0,'hu':'Csont'}])
    def test_reorder_keeps_latin_join_and_program_suffix(self):
        source='<structures><structure id="1">Bone, L#Female</structure><structure id="2" scene="eye">Artery#dummyArteries</structure></structures>'
        latin='<map><m alpha="0">7</m><m>3</m></map>'
        rows=[{'row':0,'id':'1','base_id':0,'side':'L','suffix':'#Female'},{'row':1,'id':'2','base_id':1,'side':None,'suffix':'#dummyArteries'}]
        docs,stats=build_structure_documents(source,latin,rows,{0:'Csont',1:'Artéria'})
        structs=ET.fromstring(docs['structures']); lm=ET.fromstring(docs['latin_order'])
        self.assertEqual([e.attrib['id'] for e in structs],['2','1'])
        self.assertEqual(structs[0].text,'Artéria#dummyArteries'); self.assertEqual(structs[1].text,'Csont, bal#Female')
        self.assertEqual([e.text for e in lm],['3','7']); self.assertEqual(lm[1].attrib,{'alpha':'0'})
        words=ET.fromstring(docs['words']); names=[e.attrib['n'] for e in words]
        self.assertIn('artéria',names); self.assertIn('arteria',names)
        node=next(e for e in words if e.attrib['n']=='artéria'); self.assertEqual(node[0].text,'0')
        self.assertEqual(names[-1],'\uf8ff')
    def test_empty_elements_are_never_self_closing(self):
        # Runtime regression: the app's XmlTextReader misreads <m /> (FormatException in readStructuresList).
        source='<structures><structure id="1">Bone</structure><structure id="2">Artery</structure></structures>'
        latin='<map><m></m><m alpha="0">3</m></map>'
        rows=[{'row':0,'id':'1','base_id':0,'side':None,'suffix':''},{'row':1,'id':'2','base_id':1,'side':None,'suffix':''}]
        docs,_=build_structure_documents(source,latin,rows,{0:'Csont',1:'Artéria'})
        for name,text in docs.items(): self.assertNotRegex(text,r'<[A-Za-z][^<>]*/>',name)
        self.assertIn('<m></m>',docs['latin_order'])
    def test_delta_roundtrip_and_reject_wrong_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); old=p/'old'; new=p/'new'; out=p/'out'
            old.write_bytes(b'HEADERxxxxDATAaaaaTAIL'); new.write_bytes(b'NEWHEADERxxxxDATAbbbbTAIL')
            ops,literals=make_delta(old,new,[(6,9,8),(18,21,4)])
            manifest={'source_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),'target_sha256':hashlib.sha256(new.read_bytes()).hexdigest(),'target_size':new.stat().st_size,'operations':ops}
            apply_delta(old,out,manifest,literals); self.assertEqual(out.read_bytes(),new.read_bytes())
            old.write_bytes(b'wrong'); self.assertRaises(ValueError,apply_delta,old,out,manifest,literals)

if __name__=='__main__': unittest.main()
