import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from pes6_club_identity import analyze,text_at,SOURCE_SHA256
from pes6_name_editor import NameEditor,repack
from pes6_xex_probe import reconstruct
from pes6_iso import build
from pes6_project import save,load
import json

ROOT=Path(__file__).parent


@unittest.skipUnless((ROOT/'default.xex').exists(), 'Local game data not supplied')
class NameEditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=(ROOT/'default.xex').read_bytes();cls.report=analyze(ROOT)

    def editor(self):return NameEditor(self.raw,self.report)

    def test_real_encrypted_roundtrip_and_exact_text_scope(self):
        editor=self.editor();self.assertEqual(repack(self.raw,editor.image),self.raw)
        editor.stage(69,'Chelsea','CHE');new=editor.build();image,layout=reconstruct(new)
        row=editor.rows[69]
        self.assertEqual(text_at(image,layout['base_address'],int(row['name_address'],16)),'Chelsea')
        self.assertEqual(text_at(image,layout['base_address'],int(row['short_name_address'],16)),'CHE')
        spans=sorted((int(row[field+'_address'],16)-layout['base_address'],len(row[field].encode('utf-8'))+1) for field in ('name','short_name'))
        cursor=0
        for offset,size in spans:
            self.assertEqual(image[cursor:offset],editor.image[cursor:offset]);cursor=offset+size
        self.assertEqual(image[cursor:],editor.image[cursor:])
        self.assertEqual(new[:layout['header_size']],self.raw[:layout['header_size']])
        self.assertEqual(len(new),len(self.raw))

    def test_invalid_names_preserve_pending(self):
        editor=self.editor();editor.stage(69,'Chelsea','CHE');before=dict(editor.edits)
        for name,short in (('Chelsea Football Club','CHE'),('Chelsea','CHEL'),('', 'CHE'),('Che\0sea','CHE'),('á'*9,'CHE')):
            with self.assertRaises(ValueError):editor.stage(69,name,short)
            self.assertEqual(editor.edits,before)
        with self.assertRaises(ValueError):editor.stage(True,'A','A')
        editor.stage(69,'London FC','LDN');self.assertEqual(editor.edits,{})

    def test_saved_names_and_legacy_projects(self):
        editor=self.editor();editor.stage(69,'Chelsea','CHE')
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'project.json';iso=ROOT.parent/'Pro Evolution Soccer 2006 [PAL].iso'
            save(p,iso,[],{}, {},editor.edits,SOURCE_SHA256)
            self.assertEqual(load(p,iso,[]),({},{}))
            self.assertEqual(editor.validated_project(json.loads(p.read_text())),editor.edits)
        self.assertEqual(editor.validated_project({'version':1}),{})
        with self.assertRaises(ValueError):editor.validated_project({'club_names':{'69':{'name':'Chelsea','short_name':'CHE'}},'name_source_sha256':'wrong'})

    def test_unstored_region_is_not_silently_dropped(self):
        editor=self.editor();image=bytearray(editor.image)
        offset=editor.layout['blocks'][0]['data_size'];image[offset]=1
        with self.assertRaises(ValueError):repack(self.raw,bytes(image))

    def test_unknown_source_rejected(self):
        with self.assertRaises(ValueError):NameEditor(self.raw[:-1]+bytes([self.raw[-1]^1]),self.report)


class ExecutableOutputTests(unittest.TestCase):
    def test_executable_only_outputs_and_source_guard(self):
        old=b'A'*64;new=b'B'*64;sha=hashlib.sha256(old).hexdigest()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);iso=root/'original.iso';iso.write_bytes(b'P'*16+old+b'S'*16)
            with patch('pes6_iso.locate',return_value={'default.xex':(16,64,0)}):
                files=build(iso,root/'extracted',{},'img',{'default.xex':(sha,new)})
                self.assertEqual(Path(files[0]).name,'default.xex');self.assertEqual(Path(files[0]).read_bytes(),new)
                files=build(iso,root/'iso',{},'iso',{'default.xex':(sha,new)})
                self.assertEqual(Path(files[0]).read_bytes(),b'P'*16+new+b'S'*16)
                with self.assertRaises(ValueError):build(iso,root/'bad',{},'iso',{'default.xex':('wrong',new)})
                self.assertFalse((root/'bad').exists())
            self.assertEqual(iso.read_bytes(),b'P'*16+old+b'S'*16)

if __name__=='__main__':unittest.main()
