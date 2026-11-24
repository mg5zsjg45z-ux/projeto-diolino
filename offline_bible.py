"""Validated local JSON scriptures. No downloader or remote API at runtime."""
import json
import re
from pathlib import Path

BUNDLED=Path(__file__).resolve().parent/'data/bibles'

def validate_translation(data):
    if not isinstance(data,dict) or not re.fullmatch(r'[A-Za-z0-9_-]{1,40}',str(data.get('id',''))):
        raise ValueError('Identificação da tradução inválida.')
    for key in ('name','language','license','source'):
        if not isinstance(data.get(key),str) or not data[key].strip():raise ValueError('Metadado obrigatório: '+key)
    books=data.get('books')
    if not isinstance(books,dict) or not 1<=len(books)<=100:raise ValueError('Coleção de livros inválida.')
    total=0
    for code,book in books.items():
        if not isinstance(book,dict) or not book.get('name') or not isinstance(book.get('chapters'),dict) or not book['chapters']:
            raise ValueError('Livro inválido: '+str(code))
        for chapter,verses in book['chapters'].items():
            if not chapter.isdigit() or not 1<=int(chapter)<=200 or not isinstance(verses,dict) or not verses:raise ValueError('Capítulo inválido.')
            for verse,text in verses.items():
                if not verse.isdigit() or not 1<=int(verse)<=200 or not isinstance(text,str) or not text.strip() or len(text)>20000:raise ValueError('Versículo inválido.')
                total+=1
    if total>50000:raise ValueError('Tradução excede o limite de versículos.')
    return data

def read_translation(path):
    if Path(path).stat().st_size>20000000:raise ValueError('Arquivo acima de 20 MB.')
    return validate_translation(json.loads(Path(path).read_text(encoding='utf-8-sig')))

def installed(directory):
    result={}
    for folder in (BUNDLED,Path(directory)/'bibles'):
        if folder.exists():
            for path in sorted(folder.glob('*.json')):
                try:
                    data=read_translation(path)
                    if data['id'] not in result:result[data['id']]=data
                except (ValueError,OSError,TypeError,AttributeError):continue
    return result

def search(data,query):
    query=query.strip().casefold()
    if not query:return []
    return [(b,int(c),int(v),text) for b,book in data['books'].items() for c,verses in book['chapters'].items() for v,text in verses.items() if query in text.casefold()][:200]
