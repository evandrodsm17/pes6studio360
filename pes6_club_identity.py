"""PAL source-bound name/graphic-reference table observations; no kit inference."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from pes6_xex_probe import reconstruct, u32

SOURCE_SHA256='b76db0fc2f86794f4e99bb4d93dd8148d31a00b518cb1e5c822ef0bc75ac1087'

HTML='''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>PES6 Studio — Chelsea 2006/07</title>
<style>body{background:#10151f;color:#e5edf7;font:16px system-ui;margin:30px;max-width:1100px}a{color:#a5df72}
.cards{display:flex;gap:20px;flex-wrap:wrap}.card{padding:20px;background:#1c2635;border-radius:10px}.card img{width:128px;height:128px;object-fit:contain;background:#26354a}
td,th{border-bottom:1px solid #455670;padding:8px;text-align:left}input{padding:10px;background:#26354a;color:white;border:1px solid #455670}code{overflow-wrap:anywhere}</style>
<a href="/">Voltar à galeria</a><h1>Chelsea · temporada 2006/07</h1>
<p>Escudo do Chelsea confirmado em jogo pelo usuário. Nome e uniformes de 2006/07 são as próximas etapas.</p>
<div class="cards"><div class="card"><h2>Escudo original</h2><img src="/clubs/crest?view=original"><p>Recurso 62, entrada 2710</p></div>
<div class="card"><h2>Escudo do teste</h2><img src="/clubs/crest?view=modified"><p>Prévia após conversão para o jogo</p></div></div>
<p>Validação relatada: escudo atualizado perfeitamente. Não foi informado um resultado separado para cada tela. Os nomes e uniformes continuam pendentes.</p>
<details><summary>Referências estáticas de nomes e escudos</summary><p>Os campos de referência vêm do executável. Não representam IDs de uniformes nem confirmação de uso em partida.</p>
<input id="q" placeholder="Filtrar nome ou sigla"><p id="source"></p><table><thead><tr><th>Nome original</th><th>Sigla</th><th>Campo +10</th><th>Campo +12</th></tr></thead><tbody id="rows"></tbody></table></details>
<script>const $=id=>document.getElementById(id);let data;
function render(){const q=$('q').value.toLowerCase();$('rows').replaceChildren();
for(const r of data.records.filter(r=>(r.name+' '+r.short_name).toLowerCase().includes(q))){const tr=document.createElement('tr');
for(const value of [r.name,r.short_name,r.graphic_reference_10,r.graphic_reference_12]){const td=document.createElement('td');td.textContent=value;tr.append(td)}$('rows').append(tr)}}
$('q').oninput=()=>{if(data)render()};(async()=>{try{const r=await fetch('/clubs/data');if(!r.ok)throw Error('Fonte não validada: HTTP '+r.status);
data=await r.json();$('source').textContent='XEX SHA-256: '+data.source_sha256;render()}catch(e){$('source').textContent=e.message}})();</script></html>'''


def text_at(image,base,address):
    offset=address-base
    if not 0<=offset<len(image):raise ValueError('String pointer outside image')
    end=image.find(b'\0',offset,min(len(image),offset+128))
    if end<=offset:raise ValueError('Invalid bounded string')
    value=image[offset:end].decode('utf-8')
    if not all(c.isprintable() for c in value):raise ValueError('Non-printable table string')
    return value


def parse_rows(image,base,start,count):
    if start<0 or count<=0 or start+count*24>len(image):raise ValueError('Table outside image')
    result=[]
    for i in range(count):
        off=start+i*24
        name,short=struct.unpack_from('>II',image,off)
        fields=struct.unpack_from('>4H',image,off+8)
        result.append({'record':i,'image_offset':off,'address':f'0x{base+off:08x}',
                       'name':text_at(image,base,name),'short_name':text_at(image,base,short),
                       'name_address':f'0x{name:08x}','short_name_address':f'0x{short:08x}',
                       'field_08':fields[0],'graphic_reference_10':fields[1],
                       'graphic_reference_12':fields[2],'field_14':fields[3],
                       'tail_hex':image[off+16:off+24].hex(),
                       'record_sha256':hashlib.sha256(image[off:off+24]).hexdigest()})
    return result


def analyze(root):
    source=Path(root)/'default.xex';raw=source.read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    if digest!=SOURCE_SHA256:raise ValueError('Unknown XEX identity: table profile must be revalidated')
    image,layout=reconstruct(raw)
    rows=parse_rows(image,layout['base_address'],0xd55218,214)
    confirmation_path=Path(root)/'research/chelsea_2006_07/runtime_confirmation.json'
    confirmation=None
    if confirmation_path.is_file():
        candidate=json.loads(confirmation_path.read_text(encoding='utf-8'))
        if candidate.get('source_xex_sha256')==digest and candidate.get('scope')=='Chelsea crest replacement only':
            confirmation=candidate
    return {'schema':1,'source_sha256':digest,'image_sha256':hashlib.sha256(image).hexdigest(),
            'table_image_offset':0xd55218,'stride':24,'records':rows,
            'visual_controls':[{'name':'Arsenal','graphic_reference':57},
                               {'name':'Manchester United','graphic_reference':67},
                               {'name':'R. Madrid','graphic_reference':146}],
            'target':{'original_name':'London FC','requested_identity':'Chelsea',
                      'season':'2006/07','name_record':69,'graphic_reference':62,
                      'crest_resources':['2710_part062_unpacked','2711_part062_unpacked'],
                      'runtime_verified':confirmation is not None,
                      'runtime_confirmation':confirmation,'kits':[]},
            'limitations':['Offsets apply only to the exact source hash.',
                           'Fields +10 and +12 agree in all 214 observed records; their individual roles remain unconfirmed.',
                           'Graphic reference interpretation has visual control matches, but has not been runtime traced.',
                           'No kit ID is derived from a roster or table record number.',
                           'London FC to Chelsea is the requested identity correction, not an original licensed name.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path('.'))
    p.add_argument('--out',type=Path,default=Path('research/club_identity.json'));a=p.parse_args()
    data=analyze(a.root);a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(data,indent=2),encoding='utf-8')
    print(json.dumps({'records':len(data['records']),'target':data['target']},indent=2))
