"""Read-only, bounds-checked PES6 research parsers."""
import struct
import zlib

MAX = 64 * 1024 * 1024

def afs_index(f):
    f.seek(0, 2); size = f.tell(); f.seek(0)
    h = f.read(8)
    if len(h) != 8 or h[:4] != b'AFS\0': raise ValueError('Invalid AFS')
    n = struct.unpack_from('<I', h, 4)[0]
    if n > (size - 8) // 8: raise ValueError('Truncated index')
    rows = list(struct.iter_unpack('<II', f.read(n * 8)))
    if any(s and (o < 8+n*8 or o+s > size) for o,s in rows):
        raise ValueError('Entry outside AFS')
    return rows

def unwrap(d):
    if len(d) < 16 or d[3:8] != b'WESYS': raise ValueError('Invalid WESYS')
    c,u = struct.unpack_from('>II', d, 8)
    if c > len(d)-16: raise ValueError('Truncated WESYS')
    payload = d[16:16+c]
    if d[:3] == b'\1\1\0' and u == 0: return payload
    if not 0 < u <= MAX: raise ValueError('Invalid unpacked size')
    dec = zlib.decompressobj()
    try: out = dec.decompress(payload, u+1)
    except zlib.error as exc: raise ValueError('Invalid ZLIB') from exc
    if len(out) != u or not dec.eof or dec.unused_data or dec.unconsumed_tail:
        raise ValueError('Invalid stream/size')
    return out

def parts(d):
    if len(d) < 8: raise ValueError('Truncated table')
    n,t = struct.unpack_from('>II', d)
    if t != 8 or n > (len(d)-8)//12: raise ValueError('Invalid parts table')
    rows = []; last = 8+n*12
    for i in range(n):
        o,s,tag = struct.unpack_from('>III', d, 8+i*12)
        if o < last or o+s > len(d): raise ValueError('Overlapping/outside part')
        rows.append((o,s,tag,d[o:o+s])); last = o+s
    return rows

def records(d, stride):
    if stride <= 0 or len(d) % stride: raise ValueError('Non-integral records')
    return [d[i:i+stride] for i in range(0,len(d),stride)]

def text(d):
    raw = d.split(b'\0',1)[0]
    try: return raw.decode('utf8')
    except UnicodeDecodeError: return raw.decode('cp1252', errors='replace')

def players(d):
    return [dict(player_id=i,offset=i*152,name=text(r[:46]),shirt_name=text(r[46:62]))
            for i,r in enumerate(records(d,152))]

def rosters(d,p):
    return [dict(slot=slot,position=pos,offset=slot*64+pos*2,player_id=pid,
                 valid=pid<len(p),empty=pid in (0,65535),
                 name=p[pid]['name'] if pid<len(p) else '')
            for slot,r in enumerate(records(d,64))
            for pos,pid in enumerate(struct.unpack('>32H',r))]

def profiles6670(d):
    """Observed layout only; color interpretation and team identity unconfirmed."""
    result=[]
    for slot,r in enumerate(records(d,728)):
        if any(r[432:]): raise ValueError('Unexpected nonzero profile tail')
        for sub in range(4):
            block=r[sub*108:(sub+1)*108]
            if any(block[j+2:j+4]!=b'\0\0' for j in range(0,84,4)):
                raise ValueError('Unexpected padded word layout')
            result.append(dict(candidate_record=slot,subrecord=sub,offset=slot*728+sub*108,
                words=[int.from_bytes(block[j:j+2],'big') for j in range(0,84,4)],
                metadata_hex=block[84:].hex()))
    return result

def aliases6666(d):
    return [dict(record=i,offset=i*130,player_id=int.from_bytes(r[:2],'big'),
                 name_a=text(r[2:48]),name_b=text(r[48:94]),
                 shirt_a=text(r[94:110]),shirt_b=text(r[110:126]),tail_hex=r[126:].hex())
            for i,r in enumerate(records(d,130))]
