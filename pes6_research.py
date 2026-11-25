"""Reproduce binary evidence without modifying game files."""
import argparse,collections,csv,hashlib,json,struct
from pathlib import Path
from pes6_binary import afs_index,unwrap,parts,players,rosters,records,profiles6670,aliases6666

def digest(d): return hashlib.sha256(d).hexdigest()
def write_csv(out,name,rows):
    if not rows:return
    with (out/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def run(root,out):
    out.mkdir(parents=True,exist_ok=True)
    summary={'schema':1,'associations':[], 'entries':[], 'limitations':[
        'No confirmed team-to-kit association; roster slots are database-specific.',
        '728-byte records in 6670 are a structural hypothesis, not decoded team records.',
        'No Xenia runtime validation performed by this analysis.']}
    allparts={}; refs=[]; profiles=[]; kits=[]; shaders=[]; variants={}; subprofiles=[]
    with (root/'cv.img').open('rb') as f:
        idx=afs_index(f)
        summary['afs_entries']=len(idx)
        for entry in range(6666,6672):
            o,s=idx[entry];f.seek(o);raw=f.read(s);unpacked=unwrap(raw);pp=parts(unpacked)
            row=dict(entry=entry,afs_offset=o,size=s,sha256=digest(raw),unpacked_sha256=digest(unpacked),parts=[])
            for i,(offset,size,tag,d) in enumerate(pp):
                allparts[entry,i]=d
                extracted=root/'cv_extraido_v03'/str(entry)/f'part_{i:03}.bin'
                row['parts'].append(dict(part=i,offset=offset,size=size,tag=tag,sha256=digest(d),
                    extraction_matches=extracted.exists() and extracted.read_bytes()==d))
                if entry==6671:
                    shaders.append(dict(part=i,offset=offset,size=size,
                        compiler_signature=b'Microsoft (R) Xbox 360 Shader Compiler' in d,
                        vertex=b'vs_3_0' in d,pixel=b'ps_3_0' in d))
            summary['entries'].append(row)
        for entry in (6667,6668):
            p=players(allparts[entry,0]);r=rosters(allparts[entry,1],p)
            write_csv(out,f'players_{entry}.csv',p);write_csv(out,f'rosters_{entry}.csv',r)
            variants[entry]=r
            summary[str(entry)]=dict(players=len(p),roster_slots=len(r)//32,
                invalid_nonempty_references=sum(not x['valid'] and not x['empty'] for x in r),
                auxiliary_part3_candidate_records=len(p)-1,
                auxiliary_part3_trailing_bytes=len(allparts[entry,3])-(len(p)-1)*6)
        aliases=aliases6666(allparts[6666,0]);base=players(allparts[6667,0])
        for r in aliases:
            r['name_in_6667']=base[r['player_id']]['name'] if r['player_id']<len(base) else ''
            r['matches_name_a']=r['name_a']==r['name_in_6667']
        write_csv(out,'6666_alias_candidates.csv',aliases)
        summary['6666']=dict(candidate_stride=130,records=len(aliases),
            name_a_matches_6667=sum(r['matches_name_a'] for r in aliases),status='paired-name records; purpose inferred')
        anchors={'Italy':['Buffon','Nesta','Pirlo'],'Portugal':['Ricardo','R. Carvalho','Petit'],
            'Spain':['Casillas','Sergio Ramos','Xavi'], 'Argentina':['Abbondanzieri','Ayala','Heinze'],
            'Brazil':['Dida','Cafu','Roberto Carlos'],'Arsenal':['Lehmann','Senderos','Cesc Fabregas'],
            'Chelsea':['Terry','R. Carvalho','Lampard'],'Liverpool':['Reina','Carragher','Gerrard'],
            'Manchester United':['Van der Sar','R. Ferdinand','G. Neville'],
            'Barcelona':['Puyol','Ronaldinho','Eto'], 'Real Madrid':['Casillas','Roberto Carlos','Ra'],
            'Bayern':['Rensing','Sagnol','Demichelis']}
        identities=[]
        for entry,rr in variants.items():
            for team,needles in anchors.items():
                for slot in range(len(rr)//32):
                    names=[x['name'] for x in rr[slot*32:(slot+1)*32] if not x['empty']]
                    matched=[n for n in needles if any(n.casefold() in s.casefold() for s in names)]
                    if len(matched)==len(needles):
                        identities.append(dict(entry=entry,slot=slot,team_candidate=team,
                            anchors=' | '.join(matched),names=' | '.join(names),status='roster identity inference; not graphic ID'))
        write_csv(out,'team_identity_candidates.csv',identities)
        summary['team_identity_candidates']=identities
        for part in (0,1):
            d=allparts[6670,part]
            subprofiles.extend({**r,'part':part,'words':' '.join(f'{v:04x}' for v in r['words'])} for r in profiles6670(d))
            for slot,r in enumerate(records(d,728)):
                profiles.append(dict(part=part,candidate_record=slot,offset=slot*728,
                    size=728,sha256=digest(r),first64_hex=r[:64].hex(),nonzero_bytes=sum(v!=0 for v in r)))
        # Explicit aligned numeric occurrences are evidence of values, not semantic pointers.
        for (entry,part),d in allparts.items():
            if entry==6671:continue
            for endian in ('big','little'):
                for width in (2,4):
                    for offset in range(0,len(d)-width+1,width):
                        value=int.from_bytes(d[offset:offset+width],endian)
                        if 5736<=value<=6145:
                            refs.append(dict(entry=entry,part=part,offset=offset,width=width,endian=endian,
                                value=value,status='numeric coincidence; unconfirmed reference'))
        for entry in range(5736,6146):
            o,s=idx[entry];f.seek(o);raw=f.read(s);pp=parts(unwrap(raw))
            if len(pp)!=2:raise ValueError(f'Kit candidate {entry}: expected 2 parts')
            for part,(offset,size,tag,d) in enumerate(pp):
                expected=b'WE00'+struct.pack('>HBB4H',4100,3,8,512,512,16,1040)
                if d[:16]!=expected or len(d)!=263184:raise ValueError(f'Unexpected WE00 {entry}/{part}')
                palette=d[16:1040];pixels=d[1040:]
                rgba=b''.join(palette[v*4:v*4+4] for v in pixels)
                kits.append(dict(entry=entry,part=part,afs_offset=o,part_offset=offset,size=size,
                    header_hex=d[:16].hex(),sha256=digest(d),rgba_sha256=digest(rgba),team='',status='structural candidate'))
    write_csv(out,'kit_candidates.csv',kits);write_csv(out,'numeric_kit_hits.csv',refs)
    write_csv(out,'6670_candidate_records.csv',profiles);write_csv(out,'6671_shaders.csv',shaders)
    write_csv(out,'6670_subrecords.csv',subprofiles)
    comparison=[]
    for slot in range(188):
        a=[r for r in variants[6667] if r['slot']==slot];b=[r for r in variants[6668] if r['slot']==slot]
        comparison.append(dict(slot=slot,names_6667=' | '.join(r['name'] for r in a[:11]),
            names_6668=' | '.join(r['name'] for r in b[:11]),
            same_first11=sum(x['name']==y['name'] for x,y in zip(a[:11],b[:11]))))
    write_csv(out,'roster_variant_comparison.csv',comparison)
    counts=collections.Counter(k['rgba_sha256'] for k in kits)
    summary['kits']=dict(entries=410,textures=len(kits),unique_pixels=len(counts),largest_groups=counts.most_common(5))
    summary['6671']=dict(parts=len(shaders),compiler_signatures=sum(s['compiler_signature'] for s in shaders),
        vertex=sum(s['vertex'] for s in shaders),pixel=sum(s['pixel'] for s in shaders))
    summary['6670']=dict(candidate_stride=728,part0_records=189,part1_records=16,status='hypothesis')
    summary['6670']['observed_layout']='4 x 108 bytes + 296 zero bytes; each subrecord: 21 BE16 words padded by 2 zero bytes, then 24 metadata bytes'
    summary['index_formula_hypothesis']=dict(status='unconfirmed; do not use for patching',
        count_relation='410 = 2 * (189 + 16)',formula='5736 + 2 * combined_record + variant',
        missing_evidence='Record order, variant semantics and runtime reference are unknown.')
    catalog=root/'cv_we00_texturas'/'index.csv'
    if catalog.exists():
        with catalog.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
        summary['we00_catalog_index']=dict(rows=len(rows),formats=dict(collections.Counter(r['format'] for r in rows)),
            status='index metadata only; not a fresh decode of every image')
    summary['numeric_kit_hits']=len(refs)
    (out/'evidence.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in summary.items() if k!='entries'},ensure_ascii=False,indent=2))
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path('.'))
    p.add_argument('--out',type=Path,default=Path('research'));a=p.parse_args();run(a.root,a.out)
