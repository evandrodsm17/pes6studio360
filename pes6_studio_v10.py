"""Local PES6 texture and club editor. Requires Pillow; names use cryptography."""
import argparse, csv, io, json, re, webbrowser, os, hashlib
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from PIL import Image
from pes6_texture import convert
from pes6_project import save, load
from pes6_teams import TeamMap, candidate, SLOTS
from pes6_iso import build
from pes6_we00_edit import encode,leaf,route,image_bytes
from pes6_we00_catalogo import decode
import threading, time
from pes6_resource_map import kit_pairs
from pes6_evidence import load_evidence
from pes6_profiles import inspect as inspect_profiles, HTML as PROFILES_HTML
from pes6_palette_probe import analyze as analyze_palettes
from pes6_xex_probe import analyze as analyze_executable
from pes6_club_identity import analyze as analyze_clubs
from pes6_club_editor import ClubEditor, HTML as CLUBS_HTML
from pes6_name_editor import NameEditor
from pes6_leagues import LeagueEditor
from pes6_league_ui import HTML as LEAGUES_HTML
from pes6_scoreboards import ScoreboardEditor
from pes6_scoreboard_ui import HTML as SCOREBOARDS_HTML
from pes6_duplicates import groups
HTML = '''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>PES6 Studio</title><style>
*{box-sizing:border-box}body{margin:0;background:#10151f;color:#e5edf7;font:15px system-ui}header{padding:24px 32px;background:#192333;position:sticky;top:0;z-index:1}h1{margin:0;color:#a5df72}small{color:#a5b4c8}input,select,button{background:#26354a;color:white;border:1px solid #455670;border-radius:7px;padding:10px;margin:6px 4px}button{cursor:pointer}#grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:16px;padding:24px 32px}.tile{background:#1c2635;border-radius:10px;overflow:hidden;padding:10px}.tile img{width:100%;height:145px;object-fit:contain;background:repeating-conic-gradient(#334155 0% 25%,#202a38 0% 50%) 50%/20px 20px;cursor:zoom-in}a{color:#a5df72}dialog{background:#1c2635;color:white;border:1px solid #455670;max-width:95vw}dialog img{max-width:85vw;max-height:75vh;object-fit:contain}#nav{padding:0 32px 110px}</style>
<header><h1>PES6 STUDIO</h1><small>Xbox 360 • Galeria local de texturas • Editor v0.14 • ISO original como fonte</small><div><select id="kind"><option value="">DDS + WE00</option><option>DDS</option><option>WE00</option></select><select id="archive"></select><input id="q" placeholder="Entrada AFS, ex. 0190"><select id="fmt"><option value="">Todos formatos</option></select><select id="res"><option value="">Todas resoluções</option></select><select id="cat"><option value="">Todas categorias</option><option value="unclassified">Sem categoria</option></select><select id="candidate"><option value="">Todos recursos</option><option value="yes">Faixa DDS CV 0190–0851 (cabelos)</option><option value="unmapped">Faixa de cabelos sem vínculo</option></select><select id="team"><option value="">Todas equipes</option></select><select id="slotFilter"><option value="">Todos tipos de uniforme</option></select><select id="dupes"><option value="group">Agrupar WE00 iguais</option><option value="all">Mostrar todas</option><option value="only">Somente duplicadas</option></select><button onclick="window.open('/profiles','_blank','noopener')">Inspecionar perfis 6670</button><button onclick="window.open('/clubs','_blank','noopener')">Clubes, nomes e escudos</button><button onclick="window.open('/leagues','_blank','noopener')">Ligas e competições</button><button onclick="window.open('/scoreboards','_blank','noopener')">Placares e HUD</button><button onclick="openPairs()">Mapear pares de uniformes</button><button onclick="openEvidence()">Evidências binárias</button><span id="count"></span><p>ISO original: <strong id="isoPath"></strong></p></div></header><main id="grid"></main><div id="nav"><button id="prev">Anterior</button><span id="page"></span><button id="next">Próxima</button></div><dialog id="modal"><button onclick="modal.close()">Fechar</button><p id="detail"></p><div style="display:flex;gap:12px;flex-wrap:wrap"><div>Original<br><img id="large" style="max-width:40vw;max-height:45vh"></div><div>Modificada<br><img id="edited" style="max-width:40vw;max-height:45vh"></div></div><input id="upload" type="file" accept=".png,.dds"><select id="fit"><option value="strict">Resolução original (exata)</option><option value="contain">Ajustar com transparência</option><option value="stretch">Preencher (esticar)</option></select><select id="tag"><option value="">Sem categoria</option></select><div><input id="teamName" list="teamNames" maxlength="100" placeholder="Nome da equipe"><datalist id="teamNames"></datalist><select id="slot"></select><button id="mapSave">Salvar vínculo</button><button id="mapClear">Remover vínculo</button><p><small>Vínculo manual: confirme visualmente a equipe e o tipo antes de salvar.</small></p></div><details id="occBox"><summary id="occTitle">Ocorrências</summary><button id="selectAll" type="button">Selecionar todas</button><button id="selectNone" type="button">Desmarcar todas</button><div id="occList" style="max-height:180px;overflow:auto"></div><button id="batchStage">Importar nas selecionadas</button><button id="batchTag">Categorizar selecionadas</button></details><button id="tagSave">Salvar categoria</button><button id="stage">Importar textura</button><button id="undo">Restaurar</button><p id="status"></p></dialog><div style="position:fixed;bottom:0;right:0;left:0;background:#192333;padding:8px;z-index:2;overflow-wrap:anywhere"><span id="pending">0 alterações</span><button id="saveProject">Salvar projeto</button><button id="loadProject">Carregar projeto</button><select id="mode"><option value="iso">ISO para Xenia</option><option value="img">IMG para console (experimental)</option></select><button id="build">Gerar patch verificado</button><span id="result"></span></div>
<dialog id="pairs" style="width:95vw"><button onclick="pairs.close()">Fechar</button><h2>Mapeamento de recursos • 5736–6145</h2><p>Entradas candidatas, não IDs de equipes. Os papéis principal/reserva precisam de confirmação.</p><input id="pairQuery" placeholder="Entrada ou equipe"><label><input type="checkbox" id="onlyMissing">Somente sem vínculo</label><div id="pairGrid" style="max-height:65vh;overflow:auto"></div><button id="pairPrev">Anterior</button><span id="pairPage"></span><button id="pairNext">Próxima</button><button id="pairExport">Exportar CSV dos pares</button></dialog><dialog id="evidence"><button onclick="this.parentElement.close()">Fechar</button><h2>Evidências e hipóteses</h2><p>Slots de elenco variam entre bancos. Nenhuma associação automática entre equipes e uniformes.</p><pre id="evidenceText" style="white-space:pre-wrap;max-height:65vh;overflow:auto"></pre></dialog><script>async function openEvidence(){let d=$('evidence');d.showModal();$('evidenceText').textContent='Verificando fontes...';try{let r=await fetch('/research');let j=await r.json();$('evidenceText').textContent=JSON.stringify(j,null,2)}catch(e){$('evidenceText').textContent=e.message}}let data=[],page=0,filtered=[],selected=-1;const categories=["Uniformes","Faces","Cabelos","Placares","Menus","Escudos","Estádios","Bandeiras de clubes","Bandeiras de seleções","Números","Chuteiras","Outros"];const $=id=>document.getElementById(id);const slots=["Principal","Reserva","Goleiro 1","Goleiro 2","Alternativo","Detalhe"];let pairPage=0;function getPairs(){let m=new Map();for(const t of data){if(!t.kitPair)continue;let k=t.archive+'/'+t.entry;if(!m.has(k))m.set(k,[]);m.get(k).push(t)}return [...m.values()].filter(p=>p.length===2).sort((a,b)=>a[0].entry.localeCompare(b[0].entry))}function openPairs(){pairPage=0;renderPairs();$('pairs').showModal()}function renderPairs(){let q=$('pairQuery').value.toLowerCase();let pp=getPairs().filter(p=>p.some(t=>(t.entry+' '+(t.team||'')).toLowerCase().includes(q))&&(!$('onlyMissing').checked||p.some(t=>!t.team)));pairPage=Math.max(0,Math.min(pairPage,Math.ceil(pp.length/20)-1));$('pairPage').textContent=(pairPage+1)+' / '+Math.max(1,Math.ceil(pp.length/20))+' • '+pp.length+' pares';$('pairGrid').replaceChildren();for(let p of pp.slice(pairPage*20,pairPage*20+20)){let row=document.createElement('div');row.style='display:flex;align-items:center;gap:12px;border-bottom:1px solid #455670;padding:8px;flex-wrap:wrap';let title=document.createElement('strong');title.textContent=p[0].entry;row.append(title);for(let t of p){let box=document.createElement('div'),img=document.createElement('img'),label=document.createElement('div'),b=document.createElement('button');img.src='/png?id='+t.id;img.style='width:110px;height:110px;object-fit:contain';label.textContent=t.name+' • '+(t.team||'Sem vínculo')+' '+(t.slot||'')+' • '+t.occurrences.length+' ocorrências';b.textContent='Abrir na galeria';b.onclick=()=>{$('pairs').close();$('kind').value='WE00';$('archive').value=t.archive;$('q').value=t.name;for(let id of ['fmt','res','cat','candidate','team','slotFilter'])$(id).value='';$('dupes').value='all';page=0;render();$('grid').querySelector('img')?.click()};box.append(img,label,b);row.append(box)}$('pairGrid').append(row)}}$('pairQuery').oninput=$('onlyMissing').onchange=()=>{pairPage=0;renderPairs()};$('pairPrev').onclick=()=>{pairPage--;renderPairs()};$('pairNext').onclick=()=>{pairPage++;renderPairs()};$('pairExport').onclick=()=>{let rows=[['archive','entry','resource','team','slot','occurrences'],...getPairs().flat().map(t=>[t.archive,t.entry,t.name,t.team,t.slot,t.occurrences.length])];let csv=rows.map(r=>r.map(v=>'"'+String(v??'').replaceAll('"','""')+'"').join(',')).join(String.fromCharCode(10));let a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));a.download='pes6_pares.csv';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)};function refreshTeams(){let old=$("team").value;$("team").replaceChildren(new Option("Todas equipes",""));$("teamNames").replaceChildren();for(const v of [...new Set(data.map(t=>t.team).filter(Boolean))].sort()){ $("team").append(new Option(v,v));$("teamNames").append(new Option(v,v))}$("team").value=old;if($("team").selectedIndex<0)$("team").value=""}function opts(id,values){for(const v of [...new Set(values)].sort()){let o=document.createElement('option');o.value=v;o.textContent=v;$(id).append(o)}}function render(){let q=$('q').value.trim().toLowerCase();filtered=data.filter(t=>(!$("kind").value||t.kind===$("kind").value)&&(!$("candidate").value||(t.candidate&&($("candidate").value!=="unmapped"||!t.team)))&&(!$("team").value||t.team===$("team").value)&&(!$("slotFilter").value||t.slot===$("slotFilter").value)&&(!$('archive').value||t.archive===$('archive').value)&&(!q||t.entry.includes(q)||t.name.toLowerCase().includes(q)||(t.team||'').toLowerCase().includes(q))&&(!$('fmt').value||t.format===$('fmt').value)&&(!$('res').value||t.res===$('res').value)&&(!$('cat').value||($('cat').value==='unclassified'?!t.tag:t.tag===$('cat').value)));let rawCount=filtered.length;let mode=$('dupes').value;if(mode==='only')filtered=filtered.filter(t=>t.occurrences.length>1);if(mode!=='all'){let seen=new Set();filtered=filtered.filter(t=>{if(t.modified)return true;let k=t.occurrences[0];if(seen.has(k))return false;seen.add(k);return true})}page=Math.max(0,Math.min(page,Math.ceil(filtered.length/60)-1));$('count').textContent=filtered.length+' cartões / '+rawCount+' ocorrências filtradas / '+data.length+' total';$('page').textContent=(page+1)+' / '+Math.max(1,Math.ceil(filtered.length/60));$('prev').disabled=page===0;$('next').disabled=(page+1)*60>=filtered.length;$('grid').replaceChildren();for(const t of filtered.slice(page*60,page*60+60)){let div=document.createElement('article');div.className='tile';let img=document.createElement('img');img.loading='lazy';img.src='/png?id='+t.id;img.alt='Prévia indisponível';img.onclick=()=>{$('large').src='/png?id='+t.id+'&full=1';$('detail').textContent=t.archive+' / '+t.entry+' / '+t.name+' • '+t.res;selected=t.id;showOccurrences(t);for(const id of ['upload','fit','stage','undo'])$(id).disabled=false;$('edited').style.display='';$('tag').value=t.tag||'';$('teamName').value=t.team||'';$('slot').value=t.slot||'Principal';$('edited').src='/edited?id='+t.id+'&full=1&v='+Date.now();$('status').textContent=t.kind==='WE00'?'WE00: importação PNG experimental; tamanho fixo.':'';$('upload').value='';$('modal').showModal()};let p=document.createElement('p');p.textContent=t.archive+' / '+t.entry;let s=document.createElement('small');s.textContent=t.name+' • '+t.res+' • '+t.format+(t.tag?' • '+t.tag:'')+(t.occurrences.length>1?' • '+t.occurrences.length+' ocorrências':'')+(t.modified?' • MOD':'')+(t.team?' • '+t.team+' / '+t.slot:'');let a=document.createElement('a');a.href='/png?id='+t.id+'&full=1&download=1';a.textContent='PNG';let b=document.createElement('a');b.href='/dds?id='+t.id;b.textContent='DDS';div.append(img,p,s,document.createElement('br'),a);if(t.kind==='DDS')div.append(document.createTextNode(' · '),b);$('grid').append(div)}}fetch('/config').then(r=>r.json()).then(d=>$('isoPath').textContent=d.iso);fetch('/api').then(r=>r.json()).then(d=>{data=d;refreshTeams();let all=document.createElement('option');all.value='';all.textContent='Todos arquivos';$('archive').append(all);opts('archive',data.map(t=>t.archive));opts('fmt',data.map(t=>t.format));opts('res',data.map(t=>t.res));render()});opts('slot',slots);opts('slotFilter',slots);opts('cat',categories);opts('tag',categories);for(const id of ['kind','archive','q','fmt','res','cat','candidate','team','slotFilter','dupes'])$(id).oninput=()=>{page=0;render()};$('prev').onclick=()=>{page--;render()};$('next').onclick=()=>{page++;render()};async function action(url,body){let r=await fetch(url,{method:'POST',body});let d=await r.json();if(!r.ok)throw Error(d.error);$('pending').textContent=d.count+' alterações';if(d.items){data=d.items;refreshTeams();render()}return d} function showOccurrences(t){$('occBox').open=false;$('occBox').hidden=t.occurrences.length<2;$('occTitle').textContent=t.occurrences.length+' ocorrências (imagem original)';$('occList').replaceChildren();for(const id of t.occurrences){let item=data.find(x=>x.id===id);let row=document.createElement('label');row.style.display='block';let c=document.createElement('input');c.type='checkbox';c.value=id;c.checked=id===t.id;let b=document.createElement('button');b.textContent='Abrir';b.type='button';b.onclick=()=>{$('modal').close();$('dupes').value='all';for(const f of ['kind','archive','fmt','res','cat','candidate','team','slotFilter'])$(f).value='';$('q').value=item.name;page=0;render();};row.append(c,document.createTextNode(item.entry+' / '+item.name+' '+(item.team||'')+' '+(item.modified?'MOD':'')),b);$('occList').append(row)}}function checkedIds(){return [...$('occList').querySelectorAll('input:checked')].map(c=>Number(c.value))}$('selectAll').onclick=()=>{for(const c of $('occList').querySelectorAll('input'))c.checked=true};$('selectNone').onclick=()=>{for(const c of $('occList').querySelectorAll('input'))c.checked=false};$('batchStage').onclick=async()=>{try{let ids=checkedIds(),f=$('upload').files[0];if(!ids.length||!f)throw Error('Selecione ocorrências e PNG');if(!confirm('Importar em '+ids.length+' recursos independentes?'))return;await action('/batchStage?id='+selected+'&ids='+ids.join(',')+'&fit='+$('fit').value,f);$('edited').src='/edited?id='+selected+'&full=1&v='+Date.now();$('status').textContent='Lote importado em memória; exportação ainda precisa ser validada.'}catch(e){$('status').textContent=e.message}};$('batchTag').onclick=async()=>{try{let ids=checkedIds();if(!ids.length)throw Error('Selecione ocorrências');if(!confirm('Categorizar '+ids.length+' recursos?'))return;await action('/batchTag?id='+selected+'&ids='+ids.join(','),$('tag').value);$('status').textContent='Categorias salvas'}catch(e){$('status').textContent=e.message}};$('mapSave').onclick=async()=>{try{if(!$('teamName').value.trim())throw Error('Informe a equipe');await action('/map?id='+selected,JSON.stringify({team:$('teamName').value,slot:$('slot').value}));$('status').textContent='Vínculo salvo no catálogo permanente.'}catch(e){$('status').textContent=e.message}};$('mapClear').onclick=async()=>{try{await action('/map?id='+selected,JSON.stringify({team:'',slot:''}));$('teamName').value='';$('status').textContent='Vínculo removido.'}catch(e){$('status').textContent=e.message}};$('stage').onclick=async()=>{try{let f=$('upload').files[0];if(!f)throw Error('Selecione um arquivo');await action('/stage?id='+selected+'&fit='+$('fit').value,f);$('edited').src='/edited?id='+selected+'&full=1&v='+Date.now();$('status').textContent='Importada; confira a prévia convertida e salve o projeto.';}catch(e){$('status').textContent=e.message}};$('undo').onclick=async()=>{try{await action('/undo?id='+selected,'');$('edited').src='/edited?id='+selected+'&full=1&v='+Date.now();$('status').textContent='Restaurada';}catch(e){$('status').textContent=e.message}};$('tagSave').onclick=async()=>{try{await action('/tag?id='+selected,$('tag').value);$('status').textContent='Categoria salva no catálogo permanente'}catch(e){$('status').textContent=e.message}};for(const [id,url] of [['saveProject','/save'],['loadProject','/load']])$(id).onclick=async()=>{try{if(id==='loadProject'&&!confirm('Substituir alterações atuais pelo projeto salvo?'))return;let d=await action(url,'');$('result').textContent=d.message}catch(e){$('result').textContent=e.message}};$('build').onclick=async()=>{try{$('build').disabled=true;$('result').textContent='Comprimindo, copiando e verificando ISO/IMG...';let d=await action('/build?mode='+$('mode').value,'');$('result').textContent='Verificado: '+d.files.join(' | ')}catch(e){$('result').textContent=e.message}finally{$('build').disabled=false}};</script></html>'''
def scan(roots):
    items=[]; paths=[]
    for root in roots:
        for p in sorted(root.glob('*/texture_*.dds')):
            if not p.is_file(): continue
            with p.open('rb') as f: h=f.read(128)
            if len(h)<128 or h[:4]!=b'DDS ': continue
            height=int.from_bytes(h[12:16],'little'); width=int.from_bytes(h[16:20],'little')
            fmt=h[84:88].decode('ascii','replace').strip('\x00') if h[84:88]!=b'\0'*4 else 'RGB'
            items.append(dict(id=len(paths),kind='DDS',archive=root.name,entry=p.parent.name,name=p.name,format=fmt,res=f'{width} × {height}'));paths.append(p)
    return items,paths

