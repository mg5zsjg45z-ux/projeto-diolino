# Run from a checkout of projeto-diolino, not the separate Diolino repository.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = Split-Path $PSScriptRoot -Parent
$remote = & git -C $root remote get-url origin
if ($LASTEXITCODE -ne 0 -or $remote -notmatch 'github\.com[:/]mg5zsjg45z-ux/projeto-diolino(?:\.git)?/?$') {
    throw 'Checkout incorreto: utilize o repositorio oficial projeto-diolino.'
}
foreach ($tool in @('node','npm','cargo','rustc','rustfmt')) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "Ferramenta ausente: $tool" }
}
function Invoke-Checked {
    param([scriptblock]$Command)
    & $Command
    if ($LASTEXITCODE -ne 0) { throw "Falha na etapa: $Command" }
}
Push-Location $root
try {
    Set-Location $PSScriptRoot
    Invoke-Checked { npm ci --no-audit --no-fund }
    Invoke-Checked { npm audit --audit-level=high }
    Invoke-Checked { npm test }
    Invoke-Checked { npm run build }
    Set-Location (Join-Path $PSScriptRoot 'src-tauri')
    Invoke-Checked { cargo fmt --check }
    Invoke-Checked { cargo test --locked }
    Invoke-Checked { cargo check --locked }
    Set-Location $PSScriptRoot
    Invoke-Checked { npm run tauri -- build --debug --no-bundle }
    Write-Host 'Validacao de compilacao concluida. A homologacao visual e separada.'
} finally {
    Pop-Location
}
