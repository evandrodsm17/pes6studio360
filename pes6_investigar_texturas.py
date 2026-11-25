"""Read-only inventory of nested PES6 resources; no game files modified."""
import argparse,csv,struct,zlib,collections,zipfile,io
from pathlib import Path
MAX=64*1024*1024

def inspect(root,out):
    counts=collections.Counter(); samples=collections.Counter(); rows=[]
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as archive:
        def walk(data,name,depth=0):
            if depth>5:return
            sig=data[:16].hex(' '); kind='unknown'; children=[]
            if data[3:8]==b'WESYS' and len(data)>=16:
                c,u=struct.unpack_from('>II',data,8)
                if c<=len(data)-16:
                    try:
                        if data[:3]==b'\x01\x01\x00' and u==0: x=data[16:16+c]
                        elif 0<u<=MAX:
                            d=zlib.decompressobj(); x=d.decompress(data[16:16+c],u+1)
                            if not d.eof or len(x)!=u:raise ValueError('invalid stream')
                        else:raise ValueError('size limit')
                        kind='WESYS'; children=[('unpacked',x)]
                    except (ValueError,zlib.error):kind='WESYS_unresolved'
            elif len(data)>=8:
                n,t=struct.unpack_from('>II',data)
                if t==8 and 0<n<=10000 and 8+n*12<=len(data):
                    entries=[struct.unpack_from('>III',data,8+i*12) for i in range(n)]
                    if all(a>=8+n*12 and a+l<=len(data) for a,l,_ in entries):
                        kind='part_table';children=[(f'part{i:03d}',data[a:a+l]) for i,(a,l,_) in enumerate(entries) if l]
            if kind=='unknown' and data.startswith(b'WE00'):kind='WE00'
            hits=[]
            for magic in (b'DDS ',b'XPR0',b'XPR2',b'\x89PNG\r\n\x1a\n',b'WESYS',b'WE00',b'TEX0',b'GTF\0'):
                start=0
                while len(hits)<128:
                    p=data.find(magic,start)
                    if p<0:break
                    hits.append(f'{magic.hex()}@{p:#x}');start=p+len(magic)
            key=(kind,data[:4].hex() if kind=='unknown' else '')
            counts[key]+=1
            rows.append((name,len(data),kind,sig,';'.join(hits)))
            if not children and samples[key]<3 and len(data)<=MAX:
                samples[key]+=1
                archive.writestr(f'samples/{name.replace("/","_")}.bin',data[:65536])
            for label,child in children:walk(child,name+'/'+label,depth+1)
        for folder in sorted(root.iterdir()):
            if not folder.is_dir():continue
            p=folder/'unpacked.bin'
            if not p.exists():p=folder/'original.bin'
            if p.is_file() and p.stat().st_size<=MAX:walk(p.read_bytes(),folder.name)
        s=io.StringIO(); w=csv.writer(s);w.writerow(['resource','size','kind','header','signatures']);w.writerows(rows);archive.writestr('inventory.csv',s.getvalue())
        archive.writestr('summary.txt','\n'.join(f'{k}: {v}' for k,v in counts.most_common()))
    print(f'{len(rows)} resources/subresources; report: {out}')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path);p.add_argument('output',type=Path);a=p.parse_args();inspect(a.folder,a.output)
