from pathlib import Path
import struct
import unittest
from pes6_xex_probe import reconstruct, scan_immediates


def fixture():
    image=bytearray(544);image[:2]=b'MZ';struct.pack_into('<I',image,60,64)
    image[64:68]=b'PE\0\0';struct.pack_into('<HH',image,68,0x1f2,1)
    struct.pack_into('<H',image,84,96);struct.pack_into('<H',image,88,0x10b)
    struct.pack_into('<I',image,116,0x82000000)
    image[184:192]=b'.text\0\0\0';struct.pack_into('<4I',image,192,32,512,32,512)
    struct.pack_into('<I',image,220,0x20000000)
    struct.pack_into('>II',image,512,0x38801668,0x1d6b02d8)
    xex=bytearray(1024);xex[:4]=b'XEX2';struct.pack_into('>III',xex,8,1024,0,64)
    struct.pack_into('>I',xex,20,3)
    for n,pair in enumerate(((0x3ff,512),(0x10201,0x82000000),(0x10100,0x82000200))):
        struct.pack_into('>II',xex,24+8*n,*pair)
    struct.pack_into('>I',xex,68,len(image))
    struct.pack_into('>IHHII',xex,512,16,0,1,len(image),0)
    return bytes(xex+image)


class XexProbeTests(unittest.TestCase):
    def test_synthetic_image_and_scan(self):
        image,layout=reconstruct(fixture())
        hits=scan_immediates(image,layout,{5736,728})
        self.assertEqual([(h['address'],h['mnemonic'],h['immediate']) for h in hits],
                         [('0x82000200','addi',5736),('0x82000204','mulli',728)])
        self.assertEqual(image[:2],b'MZ')

    def test_malformed_xex(self):
        source=fixture()
        for raw in (b'',b'XEX2',source[:1024],source[:-1]):
            with self.assertRaises(ValueError):reconstruct(raw)
        for offset,value in ((8,0xffffffff),(20,0xffffffff),(28,0xffffffff),(68,0xffffffff),(524,0xffffffff),(44,0x82000400)):
            raw=bytearray(source);struct.pack_into('>I',raw,offset,value)
            with self.subTest(offset=offset),self.assertRaises(ValueError):reconstruct(raw)
        raw=bytearray(source);struct.pack_into('>H',raw,518,2)
        with self.assertRaises(ValueError):reconstruct(raw)

    @unittest.skipUnless((Path(__file__).parent/'default.xex').exists(), 'Local game data not supplied')
    def test_real_source(self):
        import hashlib
        raw=(Path(__file__).parent/'default.xex').read_bytes()
        image,layout=reconstruct(raw)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'b76db0fc2f86794f4e99bb4d93dd8148d31a00b518cb1e5c822ef0bc75ac1087')
        self.assertEqual(len(image),18612224)
        self.assertEqual(layout['entry_point'],0x826d2238)
        hits=scan_immediates(image,layout,{5736,728,6670})
        self.assertTrue(any(h['address']=='0x82178430' and h['mnemonic']=='mulli' and h['immediate']==728 for h in hits))

if __name__=='__main__':unittest.main()
