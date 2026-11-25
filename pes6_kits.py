"""Source-bound kit-pair editing; resource identity does not imply team identity."""
import hashlib
import io
import struct
import zlib
from PIL import Image
from pes6_binary import afs_index, parts, unwrap
from pes6_fixed import EntryReplacement, entry_changes
from pes6_players import CV_SHA256
from pes6_resource_map import kit_pairs
from pes6_we00_catalogo import decode
from pes6_we00_edit import encode, image_bytes


class KitEditor:
    def __init__(self, source, items, paths):
        self.source=source;self.paths=paths;self.entries={};self.ids={}
        with source.open('rb') as f:
            if hashlib.file_digest(f,'sha256').hexdigest()!=CV_SHA256:
                raise ValueError('Uniformes exigem cv.img PAL original verificado')
            self.index=afs_index(f)
        for pair in kit_pairs(items):
            entry=pair['entry']
            if entry in self.ids:raise ValueError('Par de uniformes ambíguo no catálogo')
            self.ids[entry]=[r['id'] for r in pair['parts']]
        self.by_id={i:(e,p) for e,ids in self.ids.items() for p,i in enumerate(ids)}

    def selected(self, entry):
        if type(entry) is not int or entry not in self.ids:raise ValueError('Entrada de uniforme inválida')
        if entry not in self.entries:
            offset,size=self.index[entry]
            with self.source.open('rb') as f:f.seek(offset);raw=f.read(size)
            ps=parts(unwrap(raw))
            if len(ps)!=2:raise ValueError('Uniforme sem as duas partes esperadas')
            for p,(_,_,_,data) in enumerate(ps):
                decoded=decode(data)
                if decoded is None or decoded[0].size!=(512,512) or decoded[1]!='indexed8':
                    raise ValueError('Formato de uniforme divergente')
                with Image.open(self.paths[self.ids[entry][p]]) as catalog:
                    if catalog.convert('RGBA').tobytes()!=decoded[0].convert('RGBA').tobytes():
                        raise ValueError('PNG do catálogo diverge do uniforme original; regenere o catálogo')
            self.entries[entry]=raw
        return self.entries[entry]

    def preview(self,entry,part,edits,original=False):
        if type(part) is not int or part not in (0,1):raise ValueError('Parte inválida')
        raw=parts(unwrap(self.selected(entry)))[part][3];i=self.ids[entry][part]
        return image_bytes(decode(raw if original or i not in edits else encode(raw,edits[i]))[0])

    def stage(self,entry,uploads,edits):
        raw=self.selected(entry);ps=parts(unwrap(raw))
        if not isinstance(uploads,dict) or not uploads:raise ValueError('Selecione pelo menos um PNG')
        candidate=dict(edits)
        for part,png in uploads.items():
            if type(part) is not int or part not in (0,1):raise ValueError('Parte inválida')
            encoded=encode(ps[part][3],png,'strict');i=self.ids[entry][part]
            if encoded==ps[part][3]:candidate.pop(i,None)
            else:
                with Image.open(io.BytesIO(png)) as im:candidate[i]=image_bytes(im.convert('RGBA'))
        self.build_entries(candidate,{entry})
        edits.clear();edits.update(candidate)

    def build_entries(self,edits,only=None):
        changed={}
        for i,png in edits.items():
            if i not in self.by_id:continue
            entry,part=self.by_id[i]
            if only is not None and entry not in only:continue
            original=self.selected(entry);data=changed.setdefault(entry,bytearray(unwrap(original)))
            offset,size,_,raw=parts(data)[part];encoded=encode(raw,png,'strict')
            data[offset:offset+size]=encoded
        result={}
        for entry,data in changed.items():
            raw=self.selected(entry);c,_=struct.unpack_from('>II',raw,8)
            payload=zlib.compress(bytes(data),9)
            new=raw[:8]+struct.pack('>II',len(payload),len(data))+payload+raw[16+c:]
            if unwrap(new)!=data:raise ValueError('Reconstrução do uniforme divergente')
            result[entry]=EntryReplacement(hashlib.sha256(raw).hexdigest(),new,True)
        if result:
            with self.source.open('rb') as f:entry_changes(f,0,self.source.stat().st_size,result)
        return result

    def state(self,edits,mapping):
        return {'source_sha256':CV_SHA256,'runtime_verified':False,
            'note':'Partes 0 e 1 são recursos independentes; principal/reserva/goleiro não foram identificados automaticamente. Vínculos de equipe são manuais e não alteram a escolha do motor do jogo.',
            'entries':[{'entry':entry,'parts':[{'part':p,'id':i,'modified':i in edits,
                'team':mapping.get(i).get('team',''),'slot':mapping.get(i).get('slot','')} for p,i in enumerate(ids)]}
                for entry,ids in sorted(self.ids.items())]}
