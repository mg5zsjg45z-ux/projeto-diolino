"""Passage links to licensed readers; no third-party Bible text is redistributed."""
from datetime import date, timedelta
from planning import create_plan

VERSIONS = {
    'NAA': ('Nova Almeida Atualizada', '1840'),
    'ARA': ('Almeida Revista e Atualizada', '1608'),
    'ARC': ('Almeida Revista e Corrigida', '212'),
    'NVI': ('Nova Versão Internacional', '129'),
    'NVT': ('Nova Versão Transformadora', '1930'),
    'NTLH': ('Nova Tradução na Linguagem de Hoje', '211'),
    'ACF': ('Almeida Corrigida Fiel', None),
}
# Name, USFM code, chapter count, Bíblia Online abbreviation.
BOOKS = [
    ('Gênesis','GEN',50,'gn'), ('Êxodo','EXO',40,'ex'), ('Levítico','LEV',27,'lv'),
    ('Números','NUM',36,'nm'), ('Deuteronômio','DEU',34,'dt'), ('Josué','JOS',24,'js'),
    ('Juízes','JDG',21,'jz'), ('Rute','RUT',4,'rt'), ('1 Samuel','1SA',31,'1sm'),
    ('2 Samuel','2SA',24,'2sm'), ('1 Reis','1KI',22,'1rs'), ('2 Reis','2KI',25,'2rs'),
    ('1 Crônicas','1CH',29,'1cr'), ('2 Crônicas','2CH',36,'2cr'), ('Esdras','EZR',10,'ed'),
    ('Neemias','NEH',13,'ne'), ('Ester','EST',10,'et'), ('Jó','JOB',42,'jó'),
    ('Salmos','PSA',150,'sl'), ('Provérbios','PRO',31,'pv'), ('Eclesiastes','ECC',12,'ec'),
    ('Cantares','SNG',8,'ct'), ('Isaías','ISA',66,'is'), ('Jeremias','JER',52,'jr'),
    ('Lamentações','LAM',5,'lm'), ('Ezequiel','EZK',48,'ez'), ('Daniel','DAN',12,'dn'),
    ('Oséias','HOS',14,'os'), ('Joel','JOL',3,'jl'), ('Amós','AMO',9,'am'),
    ('Obadias','OBA',1,'ob'), ('Jonas','JON',4,'jn'), ('Miquéias','MIC',7,'mq'),
    ('Naum','NAM',3,'na'), ('Habacuque','HAB',3,'hc'), ('Sofonias','ZEP',3,'sf'),
    ('Ageu','HAG',2,'ag'), ('Zacarias','ZEC',14,'zc'), ('Malaquias','MAL',4,'ml'),
    ('Mateus','MAT',28,'mt'), ('Marcos','MRK',16,'mc'), ('Lucas','LUK',24,'lc'),
    ('João','JHN',21,'jo'), ('Atos','ACT',28,'atos'), ('Romanos','ROM',16,'rm'),
    ('1 Coríntios','1CO',16,'1co'), ('2 Coríntios','2CO',13,'2co'), ('Gálatas','GAL',6,'gl'),
    ('Efésios','EPH',6,'ef'), ('Filipenses','PHP',4,'fp'), ('Colossenses','COL',4,'cl'),
    ('1 Tessalonicenses','1TH',5,'1ts'), ('2 Tessalonicenses','2TH',3,'2ts'),
    ('1 Timóteo','1TI',6,'1tm'), ('2 Timóteo','2TI',4,'2tm'), ('Tito','TIT',3,'tt'),
    ('Filemom','PHM',1,'fm'), ('Hebreus','HEB',13,'hb'), ('Tiago','JAS',5,'tg'),
    ('1 Pedro','1PE',5,'1pe'), ('2 Pedro','2PE',3,'2pe'), ('1 João','1JN',5,'1jo'),
    ('2 João','2JN',1,'2jo'), ('3 João','3JN',1,'3jo'), ('Judas','JUD',1,'jd'),
    ('Apocalipse','REV',22,'ap'),
]


def passage(version, book, chapter):
    from urllib.parse import quote
    if version not in VERSIONS:
        raise ValueError('Selecione uma versão da Bíblia.')
    selected = next((row for row in BOOKS if row[0] == book), None)
    if not selected:
        raise ValueError('Selecione um livro.')
    try:
        chapter = int(chapter)
    except (ValueError, TypeError):
        raise ValueError('Informe um capítulo válido.') from None
    if not 1 <= chapter <= selected[2]:
        raise ValueError(f'{book} possui {selected[2]} capítulos.')
    version_id = VERSIONS[version][1]
    url = (f'https://www.bible.com/pt/bible/{version_id}/{selected[1]}.{chapter}.{version}' if version_id
           else f'https://www.bibliaonline.com.br/acf/{quote(selected[3])}/{chapter}')
    return {'reference': f'{book} {chapter} · {version}', 'url': url}


def reading_plan(store, book, version, start):
    first = date.fromisoformat(start)
    passage(version, book, 1)
    count = next(row[2] for row in BOOKS if row[0] == book)
    if count > 100:
        raise ValueError('Escolha um livro com até 100 capítulos para este modelo.')
    steps = [dict(title=passage(version, book, index + 1)['reference'],
                  due_date=(first + timedelta(days=index)).isoformat(),
                  notes=passage(version, book, index + 1)['url']) for index in range(count)]
    return create_plan(store, dict(title=f'Leitura de {book} · {version}', area='Bíblia', status='Ativo',
                       priority='Normal', start_date=start, end_date=steps[-1]['due_date'],
                       objective='Ler um capítulo por dia e registrar o estudo separadamente.'), steps)
