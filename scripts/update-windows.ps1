param(
    [Parameter(Mandatory=$true)][string]$Installer,
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-fA-F]{64}$')][string]$ExpectedSha256,
    [string]$DataDirectory = (Join-Path $env:LOCALAPPDATA 'ProjetoDiolino'),
    [switch]$VerifyOnly
)
$ErrorActionPreference = 'Stop'
$packagePath = (Resolve-Path -LiteralPath $Installer).ProviderPath
if ([IO.Path]::GetExtension($packagePath) -ne '.exe') { throw 'Selecione o instalador executável.' }
$stream = [IO.File]::Open($packagePath, 'Open', 'Read', 'Read')
try {
    if ((Get-FileHash -InputStream $stream -Algorithm SHA256).Hash -ne $ExpectedSha256) {
        throw 'O SHA-256 do instalador diverge da referência.'
    }
    if ($VerifyOnly) { Write-Output 'SHA-256 do instalador confirmado.'; return }
    if (Get-Process -Name Diolino -ErrorAction SilentlyContinue) { throw 'Feche o Diolino antes de atualizar.' }
    $database = Join-Path $DataDirectory 'diolino.sqlite3'
    if (Test-Path -LiteralPath $database) {
        $backup = Join-Path $DataDirectory ('backups/pre-update-' + [guid]::NewGuid() + '.diolinobak')
        $interpreter = Join-Path $PSScriptRoot '../.venv/Scripts/python.exe'
        & $interpreter (Join-Path $PSScriptRoot '../update_backup.py') $database $backup
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar a cópia de recuperação.' }
        Write-Output "Cópia criptografada de recuperação: $backup"
    }
    $result = Start-Process -FilePath $packagePath -Wait -PassThru
    if ($result.ExitCode -ne 0) { throw "Instalação interrompida (código $($result.ExitCode))." }
} finally {
    $stream.Dispose()
}
