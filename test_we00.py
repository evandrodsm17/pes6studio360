import unittest,struct,zlib,io,zipfile,os
from PIL import Image
from pes6_we00_edit import encode,decode,leaf,rewrite,image_bytes
from pes6_fixed import rebuild_fixed

def texture():
    return b'WE00'+bytes(2)+bytes([3,8])+struct.pack('>4H',64,64,16,1040)+bytes([10,20,30,255])*256+bytes(range(256))*16

def table(*parts):
    offset=8+12*len(parts);h=struct.pack('>II',len(parts),8)
    for p in parts:h+=struct.pack('>III',offset,len(p),offset+len(p));offset+=len(p)
    return h+b''.join(parts)
def wrapper(x,stored=False):
    p=x if stored else zlib.compress(x,0)
    return (b'\x01\x01\x00' if stored else b'\x00\x01\x01')+b'WESYS'+struct.pack('>II',len(p),0 if stored else len(x))+p
class Tests(unittest.TestCase):
    def test_nested(self):
        old=texture(); raw=wrapper(table(wrapper(table(old,b'untouched')),b'other'),True)
        original=image_bytes(decode(old)[0]); upload=image_bytes(Image.new('RGBA',(64,64),(1,2,3,120)))
        patched=rebuild_fixed(raw,{('0001_part000_unpacked_part000',):(original,upload)})
        self.assertEqual(len(raw),len(patched)); self.assertEqual(raw[:16],patched[:16]);self.assertEqual(leaf(patched,('u',0,'u',1)),b'untouched');self.assertEqual(leaf(patched,('u',1)),b'other')
        self.assertEqual(decode(leaf(patched,('u',0,'u',0)))[0].getpixel((0,0)),(1,2,3,120))
    def test_noop(self):
        d=texture();self.assertEqual(encode(d,image_bytes(decode(d)[0])),d)
    def test_direct(self):
        for bpp in (24,32):
            d=b'WE00'+bytes(2)+bytes([3,bpp])+struct.pack('>4H',8,8,0,16)+bytes(64*(bpp//8));r=encode(d,image_bytes(Image.new('RGBA',(8,8),(12,34,56,78))));self.assertEqual(len(r),len(d));self.assertEqual(decode(r)[0].convert('RGBA').getpixel((0,0)),(12,34,56,78 if bpp==32 else 255))
    def test_mismatch(self):
        d=texture(); raw=wrapper(table(d),True); wrong=image_bytes(Image.new('RGBA',(64,64)));self.assertRaises(ValueError,rebuild_fixed,raw,{('0001_part000',):(wrong,wrong)})
if __name__=='__main__':unittest.main()
