"""PES 6 Xbox 360 - AFS/WESYS extractor (read-only). Python 3."""
import argparse, struct, zlib, csv
from pathlib import Path

def extract(source, dest):
    dest.mkdir(parents=True, exist_ok=True)
    b=source.read_bytes()
    if b[:4]!=b"AFS\0": raise ValueError("Not AFS")
    n=struct.unpack_from("<I", b,4)[0]
    if 8+n*8>len(b): raise ValueError("Invalid index")
    rows=[]
    for i in range(n):
        o,s=struct.unpack_from("<II",b,8+i*8)
        if not s: continue
        if o+s>len(b): raise ValueError(f"Invalid entry {i}")
        raw=b[o:o+s]
        folder=dest/f"{i:04d}"
        folder.mkdir(exist_ok=True)
        (folder/"original.bin").write_bytes(raw)
        if raw[3:8]!=b"WESYS":
            rows.append([i,o,s,"raw",0,0]); continue
        c,u=struct.unpack_from(">II",raw,8)
        if c+16>len(raw): raise ValueError(f"Invalid WESYS {i}")
        x=zlib.decompress(raw[16:16+c])
        if len(x)!=u: raise ValueError(f"Size mismatch {i}")
        (folder/"unpacked.bin").write_bytes(x)
        count,table=struct.unpack_from(">II",x)
        tex=0
        if table==8 and table+count*12<=len(x):
            for j in range(count):
                a,l,end=struct.unpack_from(">III",x,table+j*12)
                if a+l>len(x): continue
                part=x[a:a+l]
                (folder/f"part_{j:03d}.bin").write_bytes(part)
                if part[:4]==b"WE00" and part[16:20]==b"DDS ":
                    (folder/f"texture_{j:03d}.dds").write_bytes(part[16:])
                    tex+=1
        rows.append([i,o,s,"WESYS",len(x),tex])
    with (dest/"index.csv").open("w",newline="") as f:
        w=csv.writer(f); w.writerow(["id","offset","size","format","unpacked_size","dds_count"]); w.writerows(rows)
    print(f"Extracted {len(rows)} entries, {sum(r[-1] for r in rows)} DDS textures.")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("source",type=Path)
    p.add_argument("destination",type=Path)
    args=p.parse_args()
    extract(args.source,args.destination)
