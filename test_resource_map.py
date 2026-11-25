import unittest,csv
from pes6_resource_map import kit_pairs
class Test(unittest.TestCase):
 def test_real_index(self):
  from pathlib import Path
  p=Path(__file__).parent/'cv_we00_texturas'/'index.csv'
  if not p.exists():self.skipTest('Índice original não disponível')
  with p.open() as f:items=[dict(id=i,kind='WE00',archive='cv',name=r['resource'],format=r['format'],res=r['width']+' × '+r['height']) for i,r in enumerate(csv.DictReader(f))]
  self.assertEqual(len(kit_pairs(items)),410)
 def test_incomplete(self):
  self.assertEqual(kit_pairs([dict(kind='WE00',archive='cv',name='5736_part000',format='indexed8',res='512 × 512')]),[])
