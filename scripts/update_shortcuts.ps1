$ErrorActionPreference = 'Stop'
$diolinoRoot = Split-Path -Parent $PSScriptRoot
$diolinoTheme = Get-Content -LiteralPath (Join-Path $diolinoRoot 'theme.py') -Raw
$diolinoVersionMatch = [regex]::Match($diolinoTheme, "(?m)^VERSION = '([0-9.]+)'")
if (-not $diolinoVersionMatch.Success) { throw 'Diolino version not found.' }
$diolinoExe = (Resolve-Path -LiteralPath (Join-Path $diolinoRoot ("releases\{0}\Diolino\Diolino.exe" -f $diolinoVersionMatch.Groups[1].Value))).Path
$diolinoShell = New-Object -ComObject WScript.Shell
$diolinoFolders = @([Environment]::GetFolderPath('DesktopDirectory'), (Join-Path $env:USERPROFILE 'Desktop'))
if ($env:OneDrive -and (Test-Path -LiteralPath (Join-Path $env:OneDrive 'Desktop'))) {
    $diolinoFolders += Join-Path $env:OneDrive 'Desktop'
}
$diolinoFolders += [Environment]::GetFolderPath('Startup')
foreach ($diolinoFolder in ($diolinoFolders | Select-Object -Unique)) {
    if (-not (Test-Path -LiteralPath $diolinoFolder)) { continue }
    $oldLink = Join-Path $diolinoFolder 'Projeto Diolino.lnk'
    $newLink = Join-Path $diolinoFolder 'Diolino.lnk'
    if ((Test-Path -LiteralPath $oldLink) -and -not (Test-Path -LiteralPath $newLink)) { Move-Item -LiteralPath $oldLink -Destination $newLink }
    $diolinoLink = $diolinoShell.CreateShortcut($newLink)
    $diolinoLink.TargetPath = $diolinoExe
    $diolinoLink.WorkingDirectory = Split-Path -Parent $diolinoExe
    $diolinoLink.Arguments = if ($diolinoFolder -eq [Environment]::GetFolderPath('Startup')) { '--background' } else { '' }
    $diolinoLink.IconLocation = "$diolinoExe,0"
    $diolinoLink.Description = 'Diolino - rotina, saude e agenda'
    $diolinoLink.Save()
    Write-Output "Updated: $diolinoFolder"
}
