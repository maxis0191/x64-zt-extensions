param(
    [Parameter(Mandatory)][string]$ZoneFile,       # the compiled .ff under test (copied into the work folder, never linked)
    [Parameter(Mandatory)][string]$SourceCsv,      # zone_source/<zone>.csv the file was built from
    [Parameter(Mandatory)][string]$SourceTree,     # zonetool/<zone> source tree the file was built from
    [Parameter(Mandatory)][string]$Work,           # fresh private work folder, on the volume of the stock
    [Parameter(Mandatory)][string]$StockRoot,      # stock game files (hard-linked, read-only use)
    [Parameter(Mandatory)][string]$ZoneTool,       # zonetool.exe (IW7 mode)
    [Parameter(Mandatory)][string]$TlsDll,
    [Parameter(Mandatory)][string]$Sentinel,       # main/fileSysCheck.cfg source
    [Parameter(Mandatory)][string]$SchedulerCore,  # ops/Resource-Scheduler.Core.ps1 of the prepared inputs
    [string]$ZoneName = '',                        # name the loader knows the zone by (default: the file name)
    [string[]]$Types = @(),                        # limit the dump to these asset kinds (-dumpzonetypes)
    [string[]]$ToolArguments = @(),                # extra ZoneTool switches, placed before the dump switch
    [string]$Intent = '',
    [string]$Noise = '',
    [string]$Json = '',
    [string]$Python = 'python',
    [int]$TimeoutSec = 900,
    [ValidateRange(0, 14400)][int]$WaitForSlotSeconds = 0, # wait in the scheduler's queue this long for the lease
    [switch]$Strict
)
# Reads a compiled fastfile back through the game's own loader and compares what the loader holds with
# what the source asked for. ZoneTool hosts the code of iw7_ship.exe in its own process: no window, no
# renderer, no sound device. The work folder is private: stock files are hard links (ff-work-profile.json,
# no disk used, never written), executables and the file under test are copies. One Extract lease covers
# the run. The work folder stays afterwards: its dump tree is the evidence.
# Exit: 0 pass, 1 errors, 2 warnings unanswered under -Strict, 3 the loader did not finish, 4 refused.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Refuse([string]$why) { [Console]::Error.WriteLine("readback refused: $why"); exit 4 }

