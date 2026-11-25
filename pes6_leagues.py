"""Source-verified English league labels and manually selected competition artwork."""
import hashlib
import json
from pathlib import Path
import re
import struct
import zlib
from pes6_binary import afs_index,parts,unwrap
from pes6_fixed import EntryReplacement,rebuild_fixed,entry_changes
from pes6_iso import KNOWN
from pes6_we00_edit import rewrite

LABEL_IDS=(0,1,2,3,4,5,6,7,8,101,102,103,104,105,106,107,108,109,110)


def parse_strings(data):
    if len(data)<8:raise ValueError('Tabela de textos truncada')
    count=struct.unpack_from('>I',data)[0]
    if not 0<count<=10000 or 8+12*count>len(data):raise ValueError('Contagem de textos inválida')
    rows=[];seen=set();spans=[]
    for i in range(count):
        header=8+i*12;sid,extra,size,chars,offset=struct.unpack_from('>4HI',data,header)
        if sid in seen or not size or offset<8+12*count or offset+size>len(data):raise ValueError('Texto duplicado ou fora da tabela')
        raw=data[offset:offset+size]
        if not raw.endswith(b'\0') or b'\0' in raw[:-1]:raise ValueError('Terminador de texto inválido')
        try:text=raw[:-1].decode('utf-8')
        except UnicodeDecodeError as exc:raise ValueError('Texto UTF-8 inválido') from exc
        if len(text)!=chars:raise ValueError('Contagem de caracteres divergente')
        rows.append({'id':sid,'extra':extra,'header_offset':header,'offset':offset,'size':size,'text':text})
        seen.add(sid);spans.append((offset,offset+size))
    spans.sort()
    if any(a[1]>b[0] for a,b in zip(spans,spans[1:])):raise ValueError('Textos sobrepostos')
    return rows


def replace_strings(data,changes):
    rows={row['id']:row for row in parse_strings(data)};out=bytearray(data)
    for sid,text in changes.items():
        if sid not in rows or not isinstance(text,str):raise ValueError('Texto de liga inválido')
        row=rows[sid];text=text.strip();encoded=text.encode('utf-8')
        if not text or not all(c.isprintable() for c in text):raise ValueError('Nome vazio ou com caracteres de controle')
        if len(encoded)>=row['size']:raise ValueError(f"Limite de {row['size']-1} bytes para este nome")
        out[row['offset']:row['offset']+row['size']]=encoded+bytes(row['size']-len(encoded))
        struct.pack_into('>HH',out,row['header_offset']+4,len(encoded)+1,len(text))
    parse_strings(out)
    return bytes(out)


def repack_strings(data,changes):
    rows=parse_strings(data)
    if set(changes)-{r['id'] for r in rows}:raise ValueError('ID de texto desconhecido')
    header=bytearray(data[:8+12*len(rows)]);pool=bytearray()
    for row in rows:
        text=changes.get(row['id'],row['text'])
        if not isinstance(text,str) or not text or not all(c.isprintable() for c in text):raise ValueError('Nome inválido')
        raw=text.encode('utf-8')+b'\0'
        if len(raw)>65535:raise ValueError('Texto excede o formato')
        struct.pack_into('>HHI',header,row['header_offset']+4,len(raw),len(text),len(header)+len(pool))
        pool.extend(raw)
    out=bytes(header+pool);parse_strings(out)
    return out


def rebuild_text_entry(raw,part,new_part):
    old=unwrap(raw);rows=parts(old);count=len(rows);header=bytearray(struct.pack('>II',count,8)+bytes(count*12));payload=bytearray()
    if not 0<=part<count:raise ValueError('Parte de idioma inválida')
    # Observed containers have only zero alignment padding outside their parts.
    cursor=8+count*12
    for offset,size,tag,data in rows:
        if any(old[cursor:offset]):raise ValueError('Dados desconhecidos entre partes')
        cursor=offset+size
    footer=rows[0][2]
    if cursor!=footer or len(old)-footer!=16*count or any(tag!=footer+16*i for i,(o,s,tag,d) in enumerate(rows)):
        raise ValueError('Tabela de nomes de partes desconhecida')
    for i,(offset,size,tag,data) in enumerate(rows):
        position=len(header)+len(payload);pad=(-position)%4;payload.extend(bytes(pad));position+=pad
        value=new_part if i==part else data
        struct.pack_into('>III',header,8+i*12,position,len(value),0);payload.extend(value)
    payload.extend(bytes((-(len(header)+len(payload)))%4));new_footer=len(header)+len(payload)
    for i in range(count):struct.pack_into('>I',header,8+i*12+8,new_footer+16*i)
    out=bytes(header+payload)+old[footer:]
    if len(new_part)==rows[part][1] and new_part==rows[part][3] and out!=old:
        raise ValueError('Layout de alinhamento desconhecido')
    compressed=zlib.compress(out,9);c,u=struct.unpack_from('>II',raw,8)
    updated=b'\x00\x01\x01WESYS'+struct.pack('>II',len(compressed),len(out))+compressed+raw[16+c:]
    if unwrap(updated)!=out:raise ValueError('Falha ao reconstruir textos')
    return updated


