import csv
import tempfile
import unittest
from pathlib import Path
from pes6_evidence import load_evidence, verify_kits
from pes6_binary import afs_index

ROOT=Path(__file__).parent

@unittest.skipUnless((ROOT/'cv.img').exists() and (ROOT/'research/kit_candidates.csv').exists(), 'Local game research not supplied')
class EvidenceTests(unittest.TestCase):
    def test_real_kit_sources(self):
        report=load_evidence(ROOT,ROOT/'research/evidence.json')
        self.assertEqual(report['kit_verification'],dict(entries=410,textures=820,status='source_verified'))
        self.assertEqual(report['associations'],[])

    def test_malformed_catalogs(self):
        with (ROOT/'research/kit_candidates.csv').open(encoding='utf-8-sig',newline='') as f:
            original=list(csv.DictReader(f))
        changed=[dict(r) for r in original]
        changed[0]['sha256']='0'*64
        bad_offset=[dict(r) for r in original]
        bad_offset[0]['part_offset']='0'
        outside=[dict(r) for r in original]
        outside[0]['entry']='-1'
        with tempfile.TemporaryDirectory() as temp, (ROOT/'cv.img').open('rb') as binary:
            index=afs_index(binary); catalog=Path(temp)/'kits.csv'
            for rows in (original[:-1],original+[original[0]],changed,bad_offset,outside):
                with self.subTest(rows=len(rows),first=rows[0]):
                    with catalog.open('w',encoding='utf-8',newline='') as f:
                        writer=csv.DictWriter(f,fieldnames=list(original[0]))
                        writer.writeheader();writer.writerows(rows)
                    with self.assertRaises(ValueError):verify_kits(binary,index,catalog)

if __name__=='__main__':unittest.main()
