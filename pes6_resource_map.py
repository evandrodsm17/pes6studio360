"""Structural candidates, not team IDs."""
import re
from collections import defaultdict

def kit_pairs(items):
    by=defaultdict(dict)
    for t in items:
        if t['kind']!='WE00' or t['format']!='indexed8' or t['res']!='512 × 512':continue
        m=re.fullmatch(r'(\d+)_part(000|001)',t['name'])
        if m and 5736<=int(m[1])<=6145:by[(t['archive'],int(m[1]))][m[2]]=t
    return [dict(archive=a,entry=e,parts=[p['000'],p['001']]) for (a,e),p in sorted(by.items()) if len(p)==2]
