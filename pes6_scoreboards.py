"""Source-bound scoreboard atlases; no runtime competition selector is assumed."""
import base64
import hashlib
import struct
import zlib
from pes6_binary import afs_index, parts, unwrap
from pes6_fixed import EntryReplacement, entry_changes
from pes6_we00_catalogo import decode
from pes6_we00_edit import encode, image_bytes

# Names read from the original English archive's part-name footer.
RESOURCES = {
    'hud': ('HUD: relógio e elementos de jogo', ((249, 0, 'game2d_00'),)),
    'panels': ('Placas e elementos auxiliares', ((249, 1, 'game2d_01'),)),
    'numbers': ('Números do placar', ((249, 2, 'game2d_number'), (253, 0, 'game2d_number'))),
    'replay': ('Indicador de replay', ((249, 3, 'replay'),)),
}


class ScoreboardEditor:
    def __init__(self, source):
        self.source = source
        self.entries = {}; self.raw = {}; self.edits = {}
        with source.open('rb') as f:
            index = afs_index(f)
            for entry in (249, 253):
                offset, size = index[entry]; f.seek(offset)
                self.entries[entry] = f.read(size)
        for key, (_, locations) in RESOURCES.items():
            for entry, part, name in locations:
                data = unwrap(self.entries[entry])
                offset, size, pointer, raw = parts(data)[part]
                if not pointer or data[pointer:pointer+16].split(b'\0')[0] != name.encode():
                    raise ValueError('Nome de recurso de placar divergente')
                if decode(raw) is None: raise ValueError('Textura de placar não suportada')
                if key in self.raw and self.raw[key] != raw:
                    raise ValueError('Cópias dos números do placar divergentes')
                self.raw[key] = raw

    def stage(self, key, png):
        if key not in self.raw: raise ValueError('Recurso de placar inválido')
        encoded = encode(self.raw[key], png, 'strict')
        candidate = dict(self.edits)
        if encoded == self.raw[key]: candidate.pop(key, None)
        else: candidate[key] = encoded
        self.build_entries(candidate)  # Validate AFS capacity before accepting the edit.
        self.edits = candidate

    def preview(self, key, original=False):
        raw = self.raw[key] if original else self.edits.get(key, self.raw[key])
        return image_bytes(decode(raw)[0])

    def build_entries(self, edits=None):
        edits = self.edits if edits is None else edits
        by_entry = {}
        for key, raw in edits.items():
            if key not in self.raw or len(raw) != len(self.raw[key]) or raw[:16] != self.raw[key][:16] or decode(raw) is None:
                raise ValueError('Textura de placar inválida')
            for entry, part, name in RESOURCES[key][1]:
                by_entry.setdefault(entry, {})[part] = raw
        result = {}
        for entry, changes in by_entry.items():
            raw = self.entries[entry]; data = bytearray(unwrap(raw)); rows = parts(data)
            for part, replacement in changes.items():
                offset, size, _, _ = rows[part]
                data[offset:offset+size] = replacement
            c, u = struct.unpack_from('>II', raw, 8)
            payload = zlib.compress(bytes(data), 9)
            new = raw[:8] + struct.pack('>II', len(payload), len(data)) + payload + raw[16+c:]
            if unwrap(new) != data: raise ValueError('Reconstrução de placar divergente')
            result[entry] = EntryReplacement(hashlib.sha256(raw).hexdigest(), new, True)
        if result:
            with self.source.open('rb') as f:
                entry_changes(f, 0, self.source.stat().st_size, result)
        return result

    def project(self):
        return {key: {'source_sha256': hashlib.sha256(self.raw[key]).hexdigest(),
                      'data': base64.b64encode(raw).decode('ascii')} for key, raw in self.edits.items()}

    def validated_project(self, data):
        edits = {}; rows = data.get('scoreboard_textures', {})
        if not isinstance(rows, dict): raise ValueError('Dados de placar inválidos')
        for key, row in rows.items():
            if key not in self.raw or row.get('source_sha256') != hashlib.sha256(self.raw[key]).hexdigest():
                raise ValueError('Placar vinculado a outra textura original')
            edits[key] = base64.b64decode(row['data'], validate=True)
        self.build_entries(edits)
        return edits

    def state(self):
        return {'automatic_selection': False, 'runtime_verified': False,
                'scope': 'Um conjunto global de texturas; troca automática por competição ainda não implementada.',
                'resources': [{'key': key, 'label': label, 'width': decode(self.raw[key])[0].width,
                    'height': decode(self.raw[key])[0].height, 'modified': key in self.edits,
                    'locations': [{'entry': e, 'part': p, 'name': n} for e, p, n in locations]}
                    for key, (label, locations) in RESOURCES.items()],
                'pending': len(self.edits)}
