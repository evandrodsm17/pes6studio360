"""Manual, persistent team-to-texture mapping; never guesses team identity."""
import json, hashlib, os, tempfile
from pathlib import Path
from pes6_project import key
SLOTS=('Principal','Reserva','Goleiro 1','Goleiro 2','Alternativo','Detalhe')
def candidate(t):
    return t.get('kind','DDS')=='DDS' and t['archive'].lower().startswith('cv_extraido') and 190<=int(t['entry'])<=851
class TeamMap:
    def __init__(self,file,paths):
        self.file=Path(file);self.paths=paths;self.records={}
        if self.file.exists():
            data=json.loads(self.file.read_text(encoding='utf-8'))
            if data.get('version')!=1:raise ValueError('Versão de mapa desconhecida')
            self.records=data['textures']
    def get(self,i):
        p=self.paths[i];r=self.records.get(key(p),{})
        if r and r['sha256']!=hashlib.sha256(p.read_bytes()).hexdigest():return {}
        return r
    def set(self,i,team,slot):
        team=team.strip();p=self.paths[i];k=key(p)
        if team and (len(team)>100 or slot not in SLOTS):raise ValueError('Equipe ou posição inválida')
        new=dict(self.records)
        r=dict(self.get(i));r.update(team=team,slot=slot if team else '',sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        if team or r.get('category'):new[k]=r
        else:new.pop(k,None)
        self._write(new)
    def set_category(self,i,tag):
        if tag not in ('','Uniformes','Faces','Cabelos','Placares','Menus','Escudos','Estádios','Bandeiras de clubes','Bandeiras de seleções','Números','Chuteiras','Outros'):raise ValueError('Categoria inválida')
        p=self.paths[i];k=key(p);new=dict(self.records);r=dict(self.get(i));r.update(category=tag,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        if tag or r.get('team'):new[k]=r
        else:new.pop(k,None)
        self._write(new)
    def _write(self,new):
        self.file.parent.mkdir(parents=True,exist_ok=True)
        fd,tmp=tempfile.mkstemp(dir=self.file.parent,prefix='.teams-')
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump({'version':1,'textures':new},f,ensure_ascii=False,indent=2)
            os.replace(tmp,self.file)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
        self.records=new
