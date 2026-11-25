import argparse, hashlib, struct, sys
from pathlib import Path
import shutil, os
MAGIC=b'MICROSOFT*XBOX*MEDIA'; S=2048; CHUNK=8*1024*1024
KNOWN='be36cdd9a864cfaaeddc67ff170d867556db9fe84200b95b6d84f24471bfbcc1'
def locate(iso, names):
    size=iso.stat().st_size; found={name:[] for name in names}
    with iso.open('rb') as f, iso.open('rb') as r:
        tail=b''; pos=0
        while chunk:=f.read(CHUNK):
            buf=tail+chunk; start=0
            while (i:=buf.find(MAGIC,start))>=0:
                start=i+1; off=pos-len(tail)+i; base=off-32*S
                if base<0 or off%S: continue
                r.seek(off); h=r.read(S)
                if len(h)!=S or h[-20:]!=MAGIC: continue
                sec,n=struct.unpack_from('<II',h,20); root=base+sec*S
                if not 14<=n<=16*1024*1024 or root+n>size: continue
                r.seek(root); d=r.read(n); stack=[0]; seen=set()
                while stack:
                    p=stack.pop()
                    if p in seen: continue
                    seen.add(p)
                    if p+14>len(d): continue
                    l,rr,sector,length,attr,nl=struct.unpack_from('<HHIIBB',d,p)
                    if p+14+nl>len(d): continue
                    name=d[p+14:p+14+nl].decode('ascii','replace')
                    if name.lower() in found and not attr&16:
                        target=base+sector*S
                        if target+length<=size: found[name.lower()].append((target,length,base))
                    stack.extend(x*4 for x in (l,rr) if x)
            pos+=len(chunk); tail=buf[-(len(MAGIC)-1):]
    result={}
    for name, matches in found.items():
        matches=list(set(matches))
        if len(matches)!=1: raise ValueError(f'XDVDFS: {name}: {len(matches)} correspondências; esperado 1')
        result[name]=matches[0]
    if len({v[2] for v in result.values()})!=1:raise ValueError('Partições diferentes')
    return result

from pes6_fixed import entry_changes

def build(iso, output, grouped, mode='iso', replacements=None):
    iso=Path(iso); output=Path(output)
    if not iso.is_file():raise ValueError('ISO não encontrada')
    if output.exists():raise ValueError('Destino já existe')
    replacements=replacements or {}
    if set(replacements)-{'default.xex'} or set(replacements)&set(grouped):raise ValueError('Substituição de arquivo inválida')
    locations=locate(iso,list(grouped)+list(replacements)); changes=[]; reports=[]
    with iso.open('rb') as f:
        for name,edits in grouped.items():
            off,n,base=locations[name]
            f.seek(off); digest=hashlib.sha256(); left=n
            while left:
                chunk=f.read(min(left,CHUNK))
                if not chunk:raise ValueError('IMG truncado')
                digest.update(chunk);left-=len(chunk)
            sha=digest.hexdigest()
            if name=='rv_e.img' and sha!=KNOWN:raise ValueError('rv_e.img na ISO não corresponde à edição PAL original validada')
            mods=entry_changes(f,off,n,edits);changes.extend(mods)
            reports.append((name,off,n,sha,mods))
        for name,(expected,new) in replacements.items():
            off,n,base=locations[name];f.seek(off);original=f.read(n)
            if hashlib.sha256(original).hexdigest()!=expected or len(new)!=n:
                raise ValueError('Executável da ISO divergente ou tamanho alterado')
            mods=[] if new==original else [(off,new)]
            changes.extend(mods);reports.append((name,off,n,expected,mods))
    if not changes:raise ValueError('Nenhuma alteração binária')
    output.mkdir(parents=True,exist_ok=False)
    files=[]
    try:
        if mode=='iso':
            target=output/'PES6_MOD.iso'; copy_verified(iso,target,0,iso.stat().st_size,changes);files.append(str(target))
        elif mode=='img':
            for name,off,n,sha,mods in reports:
                if mods:
                    target=output/name;copy_verified(iso,target,off,n,mods);files.append(str(target))
        else:raise ValueError('Modo inválido')
        import json
        (output/'manifest.json').write_text(json.dumps([dict(archive=name,offset=off,size=n,original_sha256=sha,entries_changed=len(mods)) for name,off,n,sha,mods in reports],indent=2),encoding='utf-8')
        return files
    except BaseException:
        shutil.rmtree(output);raise

def copy_verified(source,dest,start,size,changes):
    if shutil.disk_usage(dest.parent).free<size:raise ValueError('Espaço insuficiente')
    changes=sorted(changes)
    for i,(off,data) in enumerate(changes):
        if off<start or off+len(data)>start+size or (i and changes[i-1][0]+len(changes[i-1][1])>off):raise ValueError('Alterações sobrepostas ou fora do arquivo')
    def chunks():
        with source.open('rb') as f:
            f.seek(start); pos=start; idx=0
            while pos<start+size:
                b=f.read(min(CHUNK,start+size-pos))
                if not b:raise ValueError('Origem truncada')
                end=pos+len(b)
                while idx<len(changes) and changes[idx][0]+len(changes[idx][1])<=pos:idx+=1
                j=idx
                while j<len(changes) and changes[j][0]<end:
                    o,d=changes[j];lo=max(pos,o);hi=min(end,o+len(d));b=b[:lo-pos]+d[lo-o:hi-o]+b[hi-pos:];j+=1
                yield b;pos=end
    with dest.open('xb') as f:
        for b in chunks():f.write(b)
    with dest.open('rb') as f:
        for b in chunks():
            if f.read(len(b))!=b:raise ValueError('Falha na verificação binária')
        if f.read(1):raise ValueError('Tamanho divergente')
