"""Read-only inspector for observed 6670 records. No team or kit assignments."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
from pes6_binary import afs_index, unwrap, parts, profiles6670


def color5551(word):
    """Visualization hypothesis only, not a confirmed game color format."""
    if type(word) is not int or not 0 <= word <= 65535:
        raise ValueError('Invalid 16-bit word')
    return [round(((word >> shift) & 31) * 255 / 31) for shift in (11, 6, 1)] + [255 if word & 1 else 0]


def inspect(root):
    with (Path(root) / 'cv.img').open('rb') as f:
        index = afs_index(f)
        if len(index) <= 6670:
            raise ValueError('Missing AFS entry 6670')
        offset, size = index[6670]
        f.seek(offset)
        raw = f.read(size)
    unpacked = unwrap(raw)
    pp = parts(unpacked)
    if len(pp) != 2:
        raise ValueError('Expected two parts in entry 6670')
    result = {'schema': 1, 'entry': 6670, 'afs_offset': offset, 'stored_size': size,
              'sha256': hashlib.sha256(raw).hexdigest(), 'parts': [],
              'limitations': ['728-byte record semantics are unconfirmed.',
                             'RGBA5551 swatches are a visualization hypothesis.',
                             'Record numbers are not team IDs or kit IDs.'],
              'associations': []}
    for part, (po, ps, tag, data) in enumerate(pp):
        rows = profiles6670(data)
        fields = []
        for field in range(21):
            counts = collections.Counter(r['words'][field] for r in rows)
            fields.append({'word': field, 'relative_offset': field * 4,
                           'unique_values': len(counts),
                           'most_common': [{'hex': f'{v:04x}', 'count': n} for v, n in counts.most_common(8)]})
        metadata = []
        for field in range(24):
            counts = collections.Counter(bytes.fromhex(r['metadata_hex'])[field] for r in rows)
            metadata.append({'byte': field, 'relative_offset': 84 + field,
                             'unique_values': len(counts),
                             'values': [{'hex': f'{v:02x}', 'count': n} for v, n in sorted(counts.items())]})
        for row in rows:
            row['unpacked_offset'] = po + row['offset']
            row['words_hex'] = [f'{w:04x}' for w in row['words']]
            row['rgba5551_hypothesis'] = [color5551(w) for w in row['words']]
        result['parts'].append({'part': part, 'unpacked_offset': po, 'size': ps,
                                'sha256': hashlib.sha256(data).hexdigest(),
                                'candidate_records': len(data) // 728,
                                'word_fields': fields, 'metadata_fields': metadata,
                                'subrecords': rows})
    return result


HTML = '''<!doctype html><html lang="pt-BR"><meta charset="utf-8">
<title>PES6 Studio — Perfis 6670</title><style>
body{background:#10151f;color:#e5edf7;font:15px system-ui;margin:24px;max-width:1200px}
a{color:#a5df72}select,button{background:#26354a;color:white;padding:8px;margin:8px;border:1px solid #455670}
.row{background:#1c2635;padding:16px;margin:14px 0;border-radius:8px}.swatches{display:flex;flex-wrap:wrap;gap:8px}
.word{width:82px;font:12px monospace}.color{height:36px;border:1px solid #718096}
code{overflow-wrap:anywhere}table{border-collapse:collapse}td,th{padding:6px;border:1px solid #455670;text-align:left}
</style><a href="/">Voltar ao Studio</a><h1>Inspeção dos perfis 6670</h1>
<p>Estrutura observada: registros de 728 bytes, com quatro blocos de 108 bytes e 296 bytes finais zerados.
As cores abaixo usam a hipótese RGBA5551. Os números dos registros não identificam equipes nem uniformes.</p>
<p id="source">Verificando fonte...</p><label>Parte <select id="part"></select></label>
<label>Registro <select id="record"></select></label><button id="export" disabled>Exportar análise JSON</button>
<details class="row"><summary>Comparar hipóteses de cores com as paletas dos uniformes</summary>
<p>A comparação usa todas as paletas juntas, inclusive cores não utilizadas. Correspondências de cores não identificam equipes nem recursos equivalentes.</p>
<button id="compare">Executar comparação</button><p id="comparisonStatus"></p><div id="comparisonTable"></div></details>
<details class="row"><summary>Referências candidatas no executável PowerPC</summary>
<p>Busca estática por constantes nas seções executáveis. Uma ocorrência pode ser um deslocamento ou outro valor sem relação com uniformes. Não comprova associação com equipes.</p>
<button id="executable">Analisar default.xex</button><p id="executableStatus"></p><div id="executableTable"></div></details>
<main id="blocks"></main><details><summary>Distribuição dos campos na parte selecionada</summary><pre id="stats"></pre></details>
<script>
const $=id=>document.getElementById(id);let report;
function records(){const p=report.parts[Number($('part').value)];$('record').replaceChildren();
for(let n=0;n<p.candidate_records;n++)$('record').add(new Option(String(n),String(n)));render()}
function render(){const p=report.parts[Number($('part').value)],r=Number($('record').value);$('blocks').replaceChildren();
for(const row of p.subrecords.filter(s=>s.candidate_record===r)){
const box=document.createElement('section');box.className='row';const title=document.createElement('h2');
title.textContent='Bloco '+row.subrecord;const offsets=document.createElement('p');
offsets.textContent='Offset na parte: '+row.offset+' | Offset na entrada descompactada: '+row.unpacked_offset;
const swatches=document.createElement('div');swatches.className='swatches';
row.words_hex.forEach((hex,i)=>{const word=document.createElement('div');word.className='word';
const color=document.createElement('div');color.className='color';const rgba=row.rgba5551_hypothesis[i];
color.style.backgroundColor='rgb('+rgba.slice(0,3).join(',')+')';
color.title='RGB hipotético; alfa '+rgba[3]+' (exibido opaco para inspeção)';
const text=document.createElement('div');text.textContent='+'+(i*4)+' : '+hex;word.append(color,text);swatches.append(word)});
const meta=document.createElement('p');meta.textContent='Metadados +84..107: '+row.metadata_hex;
box.append(title,offsets,swatches,meta);$('blocks').append(box)}
$('stats').textContent=JSON.stringify({words:p.word_fields,metadata:p.metadata_fields},null,2)}
$('part').onchange=records;$('record').onchange=render;
$('executable').onclick=async()=>{const button=$('executable');button.disabled=true;$('executableStatus').textContent='Reconstruindo imagem em memória e buscando constantes...';
try{const response=await fetch('/profiles/executable');if(!response.ok)throw Error('Falha na análise: HTTP '+response.status);
const data=await response.json();$('executableStatus').textContent='SHA-256 do XEX: '+data.source_sha256+' | '+data.hits.length+' ocorrências. Exibindo 5736, 6145–6146, 6666–6671 e multiplicações por 728.';
const table=document.createElement('table');const header=table.createTHead().insertRow();
for(const label of ['Endereço virtual','Offset na imagem','Bytes','Instrução candidata','Imediato']){const th=document.createElement('th');th.textContent=label;header.append(th)}
for(const hit of data.hits.filter(h=>h.immediate>=5736||(h.immediate===728&&h.mnemonic==='mulli'))){const tr=table.insertRow();
for(const value of [hit.address,hit.image_offset,hit.word_hex,hit.mnemonic,hit.immediate])tr.insertCell().textContent=value}
$('executableTable').replaceChildren(table)}catch(e){$('executableStatus').textContent=e.message}finally{button.disabled=false}};
$('compare').onclick=async()=>{const b=$('compare');b.disabled=true;$('comparisonStatus').textContent='Lendo paletas da fonte...';
try{const response=await fetch('/profiles/palettes');if(!response.ok)throw Error('Falha na comparação: HTTP '+response.status);
const data=await response.json();if(data.profile_source.sha256!==report.sha256)throw Error('A fonte mudou. Recarregue a página.');
$('comparisonStatus').textContent=data.unique_words+' palavras distintas; '+data.odd_word_occurrences+'/'+data.word_occurrences+' ocorrências com bit 0 ativo. Nenhum formato confirmado.';
const table=document.createElement('table');const header=table.createTHead().insertRow();
for(const label of ['Hipótese','Bytes invertidos','Cores distintas presentes','Correspondência','Cobertura das paletas no espaço de cores']){const th=document.createElement('th');th.textContent=label;header.append(th)}
for(const row of data.comparisons){const tr=table.insertRow();for(const value of [row.layout,row.byte_swapped?'Sim':'Não',row.matched_distinct_colors+'/'+row.distinct_profile_colors,(100*row.distinct_match_fraction).toFixed(1)+'%',(100*row.palette_space_fraction).toFixed(1)+'%'])tr.insertCell().textContent=value}
$('comparisonTable').replaceChildren(table)}catch(e){$('comparisonStatus').textContent=e.message}finally{b.disabled=false}};
$('export').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));
const a=document.createElement('a');a.href=url;a.download='pes6_profiles_6670.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
(async()=>{try{const response=await fetch('/profiles/data');if(!response.ok)throw Error('Falha ao verificar a fonte: HTTP '+response.status);
report=await response.json();$('source').textContent='cv.img / entrada 6670 — SHA-256: '+report.sha256;
for(const p of report.parts)$('part').add(new Option(p.part+' ('+p.candidate_records+' registros)',String(p.part)));
$('export').disabled=false;records()}catch(e){$('source').textContent=e.message}})();
</script></html>'''


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--out', type=Path, default=Path('research/profiles_6670.json'))
    args = parser.parse_args()
    report = inspect(args.root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'source_sha256': report['sha256'], 'records': [p['candidate_records'] for p in report['parts']], 'output': str(args.out)}))
