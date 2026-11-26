param([uri]$TunnelUrl)
$ErrorActionPreference = 'Stop'
$diolinoRoot = Split-Path -Parent $PSScriptRoot
$diolinoStartupFolder = [Environment]::GetFolderPath('Startup')
$diolinoShell = New-Object -ComObject WScript.Shell
$diolinoLink = $diolinoShell.CreateShortcut((Join-Path $diolinoStartupFolder 'Diolino - acesso iPhone.lnk'))
$diolinoLink.TargetPath = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$diolinoLink.Arguments = '-NoProfile -WindowStyle Hidden -File "' + (Join-Path $PSScriptRoot 'start_mobile.ps1') + '"'
if ($TunnelUrl) {
    if ($TunnelUrl.Scheme -ne 'https') { throw 'Informe uma URL HTTPS.' }
    $diolinoLink.Arguments += ' -TunnelUrl "' + $TunnelUrl.AbsoluteUri.Replace('"', '%22') + '"'
}
$diolinoLink.WorkingDirectory = $diolinoRoot
$diolinoLink.WindowStyle = 7
$diolinoLink.Description = 'Acesso movel ao Diolino'
$diolinoLink.Save()
