param([string]$CompilerPath)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
$version = (& '.venv/Scripts/python.exe' -c 'from theme import VERSION; print(VERSION)').Trim()
if ($version -notmatch '^\d+\.\d+\.\d+$') { throw 'Versão inválida.' }
$source = Join-Path $root "releases/$version/Diolino"
if (-not (Test-Path -LiteralPath (Join-Path $source 'Diolino.exe'))) { throw 'Compile com build.ps1 primeiro.' }
if (-not $CompilerPath) { $CompilerPath = Join-Path $env:LOCALAPPDATA 'Programs/DiolinoBuildTools/InnoSetup6/ISCC.exe' }
if (-not (Test-Path -LiteralPath $CompilerPath)) { throw 'Informe -CompilerPath com o caminho oficial de ISCC.exe.' }
$signature = Get-AuthenticodeSignature -LiteralPath $CompilerPath
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notlike '*Pyrsys*') { throw 'Assinatura do compilador não confirmada.' }
$distribution = Join-Path $root "releases/$version-distribuicao"
New-Item -ItemType Directory -Path $distribution -Force | Out-Null
& '.venv/Scripts/python.exe' scripts/package_portable.py $version
if ($LASTEXITCODE -ne 0) { throw 'Falha no pacote portátil.' }
& $CompilerPath "/DAppVersion=$version" (Join-Path $PSScriptRoot 'diolino.iss')
if ($LASTEXITCODE -ne 0) { throw 'Falha na compilação Inno Setup.' }
Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $distribution 'Diolino-portatil.zip'),(Join-Path $distribution 'Diolino-Instalador.exe') | Export-Csv -LiteralPath (Join-Path $distribution 'SHA256.csv') -NoTypeInformation
