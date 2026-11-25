"""Create an exact-size experimental WESYS patch; original IMG stays untouched."""
import argparse, pathlib, struct, zlib, hashlib
from pes6_patch import convert, unpack

def run(source, image, dest, entry=29, part=3):
    b=bytearray(source.read_bytes()); assert b[:4]==b'AFS\0'
    n=struct.unpack_from('<I',b,4)[0]; assert 0<=entry<n
    o,s=struct.unpack_from('<II',b,8+entry*8); raw=bytes(b[o:o+s]); x,stored=unpack(raw)
    assert not stored
    c,u=struct.unpack_from('>II',raw,8); count,t=struct.unpack_from('>II',x); assert t==8 and 0<=part<count
    a,l,e=struct.unpack_from('>III',x,t+part*12); assert x[a:a+4]==b'WE00'
    d=x[a+16:a+l]; new=convert(d,image.read_bytes()); out=x[:a+16]+new+x[a+l:]; assert len(out)==u
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
    b[o+16:o+16+c]=stream
    with dest.open('xb') as f:f.write(b)
    print(f'Entrada {entry}, parte {part}: {s} bytes AFS, {c} bytes ZLIB, {u} bytes descompactados; todos preservados.')
    print('SHA256:',hashlib.sha256(b).hexdigest())
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=pathlib.Path);p.add_argument('image',type=pathlib.Path);p.add_argument('dest',type=pathlib.Path);p.add_argument('--entry',type=int,default=29);p.add_argument('--part',type=int,default=3);a=p.parse_args();run(a.source,a.image,a.dest,a.entry,a.part)
