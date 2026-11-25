from pathlib import Path
import unittest
from pes6_club_identity import analyze,parse_rows,text_at
from pes6_binary import afs_index
from pes6_chelsea_crest_patch import validate_entry


class ClubIdentityTests(unittest.TestCase):
    @unittest.skipUnless((Path(__file__).parent/'default.xex').exists(), 'Local game data not supplied')
    def test_real_name_and_graphic_controls(self):
        report=analyze(Path(__file__).parent)
        self.assertEqual(len(report['records']),214)
        for name,value in (('Arsenal',57),('Manchester United',67),('R. Madrid',146),('London FC',62)):
            row=next(r for r in report['records'] if r['name']==name)
            self.assertEqual((row['graphic_reference_10'],row['graphic_reference_12']),(value,value))
        self.assertEqual(report['target']['runtime_verified'],report['target']['runtime_confirmation'] is not None)
        if report['target']['runtime_confirmation'] is not None:
            self.assertEqual(report['target']['runtime_confirmation']['observer'],'user')
        self.assertEqual(report['target']['kits'],[])

    def test_bad_table_bounds(self):
        for start,count in ((-1,1),(0,0),(0,2)):
            with self.assertRaises(ValueError):parse_rows(bytes(24),0,start,count)
        for address in (-1,1,24):
            with self.assertRaises(ValueError):text_at(bytes(24),0,address)

    @unittest.skipUnless((Path(__file__).parent/'research/chelsea_2006_07/entry_2710_modified.bin').exists(), 'Local crest pilot not supplied')
    def test_only_selected_real_crest_changes(self):
        root=Path(__file__).parent
        with (root/'cv.img').open('rb') as f:
            index=afs_index(f)
            for entry,size in ((2710,128),(2711,64)):
                offset,length=index[entry];f.seek(offset);old=f.read(length)
                new=(root/f'research/chelsea_2006_07/entry_{entry}_modified.bin').read_bytes()
                self.assertEqual(validate_entry(old,new).size,(size,size))
                with self.assertRaises(ValueError):validate_entry(old,old)
                with self.assertRaises(ValueError):validate_entry(old,new[:-1])
                with self.assertRaises(ValueError):validate_entry(old,new,61)

if __name__=='__main__':unittest.main()
