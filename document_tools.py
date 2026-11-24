"""Bounded local PDF operations and offline OCR. Never saves personal records."""
from pathlib import Path
import re
import subprocess
import sys
from pypdf import PdfReader, PdfWriter
from PIL import Image

MAX_FILE = 20*1024*1024
MAX_PAGES = 200
MAX_TEXT = 1_000_000


def reader_for(path):
    path=Path(path)
    if path.stat().st_size>MAX_FILE:
        raise ValueError('Selecione um PDF de até 20 MiB.')
    reader=PdfReader(path)
    if reader.is_encrypted:
        raise ValueError('Este painel não abre PDFs protegidos por senha.')
    if len(reader.pages)>MAX_PAGES:
        raise ValueError('Este painel aceita PDFs de até 200 páginas.')
    return reader


def extract_pdf(path):
    reader=reader_for(path)
    chunks=[];length=0
    for index,page in enumerate(reader.pages,1):
        text=page.extract_text() or ''
        length+=len(text)
        if length>MAX_TEXT:
            raise ValueError('O texto excede o limite de um milhão de caracteres.')
        chunks.append(f'Página {index}\n{text}')
    return '\n\n'.join(chunks)


def page_numbers(expression,total):
    values=[]
    for token in expression.split(','):
        match=re.fullmatch(r'\s*(\d+)\s*(?:-\s*(\d+)\s*)?',token)
        if not match:
            raise ValueError('Use páginas como 1,3-5. A numeração começa em 1.')
        first,last=int(match[1]),int(match[2] or match[1])
        if not 1<=first<=last<=total:
            raise ValueError('Página ou intervalo fora do documento.')
        values.extend(range(first-1,last))
        if len(values)>MAX_PAGES:
            raise ValueError('Selecione até 200 páginas.')
    return values


def write_pdf(writer,destination):
    with Path(destination).open('xb') as file:
        writer.write(file)
    return Path(destination)


def extract_pages(source,expression,destination):
    reader=reader_for(source);writer=PdfWriter()
    for index in page_numbers(expression,len(reader.pages)):
        writer.add_page(reader.pages[index])
    return write_pdf(writer,destination)


def merge_pdfs(sources,destination):
    if not 2<=len(sources)<=10:
        raise ValueError('Selecione de 2 a 10 PDFs, na ordem desejada.')
    writer=PdfWriter()
    for source in sources:
        reader=reader_for(source)
        if len(writer.pages)+len(reader.pages)>MAX_PAGES:
            raise ValueError('A combinação excede 200 páginas.')
        for page in reader.pages:
            writer.add_page(page)
    return write_pdf(writer,destination)


def ocr_engine():
    base=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))
    root=base/'ocr' if getattr(sys,'frozen',False) else base/'assets'/'ocr'
    return root/'tesseract.exe',root/'tessdata'


def recognize_image(path):
    path=Path(path)
    if path.suffix.lower() not in ('.png','.jpg','.jpeg','.tif','.tiff','.bmp') or path.stat().st_size>MAX_FILE:
        raise ValueError('Use PNG, JPEG, TIFF ou BMP de até 20 MiB.')
    with Image.open(path) as picture:
        if picture.width*picture.height>40_000_000:
            raise ValueError('A imagem excede 40 megapixels.')
        picture.verify()
    engine,languages=ocr_engine()
    if not engine.is_file() or any(not (languages/f'{code}.traineddata').is_file() for code in ('por','eng')):
        raise ValueError('O mecanismo OCR ou os idiomas estão ausentes. Reinstale o pacote completo do Diolino.')
    try:
        result=subprocess.run([str(engine),str(path),'stdout','--tessdata-dir',str(languages),'-l','por+eng'],
                              capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60,
                              creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    except subprocess.TimeoutExpired:
        raise ValueError('O OCR excedeu 60 segundos. Tente uma imagem menor.') from None
    if result.returncode:
        raise ValueError('Não foi possível reconhecer esta imagem. Tente outra resolução ou formato.')
    if len(result.stdout)>MAX_TEXT:
        raise ValueError('O texto reconhecido excede o limite deste painel.')
    return result.stdout
