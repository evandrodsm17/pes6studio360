"""Read-only scan of decompressed resources for team-name anchors and candidate numeric references."""
import argparse,csv,struct,zipfile,json
from pathlib import Path
NAMES=['Real Madrid','Barcelona','Chelsea','Arsenal','Manchester United','Liverpool','Juventus','Bayern','Brazil','Brasil','Argentina','England','France','Inter Milan','AC Milan','Portugal']
def run(roots,out):
 rows=[]; samples={}; scanned=0
 for root in roots:
  for p in sorted(root.glob('*/unpacked.bin')):
   try: n=int(p.parent.name)
   except ValueError:continue
   # Names can be elsewhere; scan all unpacked entries, but only retain bounded samples.
   data=p.read_bytes();scanned+=1;low=data.lower()
   for name in NAMES:
    for enc in ('ascii','utf-16-le','utf-16-be'):
     needle=name.lower().encode(enc); start=0; count=0
     while (off:=low.find(needle,start))>=0 and count<20:
      start=off+len(needle);count+=1; lo=max(0,off-64);hi=min(len(data),off+len(needle)+64)
      rows.append([root.name,n,off,name,enc,data[lo:hi].hex()])
   if n<=60 and len(data)<=2*1024*1024:samples[f'{root.name}/{n:04d}.bin']=data
 with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED) as z:
  import io
  b=io.StringIO();w=csv.writer(b);w.writerow(['archive','entry','offset','name','encoding','context_hex']);w.writerows(rows);z.writestr('name_hits.csv',b.getvalue());z.writestr('summary.json',json.dumps(dict(scanned=scanned,hits=len(rows),samples=len(samples)),indent=2))
  for k,v in samples.items():z.writestr(k,v)
 print(f'{scanned} recursos; {len(rows)} ocorrências; {len(samples)} amostras. {out}')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('roots',nargs='+',type=Path);p.add_argument('--out',type=Path,default=Path('pes6_db_probe.zip'));a=p.parse_args();run(a.roots,a.out)
