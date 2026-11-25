"""Reusable club/crest editing over the Studio's existing project and build state."""
from collections import defaultdict
from pathlib import Path
from PIL import Image
from pes6_binary import afs_index
from pes6_fixed import rebuild_fixed


class ClubEditor:
    def __init__(self,report,items,paths,root):
        self.report=report;self.items=items;self.paths=paths;self.root=Path(root)
        by_name=defaultdict(list)
        for item in items:
            if item['kind']=='WE00':by_name[item['name']].append(item)
        self.resources={}
        for row in report['records']:
            ref=row['graphic_reference_10'];resources=[]
            if ref==row['graphic_reference_12']:
                for entry,size in ((2710,128),(2711,64)):
                    matches=by_name.get(f'{entry}_part{ref:03}_unpacked',[])
                    if len(matches)==1:
                        item=matches[0]
                        with Image.open(paths[item['id']]) as im:
                            if im.size!=(size,size):continue
                        resources.append({'id':item['id'],'name':item['name'],'entry':entry,'size':size})
            self.resources[row['record']]=resources

    def selected(self,record):
        if type(record) is not int or record not in self.resources:raise ValueError('Clube inválido')
        resources=self.resources[record]
        if len(resources)!=2:raise ValueError('As duas resoluções do escudo não estão disponíveis sem ambiguidade')
        return resources

    def state(self,edits):
        result=[];target=self.report['target']
        for row in self.report['records']:
            resources=self.resources[row['record']]
            verified=row['record']==target['name_record'] and target['runtime_verified']
            label=row['name']
            if verified:label=target['requested_identity']+' ('+label+')'
            result.append({'record':row['record'],'name':row['name'],'label':label,
                           'short_name':row['short_name'],'reference':row['graphic_reference_10'],
                           'evidence':'Escudo confirmado em jogo pelo usuário' if verified else 'Referência da tabela do executável',
                           'available':len(resources)==2,
                           'sharedWith':[other['name'] for other in self.report['records']
                                         if other['record']!=row['record'] and
                                         other['graphic_reference_10']==row['graphic_reference_10'] and
                                         other['graphic_reference_12']==row['graphic_reference_12']],
                           'resources':[dict(r,modified=r['id'] in edits) for r in resources]})
        return {'records':result,'pendingTotal':len(edits),
                'source_sha256':self.report['source_sha256']}

    def stage(self,record,body,fit,prepare,edits):
        if fit not in ('contain','stretch'):raise ValueError('Ajuste inválido')
        resources=self.selected(record)
        # Prepare both sizes before changing shared state. A failure keeps all edits.
        pending={r['id']:prepare(r['id'],body,{'fit':[fit]}) for r in resources}
        affected={r['entry'] for r in resources};merged=dict(edits)
        for i,(old,new) in pending.items():
            if old==new:merged.pop(i,None)
            else:merged[i]=new
        grouped=defaultdict(dict)
        for i,replacement in merged.items():
            item=self.items[i]
            if item['kind']=='WE00' and int(item['entry']) in affected:
                grouped[int(item['entry'])][(item['name'],)]=(self.paths[i].read_bytes(),replacement)
        # Verify the actual compressed entry capacity before committing the upload.
        with (self.root/'cv.img').open('rb') as f:
            index=afs_index(f)
            for entry,changes in grouped.items():
                offset,size=index[entry];f.seek(offset)
                try:rebuild_fixed(f.read(size),changes)
                except ValueError as exc:raise ValueError(f'O escudo não cabe no recurso {entry}: {exc}') from exc
        for i,(old,new) in pending.items():
            if old==new:edits.pop(i,None)
            else:edits[i]=new
        return [r['id'] for r in resources]

    def undo(self,record,edits):
        for r in self.selected(record):edits.pop(r['id'],None)


