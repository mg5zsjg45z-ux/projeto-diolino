"""Explicit one-time download of pinned local runtimes and model weights."""
import hashlib
import json
import os
from pathlib import Path
import urllib.request
import zipfile

ASSETS = [
    ('llama.zip', 'https://github.com/ggml-org/llama.cpp/releases/download/b11700/llama-b11700-bin-win-cpu-x64.zip', '4e2af6b2b39691cd84267a02839596ed6653ea2dde5ee9cdbfeb4dd9677eecbb', 'llama'),
    ('whisper.zip', 'https://github.com/ggml-org/whisper.cpp/releases/download/v1.7.6/whisper-bin-x64.zip', '0d2eca299c248f965bd0341bcb219db4b433c7f0c0ce2200d4df85765e8156a9', 'whisper'),
    ('ggml-small.bin', 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin', '1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b', None),
    ('Qwen3-1.7B-Q8_0.gguf', 'https://huggingface.co/Qwen/Qwen3-1.7B-GGUF/resolve/main/Qwen3-1.7B-Q8_0.gguf', '061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a', None),
]


def asset_directory():
    return Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'ProjetoDiolino' / 'offline-ai'


def locate(folder, name):
    candidates = list((Path(folder)).rglob(name))
    if len(candidates) != 1:
        raise ValueError('Componente de IA ausente. Use Preparar IA offline para instalar ou reparar.')
    return candidates[0]


def ready(folder=None):
    folder = Path(folder or asset_directory())
    try:
        for name in ('llama-server.exe', 'whisper-cli.exe', 'ggml-small.bin', 'Qwen3-1.7B-Q8_0.gguf'):
            locate(folder, name)
        return (folder / 'installed.json').is_file()
    except ValueError:
        return False


def install(folder=None, progress=lambda text: None):
    folder = Path(folder or asset_directory())
    folder.mkdir(parents=True, exist_ok=True)
    for name, url, digest, subdir in ASSETS:
        target = folder / name
        def checksum(path):
            with path.open('rb') as stream:
                return hashlib.file_digest(stream, 'sha256').hexdigest()
        if not target.exists() or checksum(target) != digest:
            progress('Baixando ' + name)
            partial = target.with_suffix(target.suffix + '.part')
            request = urllib.request.Request(url, headers={'User-Agent': 'Diolino/0.6'})
            with urllib.request.urlopen(request, timeout=60) as source, partial.open('wb') as output:
                total = int(source.headers.get('Content-Length', 0))
                count = 0
                last = -1
                while block := source.read(1024 * 1024):
                    output.write(block)
                    count += len(block)
                    percent = int(count * 100 / total) if total else 0
                    if percent // 10 != last:
                        progress(f'{name}: {count // (1024 * 1024)} MB' + (f' ({percent}%)' if total else ''))
                        last = percent // 10
            if checksum(partial) != digest:
                partial.unlink(missing_ok=True)
                raise ValueError('A verificação do download falhou. Tente preparar a IA novamente.')
            partial.replace(target)
        if subdir:
            destination = folder / subdir
            destination.mkdir(exist_ok=True)
            with zipfile.ZipFile(target) as archive:
                for entry in archive.infolist():
                    if not (destination / entry.filename).resolve().is_relative_to(destination.resolve()):
                        raise ValueError('Arquivo de instalação inválido.')
                archive.extractall(destination)
    (folder / 'installed.json').write_text(json.dumps({'assets': [{'name': a[0], 'sha256': a[2]} for a in ASSETS]}), encoding='utf-8')
    if not ready(folder):
        raise ValueError('Instalação incompleta dos componentes offline.')
    progress('IA offline pronta. Áudios e textos são processados neste computador.')
