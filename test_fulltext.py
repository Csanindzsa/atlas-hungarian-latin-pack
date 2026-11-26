import unittest
from fulltext_tools import validate_unit, materialize_fields, edit_xml_fields, apply_unit_corrections

class FulltextTests(unittest.TestCase):
    def test_guarded_overlay_keeps_translator_baseline_immutable(self):
        import hashlib
        digest=lambda s:hashlib.sha256(s.encode()).hexdigest()
        u=[{'unit_id':'a','en':'Bone'}];t=[{'unit_id':'a','hu':'Csont'}]
        c={'entries':[{'unit_id':'a','approved':True,'source_en_sha256':digest('Bone'),'expected_hu_sha256':digest('Csont'),'replacements':[{'old':'Csont','new':'Csontszövet'}],'evidence':['fixture']}]}
        result=apply_unit_corrections(u,t,c)
        self.assertEqual(result[0]['hu'],'Csontszövet');self.assertEqual(t[0]['hu'],'Csont')
        c['entries'][0]['expected_hu_sha256']='0'*64
        self.assertRaises(ValueError,apply_unit_corrections,u,t,c)
    def test_unapproved_or_ambiguous_overlay_refused(self):
        import hashlib
        digest=lambda s:hashlib.sha256(s.encode()).hexdigest()
        u=[{'unit_id':'a','en':'Bone'}];t=[{'unit_id':'a','hu':'Csont Csont'}]
        e={'unit_id':'a','approved':False,'source_en_sha256':digest('Bone'),'expected_hu_sha256':digest('Csont Csont'),'replacements':[{'old':'Csont','new':'Csontszövet'}],'evidence':['fixture']}
        self.assertRaises(ValueError,apply_unit_corrections,u,t,{'entries':[e]})
        e['approved']=True
        self.assertRaises(ValueError,apply_unit_corrections,u,t,{'entries':[e]})
    def test_complete_text_numbers_and_tokens(self):
        src={'unit_id':'a','en':'Select 2 structures.\\n{count}'}
        out={'unit_id':'a','hu':'Válassz ki 2 képletet.\\n{count}'}
        self.assertEqual(validate_unit(src,out),[])
        self.assertRaises(ValueError,validate_unit,src,{'unit_id':'a','hu':'Válassz képletet.'})
        self.assertIn('numeric-content-changed',validate_unit({'unit_id':'a','en':'C3-C5'}, {'unit_id':'a','hu':'C4-C6'}))
    def test_fanout_no_missing_or_duplicate_units(self):
        units=[{'unit_id':'a','keys':['x','y'],'en':'Bone'},{'unit_id':'b','keys':['z'],'en':'Nerve'}]
        t=[{'unit_id':'a','hu':'Csont'},{'unit_id':'b','hu':'Ideg'}]
        fields,warnings=materialize_fields(units,t)
        self.assertEqual(fields,{'x':'Csont','y':'Csont','z':'Ideg'});self.assertEqual(warnings,[])
        self.assertRaises(ValueError,materialize_fields,units,t[:1])
        self.assertRaises(ValueError,materialize_fields,units,t+t[:1])
    def test_definition_other_languages_and_latin_are_preserved(self):
        text='<definition><en>Bone</en><fr>Os</fr><de>Knochen</de></definition>'
        entries=[{'key':'k','node_route':'0.0','tag':'en','field':'text','en':'Bone'}]
        result=edit_xml_fields(text,entries,{'k':'Csont'})
        self.assertIn('<en>Csont</en>',result);self.assertIn('<fr>Os</fr>',result);self.assertIn('<de>Knochen</de>',result)
        self.assertRaises(ValueError,edit_xml_fields,text,entries,{'k':'Csont'},expected_script_hash='0'*64)
    def test_quiz_answer_and_commands_are_not_translated(self):
        text='<quickviews><qv full="Bone"><timeline>{0|e|001}</timeline><question><prompt>Select 1 bone</prompt><answer>001</answer></question></qv></quickviews>'
        entries=[{'key':'a','node_route':'0.0','tag':'qv','field':'@full','en':'Bone'},{'key':'b','node_route':'0.0.1.0','tag':'prompt','field':'text','en':'Select 1 bone'}]
        result=edit_xml_fields(text,entries,{'a':'Csont','b':'Válassz ki 1 csontot'})
        self.assertIn('<answer>001</answer>',result);self.assertIn('{0|e|001}',result)
        entries[0]['field']='@id'; self.assertRaises(ValueError,edit_xml_fields,text,entries,{'a':'Bad','b':'Ok'})
    def test_stale_source_and_missing_translation_refused(self):
        entries=[{'key':'k','node_route':'0','tag':'en','field':'text','en':'Nerve'}]
        self.assertRaises(ValueError,edit_xml_fields,'<en>Bone</en>',entries,{'k':'Ideg'})

if __name__=='__main__':unittest.main()
