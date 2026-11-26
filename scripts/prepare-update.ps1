param(
    [Parameter(Mandatory=$true)][string]$CandidateDirectory,
    [Parameter(Mandatory=$true)][string]$ExpectedSha256,
    [string]$DataDirectory = (Join-Path $env:LOCALAPPDATA 'ProjetoDiolino'),
    [string]$Python = 'python'
)
$ErrorActionPreference = 'Stop'
if (Get-Process -Name Diolino -ErrorAction SilentlyContinue) { throw 'Feche o Diolino completamente.' }
$exe = Join-Path $CandidateDirectory 'Diolino.exe'
if (!(Test-Path -LiteralPath $exe -PathType Leaf)) { throw 'Executável ausente.' }
if ((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash -ne $ExpectedSha256) { throw 'Hash divergente.' }
$source = Join-Path $DataDirectory 'diolino.sqlite3'
$backup = Join-Path $DataDirectory ('backups/pre-update-' + [guid]::NewGuid().ToString() + '.sqlite3')
& $Python (Join-Path $PSScriptRoot 'update_guard.py') $source $backup
if ($LASTEXITCODE -ne 0) { throw 'Backup não validado. Atualização interrompida.' }
Write-Output "Backup local não criptografado: $backup"
Write-Output "Candidato verificado parcialmente: $exe"
Write-Output 'Nenhum atalho, executável instalado ou banco ativo foi substituído. Homologue antes de ativar.'
