"""Compare color-format hypotheses globally; never produce team-to-kit mappings."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
from pes6_binary import afs_index, parts, unwrap
from pes6_profiles import inspect

LAYOUTS = {'RGBA5551': ((11,31),(6,31),(1,31)),
           'RGB565': ((11,31),(5,63),(0,31)),
           'ARGB1555': ((10,31),(5,31),(0,31))}


def signature(word, layout):
    if type(word) is not int or not 0 <= word <= 65535 or layout not in LAYOUTS:
        raise ValueError('Invalid color hypothesis')
    return tuple((word >> shift) & mask for shift,mask in LAYOUTS[layout])


def palette_rgb(raw):
    expected = b'WE00' + struct.pack('>HBB4H',4100,3,8,512,512,16,1040)
    if raw[:16] != expected or len(raw) != 263184:
        raise ValueError('Unexpected kit candidate WE00 structure')
    # Compare all palette entries, including unused/transparent entries.
    # This deliberately measures palette membership, not rendered pixels.
    return {tuple(raw[i:i+3]) for i in range(16,1040,4)}


def compare(words, colors):
    rows = []
    for layout in LAYOUTS:
        shifts = [8-mask.bit_length() for shift,mask in LAYOUTS[layout]]
        palette = {tuple(v >> shift for v,shift in zip(c,shifts)) for c in colors}
        for swapped in (False,True):
            values = Counter()
            for word,count in words.items():
                value = ((word & 255) << 8 | word >> 8) if swapped else word
                values[signature(value,layout)] += count
            matched = set(values) & palette
            # Exhaustive representation-space coverage is a baseline, not a p-value.
            universe = {signature(w,layout) for w in range(65536)}
            rows.append({'layout':layout,'byte_swapped':swapped,
                         'distinct_profile_colors':len(values),
                         'matched_distinct_colors':len(matched),
                         'profile_occurrences':sum(values.values()),
                         'matched_occurrences':sum(values[v] for v in matched),
                         'palette_colors_quantized':len(palette),
                         'representation_colors':len(universe),
                         'palette_space_fraction':len(palette)/len(universe),
                         'distinct_match_fraction':len(matched)/len(values) if values else None})
    return rows


def analyze(root):
    root = Path(root)
    profiles = inspect(root)
    words = Counter(v for p in profiles['parts'] for row in p['subrecords'] for v in row['words'])
    colors = set()
    sources = []
    with (root/'cv.img').open('rb') as f:
        index = afs_index(f)
        if len(index) <= 6145:raise ValueError('Missing kit candidate entries')
        # Recheck 6670 on this open source, rather than mixing reports silently.
        offset,size = index[6670]
        f.seek(offset)
        if hashlib.sha256(f.read(size)).hexdigest() != profiles['sha256']:
            raise ValueError('Profile source changed during analysis')
        for entry in range(5736,6146):
            offset,size = index[entry]
            f.seek(offset);raw = f.read(size)
            pp = parts(unwrap(raw))
            if len(pp) != 2:raise ValueError('Expected two kit candidate parts')
            source = {'entry':entry,'afs_offset':offset,'size':size,
                      'sha256':hashlib.sha256(raw).hexdigest(),'parts':[]}
            for part,(po,ps,tag,data) in enumerate(pp):
                colors.update(palette_rgb(data))
                source['parts'].append({'part':part,'unpacked_offset':po,'size':ps,
                                        'sha256':hashlib.sha256(data).hexdigest()})
            sources.append(source)
    return {'schema':1,'profile_source':{k:profiles[k] for k in ('entry','afs_offset','stored_size','sha256')},
            'kit_sources':sources,'word_occurrences':sum(words.values()),'unique_words':len(words),
            'odd_word_occurrences':sum(n for w,n in words.items() if w & 1),
            'palette_rgb_colors':len(colors),'comparisons':compare(words,colors),'associations':[],
            'limitations':['Global palette membership cannot establish any team or kit association.',
                           'RGB comparisons ignore alpha and include unused palette entries.',
                           'All palette RGB values are truncated to the candidate channel bit depth.',
                           'Coverage of the representation space is a descriptive baseline, not a significance test.',
                           'No color format is confirmed by these comparisons.']}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path('.'))
    parser.add_argument('--out',type=Path,default=Path('research/palette_comparison.json'))
    args=parser.parse_args();result=analyze(args.root)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('kit_sources','limitations')},indent=2))
