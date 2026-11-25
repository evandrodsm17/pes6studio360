"""Exact decoded RGBA groups, with dimensions and file metadata cache."""
import hashlib, json, os, struct
from PIL import Image

def groups(paths, items, cache_path):
    try: old=json.loads(cache_path.read_text(encoding='utf-8'))
    except (OSError,ValueError): old={}
    if not isinstance(old,dict) or old.get('version')!=1: old={}
    old=old.get('files',{}); fresh={}; result={}
    for i,(p,t) in enumerate(zip(paths,items)):
        # WE00 only: do not conflate different DDS encodings.
        if t['kind']!='WE00': continue
        key=str(p.resolve()); st=p.stat(); stamp=[st.st_size,st.st_mtime_ns,st.st_ctime_ns]
        cached=old.get(key,{})
        if cached.get('stamp')==stamp and cached.get('hash'): h=cached['hash']
        else:
            with Image.open(p) as im:
                im=im.convert('RGBA'); h=hashlib.sha256(struct.pack('>II',*im.size)+im.tobytes()).hexdigest()
        fresh[key]={'stamp':stamp,'hash':h};result.setdefault(h,[]).append(i)
    tmp=cache_path.with_suffix('.tmp');tmp.write_text(json.dumps({'version':1,'files':fresh}),encoding='utf-8');os.replace(tmp,cache_path)
    return {i:members for members in result.values() for i in members}
