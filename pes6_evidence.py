"""Serve research evidence only when the relevant source entries still match."""
import csv,json,hashlib
from pathlib import Path
from pes6_binary import afs_index,unwrap,parts

def verify_kits(f,index,catalog):
    """Verify each structural candidate against its own binary, never pixel peers."""
    with catalog.open(encoding='utf-8-sig',newline='') as source:
        rows=list(csv.DictReader(source))
    expected={(entry,part) for entry in range(5736,6146) for part in (0,1)}
    seen=set(); current_entry=None; decoded=None
    for row in rows:
        entry,part=int(row['entry']),int(row['part'])
        if (entry,part) not in expected or (entry,part) in seen:
            raise ValueError('Invalid or duplicate kit candidate')
        seen.add((entry,part))
        if entry>=len(index):raise ValueError('Kit entry outside AFS index')
        offset,size=index[entry]
        if int(row['afs_offset'])!=offset:raise ValueError('Kit AFS offset differs')
        if entry!=current_entry:
            f.seek(offset);decoded=parts(unwrap(f.read(size)));current_entry=entry
            if len(decoded)!=2:raise ValueError('Kit part count differs')
        po,ps,tag,raw=decoded[part]
        if (po,ps)!=(int(row['part_offset']),int(row['size'])) or hashlib.sha256(raw).hexdigest()!=row['sha256']:
            raise ValueError('Kit source differs from catalog; regenerate research')
        if raw[:16].hex()!=row['header_hex']:raise ValueError('Kit header differs')
    if seen!=expected:raise ValueError('Incomplete kit candidate catalog')
    return {'entries':len({entry for entry,part in seen}),'textures':len(seen),'status':'source_verified'}

def load_evidence(root,report):
    root=Path(root); report=Path(report)
    if not report.is_file():return {'status':'missing','message':'Execute pes6_research.py para gerar as evidencias.'}
    data=json.loads(report.read_text(encoding='utf8'))
    if data.get('schema')!=1:raise ValueError('Unsupported evidence schema')
    with (root/'cv.img').open('rb') as f:
        index=afs_index(f)
        for r in data['entries']:
            if not isinstance(r['entry'],int) or not 0<=r['entry']<len(index):
                raise ValueError('Research entry outside AFS index')
            o,s=index[r['entry']];f.seek(o)
            if (o,s)!=(r['afs_offset'],r['size']) or hashlib.sha256(f.read(s)).hexdigest()!=r['sha256']:
                raise ValueError('Research evidence differs from cv.img; regenerate report')
        kit_verification=verify_kits(f,index,report.parent/'kit_candidates.csv') if 'kits' in data else {'status':'not_requested'}
    return dict(data,status='source_verified',
                kit_verification=kit_verification,
                verification_scope='AFS index, listed database entries and kit candidate binary hashes when present; no team associations verified')