$Work = [IO.Path]::GetFullPath($Work)
foreach ($pair in @(@('ZoneFile', $ZoneFile), @('SourceCsv', $SourceCsv), @('ZoneTool', $ZoneTool), @('TlsDll', $TlsDll),
                    @('Sentinel', $Sentinel), @('SchedulerCore', $SchedulerCore))) {
    if (-not (Test-Path -LiteralPath $pair[1] -PathType Leaf)) { Refuse "-$($pair[0]) is not a file: $($pair[1])" }
}
foreach ($pair in @(@('SourceTree', $SourceTree), @('StockRoot', $StockRoot))) {
    if (-not (Test-Path -LiteralPath $pair[1] -PathType Container)) { Refuse "-$($pair[0]) is not a folder: $($pair[1])" }
}
if (Test-Path -LiteralPath $Work) { Refuse "the work folder must not exist yet: $Work" }
if (-not (Test-Path -LiteralPath (Split-Path $Work -Parent) -PathType Container)) { Refuse "the parent of the work folder must exist: $Work" }
$StockRoot = [IO.Path]::GetFullPath($StockRoot)
if ([IO.Path]::GetPathRoot($Work) -ne [IO.Path]::GetPathRoot($StockRoot)) { Refuse 'the work folder must be on the volume of the stock (hard links)' }
if (-not $ZoneName) { $ZoneName = [IO.Path]::GetFileNameWithoutExtension($ZoneFile) }
if ($ZoneName -notmatch '^[A-Za-z0-9_]+$') { Refuse "zone name not accepted: $ZoneName" }
$kinds = @($Types | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
foreach ($kind in $kinds) { if ($kind -notmatch '^[A-Za-z0-9_]+$') { Refuse "asset kind not accepted: $kind" } }
if ($TimeoutSec -lt 30) { Refuse '-TimeoutSec below 30' }

$profile = Get-Content -LiteralPath (Join-Path $PSScriptRoot '../t7-map/ff-work-profile.json') -Raw | ConvertFrom-Json
foreach ($i in $profile.inputs) {
    if ($i.role -eq 'stock' -and -not (Test-Path -LiteralPath (Join-Path $StockRoot $i.stock_name) -PathType Leaf)) {
        Refuse "the stock lacks $($i.stock_name)"
    }
    if ($i.relative -ieq "zone/$ZoneName.ff" -or $i.relative -ieq "main/$ZoneName.ff") {
        Refuse "$ZoneName is a stock zone of the work profile: the file under test would replace a stock link"
    }
}

. $SchedulerCore
# With -WaitForSlotSeconds the lease is asked again every 5 s while the scheduler answers with a refusal it counts as a
# wait (Test-IW7RetryableRefusal): a refused caller that asks again keeps its place in the waiting order. Measured
# 11 Nov 2026: without it a readback was refused in 1 s whenever any session ran, which on a shared machine is always.
$until = [datetime]::UtcNow.AddSeconds($WaitForSlotSeconds)
$lease = $null
while (-not $lease) {
    try {
        # The scheduler is not written for strict mode: under this script's Set-StrictMode, its queue path indexed an
        # empty list and threw 'Index was outside the bounds of the array.' (11 Nov 2026) instead of 'Resource busy'.
        $lease = & { Set-StrictMode -Off; Enter-IW7ResourceLease -Scope $Work -Kind Extract -PhysicalBytes 8GB -CommitBytes 11GB -Owner 'Compiled zone readback' }
    } catch {
        $message = $_.Exception.Message
        $retry = if (Get-Command Test-IW7RetryableRefusal -ErrorAction SilentlyContinue) { Test-IW7RetryableRefusal $message } else { $message -like 'Resource busy:*' }
        # the scheduler's state lock held by another caller for a moment (12 Nov 2026: a readback ended on it)
        if ($message -like 'Resource admission lock busy*') { $retry = $true }
        if (-not $retry -or [datetime]::UtcNow -ge $until) { Refuse "no lease: $message" }
        Start-Sleep -Seconds 5
    }
}

$outLog = Join-Path $Work 'readback.stdout.log'
$errLog = Join-Path $Work 'readback.stderr.log'
$state = 'not-started'
$seconds = 0
try {
    [IO.Directory]::CreateDirectory($Work) | Out-Null
    foreach ($i in $profile.inputs) {
        $dst = Join-Path $Work $i.relative
        [IO.Directory]::CreateDirectory((Split-Path $dst -Parent)) | Out-Null
        $src = switch ($i.role) { 'tlsdll' { $TlsDll } 'sentinel' { $Sentinel } default { Join-Path $StockRoot $i.stock_name } }
        if ($i.mode -eq 'HardLink') { New-Item -ItemType HardLink -Path $dst -Target $src | Out-Null }
        else { Copy-Item -LiteralPath $src -Destination $dst }
    }
    Copy-Item -LiteralPath $ZoneTool -Destination (Join-Path $Work 'zonetool.exe')
    Copy-Item -LiteralPath $ZoneFile -Destination (Join-Path $Work "zone/$ZoneName.ff")
    # files the builder wrote beside the fastfile under its name (sound banks .sabl / .sabs): the loader opens them too
    $base = [IO.Path]::GetFileNameWithoutExtension($ZoneFile)
    $companions = @(Get-ChildItem -LiteralPath (Split-Path ([IO.Path]::GetFullPath($ZoneFile)) -Parent) -File |
        Where-Object { $_.BaseName -ieq $base -and $_.Extension -ine '.ff' })
    foreach ($file in $companions) { Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $Work ("zone/$ZoneName" + $file.Extension.ToLowerInvariant())) }

    $arguments = @('-headless', '-unbuffered-io') + $ToolArguments
    if ($kinds.Count) { $arguments += @('-dumpzonetypes', $ZoneName, ($kinds -join ',')) } else { $arguments += @('-dumpzone', $ZoneName) }
    $watch = [Diagnostics.Stopwatch]::StartNew()
    $p = Start-Process -FilePath (Join-Path $Work 'zonetool.exe') -ArgumentList $arguments -WorkingDirectory $Work `
        -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru -NoNewWindow
    # the scheduler's busy state lock is a wait here too: an exception here went to the release while the loader still
    # ran, the lease stayed held and the loader was orphaned (12 Nov 2026)
    $addUntil = [datetime]::UtcNow.AddMinutes(2)
    while ($true) {
        try { & { Set-StrictMode -Off; Add-IW7ResourceProcess -Token $lease.Token -ProcessId $p.Id }; break }
        catch { if ($_.Exception.Message -notlike 'Resource admission lock busy*' -or [datetime]::UtcNow -ge $addUntil) { throw }; Start-Sleep -Seconds 2 }
    }
    $state = 'running'
    $read = 0L
    while (-not $p.WaitForExit(1000)) {
        # a fatal line means the loader stopped inside a dialog path: do not wait for the deadline
        $fatal = $false
        if (Test-Path -LiteralPath $outLog) {
            $stream = [IO.FileStream]::new($outLog, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite)
            try {
                if ($stream.Length -gt $read) {
                    $stream.Position = [Math]::Max(0, $read - 16)
                    $buffer = [byte[]]::new($stream.Length - $stream.Position)
                    [void]$stream.Read($buffer, 0, $buffer.Length)
                    $read = $stream.Length
                    $fatal = [Text.Encoding]::UTF8.GetString($buffer).Contains('[ FATAL ]')
                }
            } finally { $stream.Dispose() }
        }
        if ($fatal) { Start-Sleep -Milliseconds 500; if (-not $p.HasExited) { $p.Kill() }; [void]$p.WaitForExit(15000); $state = 'fatal'; break }
        if ($watch.Elapsed.TotalSeconds -ge $TimeoutSec) { $p.Kill(); [void]$p.WaitForExit(15000); $state = 'timeout'; break }
    }
    $seconds = [int]$watch.Elapsed.TotalSeconds
    if ($state -eq 'running') { $state = if ($p.ExitCode -eq 0) { 'finished' } else { "exit-$($p.ExitCode)" } }
} finally {
    # a failure above must not leave the loader running behind a released (or retained) lease
    $loader = Get-Variable -Name p -ValueOnly -ErrorAction SilentlyContinue
    if ($loader -and -not $loader.HasExited) { $loader.Kill(); [void]$loader.WaitForExit(15000) }
    $exitUntil = [datetime]::UtcNow.AddMinutes(2)
    while ($true) {
        try { & { Set-StrictMode -Off; Exit-IW7ResourceLease -Token $lease.Token }; break }
        catch { if ($_.Exception.Message -notlike 'Resource admission lock busy*' -or [datetime]::UtcNow -ge $exitUntil) { throw }; Start-Sleep -Seconds 2 }
    }
}

$dump = Join-Path $Work "dump/$ZoneName"
$dumpCsv = Join-Path $dump "$ZoneName.csv"
$dumped = (Test-Path -LiteralPath $dumpCsv -PathType Leaf) -and ((Get-Item -LiteralPath $dumpCsv).Length -gt 0)
Write-Output ("loader run: {0} in {1} s; dump list {2}; work folder {3}" -f $state, $seconds, $(if ($dumped) { 'written' } else { 'NOT written' }), $Work)
if ($state -ne 'finished' -or -not $dumped) {
    if (Test-Path -LiteralPath $outLog) { Get-Content -LiteralPath $outLog -Tail 6 | ForEach-Object { Write-Output "  log: $_" } }
    Write-Output 'the loader did not finish reading the file back: nothing is proven about what the compiled file holds'
    exit 3
}
$audit = @('-I', '-B', (Join-Path $PSScriptRoot 'iw7_zone_readback.py'), '--source-csv', $SourceCsv, '--source-tree', $SourceTree,
           '--dump', $dump, '--log', $outLog)
if ($kinds.Count) { $audit += @('--types', ($kinds -join ',')) }
if ($Intent) { $audit += @('--intent', $Intent) }
if ($Noise) { $audit += @('--noise', $Noise) }
if ($Json) { $audit += @('--json', $Json) }
if ($Strict) { $audit += '--strict' }
& $Python @audit
exit $LASTEXITCODE
