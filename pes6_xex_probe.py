"""Read-only XEX2 basic-image reconstruction and narrow PPC immediate scan.

Reference: xenia-project/xenia src/xenia/cpu/xex_module.cc and
src/xenia/kernel/util/xex2_info.h. Does not patch or execute the image.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

MAX_IMAGE=128*1024*1024
REFERENCE='https://github.com/xenia-project/xenia/blob/master/src/xenia/cpu/xex_module.cc'


def u32(data,offset,endian='>'):
    if offset<0 or offset+4>len(data):raise ValueError('Truncated 32-bit field')
    return struct.unpack_from(endian+'I',data,offset)[0]


def reconstruct(data):
    if len(data)<24 or data[:4]!=b'XEX2':raise ValueError('Expected XEX2')
    header_size=u32(data,8);security=u32(data,16);count=u32(data,20)
    if not 24<=header_size<=len(data) or count>(header_size-24)//8:
        raise ValueError('Invalid XEX header bounds')
    headers={}
    for n in range(count):
        key,value=struct.unpack_from('>II',data,24+8*n)
        if key in headers:raise ValueError('Duplicate XEX optional header')
        headers[key]=value
    if not {0x3ff,0x10201,0x10100}<=headers.keys():raise ValueError('Missing required XEX headers')
    info=headers[0x3ff];size=u32(data,info)
    if info<24+count*8 or size<16 or (size-8)%8 or info+size>header_size:
        raise ValueError('Invalid basic compression info bounds')
    enc,comp=struct.unpack_from('>HH',data,info+4)
    if enc not in (0,1) or comp!=1:raise ValueError('Only basic compression is supported')
    blocks=list(struct.iter_unpack('>II',data[info+8:info+size]))
    total=sum(a+b for a,b in blocks);stored=sum(a for a,b in blocks)
    if not 0<total<=MAX_IMAGE or stored>len(data)-header_size:raise ValueError('Invalid image block sizes')
    payload=data[header_size:header_size+stored]
    if enc:
        if security<24+count*8 or security+0x160>header_size or any(a%16 for a,b in blocks):
            raise ValueError('Invalid encrypted image bounds/alignment')
        from cryptography.hazmat.primitives.ciphers import Cipher,algorithms,modes
        def decrypt(key,raw):
            cipher=Cipher(algorithms.AES(key),modes.CBC(bytes(16))).decryptor()
            return cipher.update(raw)+cipher.finalize()
        # Public Xenia loader constant; session keys are not persisted.
        key=decrypt(bytes.fromhex('20b185a59d28fdc340583fbb0896bf91'),data[security+0x150:security+0x160])
        payload=decrypt(key,payload)
    image=bytearray();cursor=0
    for a,b in blocks:image.extend(payload[cursor:cursor+a]);image.extend(bytes(b));cursor+=a
    if security<24+count*8 or security+8>header_size:raise ValueError('Invalid security header')
    allocation=u32(data,security+4)
    if not total<=allocation<=MAX_IMAGE:raise ValueError('Invalid allocated image size')
    image.extend(bytes(allocation-total))
    image=bytes(image);layout=pe_layout(image)
    if layout['base_address']!=headers[0x10201]:raise ValueError('PE/XEX base mismatch')
    entry=headers[0x10100]
    if not any(s['rva']<=entry-layout['base_address']<s['rva']+s['size'] and s['executable'] for s in layout['sections']):
        raise ValueError('Entry point outside executable section')
    return image,dict(layout,entry_point=entry,header_size=header_size,
                      compression='basic',encryption='normal' if enc else 'none',
                      blocks=[{'data_size':a,'zero_size':b} for a,b in blocks])


def pe_layout(image):
    if len(image)<64 or image[:2]!=b'MZ':raise ValueError('Invalid reconstructed MZ')
    pe=u32(image,60,'<')
    if pe+24>len(image) or image[pe:pe+4]!=b'PE\0\0':raise ValueError('Invalid reconstructed PE')
    machine,count=struct.unpack_from('<HH',image,pe+4)
    optional_size=struct.unpack_from('<H',image,pe+20)[0];opt=pe+24
    if machine!=0x1f2 or optional_size<96 or opt+optional_size+count*40>len(image):
        raise ValueError('Unsupported PE machine/header bounds')
    if struct.unpack_from('<H',image,opt)[0]!=0x10b:raise ValueError('Expected PE32')
    base=u32(image,opt+28,'<');sections=[]
    for i in range(count):
        p=opt+optional_size+40*i
        name=image[p:p+8].rstrip(b'\0').decode('ascii','replace')
        size,rva,raw_size,raw_offset=struct.unpack_from('<4I',image,p+8)
        flags=u32(image,p+36,'<')
        executable=bool(flags&0x20000000)
        if executable and (rva%4 or rva+size>len(image)):
            raise ValueError('Executable section outside/alignment of memory image')
        sections.append(dict(name=name,rva=rva,size=size,raw_offset=raw_offset,
                             raw_size=raw_size,executable=executable,
                             bytes_in_image=max(0,min(size,len(image)-rva))))
    return {'base_address':base,'sections':sections}


def scan_immediates(image,layout,targets):
    """Hits are instruction-shaped words, not proof of reachable code or semantics."""
    hits=[]
    for section in layout['sections']:
        if not section['executable']:continue
        for offset in range(section['rva'],section['rva']+section['size']-3,4):
            word=u32(image,offset);opcode=word>>26
            if opcode not in (7,10,11,14,15):continue
            immediate=word&65535
            if opcode!=10 and immediate&32768:immediate-=65536
            if immediate not in targets:continue
            mnemonic={7:'mulli',10:'cmpli',11:'cmpi',14:'addi',15:'addis'}[opcode]
            hits.append({'image_offset':offset,'address':f"0x{layout['base_address']+offset:08x}",
                         'word_hex':f'{word:08x}','mnemonic':mnemonic,'immediate':immediate,
                         'field_rt_or_compare':(word>>21)&31,'field_ra':(word>>16)&31,
                         'context_offset':max(section['rva'],offset-16),
                         'context_hex':image[max(section['rva'],offset-16):min(section['rva']+section['size'],offset+20)].hex(),
                         'status':'instruction candidate; semantic reference unconfirmed'})
    return hits


def analyze(source):
    data=source.read_bytes();image,layout=reconstruct(data)
    targets={5736,6145,6146,6666,6667,6668,6669,6670,6671,728,108,189,204,205,410}
    hits=scan_immediates(image,layout,targets)
    result={'schema':1,'source':str(source),'source_sha256':hashlib.sha256(data).hexdigest(),
            'image_sha256':hashlib.sha256(image).hexdigest(),'image_size':len(image),
            'reference':REFERENCE,'layout':layout,'targets':sorted(targets),'hits':hits,
            'counts':dict(Counter(str(h['immediate']) for h in hits)),'associations':[],
            'limitations':['Narrow static instruction scan; no reachability or dataflow proof.',
                           'Memory image offsets equal RVA, not PE raw-file offsets.',
                           'No runtime validation or team-to-kit association.']}
    return result


def run(source,out):
    result=analyze(source)
    out.mkdir(parents=True,exist_ok=True)
    (out/'xex_immediates.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'source_sha256':result['source_sha256'],'image_sha256':result['image_sha256'],'counts':result['counts']},indent=2))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=Path('default.xex'))
    p.add_argument('--out',type=Path,default=Path('research'));a=p.parse_args();run(a.source,a.out)