def add_we00(root,items,paths):
    seen=set()
    with (root/'index.csv').open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            name=row['file']; resource=row['resource']; fmt=row['format']
            if not re.fullmatch(r'\d+(?:_part\d+|_unpacked)*',resource) or name!=resource+'.png' or fmt not in ('indexed8','direct24','direct32'):raise ValueError('Linha WE00 inválida: '+name)
            if name in seen:raise ValueError('Recurso WE00 duplicado: '+name)
            seen.add(name); path=root/name
            if not path.is_file():raise ValueError('PNG ausente: '+str(path))
            w,h=int(row['width']),int(row['height'])
            if not (0<w<=4096 and 0<h<=4096):raise ValueError('Dimensão inválida')
            items.append(dict(id=len(paths),kind='WE00',archive=root.name,entry=resource.split('_')[0],name=resource,format=fmt,res=f'{w} × {h}'));paths.append(path)

def main():
    p=argparse.ArgumentParser();p.add_argument('folders',nargs='+',type=Path);p.add_argument('--we00',type=Path,action='append',default=[]);p.add_argument('--port',type=int,default=8765);p.add_argument('--iso',required=True,type=Path);p.add_argument('--project',type=Path,default=Path('pes6_projeto.json'));p.add_argument('--team-map',type=Path,default=Path('pes6_equipes.json'));p.add_argument('--no-browser',action='store_true');a=p.parse_args()
    a.iso=a.iso.resolve()
    if not a.iso.is_file():p.error('ISO original não encontrada')
    for root in a.folders:
        if not root.is_dir(): p.error(f'Pasta não encontrada: {root}')
    items,paths=scan(a.folders)
    for root in a.we00:add_we00(root,items,paths)
    print("Indexando duplicatas WE00...",flush=True)
    duplicates=groups(paths,items,Path("pes6_duplicate_cache.json"))
    mapping=TeamMap(a.team_map,paths)
    pair_ids={t["id"] for p in kit_pairs(items) for t in p["parts"]}
    edits={}; tags={}; lock=threading.RLock();generated_directories=set()
    clubs=None;names=None;club_error=''
    try:
        club_report=analyze_clubs(Path(__file__).parent)
        clubs=ClubEditor(club_report,items,paths,Path(__file__).parent)
        names=NameEditor((Path(__file__).parent/'default.xex').read_bytes(),club_report)
    except (OSError,ValueError) as exc:club_error=str(exc)
    leagues=None;league_error=''
    try:leagues=LeagueEditor(Path(__file__).parent,items,paths)
    except (OSError,ValueError) as exc:league_error=str(exc)
    scoreboards=None;scoreboard_error=''
    try:
        if leagues is None:raise ValueError(league_error)
        scoreboards=ScoreboardEditor(leagues.source)
    except (OSError,ValueError,IndexError) as exc:scoreboard_error=str(exc)
    def pending_count():return len(edits)+(len(names.edits) if names else 0)+(len(leagues.names) if leagues else 0)+(len(scoreboards.edits) if scoreboards else 0)
    def catalog():
        result=[]
        for i,t in enumerate(items):
            r=mapping.get(i);result.append(dict(t,kitPair=i in pair_ids,occurrences=duplicates.get(i,[i]),tag=r.get('category') or tags.get(i,'Uniformes' if r.get('team') else ('Cabelos' if candidate(t) else '')),modified=i in edits,team=r.get('team',''),slot=r.get('slot',''),candidate=candidate(t)))
        return result
    print(f'{len(items)} texturas catalogadas',flush=True)
    def club_state():
        data=clubs.state(edits)
        data['pendingNames']=len(names.edits);data['pendingTotal']=pending_count()
        for row in data['records']:
            original=names.rows[row['record']];values=names.edits.get(row['record'],original)
            row.update(edited_name=values['name'],edited_short_name=values['short_name'],
                       name_limits=names.limits(row['record']),name_modified=row['record'] in names.edits)
            if row['name_modified']:row['label']=values['name']+' (original: '+row['name']+')'
        return data
    def prepare(i,body,q):
        original=paths[i].read_bytes()
        if items[i]['kind']=='WE00':
            root=next((r for r in a.folders if r.name.startswith('cv_extraido')),None)
            if root is None:raise ValueError('Informe a pasta cv_extraido_v03')
            folder=root/items[i]['entry']; src=folder/'unpacked.bin'
            if not src.exists():src=folder/'original.bin'
            raw=leaf(src.read_bytes(),route(items[i]['name']))
            old=decode(raw)
            if old is None:raise ValueError('WE00 não suportado')
            with Image.open(io.BytesIO(original)) as im:
                if im.convert('RGBA').tobytes()!=old[0].convert('RGBA').tobytes():raise ValueError('PNG do catálogo divergente')
            # Store the resized source PNG, not the quantized preview, to avoid double quantization.
            from PIL import ImageOps
            with Image.open(io.BytesIO(body)) as im:
                if im.format!='PNG':raise ValueError('WE00 aceita PNG')
                im=im.convert('RGBA'); target=old[0].size; fit=q.get('fit',['strict'])[0]
                if fit=='contain':
                    im=ImageOps.contain(im,target,Image.Resampling.LANCZOS); c=Image.new('RGBA',target);c.paste(im,((target[0]-im.width)//2,(target[1]-im.height)//2));im=c
                elif fit=='stretch':im=im.resize(target,Image.Resampling.LANCZOS)
                if im.size!=target:raise ValueError('Dimensões incompatíveis')
                replacement=image_bytes(im)
            if encode(raw,replacement)==raw:replacement=original
        else:replacement=original if body==original else convert(original,body,q.get('fit',['strict'])[0])
        return original,replacement
    class Handler(BaseHTTPRequestHandler):
        def send(self,body,mime,name=None):
            self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(body)))
            if name:self.send_header('Content-Disposition',f'attachment; filename="{name}"')
            self.end_headers();self.wfile.write(body)
        def do_POST(self):
            u=urlparse(self.path);q=parse_qs(u.query)
            try:
                if self.headers.get('Origin') not in (None,f'http://127.0.0.1:{a.port}',f'http://localhost:{a.port}'):raise ValueError('Origem não permitida')
                n=int(self.headers.get('Content-Length','0'))
                if not 0<=n<=32*1024*1024:raise ValueError('Arquivo muito grande')
                body=self.rfile.read(n)
                with lock:
                    result={}
                    if u.path.startswith('/scoreboards/'):
                        if scoreboards is None:raise ValueError('Placares indisponíveis: '+scoreboard_error)
                        key=q['key'][0]
                        if key not in scoreboards.raw:raise ValueError('Recurso de placar inválido')
                        if u.path=='/scoreboards/stage':scoreboards.stage(key,body)
                        elif u.path=='/scoreboards/undo':scoreboards.edits.pop(key,None)
                        else:raise ValueError('Ação de placar inválida')
                    elif u.path.startswith('/leagues/'):
                        if leagues is None:raise ValueError('Ligas indisponíveis: '+league_error)
                        sid=int(q['id'][0])
                        if sid not in leagues.rows:raise ValueError('Liga inválida')
                        if u.path=='/leagues/name':leagues.stage_name(sid,json.loads(body)['name'])
                        elif u.path=='/leagues/nameUndo':leagues.names.pop(sid,None)
                        elif u.path=='/leagues/link':leagues.link(sid,json.loads(body)['resource'])
                        elif u.path=='/leagues/logo':leagues.stage_logo(sid,body,q.get('fit',['contain'])[0],prepare,edits)
                        elif u.path=='/leagues/logoUndo':
                            if sid in leagues.links:edits.pop(leagues.logos[leagues.links[sid]],None)
                        else:raise ValueError('Ação de liga inválida')
                    elif u.path in ('/clubs/stage','/clubs/undo','/clubs/name','/clubs/nameUndo'):
                        if clubs is None:raise ValueError('Catálogo de clubes indisponível: '+club_error)
                        record=int(q['record'][0])
                        if u.path=='/clubs/stage':
                            result['changed_ids']=clubs.stage(record,body,q.get('fit',['contain'])[0],prepare,edits)
                        elif u.path=='/clubs/undo':clubs.undo(record,edits)
                        elif u.path=='/clubs/name':
                            d=json.loads(body);names.stage(record,d['name'],d['short_name'])
                        else:
                            names.limits(record);names.edits.pop(record,None)
                    elif u.path in ('/stage','/undo','/tag','/map'):
                        i=int(q['id'][0]);
                        if not 0<=i<len(paths):raise ValueError('ID inválido')
                        if u.path=='/stage':
                            original,replacement=prepare(i,body,q)
                            if replacement==original:edits.pop(i,None)
                            else:edits[i]=replacement
                        elif u.path=='/map':
                            d=json.loads(body);mapping.set(i,d['team'],d['slot'])
                        elif u.path=='/tag':
                            tag=body.decode('utf-8')
                            mapping.set_category(i,tag)
                            tags.pop(i,None)
                        else:edits.pop(i,None)
                    elif u.path in ('/batchStage','/batchTag'):
                        i=int(q['id'][0]); ids=list(dict.fromkeys(map(int,q['ids'][0].split(','))))
                        if not ids or not set(ids)<=set(duplicates.get(i,[])):raise ValueError('Seleção fora do grupo WE00')
                        if u.path=='/batchStage':
                            pending={j:prepare(j,body,q) for j in ids}
                            for j,(original,replacement) in pending.items():
                                if replacement==original:edits.pop(j,None)
                                else:edits[j]=replacement
                        else:
                            for j in ids:mapping.set_category(j,body.decode('utf-8'));tags.pop(j,None)
                    elif u.path=='/openOutput':
                        directory=json.loads(body)['directory']
                        if directory not in generated_directories:raise ValueError('Pasta não gerada nesta sessão')
                        os.startfile(directory);result['message']='Pasta aberta'
                    elif u.path=='/save':
                        save(a.project,a.iso,paths,edits,tags,names.edits if names else None,club_report['source_sha256'] if names else None,
                             leagues.names if leagues else None,leagues.links if leagues else None,leagues.state({})['source_sha256'] if leagues else None,
                             scoreboards.project() if scoreboards else None);result['message']='Projeto salvo: '+str(a.project.resolve())
                    elif u.path=='/load':
                        e,t=load(a.project,a.iso,paths)
                        project_data=json.loads(a.project.read_text(encoding='utf-8'))
                        if project_data.get('club_names') and names is None:raise ValueError('Nomes do projeto exigem executável compatível')
                        name_changes=names.validated_project(project_data) if names else {}
                        if (project_data.get('league_names') or project_data.get('league_logo_links')) and leagues is None:raise ValueError('Ligas do projeto exigem arquivo de idioma original')
                        league_changes,league_links=leagues.validated_project(project_data) if leagues else ({},{})
                        if project_data.get('scoreboard_textures') and scoreboards is None:raise ValueError('Placares do projeto exigem arquivo de idioma original')
                        scoreboard_changes=scoreboards.validated_project(project_data) if scoreboards else {}
                        edits.clear();edits.update(e);tags.clear();tags.update(t)
                        if names is not None:names.edits=name_changes
                        if leagues is not None:leagues.names=league_changes;leagues.links=league_links
                        if scoreboards is not None:scoreboards.edits=scoreboard_changes
                        result['message']='Projeto carregado'
                    elif u.path=='/build':
                        if not pending_count():raise ValueError('Nenhuma alteração importada')
                        grouped={}
                        for i,d in edits.items():
                            f=paths[i]
                            if items[i]['kind']=='WE00':
                                grouped.setdefault('cv.img',{}).setdefault(int(items[i]['entry']),{})[(items[i]['name'],)]=(f.read_bytes(),d)
                                continue
                            root=f.parent.parent.name
                            name=root.split('_extraido')[0].lower()+'.img'
                            if name not in ('rv_e.img','cv.img','rv_f.img','rv_g.img','rv_i.img','rv_s.img'):raise ValueError('Arquivo ainda não suportado: '+name)
                            grouped.setdefault(name,{}).setdefault(int(f.parent.name),{})[int(f.stem.split('_')[-1])]=(f.read_bytes(),d)
                        out=Path.cwd()/'pes6_patches'/str(time.time_ns())
                        if leagues and leagues.names:
                            prebuilt=leagues.build_entries();archive=grouped.setdefault('rv_e.img',{})
                            if set(archive)&set(prebuilt):raise ValueError('Conflito entre edição de liga e outra edição da mesma entrada')
                            archive.update(prebuilt)
                        if scoreboards and scoreboards.edits:
                            prebuilt=scoreboards.build_entries();archive=grouped.setdefault('rv_e.img',{})
                            if set(archive)&set(prebuilt):raise ValueError('Conflito: placares e galeria alteram a mesma entrada rv_e')
                            archive.update(prebuilt)
                        replacements={'default.xex':(club_report['source_sha256'],names.build())} if names and names.edits else {}
                        result['files']=build(a.iso,out,grouped,q.get('mode',['iso'])[0],replacements)
                        if names and names.edits:
                            (out/'club_names.json').write_text(json.dumps({'source_xex_sha256':club_report['source_sha256'],
                                'modified_xex_sha256':hashlib.sha256(replacements['default.xex'][1]).hexdigest(),
                                'changes':[{ 'record':record,'original_name':names.rows[record]['name'],
                                    'original_short_name':names.rows[record]['short_name'],**values} for record,values in names.edits.items()],
                                'runtime_verified':False,'signature_regenerated':False},ensure_ascii=False,indent=2),encoding='utf-8')
                        result['output_directory']=str(out.resolve());generated_directories.add(result['output_directory'])
                        if scoreboards and scoreboards.edits:
                            (out/'scoreboard_changes.json').write_text(json.dumps(scoreboards.state(),ensure_ascii=False,indent=2),encoding='utf-8')
                        if leagues and (leagues.names or leagues.links):
                            (out/'league_changes.json').write_text(json.dumps({'names':leagues.names,'manual_logo_links':leagues.links,
                                'source_sha256':leagues.state({})['source_sha256'],'runtime_verified':False},ensure_ascii=False,indent=2),encoding='utf-8')
                    else:raise ValueError('Ação desconhecida')
                    result['count']=pending_count();result['items']=catalog()
                self.send(json.dumps(result).encode(),'application/json')
            except Exception as e:
                body=json.dumps({'error':str(e)}).encode();self.send_response(400);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def do_GET(self):
            u=urlparse(self.path);q=parse_qs(u.query)
            try:
                if u.path=='/':self.send(HTML.encode(),'text/html; charset=utf-8');return
                if u.path=='/clubs':self.send(CLUBS_HTML.encode(),'text/html; charset=utf-8');return
                if u.path=='/leagues':self.send(LEAGUES_HTML.encode(),'text/html; charset=utf-8');return
                if u.path=='/scoreboards':self.send(SCOREBOARDS_HTML.encode(),'text/html; charset=utf-8');return
                if u.path=='/scoreboards/data':
                    with lock:
                        data=scoreboards.state() if scoreboards else {'error':'Placares indisponíveis: '+scoreboard_error}
                        data['pendingTotal']=pending_count()
                    self.send(json.dumps(data).encode(),'application/json');return
                if u.path=='/scoreboards/png':
                    if scoreboards is None:raise ValueError('Placares indisponíveis')
                    with lock:png=scoreboards.preview(q['key'][0],'original' in q)
                    self.send(png,'image/png',q['key'][0]+'.png' if 'download' in q else None);return
                if u.path=='/leagues/data':
                    with lock:
                        data=leagues.state(edits) if leagues else {'error':'Ligas indisponíveis: '+league_error}
                        if leagues:data['pendingTotal']=pending_count()
                    self.send(json.dumps(data).encode(),'application/json');return
                if u.path=='/clubs/data':
                    with lock:
                        data=club_state() if clubs is not None and names is not None else {'error':'Catálogo de clubes indisponível: '+club_error}
                    self.send(json.dumps(data).encode(),'application/json');return
                if u.path=='/clubs/crest':
                    view=q.get('view',['original'])[0]
                    if view=='original':target=Path(__file__).parent/'cv_we00_texturas/2710_part062_unpacked.png'
                    elif view=='modified':target=Path(__file__).parent/'research/chelsea_2006_07/chelsea_crest_128_encoded_preview.png'
                    else:raise ValueError('Invalid crest view')
                    self.send(target.read_bytes(),'image/png');return
                if u.path=='/profiles':self.send(PROFILES_HTML.encode(),'text/html; charset=utf-8');return
                if u.path=='/profiles/data':self.send(json.dumps(inspect_profiles(Path(__file__).parent)).encode(),'application/json');return
                if u.path=='/profiles/palettes':self.send(json.dumps(analyze_palettes(Path(__file__).parent)).encode(),'application/json');return
                if u.path=='/profiles/executable':self.send(json.dumps(analyze_executable(Path(__file__).parent/'default.xex')).encode(),'application/json');return
                if u.path=='/research':self.send(json.dumps(load_evidence(Path(__file__).parent,Path(__file__).parent/'research'/'evidence.json')).encode(),'application/json');return
                if u.path=='/config':self.send(json.dumps({'iso':str(a.iso),'version':'0.14'}).encode(),'application/json');return
                if u.path=='/api':self.send(json.dumps(catalog()).encode(),'application/json');return
                if u.path not in ('/png','/dds','/edited'):self.send_error(404);return
                i=int(q['id'][0]); assert 0<=i<len(paths);f=paths[i];name=f'{f.parent.parent.name}_{f.parent.name}_{f.stem}'
                if u.path=='/dds' and items[i]['kind']!='DDS':self.send_error(404);return
                if u.path=='/dds':self.send(f.read_bytes(),'application/octet-stream',name+'.dds');return
                preview=edits.get(i,f.read_bytes())
                if u.path=='/edited' and i in edits and items[i]['kind']=='WE00':
                    root=next(r for r in a.folders if r.name.startswith('cv_extraido'));folder=root/items[i]['entry'];src=folder/'unpacked.bin'
                    if not src.exists():src=folder/'original.bin'
                    raw=leaf(src.read_bytes(),route(items[i]['name']));preview=image_bytes(decode(encode(raw,preview))[0])
                with Image.open(io.BytesIO(preview) if u.path=='/edited' else f) as im:
                    im=im.convert('RGBA')
                    if 'full' not in q:im.thumbnail((320,240))
                    buf=io.BytesIO();im.save(buf,format='PNG')
                self.send(buf.getvalue(),'image/png',name+'.png' if 'download' in q else None)
            except (ValueError,KeyError,IndexError,AssertionError):self.send_error(400)
            except (OSError,NotImplementedError):self.send_error(422,'DDS preview unavailable')
    server=ThreadingHTTPServer(('127.0.0.1',a.port),Handler);url=f'http://127.0.0.1:{a.port}';print(url,flush=True)
    if not a.no_browser:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()
