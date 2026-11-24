"""Preserve notices from the exact installed runtime dependencies."""
from pathlib import Path
import importlib.metadata as metadata
import shutil

def collect():
    root=Path(__file__).resolve().parent.parent/'assets'/'licenses'
    root.mkdir(parents=True,exist_ok=True)
    names=['fsrs','rapidfuzz','cryptography','pypdf','cffi','pycparser','typing-extensions']
    manifest=[]
    for name in names:
        distribution=metadata.distribution(name)
        destination=root/name;destination.mkdir(exist_ok=True)
        found=[]
        for entry in distribution.files or []:
            if 'license' in str(entry).lower() and distribution.locate_file(entry).is_file():
                source=distribution.locate_file(entry)
                shutil.copyfile(source,destination/source.name);found.append(source.name)
        if not found:raise ValueError('Licença ausente: '+name)
        manifest.append(f'{name}=={distribution.version}: '+', '.join(found))
    (root/'VERSIONS.txt').write_text('\n'.join(manifest)+'\n',encoding='utf-8')

if __name__=='__main__':collect()
