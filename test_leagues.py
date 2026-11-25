import csv
from pathlib import Path
import struct
import unittest
import io,hashlib
from pes6_leagues import parse_strings,replace_strings,LeagueEditor
from pes6_binary import parts,unwrap
from pes6_fixed import entry_changes,EntryReplacement

ROOT=Path(__file__).parent


def fixture():
    names=[(105,'England League'),(106,'Ligue 1')];offset=8+12*len(names)
    header=struct.pack('>IHH',len(names),102,0);pool=b''
    for sid,name in names:
        raw=name.encode()+b'\0';header+=struct.pack('>4HI',sid,0,len(raw),len(name),offset)
        pool+=raw;offset+=len(raw)
    return header+pool


class StringTableTests(unittest.TestCase):
    def test_unicode_lengths_and_untouched_label(self):
        data=fixture();new=replace_strings(data,{105:'Brasileirão',106:'Liga 1'})
        self.assertEqual(len(data),len(new))
        rows=parse_strings(new)
        self.assertEqual([r['text'] for r in rows],['Brasileirão','Liga 1'])
        self.assertEqual(rows[0]['size'],len('Brasileirão'.encode())+1)
        self.assertEqual([r['offset'] for r in rows],[r['offset'] for r in parse_strings(data)])
        only=replace_strings(data,{106:'Liga 1'});first=parse_strings(data)[0]
        self.assertEqual(only[first['offset']:first['offset']+first['size']],data[first['offset']:first['offset']+first['size']])

    def test_malformed_and_overlong_input(self):
        data=fixture()
        for raw in (b'',data[:10],data[:-1]):
            with self.assertRaises(ValueError):parse_strings(raw)
        for offset,value in ((0,10000),(16,1),(28,32)):
            bad=bytearray(data);struct.pack_into('>I',bad,offset,value)
            with self.assertRaises(ValueError):parse_strings(bad)
        for name in ('', 'Ligue\0X','A'*15):
            with self.assertRaises(ValueError):replace_strings(data,{105:name})

    def test_afs_growth_uses_only_empty_allocated_space(self):
        raw=bytearray(8200);raw[:8]=b'AFS\0'+struct.pack('<I',2)
        struct.pack_into('<4I',raw,8,4096,16,8192,8);raw[4096:4112]=b'A'*16;raw[8192:]=b'B'*8
        change=EntryReplacement(hashlib.sha256(b'A'*16).hexdigest(),b'C'*64,True)
        mods=entry_changes(io.BytesIO(raw),0,len(raw),{0:change});out=bytearray(raw)
        for offset,value in mods:out[offset:offset+len(value)]=value
        self.assertEqual(struct.unpack_from('<I',out,12)[0],64)
        self.assertEqual(out[4096:4160],b'C'*64);self.assertEqual(out[8192:],b'B'*8)
        bad=bytearray(raw);bad[4112]=1
        with self.assertRaises(ValueError):entry_changes(io.BytesIO(bad),0,len(bad),{0:change})
        huge=EntryReplacement(change.source_sha256,b'C'*5000,True)
        with self.assertRaises(ValueError):entry_changes(io.BytesIO(raw),0,len(raw),{0:huge})


class RealLeagueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (ROOT/'rv_e_limpo.img').exists() or not (ROOT/'cv_we00_texturas/index.csv').exists():
            raise unittest.SkipTest('Local PAL game data not supplied')
        items=[];paths=[]
        with (ROOT/'cv_we00_texturas/index.csv').open(encoding='utf-8-sig',newline='') as f:
            for r in csv.DictReader(f):
                if not r['resource'].startswith('2700_'):continue
                items.append({'id':len(paths),'kind':'WE00','name':r['resource'],'entry':'2700'})
                paths.append(ROOT/'cv_we00_texturas'/r['file'])
        cls.editor=LeagueEditor(ROOT,items,paths)

    def test_real_labels_and_no_automatic_logo_mapping(self):
        editor=self.editor;state=editor.state({})
        self.assertEqual(editor.rows[105]['text'],'England League')
        self.assertEqual(editor.rows[106]['text'],'Ligue 1')
        self.assertEqual(editor.rows[108]['text'],'Serie A')
        self.assertEqual(len(state['logos']),27)
        self.assertTrue(all(r['logo'] is None for r in state['records']))

    def test_two_real_entries_change_only_the_selected_part(self):
        editor=self.editor;pending={105:'Premier League',106:'Liga 1'}
        for entry,replacement in editor.build_entries(pending).items():
            before=parts(unwrap(editor.entries[entry]));after=parts(unwrap(replacement.data));target=editor.parts[entry][0]
            for i,(a,b) in enumerate(zip(before,after)):
                self.assertEqual(a[2]-before[0][2],b[2]-after[0][2])
                if i!=target:self.assertEqual(a[3],b[3])
            names={r['id']:r['text'] for r in parse_strings(after[target][3])}
            self.assertEqual(names[105],'Premier League');self.assertEqual(names[106],'Liga 1')
        with self.assertRaises(ValueError):editor.validate_name(106,'A'*65)

if __name__=='__main__':unittest.main()
