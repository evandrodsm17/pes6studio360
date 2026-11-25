"""Conservative WE00 encoder and recursive fixed-size reconstruction."""
import io,re,struct,zlib
from PIL import Image,ImageOps
from pes6_we00_catalogo import decode
from pes6_patch import unpack

def route(name):
    if not re.fullmatch(r'\d+(?:_part\d+|_unpacked)*',name):raise ValueError('Identificador WE00 inválido')
    return tuple('u' if s=='unpacked' else int(s[4:]) for s in name.split('_')[1:])

def image_bytes(im):
    b=io.BytesIO();im.save(b,format='PNG');return b.getvalue()

def encode(original,upload,fit='strict'):
    decoded=decode(original)
    if decoded is None:raise ValueError('WE00 não suportado')
    old,fmt=decoded; w,h=old.size
    with Image.open(io.BytesIO(upload)) as im:
        if im.format!='PNG':raise ValueError('WE00 aceita apenas PNG')
        im=im.convert('RGBA')
    if fit=='contain':
        im=ImageOps.contain(im,(w,h),Image.Resampling.LANCZOS); canvas=Image.new('RGBA',(w,h));canvas.paste(im,((w-im.width)//2,(h-im.height)//2));im=canvas
    elif fit=='stretch':im=im.resize((w,h),Image.Resampling.LANCZOS)
    elif fit!='strict':raise ValueError('Ajuste inválido')
    if im.size!=(w,h):raise ValueError(f'Use PNG de {w} × {h}')
    if im.tobytes()==old.convert('RGBA').tobytes():return original
    if fmt=='indexed8':
        q=im.quantize(colors=256,method=Image.Quantize.FASTOCTREE,dither=Image.Dither.NONE)
        # Derive exact RGBA palette used by Pillow, including alpha.
        palette=q.getpalette(rawmode='RGBA'); palette=bytes(palette)
        palette=(palette+bytes(1024))[:1024]
        result=original[:16]+palette+q.tobytes()
    else:result=original[:16]+im.convert('RGBA' if fmt=='direct32' else 'RGB').tobytes()
    if len(result)!=len(original) or decode(result) is None:raise ValueError('Reconstrução WE00 inválida')
    return result

def table(d):
    if len(d)<8:raise ValueError('Tabela truncada')
    n,t=struct.unpack_from('>II',d)
    if t!=8 or not 0<n<=10000 or 8+n*12>len(d):raise ValueError('Tabela desconhecida')
    parts=[struct.unpack_from('>III',d,8+i*12) for i in range(n)]
    spans=sorted((a,a+l) for a,l,_ in parts if l)
    if any(a<8+n*12 or b>len(d) for a,b in spans) or any(b>c for (_,b),(c,_) in zip(spans,spans[1:])):raise ValueError('Tabela sobreposta ou inválida')
    return parts

def leaf(d,path):
    for k in path:
        if k=='u':d=unpack(d)[0]
        else:
            a,l,_=table(d)[k];d=d[a:a+l]
    return d

def rewrite(d,edits):
    if () in edits:
        if len(edits)!=1:raise ValueError('Edições sobrepostas')
        old,new=edits[()]
        if d!=old or len(new)!=len(d):raise ValueError('WE00 original divergente')
        return new
    if not edits:return d
    groups={}
    for p,v in edits.items():groups.setdefault(p[0],{})[p[1:]]=v
    if 'u' in groups:
        if len(groups)!=1:raise ValueError('Caminho misto inválido')
        x,stored=unpack(d); out=rewrite(x,groups['u'])
        if out==x:return d
        from pes6_fixed import exact_stream
        c,u=struct.unpack_from('>II',d,8);stream=out if stored else exact_stream(d,out,c)
        r=d[:16]+stream+d[16+c:]
        if len(r)!=len(d) or unpack(r)[0]!=out:raise ValueError('Falha WESYS')
        return r
    parts=table(d);out=bytearray(d)
    for k,v in groups.items():
        a,l,_=parts[k];out[a:a+l]=rewrite(d[a:a+l],v)
    return bytes(out)

def source_leaf(raw,name):
    # extractor starts from unpacked.bin when outer WESYS exists
    if raw[3:8]==b'WESYS':return ('u',)+route(name)
    if len(raw)>=2 and raw[0]&15==8 and int.from_bytes(raw[:2],'big')%31==0:raise ValueError('ZLIB direto ainda não suportado para escrita')
    return route(name)
