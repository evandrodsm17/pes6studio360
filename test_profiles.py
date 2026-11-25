import io
import struct
import tempfile
import unittest
from pathlib import Path
from pes6_binary import profiles6670
from pes6_profiles import color5551, inspect


class ProfilesTests(unittest.TestCase):
    def test_color_hypothesis(self):
        self.assertEqual(color5551(0xffff), [255,255,255,255])
        self.assertEqual(color5551(1), [0,0,0,255])
        self.assertEqual(color5551(0xf801), [255,0,0,255])
        self.assertEqual(color5551(0), [0,0,0,0])
        for bad in (-1,65536,'ffff',True):
            with self.assertRaises(ValueError):color5551(bad)

    @unittest.skipUnless((Path(__file__).parent/'cv.img').exists(), 'Local game data not supplied')
    def test_real_profiles(self):
        report=inspect(Path(__file__).parent)
        self.assertEqual([p['candidate_records'] for p in report['parts']],[189,16])
        self.assertEqual(report['associations'],[])
        for p in report['parts']:
            self.assertEqual(len(p['subrecords']),p['candidate_records']*4)
            for row in p['subrecords']:
                self.assertEqual(row['offset'],row['candidate_record']*728+row['subrecord']*108)
                self.assertEqual(row['unpacked_offset'],p['unpacked_offset']+row['offset'])
            for field in p['metadata_fields']:
                self.assertEqual(sum(v['count'] for v in field['values']),len(p['subrecords']))

    def test_malformed_structure(self):
        for raw in (bytes(727),bytes(729)):
            with self.assertRaises(ValueError):profiles6670(raw)
        for offset in (2,3,432,727):
            raw=bytearray(728);raw[offset]=1
            with self.assertRaises(ValueError):profiles6670(raw)
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);(p/'cv.img').write_bytes(b'AFS\0'+struct.pack('<I',0))
            with self.assertRaises(ValueError):inspect(p)

if __name__=='__main__':unittest.main()
