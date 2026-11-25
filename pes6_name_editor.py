"""Source-bound, fixed-capacity club names and XEX2 basic-image repacking."""
import hashlib
from collections import Counter
from pes6_xex_probe import reconstruct,u32
from pes6_club_identity import SOURCE_SHA256


def repack(source,image):
    original,layout=reconstruct(source)
    if len(image)!=len(original):raise ValueError('O tamanho da imagem do executável mudou')
    chunks=[];cursor=0
    for block in layout['blocks']:
        size,zero=block['data_size'],block['zero_size']
        chunks.append(image[cursor:cursor+size])
        if image[cursor+size:cursor+size+zero]!=original[cursor+size:cursor+size+zero]:
            raise ValueError('Alteração em área não armazenada do executável')
        cursor+=size+zero
    if image[cursor:]!=original[cursor:]:raise ValueError('Alteração fora dos blocos armazenados')
    payload=b''.join(chunks)
    if layout['encryption']=='normal':
        from cryptography.hazmat.primitives.ciphers import Cipher,algorithms,modes
        security=u32(source,16)
        dec=Cipher(algorithms.AES(bytes.fromhex('20b185a59d28fdc340583fbb0896bf91')),modes.CBC(bytes(16))).decryptor()
        key=dec.update(source[security+0x150:security+0x160])+dec.finalize()
        enc=Cipher(algorithms.AES(key),modes.CBC(bytes(16))).encryptor()
        payload=enc.update(payload)+enc.finalize()
    start=layout['header_size'];result=source[:start]+payload+source[start+len(payload):]
    if len(result)!=len(source) or reconstruct(result)[0]!=image:
        raise ValueError('Falha ao verificar o executável reconstruído')
    return result


class NameEditor:
    def __init__(self,source,report):
        if hashlib.sha256(source).hexdigest()!=SOURCE_SHA256 or report['source_sha256']!=SOURCE_SHA256:
            raise ValueError('Executável não corresponde à versão de nomes validada')
        self.source=source;self.image,self.layout=reconstruct(source);self.rows={r['record']:r for r in report['records']}
        self.edits={}
        self.references=Counter(r[key] for r in self.rows.values() for key in ('name_address','short_name_address'))

    def limits(self,record):
        if type(record) is not int or record not in self.rows:raise ValueError('Equipe inválida')
        row=self.rows[record]
        return {'name':len(row['name'].encode('utf-8')),'short_name':len(row['short_name'].encode('utf-8'))}

    def validate(self,record,name,short_name):
        limits=self.limits(record);row=self.rows[record];values={}
        for field,value in (('name',name),('short_name',short_name)):
            if not isinstance(value,str):raise ValueError('Nome e sigla devem ser textos')
            value=value.strip()
            if not value or not all(c.isprintable() for c in value):raise ValueError('Nome ou sigla vazio ou com caracteres de controle')
            if len(value.encode('utf-8'))>limits[field]:
                raise ValueError(f"{'Nome' if field=='name' else 'Sigla'} excede o limite de {limits[field]} bytes desta equipe")
            if value!=row[field] and self.references[row[field+'_address']]>1:
                raise ValueError('Este texto é compartilhado por outras equipes; edição individual indisponível')
            values[field]=value
        return values

    def stage(self,record,name,short_name):
        values=self.validate(record,name,short_name);row=self.rows[record]
        if values=={'name':row['name'],'short_name':row['short_name']}:self.edits.pop(record,None)
        else:self.edits[record]=values

    def validated_project(self,data):
        edits=data.get('club_names',{})
        if not isinstance(edits,dict):raise ValueError('Nomes do projeto inválidos')
        if edits and data.get('name_source_sha256')!=SOURCE_SHA256:raise ValueError('Nomes vinculados a outro executável')
        result={};seen=set()
        for record,values in edits.items():
            if not isinstance(record,str) or not record.isdecimal() or not isinstance(values,dict):raise ValueError('Registro de nome inválido')
            key=int(record)
            if key in seen:raise ValueError('Registro de nome duplicado')
            seen.add(key)
            valid=self.validate(key,values['name'],values['short_name'])
            row=self.rows[key]
            if valid!={'name':row['name'],'short_name':row['short_name']}:result[key]=valid
        return result

    def build(self):
        image=bytearray(self.image);spans=[]
        for record,values in self.edits.items():
            row=self.rows[record];values=self.validate(record,**values)
            for field,value in values.items():
                if value==row[field]:continue
                offset=int(row[field+'_address'],16)-self.layout['base_address']
                old=row[field].encode('utf-8')+b'\0';new=value.encode('utf-8')
                if self.image[offset:offset+len(old)]!=old:raise ValueError('Texto original divergente')
                spans.append((offset,offset+len(old)))
                image[offset:offset+len(old)]=new+bytes(len(old)-len(new))
        spans.sort()
        if any(a[1]>b[0] for a,b in zip(spans,spans[1:])):raise ValueError('Textos sobrepostos')
        return repack(self.source,bytes(image))
