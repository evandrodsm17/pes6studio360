import csv
from pathlib import Path
import tempfile
import unittest
from pes6_club_editor import ClubEditor
from pes6_club_identity import analyze
from pes6_project import save,load

ROOT=Path(__file__).parent


class ClubEditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (ROOT/'cv_we00_texturas/index.csv').exists() or not (ROOT/'research/chelsea_2006_07/chelsea_crest_128.png').exists():
            raise unittest.SkipTest('Local game data and crest pilot not supplied')
        cls.items=[];cls.paths=[]
        with (ROOT/'cv_we00_texturas/index.csv').open(encoding='utf-8-sig',newline='') as f:
            for row in csv.DictReader(f):
                if row['resource'].split('_')[0] not in ('2710','2711'):continue
                cls.items.append({'id':len(cls.paths),'kind':'WE00','entry':row['resource'].split('_')[0],
                                  'name':row['resource'],'archive':'cv_we00_texturas'})
                cls.paths.append(ROOT/'cv_we00_texturas'/row['file'])
        cls.report=analyze(ROOT)

    def editor(self):return ClubEditor(self.report,self.items,self.paths,ROOT)

    def test_atomic_two_resolution_upload_and_project_roundtrip(self):
        editor=self.editor();resources=editor.selected(69);edits={}
        def prepare(i,body,query):
            size=next(r['size'] for r in resources if r['id']==i)
            return self.paths[i].read_bytes(),(ROOT/f'research/chelsea_2006_07/chelsea_crest_{size}.png').read_bytes()
        editor.stage(69,b'handled by prepare','contain',prepare,edits)
        self.assertEqual(set(edits),{r['id'] for r in resources})
        self.assertTrue(all(r['modified'] for r in editor.state(edits)['records'][69]['resources']))
        with tempfile.TemporaryDirectory() as temp:
            project=Path(temp)/'project.json';iso=ROOT.parent/'Pro Evolution Soccer 2006 [PAL].iso'
            save(project,iso,self.paths,edits,{})
            restored,tags=load(project,iso,self.paths)
            self.assertEqual(restored,edits)
        editor.undo(69,edits);self.assertEqual(edits,{})

    def test_second_size_failure_preserves_previous_edits(self):
        editor=self.editor();resources=editor.selected(69)
        edits={resources[0]['id']:b'previous edit'};before=dict(edits);calls=[]
        def prepare(i,body,query):
            calls.append(i)
            if len(calls)==2:raise ValueError('second conversion failed')
            return b'old',b'new'
        with self.assertRaises(ValueError):editor.stage(69,b'png','contain',prepare,edits)
        self.assertEqual(len(calls),2);self.assertEqual(edits,before)

    def test_capacity_failure_preserves_previous_edits(self):
        editor=self.editor();resources=editor.selected(69);edits={};calls=[]
        def prepare(i,body,query):
            calls.append(i);size=next(r['size'] for r in resources if r['id']==i)
            if size==64:return self.paths[i].read_bytes(),b'invalid png'
            return self.paths[i].read_bytes(),(ROOT/f'research/chelsea_2006_07/chelsea_crest_{size}.png').read_bytes()
        with self.assertRaises((ValueError,OSError)):editor.stage(69,b'png','contain',prepare,edits)
        self.assertEqual(edits,{})

    def test_ambiguous_resources_and_invalid_records(self):
        duplicate=dict(self.items[62],id=len(self.paths))
        editor=ClubEditor(self.report,self.items+[duplicate],self.paths+[self.paths[62]],ROOT)
        self.assertFalse(editor.state({})['records'][69]['available'])
        with self.assertRaises(ValueError):editor.selected(69)
        for record in (-1,True,1000):
            with self.assertRaises(ValueError):self.editor().selected(record)

    def test_undo_only_selected_resources(self):
        editor=self.editor();chelsea=editor.selected(69);arsenal=editor.selected(64)
        edits={r['id']:b'edit' for r in chelsea+arsenal}
        editor.undo(69,edits)
        self.assertEqual(set(edits),{r['id'] for r in arsenal})

if __name__=='__main__':unittest.main()
