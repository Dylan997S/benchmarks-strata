param([Parameter(Mandatory=$true)][string]$InstallRoot)
$ErrorActionPreference = 'Stop'
$pidFile = Join-Path $InstallRoot 'edge0.pid'
$exe = Join-Path $InstallRoot 'repo\edge0-infer\build\windows\bin\edge0-infer.exe'
if (Test-Path $pidFile) {
    $servicePid = [int](Get-Content $pidFile)
    $service = Get-Process -Id $servicePid -ErrorAction SilentlyContinue
    if ($service -and $service.Path -eq $exe) {
        Stop-Process -Id $servicePid
        Wait-Process -Id $servicePid -Timeout 20 -ErrorAction SilentlyContinue
    }
    Remove-Item -LiteralPath $pidFile
}
