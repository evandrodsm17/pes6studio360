import base64, hashlib, json, os, tempfile
from pathlib import Path

def key(p):
    if p.suffix.lower()=='.png':return 'WE00/'+p.parent.name+'/'+p.name
    return '/'.join((p.parent.parent.name,p.parent.name,p.name))
def save(file,iso,paths,edits,tags,club_names=None,name_source_sha256=None,league_names=None,league_logo_links=None,league_source_sha256=None,scoreboard_textures=None,player_database=None):
    file=Path(file);file.parent.mkdir(parents=True,exist_ok=True)
    data={'version':1,'iso':str(iso),'iso_size':iso.stat().st_size,'edits':{key(paths[i]):{'sha256':hashlib.sha256(paths[i].read_bytes()).hexdigest(),'dds':base64.b64encode(d).decode('ascii')} for i,d in edits.items()},'tags':{key(paths[i]):t for i,t in tags.items()}}
    if club_names is not None:data.update(club_names=club_names,name_source_sha256=name_source_sha256)
    if league_names is not None:data.update(league_names=league_names,league_logo_links=league_logo_links or {},league_source_sha256=league_source_sha256)
    if scoreboard_textures is not None:data['scoreboard_textures']=scoreboard_textures
    if player_database is not None:data['player_database']=player_database
    fd,tmp=tempfile.mkstemp(dir=file.parent,prefix='.pes6-')
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False)
        os.replace(tmp,file)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
def load(file,iso,paths):
    data=json.loads(Path(file).read_text(encoding='utf-8'))
    if data['version']!=1 or data['iso_size']!=iso.stat().st_size or Path(data['iso']).resolve()!=iso.resolve():raise ValueError('Projeto vinculado a outra ISO')
    keys={key(p):i for i,p in enumerate(paths)};edits={};tags={}
    if len(keys)!=len(paths):raise ValueError('Identificadores duplicados no catálogo')
    for k,v in data['edits'].items():
        i=keys[k];
        orig=paths[i].read_bytes();d=base64.b64decode(v['dds'],validate=True)
        if hashlib.sha256(orig).hexdigest()!=v['sha256'] or (paths[i].suffix.lower()=='.dds' and (len(d)!=len(orig) or d[:128]!=orig[:128])):raise ValueError('Textura original divergente: '+k)
        if paths[i].suffix.lower()=='.png':
            from PIL import Image
            import io
            with Image.open(io.BytesIO(orig)) as o, Image.open(io.BytesIO(d)) as m:
                if m.format!='PNG' or m.size!=o.size:raise ValueError('PNG do projeto inválido')
        edits[i]=d
    for k,v in data.get('tags',{}).items():
        if k in keys and v in ('Uniformes','Faces','Cabelos','Placares','Menus','Escudos','Estádios','Outros'):tags[keys[k]]=v
    return edits,tags
