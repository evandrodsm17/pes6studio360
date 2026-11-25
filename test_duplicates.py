import unittest,tempfile
from pathlib import Path
from PIL import Image
from pes6_duplicates import groups
class TestGroups(unittest.TestCase):
 def test_groups_cache_and_dimensions(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d); paths=[root/f'{i}.png' for i in range(4)]
   for p,size in zip(paths,[(8,4),(8,4),(4,8),(8,4)]): Image.new('RGBA',size,(1,2,3,4)).save(p)
   items=[{'kind':'WE00'}]*3+[{'kind':'DDS'}]; c=root/'cache.json'
   expected={0:[0,1],1:[0,1],2:[2]}
   self.assertEqual(groups(paths,items,c),expected);self.assertEqual(groups(paths,items,c),expected)
   Image.new('RGBA',(8,4),(1,2,3,5)).save(paths[1]);self.assertEqual(groups(paths,items,c),{0:[0],1:[1],2:[2]})
if __name__=='__main__':unittest.main()
