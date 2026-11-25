"""Fixed-layout player names, registrations and squad numbers in PAL CV databases."""
import hashlib
import struct
import zlib
from pathlib import Path
from pes6_binary import afs_index, parts, players, unwrap
from pes6_fixed import EntryReplacement, entry_changes

CV_SHA256 = 'c3c3f2aa3bd1623b650c9f356b9da85b9878feec0aceb89ab250a9abb5eb24dc'
DATABASES = {6667: (4415, 188), 6668: (4210, 189)}
ABILITY_LABELS = ('Ataque','Defesa','Equilíbrio','Resistência','Velocidade','Aceleração',
    'Resposta','Agilidade','Precisão de drible','Velocidade de drible','Precisão de passe curto',
    'Velocidade de passe curto','Precisão de passe longo','Velocidade de passe longo',
    'Precisão de chute','Força de chute','Técnica de chute','Precisão de falta','Efeito',
    'Cabeceio','Impulsão','Trabalho em equipe','Técnica','Agressividade','Mentalidade','Goleiro')


def name_bytes(value, capacity, allow_empty=False):
    if not isinstance(value, str): raise ValueError('Nome inválido')
    value = value.strip()
    if (not value and not allow_empty) or any(not c.isprintable() for c in value):
        raise ValueError('Nome vazio ou com caracteres de controle')
    raw = value.encode('utf-8')
    if len(raw) >= capacity: raise ValueError(f'Limite de {capacity-1} bytes UTF-8')
    return raw + bytes(capacity-len(raw))


