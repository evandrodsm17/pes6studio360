"""Read-only, narrow PPC observations for the source-bound PAL HUD loader window."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from pes6_club_identity import SOURCE_SHA256
from pes6_xex_probe import reconstruct


def relative_call(image, offset, base):
    word = struct.unpack_from('>I', image, offset)[0]
    if word >> 26 != 18 or word & 3 != 1:
        raise ValueError('Expected relative bl instruction')
    displacement = word & 0x3fffffc
    if displacement & 0x2000000: displacement -= 0x4000000
    return (base+offset+displacement) & 0xffffffff


def analyze(source):
    raw = Path(source).read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256: raise ValueError('Unknown PAL executable')
    image, layout = reconstruct(raw); base = layout['base_address']; requests = []
    for load, call, resource in ((0x468114, 0x468118, 2706), (0x468184, 0x46818c, 2703)):
        expected = (14 << 26) | (3 << 21) | resource
        if struct.unpack_from('>I', image, load)[0] != expected:
            raise ValueError('Expected li r3,resource instruction')
        if call-load == 8 and struct.unpack_from('>I', image, load+4)[0] != 0x917b98d0:
            raise ValueError('Unexpected intervening stw instruction')
        requests.append({'resource_candidate': resource, 'load_rva': hex(load),
                         'call_rva': hex(call), 'callee': hex(relative_call(image, call, base))})
    return {'source_sha256': SOURCE_SHA256, 'image_sha256': hashlib.sha256(image).hexdigest(),
            'requests': requests, 'observation': 'Constants 2703 and 2706 passed in r3 to the same relative-call target.',
            'interpretation': 'Candidate HUD resource-loading path; cv entry 2703 contains scoretime/game2d/replay layouts.',
            'competition_state_address': None, 'automatic_selection_implemented': False,
            'limitations': ['Static instruction observation only; argument ABI and runtime execution not traced.',
                           'No competition ID or native competition selector has been established.',
                           'No executable bytes are modified.']}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path); p.add_argument('--out', type=Path)
    args = p.parse_args(); report = analyze(args.source); text = json.dumps(report, indent=2)
    if args.out: args.out.parent.mkdir(parents=True, exist_ok=True); args.out.write_text(text, encoding='utf-8')
    print(text)
