from pathlib import Path
import struct
import unittest
from pes6_scoreboard_probe import analyze, relative_call


class ScoreboardProbeTests(unittest.TestCase):
    def test_signed_relative_calls_and_reject_non_calls(self):
        for delta in (64, -64):
            word = 0x48000001 | (delta & 0x3fffffc)
            self.assertEqual(relative_call(struct.pack('>I', word), 0, 0x82001000), 0x82001000+delta)
        with self.assertRaises(ValueError): relative_call(bytes(4), 0, 0)

    @unittest.skipUnless((Path(__file__).parent/'default.xex').is_file(), 'Original game data not included')
    def test_real_resource_call_candidates(self):
        data = analyze(Path(__file__).parent/'default.xex')
        self.assertEqual([r['resource_candidate'] for r in data['requests']], [2706, 2703])
        self.assertEqual({r['callee'] for r in data['requests']}, {'0x827292e0'})
        self.assertIsNone(data['competition_state_address'])
        self.assertFalse(data['automatic_selection_implemented'])
        self.assertEqual([r['value'] for r in data['packed_tokens']],['0x020000f9']*2)
        self.assertEqual({r['callee'] for r in data['packed_tokens']},{'0x82729548','0x82729598'})
