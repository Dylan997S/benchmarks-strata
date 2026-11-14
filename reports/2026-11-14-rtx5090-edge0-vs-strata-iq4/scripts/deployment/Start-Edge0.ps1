param(
    [Parameter(Mandatory=$true)][string]$InstallRoot,
    [Parameter(Mandatory=$true)][string]$CudaRoot
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $InstallRoot).Path
$exe = Join-Path $root 'repo\edge0-infer\build\windows\bin\edge0-infer.exe'
$model = Join-Path $root 'models\Edge0-145B-NVFP4'
$pidFile = Join-Path $root 'edge0.pid'
if (Test-Path $pidFile) {
    $prior = Get-Process -Id ([int](Get-Content $pidFile)) -ErrorAction SilentlyContinue
    if ($prior -and $prior.Path -eq $exe) {
        Write-Output "Edge0 startup or service already running (PID $($prior.Id))"
        return
    }
}
$gpuLines = @(& nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits)
$queryExitCode = $LASTEXITCODE
$gpu = $gpuLines[0]
if ($queryExitCode -ne 0 -or [int]$gpu -lt 25000) {
    throw "Edge0 requires at least 25000 MiB of free VRAM for this profile. Current free MiB: $gpu"
}
if (Get-NetTCPConnection -State Listen -LocalPort 18089 -ErrorAction SilentlyContinue) {
    throw 'Port 18089 is already in use.'
}
$env:CUDA_PATH = (Resolve-Path -LiteralPath $CudaRoot).Path
$env:PATH = "$env:CUDA_PATH\bin\x64;$env:CUDA_PATH\bin;$env:PATH"
$env:STRATA_RESIDENT_HEADROOM_GIB = '16'
$env:TMP = Join-Path $root 'tmp'
$env:TEMP = $env:TMP
New-Item -Path $env:TMP -ItemType Directory -Force | Out-Null
& $exe inspect --model $model --json | Set-Content -Path (Join-Path $root 'inspect.json') -Encoding utf8
if ($LASTEXITCODE -ne 0) { throw 'edge0-infer inspect failed.' }
$launch = @(
    'serve', '--model', ('"' + $model + '"'), '--device', 'cuda:0',
    '--host', '127.0.0.1', '--port', '18089', '--alias', 'edge0-145b-nvfp4',
    '--context', '32768', '--model-option', 'du=q8', '--model-option', 'ple-io=direct',
    '--strata-arg', '--vram-reserve-mib', '--strata-arg', '3072',
    '--strata-arg', '--kv-resident', '--strata-arg', '32768',
    '--strata-arg', '--resident-experts',
    '--strata-arg', '--adapt-async', '--strata-arg', '1'
)
$service = Start-Process -FilePath $exe -ArgumentList $launch -WorkingDirectory $root -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $root 'serve.out.log') `
    -RedirectStandardError (Join-Path $root 'serve.err.log')
Set-Content -Path $pidFile -Value $service.Id
Write-Output "Edge0 PID $($service.Id). Check http://127.0.0.1:18089/health for readiness."
