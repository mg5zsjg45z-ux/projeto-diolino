$ErrorActionPreference = 'Stop'
$diolinoRoot = Split-Path -Parent $PSScriptRoot
try {
    $diolinoLocalAddress = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -like '192.168.0.*'} | Select-Object -First 1).IPAddress
    if (-not $diolinoLocalAddress) { throw 'Rede local 192.168.0.x nao encontrada.' }
    if (-not (Get-NetFirewallRule -DisplayName 'Diolino iPhone - rede local' -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -DisplayName 'Diolino iPhone - rede local' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8765 -LocalAddress $diolinoLocalAddress -RemoteAddress '192.168.0.0/24' -Profile Any -ErrorAction Stop | Out-Null
    }
    'Firewall configurado: TCP 8765, somente rede 192.168.0.0/24.' | Set-Content -LiteralPath (Join-Path $diolinoRoot 'test-output/mobile-network-status.txt')
} catch {
    'Falha ao configurar o Firewall.' | Set-Content -LiteralPath (Join-Path $diolinoRoot 'test-output/mobile-network-status.txt')
    throw
}
