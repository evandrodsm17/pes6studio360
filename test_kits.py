import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from pes6_binary import parts,unwrap
from pes6_fixed import entry_changes
from pes6_kits import KitEditor
from pes6_studio_v10 import add_we00
from pes6_we00_edit import image_bytes
from pes6_project import save,load
from pes6_teams import TeamMap
from pes6_kit_probe import analyze

ROOT=Path(__file__).parent


class KitProbeTests(unittest.TestCase):
    def test_unknown_executable_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'unknown.xex';source.write_bytes(b'not the original')
            with self.assertRaises(ValueError):analyze(source)

    @unittest.skipUnless((ROOT/'default.xex').is_file(),'Original game data not included')
    def test_real_request_window_without_guessed_mappings(self):
        report=analyze(ROOT/'default.xex')
        self.assertEqual(report['candidate_loader']['callee'],'0x8219def8')
        self.assertEqual(report['automatic_team_mappings'],[])
        self.assertFalse(report['runtime_verified'])


class KitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (ROOT/'cv.img').is_file() or not (ROOT/'cv_we00_texturas/index.csv').is_file():
            raise unittest.SkipTest('Original game data and catalog not included')
        items=[];paths=[];add_we00(ROOT/'cv_we00_texturas',items,paths)
        cls.editor=KitEditor(ROOT/'cv.img',items,paths)

    def png(self,entry,part,color):
        with Image.open(io.BytesIO(self.editor.preview(entry,part,{},True))) as im:
            im=im.convert('RGBA');im.putpixel((0,0),color);return image_bytes(im)

    def test_both_parts_and_no_other_resources(self):
        k=self.editor;edits={};k.stage(5736,{0:self.png(5736,0,(255,0,255,255)),1:self.png(5736,1,(0,255,0,255))},edits)
        self.assertEqual(set(edits),set(k.ids[5736]))
        self.assertNotIn(k.ids[5737][0],edits)
        changes=k.build_entries(edits);self.assertEqual(set(changes),{5736})
        before=unwrap(k.selected(5736));after=unwrap(changes[5736].data)
        self.assertEqual(len(before),len(after))
        self.assertEqual(before[:32],after[:32])
        for old,new in zip(parts(before),parts(after)):
            self.assertEqual(old[:3],new[:3]);self.assertEqual(old[3][:16],new[3][:16]);self.assertNotEqual(old[3],new[3])
        with k.source.open('rb') as f:self.assertTrue(entry_changes(f,0,k.source.stat().st_size,changes))

    def test_second_part_or_capacity_failure_is_atomic(self):
        k=self.editor;edits={999999:b'unrelated'};original=dict(edits)
        with self.assertRaises(ValueError):
            k.stage(5736,{0:self.png(5736,0,(255,0,255,255)),1:image_bytes(Image.new('RGBA',(64,64)))},edits)
        self.assertEqual(original,edits)
        with patch.object(k,'build_entries',side_effect=ValueError('No AFS capacity')):
            with self.assertRaises(ValueError):k.stage(5736,{0:self.png(5736,0,(255,0,255,255))},edits)
        self.assertEqual(original,edits)

    def test_restore_and_legacy_project_roundtrip(self):
        k=self.editor;edits={};png=self.png(5736,0,(255,0,255,255));k.stage(5736,{0:png},edits)
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder);iso=folder/'fixture.iso';iso.write_bytes(b'fixture')
            save(folder/'project.json',iso,k.paths,edits,{})
            restored,_=load(folder/'project.json',iso,k.paths);self.assertEqual(edits,restored)
            self.assertEqual(k.preview(5736,0,restored),k.preview(5736,0,edits))
            mapping=TeamMap(folder/'teams.json',k.paths)
            self.assertEqual(len(k.state(edits,mapping)['entries']),410)
        k.stage(5736,{0:k.preview(5736,0,{},True)},edits);self.assertFalse(edits)

    def test_catalog_divergence_blocks_staging(self):
        k=self.editor;entry=6145;cached=k.entries.pop(entry,None)
        with tempfile.TemporaryDirectory() as folder:
            fake=Path(folder)/'fake.png';Image.new('RGBA',(512,512),(1,2,3,255)).save(fake)
            paths=list(k.paths);paths[k.ids[entry][0]]=fake
            with patch.object(k,'paths',paths):
                with self.assertRaises(ValueError):k.selected(entry)
        if cached is not None:k.entries[entry]=cached


if __name__=='__main__':unittest.main()
