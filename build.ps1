$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$diolinoVersion = (& '.venv/Scripts/python.exe' -c 'from theme import VERSION; print(VERSION)').Trim()
$diolinoExistingRelease = Join-Path $PSScriptRoot "releases/$diolinoVersion/Diolino/Diolino.exe"
if (Test-Path -LiteralPath $diolinoExistingRelease) {
    $diolinoRunningRelease = Get-CimInstance Win32_Process -Filter "Name='Diolino.exe'" | Where-Object {
        -not $_.ExecutablePath -or $_.ExecutablePath -eq $diolinoExistingRelease
    }
    if ($diolinoRunningRelease) { throw 'Distribuicao possivelmente em uso. Gere uma nova versao em outra pasta antes de atualizar os atalhos.' }
}
& '.venv/Scripts/python.exe' scripts/collect_licenses.py
if ($LASTEXITCODE -ne 0) { throw 'Falha ao recolher licenças.' }
if (-not (Test-Path -LiteralPath 'assets/ocr/tesseract.exe')) { throw 'Prepare o mecanismo OCR antes de compilar. Consulte assets/ocr/SOURCES.md.' }
& '.venv/Scripts/python.exe' -m PyInstaller --noconfirm --windowed --onedir --noupx --name Diolino --distpath "releases/$diolinoVersion" --add-data 'data/taco/catalogue.json;data/taco' --add-data 'assets/visual;assets/visual' --add-data 'assets/licenses;licenses' --add-data 'assets/ocr;ocr' --add-data 'data/bibles;data/bibles' --hidden-import rapidfuzz.fuzz_cpp --hidden-import rapidfuzz.process_cpp --collect-all fsrs --collect-all pypdf --collect-all caldav --collect-all niquests --collect-all wassima --collect-data cryptography --collect-data icalendar --collect-data tzdata app.py
if ($LASTEXITCODE -ne 0) { throw 'Falha ao empacotar o Projeto Diolino.' }
