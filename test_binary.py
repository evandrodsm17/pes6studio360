import io,struct,unittest,zlib
from pathlib import Path
from pes6_binary import afs_index,unwrap,parts,records,players,rosters,profiles6670

class BinaryTests(unittest.TestCase):
    def test_profile_layout(self):
        self.assertEqual(len(profiles6670(bytes(728))),4)
        for offset in (2,432):
            d=bytearray(728);d[offset]=1
            with self.assertRaises(ValueError):profiles6670(d)
    def test_report_source_binding(self):
        from pes6_evidence import load_evidence
        import tempfile,json
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);raw=b'AFS\0'+struct.pack('<III',1,16,2)+b'ab'
            (p/'cv.img').write_bytes(raw)
            import hashlib
            data={'schema':1,'entries':[dict(entry=0,afs_offset=16,size=2,sha256=hashlib.sha256(b'ab').hexdigest())]}
            report=p/'evidence.json';report.write_text(json.dumps(data))
            self.assertEqual(load_evidence(p,report)['status'],'source_verified')
            (p/'cv.img').write_bytes(raw[:-1]+b'c')
            with self.assertRaises(ValueError):load_evidence(p,report)
    def test_afs_bounds(self):
        self.assertEqual(afs_index(io.BytesIO(b'AFS\0'+struct.pack('<III',1,16,2)+b'ab')),[(16,2)])
        for d in (b'',b'AFS\0'+struct.pack('<III',1,16,99)):
            with self.assertRaises(ValueError):afs_index(io.BytesIO(d))
    def test_wesys(self):
        for stored in (False,True):
            x=b'payload';c=x if stored else zlib.compress(x)
            d=(b'\1\1\0' if stored else b'\0\1\1')+b'WESYS'+struct.pack('>II',len(c),0 if stored else len(x))+c
            self.assertEqual(unwrap(d),x)
            with self.assertRaises(ValueError):unwrap(d[:-1])
        with self.assertRaises(ValueError):unwrap(b'\0\1\1WESYS'+struct.pack('>II',1,100)+b'x')
    def test_parts(self):
        d=struct.pack('>IIIII',1,8,20,3,0xfffffff0)+b'abc'
        self.assertEqual(parts(d)[0][3],b'abc')
        for bad in (d[:-1],struct.pack('>IIIII',1,8,8,3,0)+b'abc'):
            with self.assertRaises(ValueError):parts(bad)
    def test_records_and_endian(self):
        d=bytes(152)+b'Buffon\0'+bytes(145);p=players(d)
        self.assertEqual(p[1]['name'],'Buffon')
        r=rosters(struct.pack('>32H',1,*([65535]*31)),p)
        self.assertEqual(r[0]['name'],'Buffon');self.assertTrue(r[1]['empty'])
        with self.assertRaises(ValueError):records(b'123',2)
    def test_real_sources(self):
        root=Path(__file__).parent
        if not (root/'cv.img').exists():self.skipTest('Game source not present')
        with (root/'cv.img').open('rb') as f:
            idx=afs_index(f)
            for entry,count in ((6667,4),(6668,4),(6670,2),(6671,183)):
                o,s=idx[entry];f.seek(o);pp=parts(unwrap(f.read(s)))
                self.assertEqual(len(pp),count)
                if entry in (6667,6668):
                    p=players(pp[0][3]);r=rosters(pp[1][3],p)
                    self.assertFalse([x for x in r if not x['empty'] and not x['valid']])
                for i,(_,_,_,d) in enumerate(pp):
                    self.assertEqual(d,(root/'cv_extraido_v03'/str(entry)/f'part_{i:03}.bin').read_bytes())

if __name__=='__main__':unittest.main()
