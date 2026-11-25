from collections import Counter
from pathlib import Path
import struct
import unittest
from pes6_palette_probe import signature, palette_rgb, compare, analyze


class PaletteProbeTests(unittest.TestCase):
    def test_known_channels(self):
        for layout,red in (('RGBA5551',0xf801),('RGB565',0xf800),('ARGB1555',0xfc00)):
            self.assertEqual(signature(red,layout),(31,0,0))
        self.assertEqual(signature(0x7e0,'RGB565'),(0,63,0))
        for word,layout in ((-1,'RGB565'),(65536,'RGB565'),(True,'RGB565'),(0,'unknown')):
            with self.assertRaises(ValueError):signature(word,layout)

    def test_membership_is_not_association(self):
        rows=compare(Counter({0xf801:3,1:2}),{(255,0,0),(0,0,0)})
        row=rows[0]
        self.assertEqual(row['matched_distinct_colors'],2)
        self.assertEqual(row['matched_occurrences'],5)
        self.assertEqual(row['palette_space_fraction'],2/32768)
        self.assertEqual(len(rows),6)
        self.assertIsNone(compare(Counter(),set())[0]['distinct_match_fraction'])

    def test_we00_bounds(self):
        raw=bytearray(b'WE00'+struct.pack('>HBB4H',4100,3,8,512,512,16,1040)+bytes(263168))
        raw[16:20]=bytes((255,0,0,255))
        self.assertEqual(palette_rgb(raw),{(255,0,0),(0,0,0)})
        for bad in (b'',raw[:-1],b'NOPE'+raw[4:]):
            with self.assertRaises(ValueError):palette_rgb(bad)

    @unittest.skipUnless((Path(__file__).parent/'cv.img').exists(), 'Local game data not supplied')
    def test_real_sources(self):
        report=analyze(Path(__file__).parent)
        self.assertEqual(len(report['kit_sources']),410)
        self.assertEqual(report['word_occurrences'],17220)
        self.assertEqual(report['odd_word_occurrences'],17220)
        self.assertEqual(report['unique_words'],436)
        self.assertEqual(report['associations'],[])
        self.assertEqual(len(report['comparisons']),6)
        for row in report['comparisons']:
            self.assertLessEqual(row['matched_distinct_colors'],row['distinct_profile_colors'])
            self.assertLessEqual(row['matched_occurrences'],17220)

if __name__=='__main__':unittest.main()