class LeagueEditor:
    def __init__(self,root,items,paths):
        self.root=Path(root);self.items=items;self.paths=paths;self.names={};self.links={};self.entries={};self.parts={}
        source=None
        for name in ('rv_e_limpo.img','rv_e.img','rv_e_original.img'):
            p=self.root/name
            if p.is_file():
                with p.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
                if digest==KNOWN:source=p;break
        if source is None:raise ValueError('Extraia o rv_e.img original da ISO PAL para editar as ligas')
        self.source=source
        with source.open('rb') as f:
            index=afs_index(f)
            for entry,part in ((242,20),(254,0)):
                offset,size=index[entry];f.seek(offset);raw=f.read(size)
                data=parts(unwrap(raw))[part][3]
                self.entries[entry]=raw;self.parts[entry]=(part,data)
        if self.parts[242][1]!=self.parts[254][1]:raise ValueError('As duas tabelas de nomes não correspondem ao perfil validado')
        self.rows={r['id']:r for r in parse_strings(self.parts[254][1]) if r['id'] in LABEL_IDS}
        if set(self.rows)!=set(LABEL_IDS):raise ValueError('Faltam nomes de ligas/competições no idioma inglês')
        self.logos={}
        for item in items:
            if item['kind']=='WE00' and re.fullmatch(r'2700_part\d{3}_unpacked',item['name']):
                if item['name'] in self.logos:raise ValueError('Catálogo de emblemas ambíguo')
                self.logos[item['name']]=item['id']

    def validate_name(self,sid,text):
        if type(sid) is not int or sid not in self.rows:raise ValueError('Liga inválida')
        if not isinstance(text,str) or not text.strip() or not all(c.isprintable() for c in text):raise ValueError('Nome vazio ou com caracteres de controle')
        if len(text.strip().encode('utf-8'))>64:raise ValueError('Limite de 64 bytes para o nome')
        return text.strip()

    def build_entries(self,changes=None):
        changes=self.names if changes is None else changes
        if not changes:return {}
        result={}
        for entry,(part,data) in self.parts.items():
            new=repack_strings(data,changes);raw=self.entries[entry]
            updated=rebuild_text_entry(raw,part,new)
            if new!=data:result[entry]=EntryReplacement(hashlib.sha256(raw).hexdigest(),updated,True)
        if result:
            with self.source.open('rb') as f:entry_changes(f,0,self.source.stat().st_size,result)
        return result

    def stage_name(self,sid,text):
        text=self.validate_name(sid,text);pending=dict(self.names)
        if text==self.rows[sid]['text']:pending.pop(sid,None)
        else:pending[sid]=text
        self.build_entries(pending) # preflight capacity of both compressed AFS entries
        self.names=pending

    def link(self,sid,resource):
        if type(sid) is not int or sid not in self.rows or resource not in self.logos:raise ValueError('Associação de emblema inválida')
        self.links[sid]=resource

    def stage_logo(self,sid,body,fit,prepare,edits):
        if sid not in self.links:raise ValueError('Selecione primeiro o emblema a editar')
        if fit not in ('contain','stretch'):raise ValueError('Ajuste inválido')
        i=self.logos[self.links[sid]];old,new=prepare(i,body,{'fit':[fit]})
        merged=dict(edits)
        if old==new:merged.pop(i,None)
        else:merged[i]=new
        changes={(self.items[j]['name'],):(self.paths[j].read_bytes(),d) for j,d in merged.items()
                 if self.items[j]['kind']=='WE00' and int(self.items[j]['entry'])==2700}
        if changes:
            with (self.root/'cv.img').open('rb') as f:
                index=afs_index(f);offset,size=index[2700];f.seek(offset);rebuild_fixed(f.read(size),changes)
        if old==new:edits.pop(i,None)
        else:edits[i]=new

    def validated_project(self,data):
        names=data.get('league_names',{});links=data.get('league_logo_links',{})
        if not isinstance(names,dict) or not isinstance(links,dict):raise ValueError('Dados de ligas inválidos')
        if (names or links) and data.get('league_source_sha256')!=KNOWN:raise ValueError('Ligas vinculadas a outro arquivo de idioma')
        validated={};mapped={}
        for key,text in names.items():
            if not isinstance(key,str) or not key.isdecimal() or int(key) in validated:raise ValueError('Liga duplicada ou inválida')
            sid=int(key);validated[sid]=self.validate_name(sid,text)
        for key,resource in links.items():
            if not isinstance(key,str) or not key.isdecimal() or int(key) not in self.rows or resource not in self.logos:raise ValueError('Emblema de liga indisponível')
            mapped[int(key)]=resource
        self.build_entries(validated)
        return validated,mapped

    def state(self,edits):
        return {'language':'Inglês (rv_e)','records':[{'id':sid,'original_name':row['text'],
                'name':self.names.get(sid,row['text']),'limit':64,'modified':sid in self.names,
                'logo':self.links.get(sid),'logo_id':self.logos.get(self.links.get(sid)),
                'logo_modified':self.logos.get(self.links.get(sid)) in edits} for sid,row in self.rows.items()],
                'logos':[{'resource':name,'id':i,'modified':i in edits} for name,i in self.logos.items()],
                'pendingNames':len(self.names),'source_sha256':KNOWN,
                'note':'Associação de emblema manual: escolher uma imagem organiza a edição, não altera as referências do jogo.'}

    def evidence(self):
        return {'source_sha256':KNOWN,'source_file':self.source.name,'language':'English',
                'entries':[{ 'entry':e,'sha256':hashlib.sha256(raw).hexdigest(),'part':self.parts[e][0],
                             'part_sha256':hashlib.sha256(self.parts[e][1]).hexdigest()} for e,raw in self.entries.items()],
                'labels':list(self.rows.values()),'automatic_league_to_logo_mappings':[],
                'runtime_verified':False}
