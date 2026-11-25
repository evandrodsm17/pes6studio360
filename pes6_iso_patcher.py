#!/usr/bin/env python3
"""Replace one exact, contiguous, sector-aligned IMG in a copy of a disc image."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import sys

CHUNK = 8 * 1024 * 1024
SECTOR = 2048

def locate(iso, original):
    # Search a prefix, then confirm every byte. Overlap handles chunk boundaries.
    prefix = original[:4096]
    matches = []
    with iso.open('rb') as scan, iso.open('rb') as check:
        tail = b''
        pos = 0
        while True:
            chunk = scan.read(CHUNK)
            if not chunk:
                break
            buf = tail + chunk
            base = pos - len(tail)
            i = buf.find(prefix)
            while i != -1:
                offset = base + i
                if offset % SECTOR == 0:
                    check.seek(offset)
                    if check.read(len(original)) == original:
                        matches.append(offset)
                i = buf.find(prefix, i + 1)
            pos += len(chunk)
            tail = buf[-(len(prefix)-1):]
    if len(matches) != 1:
        raise ValueError(f'Esperava uma correspondencia integral alinhada; encontrei {len(matches)}. Nenhuma ISO gerada.')
    return matches[0]

def patch(iso, source, replacement, dest):
    paths = [p.resolve() for p in (iso, source, replacement, dest)]
    if len(set(paths)) != 4 or dest.exists():
        raise ValueError('Use quatro caminhos distintos e um destino que ainda nao exista.')
    original, modified = source.read_bytes(), replacement.read_bytes()
    if len(original) < 4096 or not original.startswith(b'AFS\0') or not modified.startswith(b'AFS\0'):
        raise ValueError('Os dois IMG devem possuir assinatura AFS.')
    if len(original) != len(modified) or original == modified:
        raise ValueError('Os IMG devem ter o mesmo tamanho e conteudos diferentes.')
    print('Procurando correspondencia integral na ISO...', flush=True)
    offset = locate(iso, original)
    print(f'IMG encontrado: offset {offset} (0x{offset:X}), setor {offset//SECTOR}', flush=True)
    if shutil.disk_usage(dest.parent).free < iso.stat().st_size:
        raise ValueError('Espaco insuficiente para copiar a ISO.')
    created = False
    try:
        with iso.open('rb') as src, dest.open('xb') as out:
            created = True
            shutil.copyfileobj(src, out, CHUNK)
        with dest.open('r+b') as out:
            out.seek(offset)
            if out.read(len(original)) != original:
                raise ValueError('Copia nao corresponde ao IMG original.')
            out.seek(offset)
            out.write(modified)
            out.flush()
            os.fsync(out.fileno())
        print('Verificando toda a ISO, byte a byte...', flush=True)
        with iso.open('rb') as src, dest.open('rb') as out:
            pos = 0
            while True:
                a = src.read(CHUNK)
                b = out.read(CHUNK)
                if not a and not b:
                    break
                lo, hi = max(pos, offset), min(pos+len(a), offset+len(modified))
                if lo < hi:
                    a = a[:lo-pos] + modified[lo-offset:hi-offset] + a[hi-pos:]
                if a != b:
                    raise ValueError(f'Falha de verificacao no bloco em {pos}.')
                pos += len(a)
        print('OK: somente a regiao do IMG foi substituida.')
        print('SHA256 IMG modificado:', hashlib.sha256(modified).hexdigest())
        print('ISO gerada:', dest)
    except BaseException:
        if created:
            dest.unlink(missing_ok=True)
        raise

def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('iso', 'original_img', 'modified_img', 'output_iso'):
        p.add_argument(name, type=Path)
    a = p.parse_args()
    try:
        patch(a.iso, a.original_img, a.modified_img, a.output_iso)
    except (OSError, ValueError) as e:
        print('ERRO:', e, file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
