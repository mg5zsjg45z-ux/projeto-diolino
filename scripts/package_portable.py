"""Package only the application release; reject personal databases and symlinks."""
from pathlib import Path
import re
import sys
from zipfile import ZipFile, ZIP_DEFLATED

def package(version, root=None):
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Versão inválida.')
    root=Path(root) if root else Path(__file__).resolve().parent.parent
    source=root/'releases'/version/'Diolino'
    if not (source/'Diolino.exe').is_file():
        raise ValueError('Executável ausente.')
    paths=list(source.rglob('*'))
    for path in paths:
        if path.is_symlink() or not path.resolve().is_relative_to(source.resolve()):
            raise ValueError('Link externo no pacote: '+str(path))
        if path.suffix.lower() in ('.sqlite3','.db','.env') or path.name in ('appearance.json','icloud.json','Resumo-para-o-chat.md'):
            raise ValueError('Arquivo pessoal inesperado no pacote: '+path.name)
    destination=root/'releases'/(version+'-distribuicao')/'Diolino-portatil.zip'
    destination.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(destination,'w',ZIP_DEFLATED) as archive:
        for path in sorted(paths):
            if path.is_file():archive.write(path,Path('Diolino')/path.relative_to(source))
    return destination

if __name__=='__main__':
    print(package(sys.argv[1]))
