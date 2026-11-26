param([switch]$ConfigureFirewall, [switch]$AllowInsecureLan, [uri]$TunnelUrl)
$ErrorActionPreference = 'Stop'
$diolinoRoot = Split-Path -Parent $PSScriptRoot
$diolinoPython = (Resolve-Path -LiteralPath (Join-Path $diolinoRoot '.venv\Scripts\pythonw.exe')).Path
$diolinoServer = (Resolve-Path -LiteralPath (Join-Path $diolinoRoot 'mobile_server.py')).Path
if ($TunnelUrl -and ($TunnelUrl.Scheme -ne 'https' -or $AllowInsecureLan)) {
    throw 'Informe um tunel HTTPS sem combinar com -AllowInsecureLan.'
}
if ($ConfigureFirewall) {
    $diolinoLocalAddress = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -like '192.168.0.*'} | Select-Object -First 1).IPAddress
    if (-not $diolinoLocalAddress) { throw 'Rede local 192.168.0.x nao encontrada.' }
    if (-not (Get-NetFirewallRule -DisplayName 'Diolino iPhone - rede local' -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -DisplayName 'Diolino iPhone - rede local' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8765 -LocalAddress $diolinoLocalAddress -RemoteAddress '192.168.0.0/24' -Profile Any -ErrorAction Stop | Out-Null
    }
}
$diolinoStartup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{
    ShowWindow = [uint16]0
    CreateFlags = [uint32]0x01000208
}
$diolinoArguments = ''
if ($TunnelUrl) {
    $diolinoArguments = ' --tunnel-url "' + $TunnelUrl.AbsoluteUri.Replace('"', '%22') + '"'
} elseif ($AllowInsecureLan) {
    $diolinoArguments = ' --allow-insecure-lan'
}
$diolinoResult = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
    CommandLine = '"' + $diolinoPython + '" "' + $diolinoServer + '"' + $diolinoArguments
    CurrentDirectory = $diolinoRoot
    ProcessStartupInformation = $diolinoStartup
}
if ($diolinoResult.ReturnValue -ne 0) { throw 'Nao foi possivel iniciar o acesso movel.' }
[PSCustomObject]@{ProcessId=$diolinoResult.ProcessId;Port=8765}
