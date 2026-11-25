"""Conservative PES6 Xbox 360 texture patcher. No relocation of AFS entries."""
import struct,zlib,io,shutil,os,tempfile
from pathlib import Path
from PIL import Image

def convert(original, upload):
    if original[:4]!=b'DDS ' or len(original)<128: raise ValueError('DDS inválido')
    h,w=struct.unpack_from('<II',original,12); m=struct.unpack_from('<I',original,28)[0]; fmt=original[84:88]
    if fmt not in (b'DXT1',b'DXT3',b'DXT5') or m>1: raise ValueError('Formato ou mipmaps ainda não suportados')
    n=((w+3)//4)*((h+3)//4)*(8 if fmt==b'DXT1' else 16)
    if len(original)<128+n: raise ValueError('DDS truncado')
    if upload.startswith(b'DDS '):
        if len(upload)!=128+n or upload[84:88]!=fmt or struct.unpack_from('<II',upload,12)!=(h,w) or struct.unpack_from('<I',upload,28)[0]>1: raise ValueError('DDS deve ter mesmas dimensões, DXT e apenas um nível')
        payload=upload[128:]
    else:
        with Image.open(io.BytesIO(upload)) as im:
            if im.format!='PNG' or im.size!=(w,h): raise ValueError(f'Use PNG de {w} × {h}')
            out=io.BytesIO(); im.convert('RGBA').save(out,format='DDS',pixel_format=fmt.decode()); d=out.getvalue()
        if d[84:88]!=fmt or len(d)!=128+n: raise ValueError('Conversor DDS incompatível; atualize Pillow')
        payload=d[128:]
    return original[:128]+payload+original[128+n:]

def unpack(raw):
    if raw[3:8]!=b'WESYS': raise ValueError('Somente WESYS suportado')
    c,u=struct.unpack_from('>II',raw,8); tail=raw[16+c:]
    if c+16>len(raw) or len(tail)>3 or any(tail): raise ValueError('Cabeçalho ou sufixo WESYS desconhecido')
    if raw[:3]==b'\x01\x01\x00' and u==0: return raw[16:16+c],True
    x=zlib.decompress(raw[16:16+c]);
    if len(x)!=u: raise ValueError('Tamanho WESYS inválido')
    return x,False

def rebuild(raw, edits):
    x,stored=unpack(raw); out=bytearray(x); count,t=struct.unpack_from('>II',x)
    if t!=8 or t+count*12>len(x): raise ValueError('Tabela de partes desconhecida')
    for j,(original,replacement) in edits.items():
        if not 0<=j<count: raise ValueError('Parte inválida')
        a,l,e=struct.unpack_from('>III',x,t+j*12)
        if a<t+count*12 or a+l>len(x) or x[a:a+4]!=b'WE00' or x[a+16:a+l]!=original or len(replacement)!=len(original): raise ValueError('Textura não corresponde ao IMG original')
        out[a+16:a+l]=replacement
    if bytes(out)==x:return raw
    payload=bytes(out) if stored else zlib.compress(out,9)
    r=raw[:8]+struct.pack('>II',len(payload),0 if stored else len(out))+payload
    if not stored:r+=bytes((-len(r))%4)
    assert unpack(r)[0]==out
    return r

def patch(source,dest,edits):
    source,dest=Path(source),Path(dest)
    if source.resolve()==dest.resolve() or dest.exists(): raise ValueError('Destino já existe; escolha outro nome')
    with source.open('rb') as f:
        h=f.read(8)
        if h[:4]!=b'AFS\0':raise ValueError('Não é AFS')
        n=struct.unpack_from('<I',h,4)[0]; size=source.stat().st_size
        if n>(size-8)//8:raise ValueError('Índice inválido')
        es=list(struct.iter_unpack('<II',f.read(n*8))); meta=f.read(8)
        boundaries=sorted({o for o,s in es if s}|{size})
        if len(meta)==8:
            mo,ms=struct.unpack('<II',meta)
            if 0<mo<size:boundaries=sorted(set(boundaries+[mo]))
        changes=[]
        for i,parts in edits.items():
            o,s=es[i]; f.seek(o);raw=f.read(s);r=rebuild(raw,parts)
            limit=min((v for v in boundaries if v>o),default=size)-o
            if len(r)>limit:raise ValueError(f'Entrada {i:04d}: precisa de {len(r)} bytes, espaço disponível {limit}. Use textura mais simples; realocação ainda não suportada.')
            if len(r)>s:
                f.seek(o+s)
                if any(f.read(len(r)-s)):raise ValueError('Espaço adicional não está vazio')
            changes.append((i,o,s,r))
    dest.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=dest.parent);os.close(fd)
    try:
        shutil.copyfile(source,tmp)
        with open(tmp,'r+b') as f:
            for i,o,s,r in changes:
                f.seek(o);f.write(r);f.write(bytes(max(0,s-len(r))))
                f.seek(8+i*8+4);f.write(struct.pack('<I',len(r)))
        with open(tmp,'rb') as f:
            for i,o,s,r in changes:
                f.seek(o);assert f.read(len(r))==r
        # exclusive creation, never replace existing file
        with open(tmp,'rb') as f, dest.open('xb') as g:shutil.copyfileobj(f,g)
    finally:os.unlink(tmp)
    return dest