HTML='''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PES6 Studio · Clubes, nomes e escudos</title><style>
*{box-sizing:border-box}body{margin:0;background:#10151f;color:#e5edf7;font:15px system-ui}header{background:#192333;padding:20px 28px}
h1{margin:6px 0;color:#a5df72}a{color:#a5df72}button,input,select{font:inherit;background:#26354a;color:white;border:1px solid #455670;border-radius:7px;padding:10px}button{cursor:pointer}button:disabled{opacity:.45;cursor:default}
main{display:grid;grid-template-columns:300px 1fr;gap:24px;padding:24px 28px}aside,section{background:#1c2635;border-radius:10px;padding:18px}#search{width:100%;margin-bottom:12px}#clubList{width:100%;height:65vh}
.previews{display:flex;gap:18px;flex-wrap:wrap}.card{background:#10151f;padding:14px;border-radius:8px;min-width:180px}.card img{width:128px;height:128px;object-fit:contain;background:repeating-conic-gradient(#334155 0% 25%,#202a38 0% 50%) 50%/16px 16px}
.pair{display:flex;gap:18px}.pair p{font-size:13px}.actions{display:flex;gap:10px;flex-wrap:wrap;margin:18px 0}small{color:#a5b4c8}#status{white-space:pre-wrap;overflow-wrap:anywhere}#result a{display:block}code{overflow-wrap:anywhere}
footer{padding:18px;background:#192333;border-radius:8px;margin-top:22px}@media(max-width:850px){main{grid-template-columns:1fr}#clubList{height:200px}}
</style><header><a href="/">Galeria de texturas</a><h1>Clubes, nomes e escudos</h1><small>Importe um PNG para preparar as duas resoluções. Confira o resultado convertido antes de gerar o patch.</small></header>
<main><aside><label for="search">Buscar equipe</label><input id="search" placeholder="Nome, sigla ou referência">
<select id="clubList" size="20" aria-label="Equipe"></select><p id="clubCount"></p></aside>
<section><h2 id="title">Carregando equipes...</h2><p id="evidence"></p><p id="availability"></p><div class="previews" id="previews"></div>
<h3>Nome e sigla dentro do jogo</h3><div class="actions"><label>Nome<br><input id="clubName" aria-label="Nome do clube"></label><label>Sigla<br><input id="shortName" aria-label="Sigla do clube"></label></div>
<p id="nameLimits"></p><div class="actions"><button id="saveName" disabled>Preparar nome e sigla</button><button id="undoName" disabled>Restaurar nome original</button></div>
<small>Os limites correspondem ao espaço de texto desta equipe no jogo. A exportação de nomes modifica o executável e requer teste no Xenia; console físico ainda não validado.</small>
<div class="actions"><input id="upload" type="file" accept="image/png,.png" aria-label="Novo escudo PNG"><select id="fit" aria-label="Ajuste da imagem"><option value="contain">Manter proporção e transparência</option><option value="stretch">Preencher toda a área</option></select></div>
<div class="actions"><button id="stage" disabled>Importar nas duas resoluções</button><button id="undo" disabled>Restaurar escudo deste clube</button></div>
<p id="status" role="status"></p><details><summary>Outros recursos do clube</summary><p>Uniformes: use a galeria para importar artes e salvar vínculos manuais já conferidos. A seleção de placar por competição ainda não está disponível neste editor.</p><a href="/">Abrir galeria de uniformes e demais texturas</a></details>
<footer><strong id="pending">0 alterações no projeto</strong><div class="actions"><button id="save">Salvar projeto</button><button id="load">Carregar projeto</button><select id="mode" aria-label="Formato de saída"><option value="iso">ISO para Xenia</option><option value="img">IMG para console (experimental)</option></select><button id="build" disabled>Gerar patch verificado</button></div>
<p id="result" role="status"></p><button id="openOutput" hidden>Abrir pasta do patch</button><small>O patch inclui todas as alterações do projeto, inclusive as feitas na galeria. Os arquivos originais são preservados.</small></footer></section></main>
<script>
const $=id=>document.getElementById(id);let state,selected=null,busy=false,outputDirectory=null;const mutators=['stage','undo','save','load','build','openOutput','saveName','undoName'];
function controls(){for(const id of mutators)$(id).disabled=busy||!state;const row=state?.records.find(r=>r.record===selected);
$('stage').disabled=busy||!row?.available||!$('upload').files.length;$('undo').disabled=busy||!row?.resources.some(r=>r.modified);$('build').disabled=busy||!state?.pendingTotal;$('clubList').disabled=busy;$('search').disabled=busy;$('upload').disabled=busy;$('fit').disabled=busy;$('mode').disabled=busy;nameControls()}
function nameControls(){const row=state?.records.find(r=>r.record===selected);$('clubName').disabled=$('shortName').disabled=busy||!row;
const name=$('clubName').value.trim(),short=$('shortName').value.trim(),bytes=s=>new TextEncoder().encode(s).length;
$('nameLimits').textContent=row?'Nome: '+bytes(name)+'/'+row.name_limits.name+' bytes · Sigla: '+bytes(short)+'/'+row.name_limits.short_name+' bytes.':'';
$('saveName').disabled=busy||!row||!name||!short||bytes(name)>row.name_limits.name||bytes(short)>row.name_limits.short_name||name===row.edited_name&&short===row.edited_short_name;
$('undoName').disabled=busy||!row?.name_modified}
$('clubName').oninput=$('shortName').oninput=nameControls;
async function request(url,body){const response=await fetch(url,body===undefined?{}:{method:'POST',body});let data;try{data=await response.json()}catch{throw Error('O servidor não retornou uma resposta válida')}
if(!response.ok||data.error)throw Error(data.error||'Falha HTTP '+response.status);return data}
async function refresh(){state=await request('/clubs/data');list();render()}
function list(){const q=$('search').value.trim().toLowerCase(),rows=state.records.filter(r=>(r.label+' '+r.short_name+' '+r.reference).toLowerCase().includes(q));
$('clubList').replaceChildren();for(const row of rows){const option=new Option(row.label+(row.resources.some(r=>r.modified)?' • alterado':''),String(row.record));$('clubList').add(option)}
if(!rows.some(r=>r.record===selected))selected=rows[0]?.record??null;if(selected!==null)$('clubList').value=String(selected);$('clubCount').textContent=rows.length+' equipes e registros especiais'}
function render(){const row=state.records.find(r=>r.record===selected);$('previews').replaceChildren();$('title').textContent=row?.label||'Nenhuma equipe encontrada';$('evidence').textContent=row?.evidence||'';
$('availability').textContent=row?(row.available?'Escudos de 128×128 e 64×64 disponíveis.':'Importação indisponível: faltam recursos ou há mais de um catálogo correspondente.'):'Altere a busca para escolher uma equipe.';
if(row?.sharedWith.length)$('availability').textContent+=' Este mesmo recurso também é referenciado por: '+row.sharedWith.join(', ')+'.';
for(const resource of row?.resources||[]){const card=document.createElement('article');card.className='card';const heading=document.createElement('h3');heading.textContent=resource.size+'×'+resource.size;
const pair=document.createElement('div');pair.className='pair';for(const modified of [false,true]){const box=document.createElement('div'),label=document.createElement('p'),im=document.createElement('img');
label.textContent=modified?(resource.modified?'Modificado':'Sem alteração'):'Original';im.alt=label.textContent+' '+resource.size+' pixels';im.src=(modified?'/edited':'/png')+'?id='+resource.id+'&full=1&v='+Date.now();box.append(label,im);pair.append(box)}
const download=document.createElement('a');download.href='/png?id='+resource.id+'&full=1&download=1';download.textContent='Exportar PNG original';card.append(heading,pair,download);$('previews').append(card)}
$('clubName').value=row?.edited_name||'';$('shortName').value=row?.edited_short_name||'';
$('pending').textContent=state.pendingTotal+' alterações no projeto';controls()}
$('search').oninput=()=>{list();render()};$('clubList').onchange=()=>{selected=Number($('clubList').value);$('upload').value='';$('status').textContent='';render()};$('upload').onchange=controls;
async function action(url,body,message){busy=true;controls();$('status').textContent='Processando...';try{const result=await request(url,body);await refresh();$('status').textContent=message||result.message||'Concluído';return result}catch(e){$('status').textContent=e.message;return null}finally{busy=false;controls()}}
$('stage').onclick=async()=>{const file=$('upload').files[0];if(!file||selected===null)return;await action('/clubs/stage?record='+selected+'&fit='+$('fit').value,file,'Escudo preparado nas duas resoluções. Confira as prévias, salve o projeto e gere o patch.')};
$('undo').onclick=()=>action('/clubs/undo?record='+selected,'','Escudo restaurado nas duas resoluções.');
$('saveName').onclick=()=>action('/clubs/name?record='+selected,JSON.stringify({name:$('clubName').value,short_name:$('shortName').value}),'Nome e sigla preparados. Salve o projeto e gere o patch para aplicar no jogo.');
$('undoName').onclick=()=>action('/clubs/nameUndo?record='+selected,'','Nome e sigla originais restaurados.');
$('save').onclick=()=>action('/save','');$('load').onclick=()=>{if(confirm('Carregar o projeto salvo e substituir as alterações atuais?'))action('/load','')};
$('build').onclick=async()=>{outputDirectory=null;$('openOutput').hidden=true;$('result').textContent='Gerando e verificando o patch. Aguarde...';const result=await action('/build?mode='+$('mode').value,'','');
$('result').replaceChildren();if(result){for(const file of result.files){const p=document.createElement('p');p.textContent=file;$('result').append(p)}outputDirectory=result.output_directory;$('openOutput').hidden=!outputDirectory;$('status').textContent='Patch gerado e verificado. Abra a ISO resultante no Xenia para conferir no jogo.'}else $('result').textContent='O patch não foi gerado. Veja a mensagem acima.'};
$('openOutput').onclick=()=>{if(outputDirectory)action('/openOutput',JSON.stringify({directory:outputDirectory}),'Pasta do patch aberta.')};
refresh().catch(e=>{$('status').textContent=e.message;controls()});
</script></html>'''
