"""Read-only WE00 indexed and direct color preview extractor. Python + Pillow."""
import argparse,struct,zlib,csv
from pathlib import Path
from PIL import Image
MAX=64*1024*1024

def decode(d):
    if len(d)<16 or d[:4]!=b'WE00' or d[6]!=3:return None
    bpp=d[7]; w,h,p,q=struct.unpack_from('>4H',d,8)
    if not (0<w<=4096 and 0<h<=4096):return None
    if bpp==8 and p==16 and q==1040 and len(d)==q+w*h:
        im=Image.frombytes('P',(w,h),d[q:]);im.putpalette(d[p:q],rawmode='RGBA');return im.convert('RGBA'),'indexed8'
    if bpp in (24,32) and p==0 and q==16 and len(d)==q+w*h*(bpp//8):
        mode='RGBA' if bpp==32 else 'RGB';return Image.frombytes(mode,(w,h),d[q:]),'direct'+str(bpp)
    return None

def walk(d,name,depth=0):
    if depth>12:return
    if d.startswith(b'WE00'):
        yield name,d;return
    if len(d)>=16 and d[3:8]==b'WESYS':
        c,u=struct.unpack_from('>II',d,8)
        if c>len(d)-16:return
        try:
            if d[:3]==b'\x01\x01\x00' and u==0:x=d[16:16+c]
            elif 0<u<=MAX:
                dec=zlib.decompressobj();x=dec.decompress(d[16:16+c],u+1)
                if not dec.eof or len(x)!=u:return
            else:return
        except zlib.error:return
        yield from walk(x,name+'_unpacked',depth+1);return
    if len(d)>=8:
        n,t=struct.unpack_from('>II',d)
        if t!=8 or not 0<n<=10000 or 8+n*12>len(d):return
        parts=[struct.unpack_from('>III',d,8+i*12) for i in range(n)]
        if not all(a>=8+n*12 and a+l<=len(d) for a,l,_ in parts if l):return
        for i,(a,l,_) in enumerate(parts):
            if l:yield from walk(d[a:a+l],f'{name}_part{i:03}',depth+1)

def main(root,out):
    out.mkdir(parents=True,exist_ok=True); count=0; skipped=0
    with (out/'index.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(['resource','format','width','height','file'])
        for folder in sorted(root.iterdir()):
            if not folder.is_dir():continue
            p=folder/'unpacked.bin'
            if not p.exists():p=folder/'original.bin'
            if not p.is_file() or p.stat().st_size>MAX:continue
            for name,d in walk(p.read_bytes(),folder.name):
                result=decode(d)
                if result is None:skipped+=1;continue
                im,fmt=result; filename=name+'.png';im.save(out/filename);writer.writerow([name,fmt,*im.size,filename]);count+=1
            if folder.name.isdigit() and int(folder.name)%500==0:print(f'{folder.name}: {count} PNGs',flush=True)
    print(f'{count} PNGs; {skipped} unsupported WE00 blocks. {out}/index.csv')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('destination',type=Path);a=p.parse_args();main(a.source,a.destination)
