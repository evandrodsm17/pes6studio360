"""DDS import with explicit BC2/DXT3 alpha, no texture relocation."""
import io, struct
from PIL import Image
from pes6_patch import convert as legacy_convert

def fit_image(im, size, mode):
    im=im.convert('RGBA')
    if im.size==size:return im
    if mode=='strict':raise ValueError(f'Use PNG de {size[0]} × {size[1]}')
    if mode=='stretch':return im.resize(size,Image.Resampling.LANCZOS)
    if mode=='contain':
        im.thumbnail(size,Image.Resampling.LANCZOS)
        # Upscale small imports too, preserving aspect ratio.
        scale=min(size[0]/im.width,size[1]/im.height)
        if scale>1:im=im.resize((min(size[0],round(im.width*scale)),min(size[1],round(im.height*scale))),Image.Resampling.LANCZOS)
        dst=Image.new('RGBA',size);dst.paste(im,((size[0]-im.width)//2,(size[1]-im.height)//2));return dst
    raise ValueError('Modo de ajuste inválido')

def convert(original,upload,mode='strict'):
    if original[:4]!=b'DDS ' or len(original)<128:raise ValueError('DDS inválido')
    if upload.startswith(b'DDS '):return legacy_convert(original,upload)
    h,w=struct.unpack_from('<II',original,12)
    with Image.open(io.BytesIO(upload)) as im:
        if im.format!='PNG':raise ValueError('Selecione PNG ou DDS')
        im=fit_image(im,(w,h),mode)
    buf=io.BytesIO();im.save(buf,format='PNG');out=bytearray(legacy_convert(original,buf.getvalue()))
    if original[84:88]==b'DXT3':
        alpha=im.getchannel('A');pixels=alpha.load();off=128
        for y in range(0,h,4):
            for x in range(0,w,4):
                bits=0
                for j in range(4):
                    for i in range(4):
                        v=pixels[min(x+i,w-1),min(y+j,h-1)]
                        bits|=((v+8)//17)<<(4*(j*4+i))
                out[off:off+8]=bits.to_bytes(8,'little');off+=16
        with Image.open(io.BytesIO(out)) as check:
            actual=check.convert('RGBA').getchannel('A').tobytes()
        if any(abs(a-b)>8 for a,b in zip(alpha.tobytes(),actual)):raise ValueError('Falha de validação alpha DXT3')
    return bytes(out)
