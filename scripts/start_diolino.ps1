param([switch]$Background)

$ErrorActionPreference = 'Stop'
$diolinoRoot = Split-Path -Parent $PSScriptRoot
$diolinoTheme = Get-Content -LiteralPath (Join-Path $diolinoRoot 'theme.py') -Raw
$diolinoMatch = [regex]::Match($diolinoTheme, "(?m)^VERSION = '([0-9.]+)'")
if (-not $diolinoMatch.Success) { throw 'Diolino version not found.' }
$diolinoInstalledExe = Join-Path $env:LOCALAPPDATA ("Programs\Diolino\{0}\Diolino.exe" -f $diolinoMatch.Groups[1].Value)
$diolinoCandidate = if (Test-Path -LiteralPath $diolinoInstalledExe) { $diolinoInstalledExe } else { Join-Path $diolinoRoot ("releases\{0}\Diolino\Diolino.exe" -f $diolinoMatch.Groups[1].Value) }
$diolinoExe = (Resolve-Path -LiteralPath $diolinoCandidate).Path
$diolinoCommand = '"' + $diolinoExe + '"'
if ($Background) { $diolinoCommand += ' --background' }

# The automation host can close its entire process job when the GPT exits.
# WMI plus BREAKAWAY creates an independent process, outside both the host's
# job and WMI's provider job. No service, elevated rights or settings changes.
$diolinoStartup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{
    ShowWindow = [uint16]$(if ($Background) { 0 } else { 1 })
    CreateFlags = [uint32]0x01000208 # BREAKAWAY | NEW_PROCESS_GROUP | DETACHED
}
$diolinoResult = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
    CommandLine = $diolinoCommand
    CurrentDirectory = Split-Path -Parent $diolinoExe
    ProcessStartupInformation = $diolinoStartup
}
if ($diolinoResult.ReturnValue -ne 0) {
    throw "Could not launch Diolino independently (Windows code $($diolinoResult.ReturnValue))."
}
[PSCustomObject]@{ProcessId=$diolinoResult.ProcessId;Version=$diolinoMatch.Groups[1].Value;Background=[bool]$Background}