class PlayerEditor:
    def __init__(self, source):
        self.source = Path(source); self.entries = {}; self.payloads = {}; self.rows = {}
        self.edits = {}; self.squads = {}; self.abilities = {}
        with self.source.open('rb') as f:
            if hashlib.file_digest(f, 'sha256').hexdigest() != CV_SHA256:
                raise ValueError('Editor de jogadores exige cv.img PAL original verificado')
            index = afs_index(f)
            for entry, (count, teams) in DATABASES.items():
                offset, size = index[entry]; f.seek(offset); raw = f.read(size)
                data = unwrap(raw); ps = parts(data)
                if len(ps) != 4 or [len(p) for _, _, _, p in ps[:3]] != [count*152, teams*64, teams*32]:
                    raise ValueError('Estrutura de jogadores/elencos divergente')
                self.entries[entry] = raw; self.payloads[entry] = data
                self.rows[entry] = players(ps[0][3])
                for (pid,) in struct.iter_unpack('>H', ps[1][3]):
                    if pid not in (0, 65535) and pid >= count: raise ValueError('ID de jogador fora da base')

    def validate_player(self, entry, pid, name, shirt_name):
        if entry not in DATABASES or type(pid) is not int or not 0 < pid < DATABASES[entry][0]:
            raise ValueError('Jogador inválido; registro zero é reservado')
        name_bytes(name, 46); name_bytes(shirt_name, 16, True)
        return {'name': name.strip(), 'shirt_name': shirt_name.strip()}

    def stage_player(self, entry, pid, name, shirt_name):
        values = self.validate_player(entry, pid, name, shirt_name)
        candidate = dict(self.edits)
        original = {k: self.rows[entry][pid][k] for k in values}
        if values == original: candidate.pop((entry, pid), None)
        else: candidate[entry, pid] = values
        self.build_entries(candidate, self.squads)
        self.edits = candidate

    def original_squad(self, entry, slot):
        if entry not in DATABASES or type(slot) is not int or not 0 <= slot < DATABASES[entry][1]:
            raise ValueError('Elenco inválido')
        ps = parts(self.payloads[entry]); ids = struct.unpack_from('>32H', ps[1][3], slot*64)
        return [{'player_id': pid, 'number': ps[2][3][slot*32+i]} for i, pid in enumerate(ids)]

    def validate_squad(self, entry, slot, rows):
        self.original_squad(entry, slot)
        if not isinstance(rows, list) or len(rows) != 32: raise ValueError('Elenco exige exatamente 32 posições')
        seen = set(); validated = []
        for row in rows:
            if not isinstance(row, dict): raise ValueError('Posição de elenco inválida')
            pid, number = row.get('player_id'), row.get('number')
            if type(pid) is not int or (pid not in (0, 65535) and not 0 < pid < DATABASES[entry][0]):
                raise ValueError('ID fora da base selecionada')
            if type(number) is not int or not (0 <= number <= 99 or number == 255):
                raise ValueError('Número deve estar entre 0 e 99, ou 255 (não definido)')
            if pid not in (0, 65535):
                if pid in seen: raise ValueError('Jogador repetido no mesmo elenco')
                seen.add(pid)
            validated.append({'player_id': pid, 'number': number})
        return validated

    def stage_squad(self, entry, slot, rows):
        values = self.validate_squad(entry, slot, rows); candidate = dict(self.squads)
        if values == self.original_squad(entry, slot): candidate.pop((entry, slot), None)
        else: candidate[entry, slot] = values
        self.build_entries(self.edits, candidate)
        self.squads = candidate

    def transfer(self, entry, source, position, target):
        if source == target: raise ValueError('Selecione outro elenco de destino')
        if type(position) is not int or not 0 <= position < 32: raise ValueError('Posição inválida')
        a = [dict(r) for r in self.squads.get((entry, source), self.original_squad(entry, source))]
        b = [dict(r) for r in self.squads.get((entry, target), self.original_squad(entry, target))]
        row = a[position]
        if row['player_id'] in (0, 65535): raise ValueError('A posição de origem está vazia')
        if any(r['player_id'] == row['player_id'] for r in b): raise ValueError('Jogador já está no destino')
        free = next((i for i, r in enumerate(b) if r['player_id'] in (0, 65535)), None)
        if free is None: raise ValueError('Elenco de destino sem vaga')
        b[free] = row; a[position] = {'player_id': 65535, 'number': 255}
        candidate = dict(self.squads)
        for slot, rows in ((source, a), (target, b)):
            rows = self.validate_squad(entry, slot, rows)
            if rows == self.original_squad(entry, slot): candidate.pop((entry, slot), None)
            else: candidate[entry, slot] = rows
        self.build_entries(self.edits, candidate)
        self.squads = candidate

    def original_abilities(self, entry, pid):
        self.validate_player(entry,pid,'Valid','')
        raw=parts(self.payloads[entry])[0][3][pid*152+70:pid*152+96]
        return [value>>1 for value in raw]

    def validate_abilities(self,entry,pid,values):
        self.original_abilities(entry,pid)
        if not isinstance(values,list) or len(values)!=26 or any(type(v) is not int or not 0<=v<=99 for v in values):
            raise ValueError('Informe exatamente 26 atributos inteiros entre 0 e 99')
        return list(values)

    def stage_abilities(self,entry,pid,values):
        values=self.validate_abilities(entry,pid,values);candidate=dict(self.abilities)
        if values==self.original_abilities(entry,pid):candidate.pop((entry,pid),None)
        else:candidate[entry,pid]=values
        self.build_entries(self.edits,self.squads,candidate)
        self.abilities=candidate

    def build_entries(self, edits=None, squads=None, abilities=None):
        edits = self.edits if edits is None else edits
        squads = self.squads if squads is None else squads
        abilities = self.abilities if abilities is None else abilities
        changed = {}
        for (entry, pid), values in edits.items():
            values = self.validate_player(entry, pid, **values)
            data = changed.setdefault(entry, bytearray(self.payloads[entry])); offset = parts(data)[0][0] + pid*152
            data[offset:offset+46] = name_bytes(values['name'], 46)
            data[offset+46:offset+62] = name_bytes(values['shirt_name'], 16, True)
        for (entry, slot), rows in squads.items():
            rows = self.validate_squad(entry, slot, rows)
            data = changed.setdefault(entry, bytearray(self.payloads[entry])); ps = parts(data)
            struct.pack_into('>32H', data, ps[1][0]+slot*64, *(r['player_id'] for r in rows))
            data[ps[2][0]+slot*32:ps[2][0]+(slot+1)*32] = bytes(r['number'] for r in rows)
        for (entry,pid),values in abilities.items():
            values=self.validate_abilities(entry,pid,values)
            data=changed.setdefault(entry,bytearray(self.payloads[entry]));offset=parts(data)[0][0]+pid*152+70
            for i,value in enumerate(values):data[offset+i]=(data[offset+i]&1)|(value<<1)
        result = {}
        for entry, data in changed.items():
            original = self.entries[entry]; c, _ = struct.unpack_from('>II', original, 8)
            payload = zlib.compress(bytes(data), 9)
            raw = original[:8]+struct.pack('>II', len(payload), len(data))+payload+original[16+c:]
            if unwrap(raw) != data: raise ValueError('Reconstrução da base divergente')
            result[entry] = EntryReplacement(hashlib.sha256(original).hexdigest(), raw, True)
        if result:
            with self.source.open('rb') as f: entry_changes(f, 0, self.source.stat().st_size, result)
        return result

    def project(self):
        return {'source_sha256': CV_SHA256,
                'players': [{'database': e, 'player_id': p, **v} for (e, p), v in sorted(self.edits.items())],
                'squads': [{'database': e, 'slot': s, 'rows': rows} for (e, s), rows in sorted(self.squads.items())],
                'abilities':[{'database':e,'player_id':pid,'values':v} for (e,pid),v in sorted(self.abilities.items())]}

    def probe(self):
        """Return an isolated diagnostic patch without touching pending edits."""
        changes = {}; markers = []
        for entry in DATABASES:
            if self.rows[entry][144]['name'] != 'Lampard' or not any(r['player_id'] == 144 for r in self.original_squad(entry, 69)):
                raise ValueError('Controle Lampard/Chelsea divergente')
            values = {'name': f'Lampard DB{entry}', 'shirt_name': f'DB{entry}'}
            changes[entry, 144] = self.validate_player(entry, 144, **values)
            markers.append({'database': entry, 'player_id': 144, **values})
        return self.build_entries(changes, {}, {}), {'source_sha256': CV_SHA256, 'markers': markers,
            'isolated_test': True, 'runtime_verified': False,
            'instructions': 'Use os arquivos deste teste numa cópia do jogo. Confira Lampard no Chelsea/London FC e na Inglaterra em cada modo. DB6667 ou DB6668 identifica a origem do nome nessa tela; o resultado não comprova todos os modos. Se nenhum marcador aparecer, confira os arquivos usados e a influência do option file/save. Não apague seus saves.'}

    def validated_project(self, data):
        d = data.get('player_database', {}); edits = {}; squads = {}; abilities={}
        if not isinstance(d, dict): raise ValueError('Base de jogadores inválida')
        if d and d.get('source_sha256') != CV_SHA256: raise ValueError('Projeto vinculado a outro cv.img')
        for row in d.get('players', []):
            key = row['database'], row['player_id']
            if key in edits: raise ValueError('Jogador repetido no projeto')
            edits[key] = self.validate_player(*key, row['name'], row['shirt_name'])
        for row in d.get('squads', []):
            key = row['database'], row['slot']
            if key in squads: raise ValueError('Elenco repetido no projeto')
            squads[key] = self.validate_squad(*key, row['rows'])
        for row in d.get('abilities',[]):
            key=row['database'],row['player_id']
            if key in abilities:raise ValueError('Atributos repetidos no projeto')
            abilities[key]=self.validate_abilities(*key,row['values'])
        self.build_entries(edits, squads, abilities)
        return edits, squads, abilities

    def state(self, entry, labels):
        if entry not in DATABASES: raise ValueError('Base inválida')
        result = []
        for row in self.rows[entry][1:]:
            pid = row['player_id']; result.append(dict(row, **{'name': self.edits.get((entry, pid), row)['name'],
                'shirt_name': self.edits.get((entry, pid), row)['shirt_name'], 'modified': (entry, pid) in self.edits or (entry,pid) in self.abilities}))
        return {'database': entry, 'players': result,
                'teams': [{'slot': slot, 'reference_name': labels[slot] if entry == 6668 and slot < len(labels) else '',
                           'modified': (entry, slot) in self.squads} for slot in range(DATABASES[entry][1])],
                'pending': len(self.edits)+len(self.squads)+len(self.abilities), 'runtime_verified': False,
                'note': 'Bases independentes. Confirme o elenco pelos jogadores; os nomes de equipes são referências para a base 6668. A base ativa ainda exige teste no jogo. Nomes são compartilhados por todas as equipes que utilizam o mesmo ID nesta base. A ordem do elenco não define a formação tática.'}
