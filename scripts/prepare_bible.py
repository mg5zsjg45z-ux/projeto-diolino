"""Convert the official eBible USFX archive; no network needed at runtime."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

def convert(source, destination):
    with ZipFile(source) as archive:
        names={b.attrib['code']:b.attrib['short'] for b in ET.fromstring(archive.read('BookNames.xml'))}
        root=ET.fromstring(archive.read('porbrbsl_usfx.xml'))
        books={}
        current=None
        def walk(node):
            nonlocal current
            if node.tag in ('f','x','h','toc','s','r','d','mt','cl','cp'):
                return
            if node.tag=='v':
                reference=node.attrib['bcv'].split('.')
                if len(reference)==3 and reference[1].isdigit() and reference[2].isdigit():
                    b,c,v=reference
                    book=books.setdefault(b,dict(name=names.get(b,b),chapters={}))
                    verses=book['chapters'].setdefault(c,{})
                    verses[v]='';current=(verses,v)
            elif node.tag=='ve':current=None
            if current and node.text:current[0][current[1]]+=node.text
            for child in node:
                walk(child)
                if current and child.tail:current[0][current[1]]+=child.tail
        walk(root)
        for book in books.values():
            for verses in book['chapters'].values():
                for key,text in list(verses.items()):
                    cleaned=' '.join(text.split())
                    if cleaned:verses[key]=cleaned
                    else:del verses[key]
        target=Path(destination);target.mkdir(parents=True,exist_ok=True)
        payload=dict(id='BPM',name='Bíblia Portuguesa Mundial',language='pt-BR',license='Public Domain',
            source='https://ebible.org/details.php?id=porbrbsl',status='Tradução em revisão, conforme aviso do editor.',
            archive_sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest(),books=books)
        (target/'BPM.json').write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
        (target/'BPM-copyright.html').write_bytes(archive.read('copr.htm'))
        print(len(books),'livros;',sum(len(v) for b in books.values() for v in b['chapters'].values()),'versículos')

if __name__=='__main__':
    convert('test-output/porbrbsl_usfx.zip','data/bibles')
