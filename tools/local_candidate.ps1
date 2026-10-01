param([ValidateSet('Start','Stop','Status')][string]$Action = 'Start')
$ErrorActionPreference = 'Stop'
$candidateRepo = Split-Path $PSScriptRoot -Parent
$candidateWorkspace = Split-Path $candidateRepo -Parent
$candidateRoot = Join-Path $candidateRepo 'local-candidate'
$candidateConfig = Join-Path $candidateRoot 'router.json'
$candidateExe = Join-Path $candidateRoot 'bin\strata.exe'
$candidateRouter = Join-Path $candidateRepo 'serve\preset_router.py'
$candidatePython = Join-Path $candidateWorkspace 'Strata\.venv\Scripts\python.exe'
$candidateSnapshot = @(Get-CimInstance Win32_Process)
$candidateIds = [System.Collections.Generic.HashSet[int]]::new()
foreach ($candidateProcess in $candidateSnapshot) {
    if (($candidateProcess.Name -eq 'strata.exe' -and $candidateProcess.ExecutablePath -eq $candidateExe) -or
        ($candidateProcess.Name -in @('python.exe','pythonw.exe') -and
         $candidateProcess.CommandLine -like ('*' + $candidateConfig + '*'))) {
        # CIM can briefly retain a terminated process after Wait-Process succeeds.
        $candidateLive = Get-Process -Id $candidateProcess.ProcessId -ErrorAction SilentlyContinue
        if ($candidateLive -and -not $candidateLive.HasExited) { [void]$candidateIds.Add([int]$candidateProcess.ProcessId) }
    }
}
do {
    $candidateAdded = $false
    foreach ($candidateProcess in $candidateSnapshot) {
        if ($candidateIds.Contains([int]$candidateProcess.ParentProcessId)) {
            if ($candidateIds.Add([int]$candidateProcess.ProcessId)) { $candidateAdded = $true }
        }
    }
} while ($candidateAdded)
if ($Action -eq 'Status') {
    if ($candidateIds.Count) { Write-Host ('Candidate running; process IDs: ' + ($candidateIds -join ', ')) }
    else { Write-Host 'Candidate stopped.' }
    exit 0
}
if ($Action -eq 'Stop') {
    # Stop router roots, then Python backends, then engines so nothing can respawn.
    $candidateStopOrder = @($candidateSnapshot | Where-Object { $candidateIds.Contains([int]$_.ProcessId) } |
        Sort-Object @{Expression = {
            if ($_.CommandLine -like ('*' + $candidateConfig + '*')) { 0 }
            elseif ($_.Name -in @('python.exe','pythonw.exe')) { 1 }
            else { 2 }
        }})
    foreach ($candidateProcess in $candidateStopOrder) { Stop-Process -Id $candidateProcess.ProcessId -Force -ErrorAction SilentlyContinue }
    foreach ($candidatePid in $candidateIds) { Wait-Process -Id $candidatePid -Timeout 20 -ErrorAction SilentlyContinue }
    if (@($candidateIds | ForEach-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue }).Count) {
        throw 'Some candidate processes did not exit.'
    }
    Write-Host 'Strata candidate stopped.'
    exit 0
}
if ($candidateIds.Count) { throw 'Candidate already running. Use Stop Strata Candidate.cmd first.' }
if (@($candidateSnapshot | Where-Object { $_.Name -match '^strata.*\.exe$' -and (Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue) }).Count) {
    throw 'Another Strata engine is running. Stop it before starting the candidate.'
}
foreach ($candidatePort in @(8080,8081)) {
    if (Get-NetTCPConnection -LocalPort $candidatePort -State Listen -ErrorAction SilentlyContinue) { throw "Port $candidatePort is already occupied." }
}
foreach ($candidatePath in @($candidateExe,$candidateConfig,$candidateRouter,$candidatePython)) {
    if (-not (Test-Path -LiteralPath $candidatePath)) { throw "Missing candidate file: $candidatePath" }
}
$candidateManifest = Get-Content -LiteralPath (Join-Path $candidateRoot 'manifest.json') -Raw | ConvertFrom-Json
if ((Get-FileHash -LiteralPath $candidateExe -Algorithm SHA256).Hash.ToLowerInvariant() -ne $candidateManifest.exe_sha256) {
    throw 'Candidate executable differs from the validated package.'
}
Write-Host 'Starting Strata candidate at http://127.0.0.1:8080. Keep this window open.'
Write-Host 'Select swift-1.5-iq2_xs-c4 in DSH for MTP overlap plus prefill yielding.'
Write-Host 'Other presets retain their existing engine configurations. Use Stop Strata Candidate.cmd to unload.'
# Match the benchmark's clean process environment; never alter user/system variables.
foreach ($candidateVariable in @(Get-ChildItem Env: | Where-Object { $_.Name -match '^(STRATA_|CUDA_|CUBLAS_)' })) {
    [Environment]::SetEnvironmentVariable($candidateVariable.Name, $null, 'Process')
}
Push-Location $candidateRepo
try { & $candidatePython -u $candidateRouter --config $candidateConfig; $candidateExit = $LASTEXITCODE }
finally { Pop-Location }
exit $candidateExit
