"""Read-only AFS/WESYS extractor and diagnostic tool. Python 3."""
import argparse, csv, struct, zlib
from pathlib import Path

def extract(source, dest):
    dest.mkdir(parents=True, exist_ok=True)
    if source.resolve().is_relative_to(dest.resolve()):
        raise ValueError('Use an output directory separate from the source')
    total = textures = errors = 0
    with source.open('rb') as f, (dest/'index.csv').open('w', newline='', encoding='utf-8') as report:
        size = source.stat().st_size
        h = f.read(8)
        if len(h)!=8 or h[:4]!=b'AFS\0': raise ValueError('Not AFS')
        n = struct.unpack_from('<I',h,4)[0]
        if 8+n*8>size: raise ValueError('Invalid index')
        entries = list(struct.iter_unpack('<II', f.read(n*8)))
        w = csv.writer(report)
        w.writerow(['id','offset','size','format','unpacked_size','dds_count','header_hex','error'])
        for i,(o,s) in enumerate(entries):
            if not s: continue
            total += 1
            fmt, x, tex, err, header = 'raw', None, 0, '', ''
            try:
                if o+s>size: raise ValueError('Entry outside file')
                f.seek(o); raw=f.read(s)
                if len(raw)!=s: raise ValueError('Truncated entry')
                header=raw[:64].hex(' ')
                folder=dest/f'{i:04d}'; folder.mkdir(exist_ok=True)
                (folder/'original.bin').write_bytes(raw)
                if raw[3:8]==b'WESYS':
                    fmt='WESYS_unknown'
                    if len(raw)<16: raise ValueError('Truncated WESYS header')
                    c,u=struct.unpack_from('>II',raw,8)
                    if c+16>len(raw): raise ValueError(f'Invalid WESYS size: {c}')
                    if raw[:3]==b'\x01\x01\x00' and u==0 and c+16==len(raw):
                        x=raw[16:16+c]
                        fmt='WESYS_stored'
                    else:
                        x=zlib.decompress(raw[16:16+c])
                        if len(x)!=u: raise ValueError(f'Size mismatch: expected {u}, got {len(x)}')
                        fmt='WESYS_zlib'
                elif len(raw)>=2 and raw[0]&15==8 and raw[0]>>4<=7 and int.from_bytes(raw[:2],'big')%31==0:
                    fmt='zlib_candidate'
                    d=zlib.decompressobj()
                    x=d.decompress(raw, 256*1024*1024)
                    if not d.eof: raise ValueError('Incomplete or oversized ZLIB stream')
                    fmt='zlib_direct'
                if x is not None:
                    (folder/'unpacked.bin').write_bytes(x)
                    if len(x)>=8:
                        count,table=struct.unpack_from('>II',x)
                        if table==8 and table+count*12<=len(x):
                            for j in range(count):
                                a,l,end=struct.unpack_from('>III',x,table+j*12)
                                if a<table+count*12 or a+l>len(x): continue
                                part=x[a:a+l]
                                (folder/f'part_{j:03d}.bin').write_bytes(part)
                                if part[:4]==b'WE00' and part[16:20]==b'DDS ':
                                    (folder/f'texture_{j:03d}.dds').write_bytes(part[16:]); tex+=1
            except (ValueError,struct.error,zlib.error) as exc:
                err=str(exc); errors+=1
                print(f'Warning: entry {i:04d}: {err}', flush=True)
                if fmt=='raw': fmt='invalid'
            textures+=tex
            w.writerow([i,o,s,fmt,len(x) if x is not None else 0,tex,header,err])
            report.flush()
            if total%100==0: print(f'Processed {total} entries...',flush=True)
    print(f'Processed {total} entries, {textures} DDS textures, {errors} errors. Report: {dest / "index.csv"}')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path); p.add_argument('destination',type=Path)
    args=p.parse_args(); extract(args.source,args.destination)
