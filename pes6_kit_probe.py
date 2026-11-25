"""Read-only source-bound kit loader observations; emits no team-to-kit guesses."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from pes6_club_identity import SOURCE_SHA256
from pes6_xex_probe import reconstruct
from pes6_scoreboard_probe import relative_call


def analyze(source):
    raw=Path(source).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA256:raise ValueError('Unknown PAL executable')
    image,layout=reconstruct(raw)
    expected=(0x817f00d4,0x38810050,0x387f00b0,0x93c10050,0x3bab1668,
              0x4be513c5,0x7fa4eb78,0x7fc3f378,0x4bea3d51,0x7fc3f378,0x4bea3ea9)
    if struct.unpack_from('>'+str(len(expected))+'I',image,0x2fa188)!=expected:
        raise ValueError('Kit request instruction window differs')
    return {'source_sha256':SOURCE_SHA256,'image_sha256':hashlib.sha256(image).hexdigest(),
        'candidate_loader':{'field_load_rva':'0x2fa188','object_field':'0xd4',
            'addition_rva':'0x2fa198','constant':5736,'expression':'5736 + object word at +0xd4',
            'argument_move_rva':'0x2fa1a0','request_call_rva':'0x2fa1a8',
            'callee':hex(relative_call(image,0x2fa1a8,layout['base_address']))},
        'excluded_numeric_hits':[
            {'rva':'0x5c5834','reason':'Together with preceding lis constructs code pointer 0x825c1668; not an AFS index.'},
            {'rva':'0xafe934','reason':'0x1801 is one of several validation status returns; not a demonstrated kit resource.'},
            {'rva':'0xafed40','reason':'Same status-code pattern as 0xafe934.'}],
        'automatic_team_mappings':[],'runtime_verified':False,
        'limitations':['Object +0xd4 provenance and live team/variant selection remain untraced.',
                       'No kit ID is derived from roster positions or crest references.',
                       'No XEX flag or executable instruction is modified.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--out',type=Path)
    args=p.parse_args();report=analyze(args.source);text=json.dumps(report,indent=2)
    if args.out:args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(text,encoding='utf-8')
    print(text)
