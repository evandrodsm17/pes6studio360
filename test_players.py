from pathlib import Path
import unittest
from unittest.mock import patch
from pes6_binary import parts, unwrap
from pes6_players import PlayerEditor, name_bytes

ROOT = Path(__file__).parent


class NameFieldTests(unittest.TestCase):
    def test_utf8_limits_and_control_characters(self):
        self.assertEqual(name_bytes('João', 8), 'João'.encode()+bytes(3))
        for value in ('', 'X\0Y', 'A\nB', 'é'*23):
            with self.assertRaises(ValueError): name_bytes(value, 46)
        self.assertEqual(name_bytes('', 16, True), bytes(16))


class RealPlayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (ROOT/'cv.img').is_file(): raise unittest.SkipTest('Original game data not included')
        cls.editor = PlayerEditor(ROOT/'cv.img')

    def setUp(self):
        self.editor.edits = {}; self.editor.squads = {}

    def test_name_changes_only_selected_fields_in_one_database(self):
        e = self.editor; e.stage_player(6668, 144, 'Frank Lampard', 'LAMPARD')
        changes = e.build_entries(); self.assertEqual(set(changes), {6668})
        before = e.payloads[6668]; after = unwrap(changes[6668].data)
        off = parts(before)[0][0]+144*152
        self.assertEqual(before[:off], after[:off]); self.assertEqual(before[off+62:], after[off+62:])
        self.assertEqual(after[off:off+46], name_bytes('Frank Lampard', 46))
        e.stage_player(6668, 144, e.rows[6668][144]['name'], e.rows[6668][144]['shirt_name'])
        self.assertFalse(e.edits)

    def test_roster_and_number_bytes_are_bounded(self):
        e = self.editor; rows = e.original_squad(6668, 69)
        rows[0], rows[1] = rows[1], rows[0]; rows[0]['number'] = 33
        e.stage_squad(6668, 69, rows)
        after = unwrap(e.build_entries()[6668].data); before = e.payloads[6668]
        ps = parts(before); allowed = set(range(ps[1][0]+69*64, ps[1][0]+70*64)) | set(range(ps[2][0]+69*32, ps[2][0]+70*32))
        self.assertTrue(all(i in allowed for i, (a, b) in enumerate(zip(before, after)) if a != b))
        self.assertEqual(parts(after)[0][3], ps[0][3]); self.assertEqual(parts(after)[3][3], ps[3][3])

    def test_transfer_preserves_other_registrations_and_is_atomic(self):
        e = self.editor; source = 69; target = 64; position = 2  # Terry, also in England.
        target_rows = e.original_squad(6668, target); target_rows[-1] = {'player_id': 65535, 'number': 255}
        e.stage_squad(6668, target, target_rows)
        before = dict(e.squads)
        with patch.object(e, 'build_entries', side_effect=ValueError('capacity')):
            with self.assertRaises(ValueError): e.transfer(6668, source, position, target)
        self.assertEqual(before, e.squads)
        england = e.original_squad(6668, 6); e.transfer(6668, source, position, target)
        self.assertEqual(e.squads[6668, source][position]['player_id'], 65535)
        self.assertIn(141, [r['player_id'] for r in e.squads[6668, target]])
        self.assertNotIn((6668, 6), e.squads); self.assertEqual(england, e.original_squad(6668, 6))

    def test_validation_and_project_roundtrip(self):
        e = self.editor; rows = e.original_squad(6668, 69); rows[1] = dict(rows[0])
        with self.assertRaises(ValueError): e.stage_squad(6668, 69, rows)
        rows = e.original_squad(6668, 69); rows[0]['player_id'] = 4300
        with self.assertRaises(ValueError): e.stage_squad(6668, 69, rows)
        rows = e.original_squad(6668, 69); rows[0]['number'] = 100
        with self.assertRaises(ValueError): e.stage_squad(6668, 69, rows)
        self.assertFalse(e.squads)
        e.stage_player(6667, 144, 'Frank Lampard', 'LAMPARD')
        e.stage_player(6668, 144, 'Lampard Test', 'LAMPARD')
        edits, squads = e.validated_project({'player_database': e.project()})
        self.assertEqual(edits, e.edits); self.assertEqual(squads, e.squads)
        bad = e.project(); bad['source_sha256'] = '0'*64
        with self.assertRaises(ValueError): e.validated_project({'player_database': bad})


if __name__ == '__main__': unittest.main()
