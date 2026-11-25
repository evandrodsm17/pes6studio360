import base64
from pathlib import Path
import unittest
from PIL import Image
from pes6_binary import parts, unwrap
from pes6_scoreboards import ScoreboardEditor
from pes6_we00_edit import image_bytes

ROOT = Path(__file__).parent


class ScoreboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = ROOT/'rv_e_limpo.img'
        if not source.is_file(): raise unittest.SkipTest('Original game data not included')
        cls.source = source

    def setUp(self):
        self.editor = ScoreboardEditor(self.source)

    def changed_png(self, key):
        import io
        with Image.open(io.BytesIO(self.editor.preview(key, True))) as im:
            im = im.convert('RGBA'); im.putpixel((0, 0), (17, 128, 239, 255))
            return image_bytes(im)

    def test_numbers_update_both_copies_and_preserve_every_other_part(self):
        self.editor.stage('numbers', self.changed_png('numbers'))
        changes = self.editor.build_entries()
        self.assertEqual(set(changes), {249, 253})
        copies = []
        for entry, change in changes.items():
            before = unwrap(self.editor.entries[entry]); after = unwrap(change.data)
            old_parts = parts(before); new_parts = parts(after)
            target = 2 if entry == 249 else 0
            for i, (old, new) in enumerate(zip(old_parts, new_parts)):
                self.assertEqual(old[:3], new[:3])
                if i != target: self.assertEqual(old[3], new[3])
                else: copies.append(new[3]); self.assertNotEqual(old[3], new[3])
            # Directory, all gaps and named footer remain byte-identical.
            offset, size, _, _ = old_parts[target]
            self.assertEqual(before[:offset], after[:offset])
            self.assertEqual(before[offset+size:], after[offset+size:])
        self.assertEqual(copies[0], copies[1])

    def test_project_source_binding_and_noop_restore(self):
        self.editor.stage('hud', self.changed_png('hud'))
        data = {'scoreboard_textures': self.editor.project()}
        other = ScoreboardEditor(self.source)
        self.assertEqual(other.validated_project(data), self.editor.edits)
        data['scoreboard_textures']['hud']['source_sha256'] = '0'*64
        with self.assertRaises(ValueError): other.validated_project(data)
        self.editor.stage('hud', self.editor.preview('hud', True))
        self.assertFalse(self.editor.edits)

    def test_reject_invalid_size_or_header_without_losing_edits(self):
        self.editor.stage('replay', self.changed_png('replay'))
        before = dict(self.editor.edits)
        with self.assertRaises(ValueError):
            self.editor.stage('hud', image_bytes(Image.new('RGBA', (8, 8))))
        self.assertEqual(before, self.editor.edits)
        data = {'scoreboard_textures': self.editor.project()}
        row = data['scoreboard_textures']['replay']; raw = bytearray(before['replay']); raw[8] ^= 1
        row['data'] = base64.b64encode(raw).decode()
        with self.assertRaises(ValueError): self.editor.validated_project(data)
        self.assertFalse(self.editor.state()['automatic_selection'])


if __name__ == '__main__': unittest.main()
