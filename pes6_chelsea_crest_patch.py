"""Build a source-verified Chelsea crest pilot; no XEX or kit changes."""
import argparse
import hashlib
import json
from pathlib import Path
from pes6_binary import afs_index, parts, unwrap
from pes6_club_identity import analyze
from pes6_iso import copy_verified
from pes6_we00_catalogo import decode


def prepare(root):
    """Resize externally supplied artwork and rebuild only the two selected parts."""
    from PIL import Image,ImageOps
    from pes6_we00_edit import image_bytes
    from pes6_fixed import rebuild_fixed
    root=Path(root);assets=root/'research/chelsea_2006_07'
    with Image.open(assets/'chelsea_crest_external.png') as source:
        if source.format!='PNG':raise ValueError('External crest must be PNG')
        artwork=source.convert('RGBA')
    with (root/'cv.img').open('rb') as f:
        index=afs_index(f)
        for entry,size in ((2710,128),(2711,64)):
            im=ImageOps.contain(artwork,(size,size),Image.Resampling.LANCZOS)
            canvas=Image.new('RGBA',(size,size));canvas.paste(im,((size-im.width)//2,(size-im.height)//2))
            upload=image_bytes(canvas);(assets/f'chelsea_crest_{size}.png').write_bytes(upload)
            original=(root/f'cv_we00_texturas/{entry}_part062_unpacked.png').read_bytes()
            offset,length=index[entry];f.seek(offset);raw=f.read(length)
            modified=rebuild_fixed(raw,{(f'{entry}_part062_unpacked',):(original,upload)})
            validate_entry(raw,modified)
            (assets/f'entry_{entry}_modified.bin').write_bytes(modified)


def validate_entry(original,modified,part=62):
    if len(original)!=len(modified):raise ValueError('AFS entry length changed')
    before=parts(unwrap(original));after=parts(unwrap(modified))
    if len(before)!=len(after) or not 0<=part<len(before):raise ValueError('Part table changed')
    for i,(a,b) in enumerate(zip(before,after)):
        if a[:3]!=b[:3]:raise ValueError('Part boundaries/tags changed')
        if i!=part and a[3]!=b[3]:raise ValueError('Unselected resource changed')
    old=decode(unwrap(before[part][3]));new=decode(unwrap(after[part][3]))
    if old is None or new is None or old[0].size!=new[0].size or old[1]!=new[1]:
        raise ValueError('Crest texture format/dimensions changed')
    if old[0].tobytes()==new[0].tobytes():raise ValueError('Crest did not change')
    return new[0]


def build(root,output):
    root=Path(root).resolve();output=Path(output).resolve()
    if output.exists():raise ValueError('Output must be a new file')
    if not output.parent.is_dir():raise ValueError('Output directory does not exist')
    identity=analyze(root)
    target=identity['target'];record=identity['records'][target['name_record']]
    if record['name']!='London FC' or (record['graphic_reference_10'],record['graphic_reference_12'])!=(62,62):
        raise ValueError('Target source record differs')
    assets=root/'research/chelsea_2006_07';source=root/'cv.img'
    base=json.loads((assets/'base_verification.json').read_text(encoding='utf-8'))
    with source.open('rb') as f:source_hash=hashlib.file_digest(f,'sha256').hexdigest()
    if not base['matches'] or source_hash!=base['iso_cv_sha256']:
        raise ValueError('cv.img differs from verified ISO source')
    changes=[];entries=[]
    with source.open('rb') as f:
        index=afs_index(f)
        for entry,size in ((2710,128),(2711,64)):
            offset,length=index[entry];f.seek(offset);original=f.read(length)
            modified=(assets/f'entry_{entry}_modified.bin').read_bytes()
            preview=validate_entry(original,modified)
            if preview.size!=(size,size):raise ValueError('Unexpected crest resolution')
            preview.save(assets/f'chelsea_crest_{size}_encoded_preview.png')
            changes.append((offset,modified))
            entries.append({'entry':entry,'part':62,'offset':offset,'size':length,
                            'original_sha256':hashlib.sha256(original).hexdigest(),
                            'modified_sha256':hashlib.sha256(modified).hexdigest()})
    copy_verified(source,output,0,source.stat().st_size,changes)
    with output.open('rb') as f:output_hash=hashlib.file_digest(f,'sha256').hexdigest()
    report={'schema':1,'kind':'Chelsea 2006/07 crest pilot','source':str(source),
            'source_sha256':source_hash,'xex_sha256':identity['source_sha256'],
            'output':str(output),'output_sha256':output_hash,'entries':entries,
            'art_source':'https://resources.premierleague.com/premierleague/badges/t8.png',
            'art_sha256':hashlib.sha256((assets/'chelsea_crest_external.png').read_bytes()).hexdigest(),
            'runtime_verified':False,'target_name_in_game':'London FC',
            'unchanged':['XEX','team names','kits','other crest parts','leagues','scoreboards'],
            'required_observation':'Check London FC crest in selection, formation and match; do not infer kit links from this test.'}
    output.with_suffix(output.suffix+'.manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path('.'))
    p.add_argument('--output',type=Path);p.add_argument('--prepare',action='store_true');a=p.parse_args()
    if not a.prepare and a.output is None:p.error('Use --prepare and/or --output')
    if a.prepare:prepare(a.root)
    if a.output is not None:print(json.dumps(build(a.root,a.output),indent=2))
