import struct, zlib, hashlib
from dataclasses import dataclass
from pes6_patch import unpack

@dataclass(frozen=True)
class EntryReplacement:
    source_sha256: str
    data: bytes
    allow_growth: bool = False

def exact_stream(raw,out,c):
    stream=None
    for mem in (8,9,7,6,5,4,3,2,1):
        for level in range(9,0,-1):
            for strategy in (zlib.Z_DEFAULT_STRATEGY,zlib.Z_FILTERED,zlib.Z_FIXED,zlib.Z_RLE,zlib.Z_HUFFMAN_ONLY):
                obj=zlib.compressobj(level,zlib.DEFLATED,-15,mem,strategy)
                prefix=obj.compress(out)+obj.flush(zlib.Z_SYNC_FLUSH)
                remaining=c-8-len(prefix)
                # Empty fixed blocks consume 10 bits each; final block consumes 10 bits.
                for k in range(20):
                    extra=(10*(k+1)+7)//8
                    pad=c-6-len(prefix)-extra
                    if pad<0 or pad%5: continue
                    bits=1<<(10*k) | 1<<(10*k+1)
                    for j in range(k): bits |= 2<<(10*j)
                    candidate=raw[16:18]+prefix+b'\x00\x00\x00\xff\xff'*(pad//5)+bits.to_bytes(extra,'little')+struct.pack('>I',zlib.adler32(out)&0xffffffff)
                    dec=zlib.decompressobj()
                    if len(candidate)==c and dec.decompress(candidate)==out and dec.eof and not dec.unused_data:
                        stream=candidate; break
                if stream is not None: break
            if stream is not None: break
        if stream is not None: break
    if stream is None: raise ValueError('Não foi possível manter o tamanho comprimido exato')
    dec=zlib.decompressobj(); assert dec.decompress(stream)==out and dec.eof and not dec.unused_data
    assert len(stream)==c
    return stream

def rebuild_fixed(raw, edits):
    if any(isinstance(k,tuple) for k in edits):
        from pes6_we00_edit import rewrite,source_leaf,leaf,encode
        from PIL import Image
        import io
        nested={}
        for k,(original,replacement) in edits.items():
            if isinstance(k,tuple):
                path=source_leaf(raw,k[0]); old=leaf(raw,path)
                from pes6_we00_catalogo import decode
                decoded=decode(old)
                if decoded is None:raise ValueError('WE00 inválido na ISO')
                with Image.open(io.BytesIO(original)) as im:
                    if im.size!=decoded[0].size or im.convert('RGBA').tobytes()!=decoded[0].convert('RGBA').tobytes():raise ValueError('PNG original diverge do WE00 da ISO')
                nested[path]=(old,encode(old,replacement))
            else:
                path=('u',k);old=leaf(raw,path)
                if old[:4]!=b'WE00' or old[16:]!=original:raise ValueError('DDS original divergente')
                nested[path]=(old,old[:16]+replacement)
        return rewrite(raw,nested)
    x,stored=unpack(raw)
    count,t=struct.unpack_from('>II',x)
    if t!=8 or t+count*12>len(x): raise ValueError('Tabela de partes desconhecida')
    out=bytearray(x)
    for j,(original,replacement) in edits.items():
        if not 0<=j<count: raise ValueError('Parte inválida')
        a,l,e=struct.unpack_from('>III',x,t+j*12)
        if a<t+count*12 or l<16 or a+l>len(x) or x[a:a+4]!=b'WE00' or x[a+16:a+l]!=original or len(replacement)!=len(original):
            raise ValueError('DDS extraído diverge do IMG da ISO; extraia novamente a partir da ISO limpa')
        out[a+16:a+l]=replacement
    if out==x:return raw
    c,u=struct.unpack_from('>II',raw,8)
    stream=bytes(out) if stored else exact_stream(raw,bytes(out),c)
    result=raw[:16]+stream+raw[16+c:]
    if len(result)!=len(raw) or unpack(result)[0]!=out:raise ValueError('Falha de validação WESYS')
    return result

def entry_changes(f,base,size,edits):
    f.seek(base); h=f.read(8)
    if h[:4]!=b'AFS\0':raise ValueError('IMG não é AFS')
    n=struct.unpack_from('<I',h,4)[0]
    if n>(size-8)//8:raise ValueError('Índice AFS inválido')
    table=f.read(n*8); changes=[]
    for i,parts in sorted(edits.items()):
        if not 0<=i<n:raise ValueError('Entrada AFS inválida')
        o,s=struct.unpack_from('<II',table,i*8)
        if o<8+n*8 or s<16 or o+s>size:raise ValueError('Limites AFS inválidos')
        f.seek(base+o); raw=f.read(s)
        try:
            if isinstance(parts,EntryReplacement):
                if hashlib.sha256(raw).hexdigest()!=parts.source_sha256 or (not parts.allow_growth and len(parts.data)!=len(raw)):
                    raise ValueError('Entrada binária divergente ou tamanho alterado')
                if parts.allow_growth:
                    rows=list(struct.iter_unpack('<II',table))
                    capacity=min([other_o for j,(other_o,other_s) in enumerate(rows) if j!=i and other_s and other_o>o]+[size])-o
                    if len(parts.data)>capacity:raise ValueError('Entrada não cabe no espaço AFS disponível')
                    if any(j!=i and other_s and other_o<o+s and other_o+other_s>o for j,(other_o,other_s) in enumerate(rows)):
                        raise ValueError('Entrada compartilha bytes com outro recurso AFS')
                    if len(parts.data)>s:
                        f.seek(base+o+s)
                        if any(f.read(len(parts.data)-s)):raise ValueError('Espaço AFS adicional não está vazio')
                    if len(parts.data)!=s:changes.append((base+8+i*8+4,struct.pack('<I',len(parts.data))))
                new=parts.data
            else:new=rebuild_fixed(raw,parts)
        except ValueError as exc:raise ValueError(f'Entrada {i:04d}: {exc}') from exc
        if new!=raw:changes.append((base+o,new))
    return changes
