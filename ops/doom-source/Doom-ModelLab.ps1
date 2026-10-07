param(
    [Parameter(Mandatory)][string]$GameRoot,
    [Parameter(Mandatory)][string]$CandidateRoot,
    [Parameter(Mandatory)][string]$DoomBuildRun,
    [string]$PackageRoot,
    [ValidateRange(27100,27999)][int]$ServerPort=27116,
    [ValidateRange(27100,27999)][int]$ClientPort=27117,
    [switch]$Debugger,
    [switch]$Run
)
# Independent Doom rigid witness; without -Run this only validates a plan.
# The original cube lab and its fixed counts/hash/route remain unchanged.
# Reuse an existing complete test dedicated. No stock Prepare/copy, no Main deployment.
$ErrorActionPreference='Stop'
if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'Use PowerShell 7.' }

$ops=Split-Path $PSScriptRoot -Parent
$repo=Split-Path $ops -Parent
. "$ops/Base-Client.Core.ps1"
. "$ops/Resource-Scheduler.Core.ps1"
. "$ops/Lab-Lifecycle.ps1"
. "$ops/Agent-Scenario.Core.ps1"
. "$ops/Agent-LabCrash.Core.ps1"
. "$ops/Agent-LabEvidence.Core.ps1"

$ObservationMode='model';$DryRun=-not $Run
. "$PSScriptRoot/../model-lab/ModelFF.Core.ps1"
. "$PSScriptRoot/Writer.Core.ps1"
. "$PSScriptRoot/FF.Core.ps1"
. "$PSScriptRoot/Doom-Runtime.Core.ps1"
$model=Read-IW7DoomBuild $DoomBuildRun
$fixtureSource=Join-Path $PSScriptRoot 'doom_model_fixture.gsc';$fixtureName='agent_doom_model_fixture.gsc'
$armedMarker='[Paris Doom model] ARMED;'
$ScenarioPath=Join-Path $PSScriptRoot 'scenario.json'
if(!$PackageRoot){$PackageRoot=Join-Path $repo 'runtime/native-builds/3B9F-before-voice-watch-20261007-v2/package'}
$GameRoot=(Resolve-Path -LiteralPath $GameRoot).Path.TrimEnd('\','/')
$CandidateRoot=(Resolve-Path -LiteralPath $CandidateRoot).Path.TrimEnd('\','/')
$null=Resolve-IW7BasePath $GameRoot 'iw7-mod'
$null=Resolve-IW7BasePath $CandidateRoot 'iw7-mod'
if ($CandidateRoot -eq $GameRoot -or $CandidateRoot.StartsWith($GameRoot+'\',[StringComparison]::OrdinalIgnoreCase) -or
    $GameRoot.StartsWith($CandidateRoot+'\',[StringComparison]::OrdinalIgnoreCase) -or $ServerPort -eq $ClientPort) { throw 'Separate retained dedicated and distinct test ports required.' }
$marker=Resolve-IW7BasePath $CandidateRoot 'iw7-mod/paris-isolated-lab.marker'
if (!(Test-Path -LiteralPath $marker) -or [IO.File]::ReadAllText($marker) -cne 'iw7-paris-isolated-lab-v1' -or
    (Test-Path -LiteralPath (Join-Path $CandidateRoot 'STOCK-ASSETS-REMOVED.json')) -or
    !(Test-Path -LiteralPath (Join-Path $CandidateRoot 'iw7_ship.exe'))) { throw 'Retained complete marked dedicated required; no automatic stock restoration.' }
$packageExe=Join-Path $PackageRoot 'iw7-paris-voice.exe'
$manifest=Read-IW7DoomNativeArchive $PackageRoot $repo
$scenario=Read-IW7AgentScenario $ScenarioPath
Assert-IW7AgentObservationMode $scenario 'actions'
if ($model -and @($scenario.Steps | Where-Object action -CNotIn @('wait','capture')).Count) { throw 'Model witness accepts only wait/capture steps.' }
$catalog=Get-Content -LiteralPath (Join-Path $repo 'config/modules.json') -Raw | ConvertFrom-Json
$scripts=@(@($catalog.CoreScripts)+@($catalog.Modules | ForEach-Object Scripts) | Select-Object -Unique)
foreach ($script in $scripts) { if ($script -notmatch '^[a-zA-Z0-9_]+\.gsc$') { throw 'Invalid catalog path.' } }
. "$ops/Lab-RunPlan.ps1"
$budget=Get-IW7LabRunPlan -PlannedClients 1 -GraphicsProfile Reduced -Debugger:$Debugger
$name='iw7-paris-agent-lab.exe'
$baseExe=Resolve-IW7BasePath $GameRoot $name
$serverExe=Resolve-IW7BasePath $CandidateRoot $name
$plan=[ordered]@{Schema='iw7.doom-model-lab/1';GameRoot=$GameRoot;CandidateRoot=$CandidateRoot;BaseClientImage=$baseExe;ServerImage=$serverExe;
    ServerPort=$ServerPort;ClientPort=$ClientPort;PhysicalBytes=$budget.PhysicalBytes;CommitBytes=$budget.CommitBytes;NativeSHA256=$manifest.SHA256;
    ArchivedNativeSourceEvidence=$manifest.DoomSourceEvidence;Scenario=$scenario.Name;ScenarioSHA256=$scenario.SHA256;ObservationMode=$ObservationMode;FixtureSHA256=(Get-FileHash -LiteralPath $fixtureSource).Hash;Debugger=[bool]$Debugger;StockCopied=$false;MainDeployed=$false}



if ($model) { $plan.Model=[ordered]@{BuildRun=$model.RunRoot;ReaderSHA256=$model.ReaderSHA256;FFSHA256=$model.SHA256;FFBytes=$model.Bytes.Length;Ready=$false} }
if ($DryRun) { $plan | ConvertTo-Json -Depth 8;return }
Assert-IW7BaseVacant $GameRoot
foreach ($process in @(Get-CimInstance Win32_Process | Where-Object Name -Match '^iw7.*\.exe$')) {
    if (!$process.ExecutablePath -or $process.ExecutablePath.StartsWith($CandidateRoot+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Candidate process identity/ownership conflict; preserve it.' }
}
if (Get-NetUDPEndpoint -LocalPort $ServerPort,$ClientPort -ErrorAction SilentlyContinue) { throw 'Test ports occupied.' }
$stamp=[datetime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff')+'-'+[guid]::NewGuid().ToString('N').Substring(0,8)
$output=Join-Path $repo ('runtime/doom-model-lab/'+$stamp)
[IO.Directory]::CreateDirectory($output) | Out-Null
$lease=$null;$server=$null;$session=$null;$serverIdentity=$null;$baseTransaction=$null;$serverTransaction=$null
$passed=$false;$restored=$false;$startedClient=$false;$failure=$null;$startupCrash=$null;$crashCache=@{}

$modelHttp=$null;$modelBasePaths=@();$modelServerPaths=@()

try {
    # Complete scenario admission precedes the first staged byte or process.
    $lease=Enter-IW7ResourceLease -Scope $CandidateRoot -Kind Runtime -PhysicalBytes $budget.PhysicalBytes -CommitBytes $budget.CommitBytes -Owner $(if ($Debugger) {'Doom model dedicated + base client + diagnostics'} else {'Doom model dedicated + base client; debugger disabled'}) -BaseClientImage $baseExe
    $baseStage=[pscustomobject]@{GameRoot=$GameRoot;MutableFiles=@($name);ProfileDirectory='iw7-mod/players2';ProfileDirectories=@()}

    if ($model) {
        $modelBasePaths=@(Get-IW7DoomProfilePaths $GameRoot);$modelServerPaths=@(Get-IW7DoomProfilePaths $CandidateRoot)
        $baseStage.ProfileDirectories=$modelBasePaths
    }
    $baseTransaction=Save-IW7BaseTransaction $baseStage (Join-Path $output 'base-executable-backup')
    $serverFiles=@($name,'iw7-mod/server_spaceland.cfg','iw7-mod/server_modules.cfg','iw7-mod/server_private_access.cfg','iw7-mod/server_agent_test.cfg')+
        @($scripts | ForEach-Object {'iw7-mod/custom_scripts/cp/'+$_})+@('iw7-mod/custom_scripts/cp/'+$fixtureName)
    $serverStage=[pscustomobject]@{GameRoot=$CandidateRoot;MutableFiles=$serverFiles;ProfileDirectory='iw7-mod/players2';
        ProfileDirectories=@('iw7-mod/custom_scripts/cp','iw7-mod/lab-appdata','mods/paris_beta/bank')}

    if ($model) { $serverStage.ProfileDirectories+=@($modelServerPaths) }
    $serverTransaction=Save-IW7BaseTransaction $serverStage (Join-Path $output 'dedicated-backup')

    if ($model) {
        # Reuse the hash-verified transaction clear; only model paths admitted above.
        . "$ops/hud-lab/Hud-Runtime.Core.ps1"
        Clear-IW7HudProfiles $GameRoot $modelBasePaths $baseTransaction
        Clear-IW7HudProfiles $CandidateRoot $modelServerPaths $serverTransaction
        $ff=Resolve-IW7BasePath $CandidateRoot ($model.FsGame+'/mod.ff')
        [IO.Directory]::CreateDirectory((Split-Path $ff)) | Out-Null
        [IO.File]::WriteAllBytes($ff,$model.Bytes)
        if ((Get-FileHash -LiteralPath $ff).Hash -cne $model.SHA256) { throw 'Staged server model FF mismatch.' }
        if (!('IW7DoomHttp' -as [type])) { Add-Type -Path "$ops/doom-source/DoomHttp.cs" }
        $modelHttp=[IW7DoomHttp]::new($model.Bytes,$model.SHA256,(Join-Path $output 'doom-http.jsonl'),[IW7DoomHttp]::Route)
        Assert-IW7DoomHttpContract $modelHttp $model
    }
    $plan | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $output 'plan.local.json')
    Copy-Item -LiteralPath $packageExe -Destination $baseExe
    Copy-Item -LiteralPath $packageExe -Destination $serverExe
    foreach ($image in @($baseExe,$serverExe)) { if ((Get-FileHash -LiteralPath $image).Hash -ne $manifest.SHA256) { throw 'Staged native hash mismatch.' } }
    $cp=Resolve-IW7BasePath $CandidateRoot 'iw7-mod/custom_scripts/cp'
    [IO.Directory]::CreateDirectory($cp) | Out-Null
    # Previous test fixtures must not run alongside this observer. Their exact
    # bytes were saved; restore after the owned candidate closes.
    foreach ($file in Get-ChildItem -LiteralPath $cp -File) {
        if ($file.Extension -in @('.gsc','.gscbin')) { Remove-Item -LiteralPath $file.FullName }
    }
    foreach ($script in $scripts) { Copy-Item -LiteralPath (Join-Path $repo ('src/custom_scripts/cp/'+$script)) -Destination (Join-Path $cp $script) }
    Copy-Item -LiteralPath $fixtureSource -Destination (Join-Path $cp $fixtureName)
    foreach ($cfg in @('server_spaceland.cfg','server_modules.cfg')) { Copy-Item -LiteralPath (Join-Path $repo ('config/'+$cfg)) -Destination (Resolve-IW7BasePath $CandidateRoot ('iw7-mod/'+$cfg)) }
    [IO.File]::WriteAllText((Resolve-IW7BasePath $CandidateRoot 'iw7-mod/server_private_access.cfg'),'set g_password ""')
    [IO.Directory]::CreateDirectory((Resolve-IW7BasePath $CandidateRoot 'mods/paris_beta/bank')) | Out-Null
    $password=[guid]::NewGuid().ToString('N')
    $movementCase=switch ($scenario.Name) { 'agent-move-left' { 'left' }; 'agent-move-back' { 'back' }; default { 'forward' } }
    $config=@"
exec server_spaceland.cfg
exec server_modules.cfg
set net_ip 127.0.0.1
set g_password "$password"
set fs_game ""
set g_inactivity 0
set sv_cheats 0
set developer_script 1
set paris_isolated_lab 1
set paris_test_probe 1
set paris_agent_actions_probe 1
set paris_agent_combat_probe 0
set paris_model_probe 0
set paris_doom_model_probe 1
set paris_agent_observation "$ObservationMode"
set paris_agent_movement_case "$movementCase"
set paris_mod_voice 0
set paris_mod_doom 0
set paris_mod_rush 0
set paris_mod_loadout 0
set paris_join_loadout_test 0
set sv_mapRotation "gametype zombie map cp_zmb"
set sv_mapRotationCurrent ""
"@

    if ($model) { $config+="`nset fs_game `"$($model.FsGame)`"`nset sv_wwwBaseURL `"$($modelHttp.BaseUrl)`"`n" }
    [IO.File]::WriteAllText((Resolve-IW7BasePath $CandidateRoot 'iw7-mod/server_agent_test.cfg'),$config,[Text.UTF8Encoding]::new($false))
    if (!('IW7LabProcess' -as [type])) { Add-Type -Path "$ops/native/LabProcess.cs" }
    $serverLog=Join-Path $output 'server.stdout.log'
    $desktop='IW7ParisLab_'+[guid]::NewGuid().ToString('N')
    [ordered]@{Image=$serverExe;SHA256=$manifest.SHA256;DesktopName=$desktop;ServerPort=$ServerPort;PlannedUtc=[datetime]::UtcNow.ToString('o');LeaseToken=$lease.Token} |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $output 'server.launch.local.json')
    $dumpDirectory=Resolve-IW7BasePath $CandidateRoot 'minidumps'
    $dumpsBefore=@()
    if (Test-Path -LiteralPath $dumpDirectory) { $dumpsBefore=@(Get-ChildItem -LiteralPath $dumpDirectory -Filter '*.zip' -File | ForEach-Object FullName) }
    $debugArguments=if ($Debugger) { ' -paris-debugger' } else { '' }
    $args="-dedicated -allow_root_io -noupdate -nosteam -cpMode -stdout -paris-server-test -paris-isolated-lab$debugArguments +set net_ip 127.0.0.1 +set net_port $ServerPort +exec server_agent_test.cfg +map_rotate"
    $server=[IW7LabProcess]::StartOwned($serverExe,$args,$CandidateRoot,$serverLog,(Join-Path $output 'server.stderr.log'),$desktop)
    $p=Get-Process -Id $server.Id
    try { $serverIdentity=[pscustomobject]@{PID=$server.Id;Image=$serverExe;CreatedUtc=$p.StartTime.ToUniversalTime().ToString('o');SHA256=$manifest.SHA256;Stdout=$serverLog;DesktopName=$desktop} } finally {$p.Dispose()}
    $serverIdentity | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $output 'server.identity.local.json')
    Add-IW7ResourceProcess -Token $lease.Token -ProcessId $server.Id
    $deadline=[datetime]::UtcNow.AddSeconds(120)
    do {
        $startupCrash=Get-IW7AgentNewCrash -CandidateRoot $CandidateRoot -Identity $serverIdentity -Before $dumpsBefore -OutputRoot $output -Cache $crashCache
        if ($startupCrash) {
            $startupCrash | ConvertTo-Json -Depth 16 | Set-Content -LiteralPath (Join-Path $output 'startup-crash.local.json')
            throw 'Fresh candidate-native startup exception captured; correlate retained dump/dialog before recovery.'
        }
        if ($server.HasExited) { throw 'Candidate exited during startup; retain logs/symbols.' }
        $log=Read-IW7BaseLog $serverLog
        if ($log -match '(?i)script compile error|unknown function|MAX_CANONICAL_STRING|\[Paris (?:agent (?:effects|aim|combat)|Doom model)\] FAIL') { throw 'Candidate startup failed; retain diagnostics.' }
        if ($log.Contains($armedMarker)) { break }
        Start-Sleep -Milliseconds 500
    } while ([datetime]::UtcNow -lt $deadline)
    if (!$log.Contains($armedMarker)) { throw 'Candidate initialization timeout; missing UDP alone does not authorize termination.' }

    $clientPlan=New-IW7BaseClientPlan -GameRoot $GameRoot -ClientImage $baseExe -ServerPort $ServerPort -ClientPort $ClientPort -GraphicsProfile Reduced -Debugger:$Debugger

    $session=Start-IW7BaseClient -Plan $clientPlan -ServerIdentity $serverIdentity -LeaseToken $lease.Token -Password $password -OutputRoot (Join-Path $output 'base-client')
    $startedClient=$true
    $deadline=[datetime]::UtcNow.AddSeconds(180)
    do {

        if ($modelHttp -and $modelHttp.Error) { throw "Model delivery failed before playable protection: $($modelHttp.Error)" }
        $sample=Update-IW7BaseClient $session
        if ($sample.Protected) {break}
        Start-Sleep -Milliseconds 500
    } while ([datetime]::UtcNow -lt $deadline)
    if (!$session.Protected) { throw 'Protected playable client evidence absent.' }
    # Wait for the Doom fixture and fresh native safety before
    # dispatching the capture-only scenario.
    $deadline=[datetime]::UtcNow.AddSeconds(100)
    $nativeReady=$false
    $readyMarker='[Paris Doom model] READY_MODEL;'
    do {

        if ($modelHttp -and $modelHttp.Error) { throw "Model delivery failed before observer readiness: $($modelHttp.Error)" }
        $null=Update-IW7BaseClient $session;$log=Read-IW7BaseLog $serverLog
        if ($log -match '\[Paris (?:agent (?:effects|aim|combat)|Doom model)\] FAIL') { throw 'Observer failed before action dispatch; retain fresh evidence.' }
        $nativeSession=Read-IW7AgentWire (Resolve-IW7BasePath $GameRoot 'iw7-mod/paris-agent.session') -RequireTerminator
        if ($nativeSession -match ('^'+$session.Identity.PID+' ([a-f0-9]{32})$')) {
            $nonce=$Matches[1]
            $safety=Read-IW7AgentWire (Resolve-IW7BasePath $GameRoot 'iw7-mod/paris-agent.safety') -RequireTerminator
            if ($safety -match ('^'+$session.Identity.PID+' '+$nonce+' 1 (\d+) cp_zmb$')) {
                $age=[Environment]::TickCount64-[long]$Matches[1]
                $nativeReady=$age -ge 0 -and $age -le 500
            } else { $nativeReady=$false }
        }
        if ($nativeReady -and $log.Contains($readyMarker)) {break}
        Start-Sleep -Milliseconds 250
    } while ([datetime]::UtcNow -lt $deadline)
    if (!$nativeReady -or !$log.Contains($readyMarker)) { throw 'Settled player observer and fresh native input safety readiness absent.' }

    if ($model) { Wait-IW7DoomRuntimeEvidence $session $model $modelHttp $output }
    $null=Save-IW7AgentPreActionFrame $session $output
    $result=Invoke-IW7AgentScenario -Session $session -ScenarioPath $ScenarioPath
    $result | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $output 'scenario.result.json')
    $passed=[bool]$result.Passed
} catch {
    $failure=$_.Exception.Message
    # A failed start retains its original handle/context for exact recovery.
    if (!$session -and $_.Exception.Data.Contains('BaseClientContext')) { $session=$_.Exception.Data['BaseClientContext'] }
    throw
} finally {
    $cleanupError=$null
    try {

        # In-process HTTP must close before StopBaseClient restores its profile,
        # and before either outer transaction or resource reservation is released.

        if ($modelHttp) {
            $modelHttp.Dispose()
            if (!$modelHttp.Stopped) { throw 'Model HTTP worker remains active; preserve transactions and lease.' }
            [ordered]@{Stopped=$true;CompletedGets=$modelHttp.CompletedGets;Error=$modelHttp.Error;FFSHA256=$model.SHA256} |
                ConvertTo-Json | Set-Content -LiteralPath (Join-Path $output 'doom-http-closed.local.json')
        }
        if ($session) { Stop-IW7BaseClient $session }
        if ($server -and !$server.HasExited) {
            Assert-IW7BaseIdentity $serverIdentity
            if ($startupCrash -and $startupCrash.ConfirmedFatal -and !$startedClient -and !$session) {
                # Fatal recovery requires correlated exception/image/time and
                # exact-owned fatal dialog evidence. Missing UDP is not its trigger.
                Assert-IW7BaseVacant $GameRoot
                $games=@(Get-CimInstance Win32_Process | Where-Object Name -Match '^iw7.*\.exe$')
                foreach ($game in $games) {
                    if ($game.ProcessId -ne $server.Id -and (!$game.ExecutablePath -or $game.ExecutablePath.StartsWith($CandidateRoot+'\',[StringComparison]::OrdinalIgnoreCase))) { throw 'Fatal candidate ownership conflict; retain evidence.' }
                }
                if ((Read-IW7BaseLog $serverIdentity.Stdout) -match 'Setting client \d+ XUID') { throw 'Fatal recovery cannot exclude a prior player connection; preserve candidate.' }
                # Validate each bank backup before any termination/restoration.
                foreach ($entry in $serverTransaction.Files | Where-Object { $_.Existed -and $_.Path.StartsWith('mods/paris_beta/bank/') }) {
                    $backup=Resolve-IW7BasePath $serverTransaction.BackupRoot $entry.Path
                    if ((Get-FileHash -LiteralPath $backup).Hash -ne $entry.SHA256) { throw 'Fatal bank backup verification failed.' }
                }
                Assert-IW7BaseIdentity $serverIdentity
                $server.Terminate(3758096385)
                if (!$server.WaitForExit(5000)) { throw 'Exact fatal candidate closure unconfirmed.' }
                [ordered]@{FatalConfirmed=$true;PID=$server.Id;NativeSHA256=$serverIdentity.SHA256;Artifact=$startupCrash.Artifact;
                    BankBackupsVerified=$true;ClientStarted=$false;StoppedExactOwnedProcess=$true} |
                    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $output 'fatal-recovery.local.json')
            }
        }
        if ($server -and !$server.HasExited) {
            Assert-IW7BaseIdentity $serverIdentity
            # Ordinary server stop requires continuous real zero-client UDP.
            $emptySince=$null;$stopDeadline=[datetime]::UtcNow.AddSeconds(70)
            while (!$emptySince -or ([datetime]::UtcNow-$emptySince).TotalSeconds -lt 30) {
                if ([datetime]::UtcNow -gt $stopDeadline) { throw 'Candidate empty stop not established; retain process, reservation and backups.' }
                try { $info=& "$ops/Get-ServerInfo.ps1" -Port $ServerPort } catch { $emptySince=$null;throw 'UDP unavailable: preserve candidate for diagnosis.' }
                if ($info.clients -ne '0' -or $info.sv_running -ne '1' -or $info.mapname -ne 'cp_zmb') { throw 'Candidate may be occupied/unresponsive; preserve it.' }
                if (!$emptySince) { $emptySince=[datetime]::UtcNow }
                Start-Sleep -Milliseconds 1000
            }
            Assert-IW7BaseIdentity $serverIdentity
            $null=Invoke-IW7OwnedStop -Handle $server -TimeoutMs 10000 -StopAction {
                & python "$ops/Send-ServerCommand.py" --module-client $server.Id 'quit'
                if ($LASTEXITCODE) { throw 'Owned candidate quit request failed.' }
            }
        }
        if (!$server -or $server.HasExited) {
            Assert-IW7BaseVacant $GameRoot
            # The complete scope reservation is still held. Recheck live process
            # identities and test ports immediately before restoring candidate
            # configs/bank, including a dedicated that started after ours exited.
            Assert-IW7AgentCandidateVacant -CandidateRoot $CandidateRoot -Ports @($ServerPort,$ClientPort)
            if ($serverTransaction) { Restore-IW7BaseTransaction $serverTransaction }
            if ($baseTransaction) { Restore-IW7BaseTransaction $baseTransaction }
            $restored=$true
            if ($lease) { Exit-IW7ResourceLease -Token $lease.Token }
        }
    } catch { $cleanupError=$_.Exception.Message;Write-Warning "Doom model lab cleanup pending: $cleanupError" }
    if ($server) { $server.Dispose() }
    [ordered]@{Schema='iw7.doom-model-lab/1';Passed=$passed;Restored=$restored;Admitted=($null -ne $lease);Failure=$failure;CleanupError=$cleanupError;
        OutputRoot=$output;ServerPort=$ServerPort;ClientPort=$ClientPort;Debugger=[bool]$Debugger;StockCopied=$false;MainDeployed=$false;OwnerAcceptance=$false} |
        ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $output 'result.json')
    if ($cleanupError -and !$failure) { throw "Doom model lab restoration incomplete: $cleanupError" }
}
Write-Output "Doom model lab passed=$passed restored=$restored evidence=$output"
