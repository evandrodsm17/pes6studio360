import argparse, hashlib, struct, sys
from pathlib import Path
import shutil, os
MAGIC=b'MICROSOFT*XBOX*MEDIA'; S=2048; CHUNK=8*1024*1024
KNOWN='be36cdd9a864cfaaeddc67ff170d867556db9fe84200b95b6d84f24471bfbcc1'
def locate(iso):
    size=iso.stat().st_size; found=[]
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
                    if name.lower()=='rv_e.img' and not attr&16:
                        target=base+sector*S
                        if target+length<=size: found.append((target,length,base))
                    stack.extend(x*4 for x in (l,rr) if x)
            pos+=len(chunk); tail=buf[-(len(MAGIC)-1):]
    found=list(set(found))
    if len(found)!=1: raise ValueError(f'XDVDFS: {len(found)} entradas rv_e.img validas; esperado 1.')
    return found[0]
def main():
    p=argparse.ArgumentParser(); p.add_argument('iso',type=Path); p.add_argument('original',type=Path); p.add_argument('modified',type=Path); p.add_argument('output',type=Path); p.add_argument('--diagnostico',action='store_true'); a=p.parse_args()
    off,n,base=locate(a.iso); print(f'XDVDFS base=0x{base:X}; rv_e.img offset=0x{off:X}; tamanho={n}')
    with a.iso.open('rb') as f: f.seek(off); actual=f.read(n)
    original=a.original.read_bytes(); modified=a.modified.read_bytes()
    for name,data in [('ISO',actual),('IMG local',original),('IMG modificado',modified)]: print(name,len(data),hashlib.sha256(data).hexdigest())
    print('Referencia enviada anteriormente:',KNOWN)
    print('ISO == IMG local:',actual==original)
    if a.diagnostico: return
    if actual!=original: raise ValueError('IMG local diverge da ISO. Nenhuma alteracao realizada.')
    if not actual.startswith(b'AFS\0') or not modified.startswith(b'AFS\0') or len(modified)!=n or actual==modified: raise ValueError('IMG modificado invalido ou identico.')
    if a.output.exists() or len({x.resolve() for x in (a.iso,a.original,a.modified,a.output)})!=4: raise ValueError('Destino deve ser novo e distinto.')
    if shutil.disk_usage(a.output.parent).free<a.iso.stat().st_size: raise ValueError('Espaco insuficiente.')
    created=False
    try:
        with a.iso.open('rb') as src,a.output.open('xb') as dst:
            created=True; pos=0
            while b:=src.read(CHUNK):
                lo=max(pos,off); hi=min(pos+len(b),off+n)
                if lo<hi: b=b[:lo-pos]+modified[lo-off:hi-off]+b[hi-pos:]
                dst.write(b); pos+=len(b)
        with a.iso.open('rb') as src,a.output.open('rb') as dst:
            pos=0
            while b:=src.read(CHUNK):
                lo=max(pos,off); hi=min(pos+len(b),off+n)
                if lo<hi: b=b[:lo-pos]+modified[lo-off:hi-off]+b[hi-pos:]
                if dst.read(len(b))!=b: raise ValueError('Falha na verificacao.')
                pos+=len(b)
            if dst.read(1): raise ValueError('Tamanho divergente.')
        print('OK: ISO verificada:',a.output)
    except BaseException:
        if created: a.output.unlink(missing_ok=True)
        raise
if __name__=='__main__':
    try: main()
    except (OSError,ValueError) as e: print('ERRO:',e,file=sys.stderr); sys.exit(1)
