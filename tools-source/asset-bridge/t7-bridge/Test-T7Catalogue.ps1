# Synthetic files, fake job owner/clock and real H1 cleanup. No native types or lease.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$core=Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1'
. $core
. (Join-Path $PSScriptRoot 'T7Prepatch.Profile.ps1')
. (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
. (Join-Path $PSScriptRoot 'T7ResidentExport.Profile.ps1')
$script:checks=0;$script:clock=0;$script:releaseDelay=0;$script:releaseFails=$false;$script:publicationLate=$false
function Check([bool]$Value,[string]$Why){if(!$Value){throw $Why};$script:checks++}
function Refuses([scriptblock]$Body,[string]$Pattern){
    $caught=$false
    try{& $Body}catch{$caught=$true;Check ($_.Exception.Message -match $Pattern) ('Unexpected error: '+$_.Exception.Message)}
    Check $caught ('Expected refusal: '+$Pattern)
}
function Get-H1Clock {$script:clock}
function Start-Sleep {param([int]$Milliseconds,[int]$Seconds);$script:clock+=$Milliseconds+1000*$Seconds}
function Get-IW7ResourceSnapshot {[pscustomobject]@{CommitLimit=100;Committed=10}}
function Register-H1Original($Lease,$Identity){$script:events.Add('register')}
function Exit-IW7ResourceLease($Token){$script:events.Add('release');$script:clock+=$script:releaseDelay;if($script:releaseFails){throw 'injected release failure'}}
function New-H1Owner {$script:fakeOwner}
function Get-T7CatalogueFileId($Path){'synthetic-id'}
$root=Join-Path ([IO.Path]::GetTempPath()) ('t7-catalogue-tests-'+[guid]::NewGuid().ToString('N'))
$work=Join-Path $root 'work';$evidence=Join-Path $root 'evidence'
[IO.Directory]::CreateDirectory($work)|Out-Null;[IO.Directory]::CreateDirectory($evidence)|Out-Null
$context=[pscustomobject]@{Guards=[Collections.Generic.List[object]]::new()}
$identity=[pscustomobject]@{PID=123;CreatedUtc='2026-10-12T00:00:00.0000000Z'}
function New-TestCatalogue([int]$Count=1) {
    $rows=@(for($i=0;$i -lt $Count;$i++) {
        [pscustomobject]@{name=('invented_test_{0:D4}' -f $i);reference=$false;resolved_nondefault=$true;
            counts=[pscustomobject]@{bones=1;roots=1;cosmetic_bones=0;lods=2}}
    })
    [pscustomobject]@{schema='iw7.t7-iw7-model-catalog/1';requested_zone='mp_freerun_04';
        provenance='observed_during_requested_zone_load';model_count=$Count;
        name_bytes=[int](($rows|ForEach-Object {$_.name.Length+1}|Measure-Object -Sum).Sum);models=$rows;
        truncated=$false;asset_zone_ownership_verified=$false;zonetool_xpak_helper_reads_allowed=$false;
        engine_io_verified=$false;geometry_verified=$false;runtime_verified=$false;ready=$false}
}
function Reset-Owner([int]$Exit=0,[bool]$Empty=$true) {
    $script:clock=0;$script:releaseDelay=0;$script:releaseFails=$false;$script:publicationLate=$false
    $script:events=[Collections.Generic.List[string]]::new()
    $script:fakeOwner=[pscustomobject]@{PID=123;Image=(Join-Path $work 'candidate.exe');CreationFileTime=[DateTime]::Parse($identity.CreatedUtc).ToFileTimeUtc();Closed=$false;ExitCode=$Exit;Empty=$Empty;StopFails=$false}
    $script:fakeOwner|Add-Member ScriptMethod Start {param($start,$hash,$out,$err);$script:events.Add('start')}
    $script:fakeOwner|Add-Member ScriptMethod TreeExited {$this.Empty}
    $script:fakeOwner|Add-Member ScriptMethod CloseConfirmed {if(!$this.Empty){throw 'job active'};$script:events.Add('close');$this.Closed=$true}
    $script:fakeOwner|Add-Member ScriptMethod StopAndConfirm {param($milliseconds);$script:events.Add('stop');if($this.StopFails){throw 'injected stop failure'};$this.Empty=$true;$this.Closed=$true;$this.ExitCode=-1}
    $script:ctx=[pscustomobject]@{Owner=$null;Closed=$true;Lease=[pscustomobject]@{Token='synthetic'};Guards=[Collections.Generic.List[object]]::new()}
    $script:state=[ordered]@{Stage='Catalogue';DeadlineSeconds=120;MaxObservedOutputBytes=0L;TreeClosureConfirmed=$false;LeaseReleased=$false;Quarantined=$false;Status='Running';LeaseToken='synthetic';TerminationRequested=$false;ExitCode=$null;Aliases=@();InputFileIds=@()}
}
try {
    Check ((Get-T7CatalogueOutcome $null 2) -ceq 'NoCatalogue') 'Absent catalogue differs.'
    Check ((Get-T7CatalogueOutcome (New-TestCatalogue 0) 0) -ceq 'EmptyCatalogue') 'Empty catalogue lost.'
    foreach($n in 1,1024){Check ((Get-T7CatalogueOutcome (New-TestCatalogue $n) 0) -ceq 'CatalogueWithNames') 'Valid bounded names lost.'}
    Check ((Get-T7CatalogueOutcome (New-TestCatalogue) 2) -ceq 'ValidCatalogueFromFailedProcess') 'Nonzero root upgraded.'
    $r=New-TestCatalogue;$r.requested_zone='zm_common'
    Check ((Get-T7CatalogueOutcome $r 0 'zm_common') -ceq 'CatalogueWithNames') 'Allowlisted Zombies catalogue lost.'
    Refuses {Get-T7CatalogueOutcome $r 0} 'request/provenance'
    $r.requested_zone='mp_freerun_04'
    Refuses {Get-T7CatalogueOutcome $r 0 'zm_common'} 'request/provenance'
    $r.requested_zone=@('zm_common')
    Refuses {Get-T7CatalogueOutcome $r 0 'zm_common'} 'request/provenance'
    foreach($name in @('unknown_zone','ZM_COMMON','zm_common.ff','../zm_common','zm_common/','zm_common ',"zm_common`n",$null,1)){
        Refuses {Get-T7CatalogueOutcome $null 0 $name} 'allowlisted'
    }
    Refuses {Get-T7CatalogueOutcome (New-TestCatalogue 1025) 0} 'count exceeds'
    foreach($field in 'truncated','asset_zone_ownership_verified','zonetool_xpak_helper_reads_allowed','engine_io_verified','geometry_verified','runtime_verified','ready') {
        $r=New-TestCatalogue;$r.$field=$true
        Refuses {Get-T7CatalogueOutcome $r 0} 'overclaims'
    }
    $r=New-TestCatalogue;$r.requested_zone='different_zone'
    Refuses {Get-T7CatalogueOutcome $r 0} 'request/provenance'
    $r=New-TestCatalogue;$r.name_bytes++
    Refuses {Get-T7CatalogueOutcome $r 0} 'byte count'
    $r=New-TestCatalogue;$r.model_count=$true
    Refuses {Get-T7CatalogueOutcome $r 0} 'count exceeds'
    $r=New-TestCatalogue;$r.models[0].counts.bones=1.5
    Refuses {Get-T7CatalogueOutcome $r 0} 'count width'
    $r=New-TestCatalogue;$r.models[0].counts.cosmetic_bones=65536
    Refuses {Get-T7CatalogueOutcome $r 0} 'count width'
    $r=New-TestCatalogue;$r.models[0].name="ascii`n"
    Refuses {Get-T7CatalogueOutcome $r 0} 'bounded ASCII'
    $r=New-TestCatalogue 2;$r.models[1].name=$r.models[0].name
    Refuses {Get-T7CatalogueOutcome $r 0} 'sorted and unique'
    $r=New-TestCatalogue;$r.models[0].resolved_nondefault=$false
    Refuses {Get-T7CatalogueOutcome $r 0} 'Unresolved'
    $r.models[0].counts=$null
    Check ((Get-T7CatalogueOutcome $r 0) -ceq 'CatalogueWithNames') 'Unresolved name lost.'
    $r.models[0].name=',reference';$r.models[0].reference=$true;$r.name_bytes=11
    Check ((Get-T7CatalogueOutcome $r 0) -ceq 'CatalogueWithNames') 'Reference observation lost.'
    $r.models[0].resolved_nondefault=$true
    Refuses {Get-T7CatalogueOutcome $r 0} 'Reference alias'
    $r=New-TestCatalogue;$r|Add-Member NoteProperty unexpected 1
    Refuses {Get-T7CatalogueOutcome $r 0} 'Exact catalogue fields'

    $plan=[pscustomobject]@{WorkingDirectory=$work;Image=(Join-Path $work 'candidate.exe');StageRoot=$evidence;RunRoot=$root;
        OutputLimitBytes=64MB;MetadataReserveBytes=64KB;LogLimitBytes=1MB;OutputKey='catalog-output';InputMetadata=@();Bindings=@();PreservedMain=$identity}
    $outDir=Join-Path $work $plan.OutputKey;[IO.Directory]::CreateDirectory($outDir)|Out-Null
    $path=Join-Path $outDir 'catalog.json'
    [IO.File]::WriteAllText($path,((New-TestCatalogue)|ConvertTo-Json -Depth 8))
    $s=[ordered]@{ExitCode=0;CatalogueOutcome='NoCatalogue'}
    Check ((Read-T7CatalogueReport $plan $s $context) -ceq 'CatalogueWithNames' -and $context.Guards.Count -eq 1) 'Guarded report failed.'
    Refuses {[IO.File]::AppendAllText($path,'x')} '.'
    foreach($g in $context.Guards){$g.Dispose()};$context.Guards.Clear()
    $plan|Add-Member NoteProperty Zone ([pscustomobject]@{Path=(Join-Path $root 'zm_common.ff')})
    $r=New-TestCatalogue;$r.requested_zone='zm_common'
    [IO.File]::WriteAllText($path,($r|ConvertTo-Json -Depth 8))
    Check ((Read-T7CatalogueReport $plan $s $context) -ceq 'CatalogueWithNames') 'Report reader ignored selected Zombies zone.'
    foreach($g in $context.Guards){$g.Dispose()};$context.Guards.Clear()
    [IO.File]::WriteAllText($path,((New-TestCatalogue)|ConvertTo-Json -Depth 8))
    Refuses {Read-T7CatalogueReport $plan $s $context} 'request/provenance'
    foreach($g in $context.Guards){$g.Dispose()};$context.Guards.Clear()
    $plan.PSObject.Properties.Remove('Zone')
    [IO.File]::WriteAllBytes($path,[byte[]]::new(512KB+1))
    Refuses {Read-T7CatalogueReport $plan $s $context} 'JSON size'
    Remove-Item -LiteralPath $path
    Remove-Item -LiteralPath $outDir

    # One synthetic 16 MiB FF; never read owner stock in tests.
    $fakeFF=Join-Path $root 'mp_freerun_04.ff'
    $file=[IO.FileStream]::new($fakeFF,'CreateNew','Write','Read');try{$file.SetLength(16977344)}finally{$file.Dispose()}
    $item=Get-Item -LiteralPath $fakeFF
    $zone=[pscustomobject]@{Path=$fakeFF;Bytes=$item.Length;Attributes=[string]$item.Attributes;LastWriteUtc=$item.LastWriteTimeUtc.ToString('o')}
    $z=Open-T7CatalogueZone $zone $context
    Check ($z.SHA256 -cmatch '^[0-9a-f]{64}$' -and $z.HashProvenance -ceq 'ObservedUnderLeaseNotDepotVerified') 'Observed hash falsely presealed.'
    Refuses {[IO.File]::AppendAllText($fakeFF,'x')} '.'
    $aliasPath=Join-Path $work 'synthetic-link.ff'
    $alias=New-T7CatalogueAlias $z $aliasPath $context
    Check ($alias.FileId -ceq $z.FileId) 'Alias identity not retained.'
    $guard=Open-H1Pin $z;$guard.Dispose();$checks++
    foreach($g in $context.Guards){$g.Dispose()};$context.Guards.Clear()
    Remove-Item -LiteralPath $aliasPath
    $zone.LastWriteUtc='2000-01-01T00:00:00.0000000Z'
    Refuses {Open-T7CatalogueZone $zone $context} 'metadata changed'
    Remove-Item -LiteralPath $fakeFF

    $build=[pscustomobject]@{Schema='iw7.t7-minimal-build/1';PlanSHA256='daa7097f872b83a5762b2cb56bf6dd5a235ed2beee8e0ff077276c61622d53fa';Status='Passed';InputsReverified=$true;TreeClosureConfirmed=$true;LeaseReleased=$true;Quarantined=$false;CandidateExecuted=$false;
        Stages=@([pscustomobject]@{Artifacts=@([pscustomobject]@{Path='candidate';Bytes=100;SHA256=('a'*64)})})}
    $bp=[pscustomobject]@{ExpectedBuildPlanSHA256=$build.PlanSHA256;CandidateSource='candidate';CandidateBytes=100;CandidateSHA256=('a'*64)}
    Assert-T7CatalogueBuild $bp $build;$checks++
    $build|Add-Member NoteProperty BuildProfile ([pscustomobject]@{Name='t7-prepatch-probe'})
    Refuses {Assert-T7CatalogueBuild $bp $build} 'ordinary D2'
    $build.PSObject.Properties.Remove('BuildProfile');$bp.CandidateSHA256='b'*64
    Refuses {Assert-T7CatalogueBuild $bp $build} 'artifact'
    $start=New-T7CatalogueStart $plan
    Check (($start.ArgumentList -join '|') -ceq '-t7-iw7-catalog|mp_freerun_04' -and !$start.UseShellExecute -and $start.CreateNoWindow) 'Fixed catalogue command changed.'
    Check ($start.Environment['LOCALAPPDATA'].StartsWith((Join-Path $root 'temp'))) 'Private environment changed.'
    $plan|Add-Member NoteProperty Zone ([pscustomobject]@{Path=(Join-Path $root 'zm_common.ff')})
    $start=New-T7CatalogueStart $plan
    Check (($start.ArgumentList -join '|') -ceq '-t7-iw7-catalog|zm_common') 'Selected Zombies catalogue command differs.'
    $zoneDir=Join-Path $work 'zone';[IO.Directory]::CreateDirectory($zoneDir)|Out-Null
    $zoneAlias=Join-Path $zoneDir 'zm_common.ff';[IO.File]::WriteAllText($zoneAlias,'authored synthetic zone name only')
    Assert-T7CatalogueEngineOutputs $plan;$checks++
    $wrongAlias=Join-Path $zoneDir 'mp_freerun_04.ff';[IO.File]::WriteAllText($wrongAlias,'authored wrong zone name only')
    Refuses {Assert-T7CatalogueEngineOutputs $plan} 'Unexpected zone'
    Remove-Item -LiteralPath $wrongAlias;Remove-Item -LiteralPath $zoneAlias;Remove-Item -LiteralPath $zoneDir
    $plan.PSObject.Properties.Remove('Zone')

    $appid=Join-Path $work 'steam_appid.txt'
    [IO.File]::WriteAllText($appid,'')
    Assert-T7CatalogueEngineOutputs $plan;$checks++
    Refuses {Assert-T7CatalogueEngineOutputs $plan -Closed -Context $context} 'length differs'
    [IO.File]::WriteAllText($appid,'311210')
    foreach($dir in 'identities/dedicatedpc/dumps','identities/dedicatedpc/LPC'){[IO.Directory]::CreateDirectory((Join-Path $work $dir))|Out-Null}
    Assert-T7CatalogueEngineOutputs $plan -Closed -Context $context;$checks++
    Refuses {[IO.File]::WriteAllText($appid,'999999')} '.'
    foreach($g in $context.Guards){$g.Dispose()};$context.Guards.Clear()
    [IO.File]::WriteAllText($appid,'999999')
    Assert-T7CatalogueEngineOutputs $plan;$checks++
    Refuses {Assert-T7CatalogueEngineOutputs $plan -Closed -Context $context} 'hash/length differs'
    [IO.File]::WriteAllText($appid,"311210`n")
    Refuses {Assert-T7CatalogueEngineOutputs $plan} 'type/size'
    Remove-Item -LiteralPath $appid
    [IO.Directory]::CreateDirectory($appid)|Out-Null
    Refuses {Assert-T7CatalogueEngineOutputs $plan} 'type/size'
    Remove-Item -LiteralPath $appid
    $keyPath=Join-Path $work 'identities/dedicatedpc/synthetic-private-key'
    $key=[IO.FileStream]::new($keyPath,'CreateNew','Write','None')
    try {Refuses {Assert-T7CatalogueEngineOutputs $plan} 'Unexpected identity entry'}finally{$key.Dispose()}
    Remove-Item -LiteralPath $keyPath
    $unexpected=Join-Path $work 'identities/dedicatedpc/other'
    [IO.Directory]::CreateDirectory($unexpected)|Out-Null
    Refuses {Assert-T7CatalogueEngineOutputs $plan} 'Unexpected identity entry'
    Remove-Item -LiteralPath $unexpected
    foreach($dir in 'identities/dedicatedpc/dumps','identities/dedicatedpc/LPC','identities/dedicatedpc','identities'){Remove-Item -LiteralPath (Join-Path $work $dir)}

    Enable-T7CatalogueRuntimeProfile $plan
    $budgetState=[ordered]@{MaxObservedOutputBytes=0L}
    [IO.File]::WriteAllText((Join-Path $work 'unexpected.ff'),'synthetic')
    Refuses {Test-H1Budget $plan $budgetState} 'Unexpected engine output'
    Remove-Item -LiteralPath (Join-Path $work 'unexpected.ff')
    [IO.Directory]::CreateDirectory((Join-Path $work 'zone'))|Out-Null
    [IO.File]::WriteAllText((Join-Path $work 'zone/guessed_bootstrap.ff'),'synthetic')
    Refuses {Test-H1Budget $plan $budgetState} 'Unexpected zone/catalogue'
    Remove-Item -LiteralPath (Join-Path $work 'zone/guessed_bootstrap.ff')
    Remove-Item -LiteralPath (Join-Path $work 'zone')
    $log=Join-Path $evidence 'stdout.log'
    $f=[IO.FileStream]::new($log,'CreateNew','Write','Read');try{$f.SetLength(1MB+1)}finally{$f.Dispose()}
    Refuses {Test-H1Budget $plan $budgetState} 'log cap'
    Remove-Item -LiteralPath $log
    for($i=0;$i -lt 65;$i++){[IO.File]::WriteAllText((Join-Path $evidence ('entry-'+$i)),'')}
    Refuses {Test-H1Budget $plan $budgetState} 'entry count'
    for($i=0;$i -lt 65;$i++){Remove-Item -LiteralPath (Join-Path $evidence ('entry-'+$i))}
    . $core
    function Get-H1Clock {$script:clock}
    function New-H1Owner {$script:fakeOwner}
    function Register-H1Original($Lease,$Identity){$script:events.Add('register')}

    # Exercise fixed-plan rejection without game files, hashes or native types.
    & {
        $fakeRepo=Join-Path $root 'repo';$runRoot=Join-Path $fakeRepo 'runtime/t7-catalog-test'
        foreach($dir in 'work','evidence','temp'){[IO.Directory]::CreateDirectory((Join-Path $runRoot $dir))|Out-Null}
        $bindings=@(
            [pscustomobject]@{Path=(Join-Path $root 'd2.exe');Bytes=21740032;SHA256='94dd29a9cb538504ddeb3545483e43a5dfea195aaca155db5bf147f1c6334c15';IsText=$false},
            [pscustomobject]@{Path=(Join-Path $root 'dedicated.exe');Bytes=21737352;SHA256='3df511d71e3690b14517379783bbfb713f6fe2ed2f2e73b445b4878216686156';IsText=$false},
            [pscustomobject]@{Path=(Join-Path $root 'steam_api64.dll');Bytes=235600;SHA256='71af8666392acad2080a816b9f1196fe9ccb950e1db8a549f8312c4d231f55a8';IsText=$false})
        $ff=[pscustomobject]@{Path=(Join-Path $root 'mp_freerun_04.ff');Bytes=16977344;SHA256=$null;RelativePath='zone/mp_freerun_04.ff';HashProvenance='ObserveUnderLease';Attributes='Archive';LastWriteUtc='2026-10-12T00:00:00.0000000Z'}
        $metadata=@($bindings|ForEach-Object {[pscustomobject]@{Path=$_.Path;Bytes=$_.Bytes;Attributes='Archive';LastWriteUtc=$ff.LastWriteUtc}})+@($ff)
        function Get-Item($LiteralPath){$m=@($metadata|Where-Object Path -CEQ $LiteralPath)[0];[pscustomobject]@{PSIsContainer=$false;Length=$m.Bytes;Attributes='Archive';LastWriteTimeUtc=([datetimeoffset]$m.LastWriteUtc).UtcDateTime}}
        $fixed=[pscustomobject]@{Schema='iw7.t7-catalogue-plan/1';EngineOutputProfile='ObservedStartupA';Runner='synthetic-runner';PhysicalBytes=6GB;CommitBytes=8GB;GroupDeadlineSeconds=200;DeadlineSeconds=120;MutableOutputLimitBytes=64MB;MetadataReserveBytes=64KB;CleanupSeconds=5;ReportLimitBytes=512KB;LogLimitBytes=1MB;OutputLimitBytes=127799192;RetryAuthorized=$false;
            RunRoot=$runRoot;WorkingDirectory=(Join-Path $runRoot 'work');StageRoot=(Join-Path $runRoot 'evidence');Image=(Join-Path $runRoot 'work/t7-zonetool-candidate.exe');Arguments=@('-t7-iw7-catalog','mp_freerun_04');OutputKey='t7_iw7_catalog_1d7749fdf2454720fad852816e9ddde027a157a4cc486aa18b3eb8fd4a25c2ce';Bindings=$bindings;InputMetadata=$metadata;Zone=$ff;CandidateSource=$bindings[0].Path;CandidateBytes=$bindings[0].Bytes;CandidateSHA256=$bindings[0].SHA256;EngineSource=$bindings[1].Path;SteamSource=$bindings[2].Path}
        Assert-T7CataloguePlan $fixed $fakeRepo 'synthetic-runner';$script:checks++
        $fixed.Arguments+=@('+set')
        Refuses {Assert-T7CataloguePlan $fixed $fakeRepo 'synthetic-runner'} 'Exact catalogue command'
        $fixed.Arguments=@('-t7-iw7-catalog','mp_freerun_04');$fixed.Zone.SHA256='f'*64
        Refuses {Assert-T7CataloguePlan $fixed $fakeRepo 'synthetic-runner'} 'explicit unsealed'
        $fixed.Zone.SHA256=$null;$fixed.RetryAuthorized=$true
        Refuses {Assert-T7CataloguePlan $fixed $fakeRepo 'synthetic-runner'} 'Fixed catalogue plan'
        $fixed.RetryAuthorized=$false
        $fixed|Add-Member NoteProperty CandidateProfile 'unknown'
        Refuses {Assert-T7CataloguePlan $fixed $fakeRepo 'synthetic-runner'} 'Unknown catalogue'
        $fixed.CandidateProfile='ordinary-d2';$fixed.CandidateSHA256='0'*64
        Refuses {Assert-T7CataloguePlan $fixed $fakeRepo 'synthetic-runner'} 'Ordinary D2'
        $fixed.CandidateSHA256=$bindings[0].SHA256
        $fixed.CandidateProfile='t7-catalog-exit-context'
        $fixed|Add-Member NoteProperty TraceStderrLimitBytes 4096
        Assert-T7CataloguePlan $fixed $fakeRepo 'synthetic-runner';$script:checks++
        $fixed.TraceStderrLimitBytes=1536
        Refuses {Assert-T7CataloguePlan $fixed $fakeRepo 'synthetic-runner'} 'Exact trace stderr'
        $fixed.TraceStderrLimitBytes='4096'
        Refuses {Assert-T7CataloguePlan $fixed $fakeRepo 'synthetic-runner'} 'Exact trace stderr'
        $fixed.CandidateProfile='t7-catalog-callers';$fixed.TraceStderrLimitBytes=8192
        Assert-T7CataloguePlan $fixed $fakeRepo 'synthetic-runner';$script:checks++
        foreach($limit in @(4096,8193,'8192')) {
            $fixed.TraceStderrLimitBytes=$limit
            Refuses {Assert-T7CataloguePlan $fixed $fakeRepo 'synthetic-runner'} 'Exact trace stderr'
        }
        $fixed.CandidateProfile='t7-catalog-message';$fixed.TraceStderrLimitBytes=8192
        Assert-T7CataloguePlan $fixed $fakeRepo 'synthetic-runner';$script:checks++
        foreach($limit in @(4096,8193,'8192')) {
            $fixed.TraceStderrLimitBytes=$limit
            Refuses {Assert-T7CataloguePlan $fixed $fakeRepo 'synthetic-runner'} 'Exact trace stderr'
        }
        $fixed.PSObject.Properties.Remove('TraceStderrLimitBytes');$fixed.CandidateProfile='ordinary-d2'
        [IO.File]::WriteAllText((Join-Path $runRoot 'attempt.json'),'{}')
        Refuses {Assert-T7CataloguePlan $fixed $fakeRepo 'synthetic-runner'} 'Fresh attempt'
    }

    Reset-Owner
    Invoke-H1OwnedStage $plan $state $ctx $start ('a'*64) $evidence
    Complete-H1Stage $ctx $state
    Check (($events -join ',') -ceq 'start,register,close,release') 'Normal owner lifecycle differs.'
    Reset-Owner 2
    Refuses {Invoke-H1OwnedStage $plan $state $ctx $start ('a'*64) $evidence} 'Original stage process failed'
    Complete-H1Stage $ctx $state
    Check ($state.ExitCode -eq 2 -and $state.LeaseReleased -and !$events.Contains('stop')) 'Bootstrap failure lost or forcibly stopped.'
    Reset-Owner 0 $false;$state.DeadlineSeconds=0
    Refuses {Invoke-H1OwnedStage $plan $state $ctx $start ('a'*64) $evidence} 'deadline'
    Check (!$events.Contains('start')) 'Expired job started.'
    Reset-Owner 0 $false;$ctx.Owner=$fakeOwner;$ctx.Closed=$false;$fakeOwner.StopFails=$true
    Complete-H1Stage $ctx $state
    Check ($state.Quarantined -and $ctx.Lease -and !$ctx.Closed) 'Unclosed job lost owner/lease.'
    [AppDomain]::CurrentDomain.SetData('IW7.H1.Quarantine.synthetic',$null)

    $tokens=$null;$errors=$null
    $ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Run-T7Catalogue.ps1'),[ref]$tokens,[ref]$errors)
    Check ($errors.Count -eq 0) 'Runner parse failed.'
    $outer=@($ast.EndBlock.Statements|Where-Object {$_ -is [Management.Automation.Language.TryStatementAst]})[0]
    $text=$outer.Finally.Extent.Text;$finalizer=[scriptblock]::Create($text.Substring(1,$text.Length-2));$export=$false;$parts=$false;$provenance=$false;$registration=$false
    function Read-T7CatalogueReport($Plan,$State,$Context){$script:reportReads++;if($mode -cin @('trace-only','context-only','context-partial','callers-only','callers-partial','message-only','message-prefix','message-partial')){'NoCatalogue'}else{'EmptyCatalogue'}}
    function Read-T7CatalogueTrace($Plan,$State,$Context){
        if((Get-T7CatalogueCandidateProfile $Plan) -ceq 'ordinary-d2'){return}
        $script:traceReads++
        $State.TraceOutcome=if($mode -ceq 'trace-missing'){'NoTrace'}else{'TraceObserved'}
        if($mode.StartsWith('context-')){$State.ExitContextOutcome=if($mode -ceq 'context-partial'){'Partial'}else{'Observed'}}
        if($mode.StartsWith('callers-')){$State.ExitContextOutcome='Observed';$State.CallersOutcome=if($mode -ceq 'callers-partial'){'Partial'}else{'Observed'}}
        if($mode.StartsWith('message-')){$State.ExitContextOutcome='Observed';$State.CallersOutcome='Observed';$State.MessageOutcome=switch($mode){'message-prefix'{'Prefix'};'message-partial'{'Partial'};default{'Observed'}}}
        if($mode -ceq 'trace-malformed'){$State.TraceOutcome='TracePresentUnqualified';throw 'injected malformed trace'}
    }
    function Assert-T7PrepatchMain($Expected){$script:mainChecks++;if($mode -cin @('main-changed','parts-main-changed','prov-main-changed','reg-main-changed')){throw 'injected Main state change'};[pscustomobject]@{GenerationAndUDP27016OwnerUnchanged=$true}}
    function Open-H1Pin($Pin){$script:pinReads++;[IO.MemoryStream]::new()}
    foreach($mode in 'normal','release-late','publication-late','release-failed','forced','unclosed','trace-valid','trace-only','trace-missing','trace-malformed','trace-forced','main-changed','context-only','context-partial','context-forced','callers-only','callers-partial','callers-forced','message-only','message-prefix','message-partial','message-forced') {
        Reset-Owner;$context=$ctx;$context.Owner=$fakeOwner;$context.Closed=$true
        $guards=$context.Guards;$attempted=$true;$failure=$null;$zonePin=[pscustomobject]@{Path='synthetic'}
        $state.InputsReverified=$false;$state.CatalogueOutcome='NoCatalogue';$state.Identity=$identity;$state.ExitCode=0
        Enable-T7CatalogueRuntimeProfile $plan
        $script:reportReads=0;$script:pinReads=0;$script:traceReads=0;$script:mainChecks=0
        $plan|Add-Member NoteProperty CandidateProfile $(if($mode.StartsWith('trace-')){'t7-catalog-trace'}elseif($mode.StartsWith('context-')){'t7-catalog-exit-context'}elseif($mode.StartsWith('callers-')){'t7-catalog-callers'}elseif($mode.StartsWith('message-')){'t7-catalog-message'}else{'ordinary-d2'}) -Force
        if($mode -ceq 'release-late'){$script:clock=199999;$script:releaseDelay=2}
        if($mode -ceq 'publication-late'){$script:clock=199999;$script:publicationLate=$true}
        if($mode -ceq 'release-failed'){$script:releaseFails=$true}
        if($mode -cin @('forced','unclosed','trace-forced','context-forced','callers-forced','message-forced')){$context.Closed=$false;$failure='injected runtime failure';$state.Status='Failed';$fakeOwner.StopFails=$mode -ceq 'unclosed'}
        function Write-H1Receipt($Plan,$State,$StageRoot){if($script:publicationLate){$script:clock+=2;$script:publicationLate=$false};[IO.File]::WriteAllText((Join-Path $StageRoot 'receipt.json'),($State|ConvertTo-Json -Depth 8))}
        . $finalizer
        $saved=Get-Content -Raw -LiteralPath (Join-Path $evidence 'receipt.json')|ConvertFrom-Json
        if($mode -cin @('normal','trace-valid')){Check ($saved.Status -ceq 'CatalogueObservedPendingDonorReview' -and $saved.CatalogueOutcome -ceq 'EmptyCatalogue') 'Empty observation lost.'}
        elseif($mode -cin @('trace-only','trace-missing','trace-malformed','context-only','context-partial','callers-only','callers-partial','message-only','message-prefix','message-partial')){Check ($saved.Status -ceq 'Failed' -and $state.InputsReverified -and $state.LeaseReleased -and $reportReads -eq 1) 'Trace upgraded failure or prevented independent catalogue/input checks.'}
        elseif($mode -ceq 'main-changed'){Check ($saved.Status -ceq 'Failed' -and $state.InputsReverified -and $state.LeaseReleased -and $saved.MainAfterError -ceq 'injected Main state change') 'Main state change accepted.'}
        elseif($mode -cin @('release-late','publication-late')){Check ($saved.Status -ceq 'Failed' -and $state.LeaseReleased -and $null -ne $failure) 'Late success survived.'}
        elseif($mode -cin @('forced','trace-forced','context-forced','callers-forced','message-forced')){Check ($state.TerminationRequested -and $state.LeaseReleased -and $pinReads -eq 0 -and $reportReads -eq 1 -and $saved.Status -ceq 'Failed') 'Forced closure rehashed stock or succeeded.'}
        else{Check ($state.Quarantined -and $context.Lease) 'Uncertain closure/release lost lease.'}
        if($mode -ceq 'unclosed'){Check ($reportReads -eq 0 -and $pinReads -eq 0) 'Unclosed job report inspected.'}
        if($mode.StartsWith('trace-') -or $mode.StartsWith('context-') -or $mode.StartsWith('callers-') -or $mode.StartsWith('message-')){Check ($traceReads -eq 1) 'Trace was not inspected exactly once after closure.'}
        Check ($mainChecks -eq $(if($mode -ceq 'unclosed'){0}else{1})) 'Main postflight must run exactly once only after closure.'
        [AppDomain]::CurrentDomain.SetData('IW7.H1.Quarantine.synthetic',$null)
        Remove-Item -LiteralPath (Join-Path $evidence 'receipt.json')
        if(Test-Path -LiteralPath (Join-Path $evidence 'receipt.deadline-exceeded.json')){Remove-Item -LiteralPath (Join-Path $evidence 'receipt.deadline-exceeded.json')}
        . $core
        function Get-H1Clock {$script:clock}
        function Open-H1Pin($Pin){$script:pinReads++;[IO.MemoryStream]::new()}
    }
    # Exercise the same runner finally AST through selective-export outcomes.
    # Export payload inspection must occur once under admission, or never after forced closure.
    # Match the real export entry's profile import; use its actual finite selector.
    Check ($null -eq (Get-T7SelectedStreamedExport $plan)) 'Resident fixture selected streamed export.'
    function Read-T7ResidentExportReport($Plan,$State,$Context){
        if(!$Context.Closed -or !$Context.Lease){throw 'Export read escaped original admission.'}
        $script:exportReads++
        switch($mode){'export-missing'{'NoExport'};'export-nonzero'{'ValidExportFromFailedProcess'};default{'ExportFilesObserved'}}
    }
    $export=$true
    foreach($mode in @('export-normal','export-missing','export-nonzero','export-forced','export-unclosed','export-release-failed')){
        Reset-Owner;$context=$ctx;$context.Owner=$fakeOwner;$context.Closed=$true
        $guards=$context.Guards;$attempted=$true;$failure=$null;$zonePin=[pscustomobject]@{Path='synthetic'}
        $state.InputsReverified=$false;$state.ExportOutcome='NoExport';$state.Identity=$identity;$state.ExitCode=0
        $state.TraceOutcome='DisabledForResidentExportCLI';$state.EngineOutputsValidated=$false
        $script:exportReads=0;$script:traceReads=0;$script:reportReads=0;$script:pinReads=0;$script:mainChecks=0
        Enable-T7CatalogueRuntimeProfile $plan
        if($mode -ceq 'export-nonzero'){$state.ExitCode=1;$failure='original nonzero exit';$state.Status='Failed'}
        if($mode -ceq 'export-release-failed'){$script:releaseFails=$true}
        if($mode -cin @('export-forced','export-unclosed')){
            $context.Closed=$false;$failure='injected runtime failure';$state.Status='Failed';$fakeOwner.StopFails=$mode -ceq 'export-unclosed'
        }
        . $finalizer
        $saved=Get-Content -Raw -LiteralPath (Join-Path $evidence 'receipt.json')|ConvertFrom-Json
        Check ($traceReads -eq 0 -and $reportReads -eq 0 -and $saved.TraceOutcome -ceq 'DisabledForResidentExportCLI') 'Export claimed catalogue diagnostics.'
        if($mode -ceq 'export-normal'){Check ($saved.Status -ceq 'ExportObservedPendingReadback' -and $state.LeaseReleased -and $exportReads -eq 1) 'Export completion differs.'}
        elseif($mode -ceq 'export-forced'){Check ($state.TerminationRequested -and $state.LeaseReleased -and $exportReads -eq 0 -and $pinReads -eq 0 -and $saved.Status -ceq 'Failed') 'Forced export read payload after release.'}
        elseif($mode -ceq 'export-unclosed'){Check ($state.Quarantined -and $context.Lease -and $exportReads -eq 0 -and $pinReads -eq 0) 'Unclosed export lost ownership or read payload.'}
        elseif($mode -ceq 'export-release-failed'){Check ($state.Quarantined -and $context.Lease -and $exportReads -eq 1 -and $saved.Status -cne 'ExportObservedPendingReadback') 'Failed release accepted export.'}
        else{Check ($saved.Status -ceq 'Failed' -and $state.LeaseReleased -and $exportReads -eq 1) 'Missing/nonzero export upgraded.'}
        [AppDomain]::CurrentDomain.SetData('IW7.H1.Quarantine.synthetic',$null)
        Remove-Item -LiteralPath (Join-Path $evidence 'receipt.json')
        . $core
        function Get-H1Clock {$script:clock}
        function Open-H1Pin($Pin){$script:pinReads++;[IO.MemoryStream]::new()}
    }
    # Exercise the REAL finally AST for the distinct G3 route; no CatalogueOutcome
    # exists, so a legacy nonexport fall-through must fail this causal fixture.
    function Read-T7MaterialPartsReport($Plan,$State,$Context){
        if(!$Context.Closed -or !$Context.Lease){throw 'Parts read escaped original admission.'}
        $script:partsReads++
        switch($mode){'parts-missing'{'NoPartsMetadata'};'parts-nonzero'{'PartsMetadataRefused'};default{'PartsMetadataObserved'}}
    }
    $parts=$true;$export=$false
    foreach($mode in @('parts-normal','parts-missing','parts-nonzero','parts-forced','parts-unclosed','parts-release-failed','parts-release-late','parts-publication-late','parts-main-changed')){
        Reset-Owner;$context=$ctx;$context.Owner=$fakeOwner;$context.Closed=$true
        $guards=$context.Guards;$attempted=$true;$failure=$null;$zonePin=[pscustomobject]@{Path='synthetic'}
        $state.InputsReverified=$false;$state.PartsOutcome='NoPartsMetadata';$state.Identity=$identity;$state.ExitCode=0
        $state.EngineOutputsValidated=$false;$script:partsReads=0;$script:traceReads=0;$script:reportReads=0;$script:pinReads=0;$script:mainChecks=0
        Enable-T7CatalogueRuntimeProfile $plan
        $plan|Add-Member NoteProperty CandidateProfile 't7-material-parts-v1' -Force
        if($mode -ceq 'parts-nonzero'){$state.ExitCode=1;$failure='original nonzero exit';$state.Status='Failed'}
        if($mode -ceq 'parts-release-failed'){$script:releaseFails=$true}
        if($mode -ceq 'parts-release-late'){$script:clock=199999;$script:releaseDelay=2}
        if($mode -ceq 'parts-publication-late'){$script:clock=199999;$script:publicationLate=$true}
        function Write-H1Receipt($Plan,$State,$StageRoot){if($script:publicationLate){$script:clock+=2;$script:publicationLate=$false};[IO.File]::WriteAllText((Join-Path $StageRoot 'receipt.json'),($State|ConvertTo-Json -Depth 8))}
        if($mode -cin @('parts-forced','parts-unclosed')){
            $context.Closed=$false;$failure='injected runtime failure';$state.Status='Failed';$fakeOwner.StopFails=$mode -ceq 'parts-unclosed'
        }
        . $finalizer
        $saved=Get-Content -Raw -LiteralPath (Join-Path $evidence 'receipt.json')|ConvertFrom-Json
        Check ($traceReads -eq 0 -and $reportReads -eq 0) 'Parts route inspected a legacy trace/catalogue.'
        if($mode -ceq 'parts-normal'){Check ($saved.Status -ceq 'PartsMetadataObservedPendingReview' -and $state.LeaseReleased -and $partsReads -eq 1) 'Parts success was not promoted through its own outcome.'}
        elseif($mode -ceq 'parts-forced'){Check ($state.TerminationRequested -and $state.LeaseReleased -and $partsReads -eq 0 -and $pinReads -eq 0 -and $saved.Status -ceq 'Failed') 'Forced parts route inspected after release.'}
        elseif($mode -ceq 'parts-unclosed'){Check ($state.Quarantined -and $context.Lease -and $partsReads -eq 0 -and $pinReads -eq 0) 'Unclosed parts route lost ownership.'}
        elseif($mode -ceq 'parts-release-failed'){Check ($state.Quarantined -and $context.Lease -and $partsReads -eq 1 -and $saved.Status -cne 'PartsMetadataObservedPendingReview') 'Failed lease release accepted parts.'}
        else{Check ($saved.Status -ceq 'Failed' -and $state.LeaseReleased -and $partsReads -eq 1) ('Missing/nonzero/late parts metadata upgraded: '+$mode+'/'+$saved.Status+'/'+$partsReads)}
        [AppDomain]::CurrentDomain.SetData('IW7.H1.Quarantine.synthetic',$null)
        Remove-Item -LiteralPath (Join-Path $evidence 'receipt.json')
        if(Test-Path -LiteralPath (Join-Path $evidence 'receipt.deadline-exceeded.json')){Remove-Item -LiteralPath (Join-Path $evidence 'receipt.deadline-exceeded.json')}
        . $core
        function Get-H1Clock {$script:clock}
        function Open-H1Pin($Pin){$script:pinReads++;[IO.MemoryStream]::new()}
    }
    # Reuse the actual finally AST for F2; every outcome retains original admission.
    function Read-T7ImageProvenanceRecord($Plan,$State,$Context){
        if(!$Context.Closed -or !$Context.Lease){throw 'Provenance read escaped original admission.'}
        $script:provReads++
        switch($mode){'prov-missing'{'ProvenanceNoReport'};'prov-nonzero'{'ProvenanceRecordFromFailedProcess'};default{'ProvenanceRecordCaptured'}}
    }
    $parts=$false;$export=$false;$provenance=$true
    foreach($mode in @('prov-normal','prov-missing','prov-nonzero','prov-forced','prov-unclosed','prov-release-failed','prov-release-late','prov-publication-late','prov-main-changed','reg-main-changed')){
        Reset-Owner;$context=$ctx;$context.Owner=$fakeOwner;$context.Closed=$true
        $guards=$context.Guards;$attempted=$true;$failure=$null;$zonePin=[pscustomobject]@{Path='synthetic'}
        $state.InputsReverified=$false;$state.ProvenanceOutcome='ProvenanceNoReport';$state.Identity=$identity;$state.ExitCode=0
        $state.EngineOutputsValidated=$false;$script:provReads=0;$script:traceReads=0;$script:reportReads=0;$script:pinReads=0;$script:mainChecks=0
        Enable-T7CatalogueRuntimeProfile $plan
        $plan|Add-Member NoteProperty CandidateProfile 't7-image-provenance-v1' -Force
        if($mode -ceq 'prov-nonzero'){$state.ExitCode=1;$failure='original nonzero exit';$state.Status='Failed'}
        if($mode -ceq 'prov-release-failed'){$script:releaseFails=$true}
        if($mode -ceq 'prov-release-late'){$script:clock=199999;$script:releaseDelay=2}
        if($mode -ceq 'prov-publication-late'){$script:clock=199999;$script:publicationLate=$true}
        function Write-H1Receipt($Plan,$State,$StageRoot){if($script:publicationLate){$script:clock+=2;$script:publicationLate=$false};[IO.File]::WriteAllText((Join-Path $StageRoot 'receipt.json'),($State|ConvertTo-Json -Depth 8))}
        if($mode -cin @('prov-forced','prov-unclosed')){
            $context.Closed=$false;$failure='injected runtime failure';$state.Status='Failed';$fakeOwner.StopFails=$mode -ceq 'prov-unclosed'
        }
        . $finalizer
        $saved=Get-Content -Raw -LiteralPath (Join-Path $evidence 'receipt.json')|ConvertFrom-Json
        Check ($traceReads -eq 0 -and $reportReads -eq 0) 'Provenance route inspected a legacy trace/catalogue.'
        if($mode -ceq 'prov-normal'){Check ($saved.Status -ceq 'ProvenanceRecordCapturedPendingReview' -and $state.LeaseReleased -and $provReads -eq 1) 'Provenance success was not promoted through its own outcome.'}
        elseif($mode -ceq 'prov-forced'){Check ($state.TerminationRequested -and $state.LeaseReleased -and $provReads -eq 0 -and $pinReads -eq 0 -and $saved.Status -ceq 'Failed') 'Forced provenance route inspected after release.'}
        elseif($mode -ceq 'prov-unclosed'){Check ($state.Quarantined -and $context.Lease -and $provReads -eq 0 -and $pinReads -eq 0) 'Unclosed provenance route lost ownership.'}
        elseif($mode -ceq 'prov-release-failed'){Check ($state.Quarantined -and $context.Lease -and $provReads -eq 1 -and $saved.Status -cne 'ProvenanceRecordCapturedPendingReview') 'Failed lease release accepted provenance.'}
        else{Check ($saved.Status -ceq 'Failed' -and $state.LeaseReleased -and $provReads -eq 1) ('Missing/nonzero/late provenance record upgraded: '+$mode+'/'+$saved.Status+'/'+$provReads)}
        [AppDomain]::CurrentDomain.SetData('IW7.H1.Quarantine.synthetic',$null)
        Remove-Item -LiteralPath (Join-Path $evidence 'receipt.json')
        if(Test-Path -LiteralPath (Join-Path $evidence 'receipt.deadline-exceeded.json')){Remove-Item -LiteralPath (Join-Path $evidence 'receipt.deadline-exceeded.json')}
        . $core
        function Get-H1Clock {$script:clock}
        function Open-H1Pin($Pin){$script:pinReads++;[IO.MemoryStream]::new()}
    }
    function Read-T7RegistrationImageRecord($Plan,$State,$Context){
        if(!$Context.Closed -or !$Context.Lease){throw 'Provenance read escaped original admission.'}
        $script:regReads++
        switch($mode){'reg-missing'{'RegistrationNoReport'};'reg-nonzero'{'RegistrationRecordFromFailedProcess'};default{'RegistrationRecordCaptured'}}
    }
    $parts=$false;$export=$false;$provenance=$false;$registration=$true
    foreach($mode in @('reg-normal','reg-missing','reg-nonzero','reg-forced','reg-unclosed','reg-release-failed','reg-release-late','reg-publication-late','reg-main-changed','reg-main-changed')){
        Reset-Owner;$context=$ctx;$context.Owner=$fakeOwner;$context.Closed=$true
        $guards=$context.Guards;$attempted=$true;$failure=$null;$zonePin=[pscustomobject]@{Path='synthetic'}
        $state.InputsReverified=$false;$state.RegistrationOutcome='RegistrationNoReport';$state.Identity=$identity;$state.ExitCode=0
        $state.EngineOutputsValidated=$false;$script:regReads=0;$script:traceReads=0;$script:reportReads=0;$script:pinReads=0;$script:mainChecks=0
        Enable-T7CatalogueRuntimeProfile $plan
        $plan|Add-Member NoteProperty CandidateProfile 't7-registration-image-header-metadata-v1' -Force
        if($mode -ceq 'reg-nonzero'){$state.ExitCode=1;$failure='original nonzero exit';$state.Status='Failed'}
        if($mode -ceq 'reg-release-failed'){$script:releaseFails=$true}
        if($mode -ceq 'reg-release-late'){$script:clock=199999;$script:releaseDelay=2}
        if($mode -ceq 'reg-publication-late'){$script:clock=199999;$script:publicationLate=$true}
        function Write-H1Receipt($Plan,$State,$StageRoot){if($script:publicationLate){$script:clock+=2;$script:publicationLate=$false};[IO.File]::WriteAllText((Join-Path $StageRoot 'receipt.json'),($State|ConvertTo-Json -Depth 8))}
        if($mode -cin @('reg-forced','reg-unclosed')){
            $context.Closed=$false;$failure='injected runtime failure';$state.Status='Failed';$fakeOwner.StopFails=$mode -ceq 'reg-unclosed'
        }
        . $finalizer
        $saved=Get-Content -Raw -LiteralPath (Join-Path $evidence 'receipt.json')|ConvertFrom-Json
        Check ($traceReads -eq 0 -and $reportReads -eq 0) 'Provenance route inspected a legacy trace/catalogue.'
        if($mode -ceq 'reg-normal'){Check ($saved.Status -ceq 'RegistrationRecordCapturedPendingReview' -and $state.LeaseReleased -and $regReads -eq 1) 'Provenance success was not promoted through its own outcome.'}
        elseif($mode -ceq 'reg-forced'){Check ($state.TerminationRequested -and $state.LeaseReleased -and $regReads -eq 0 -and $pinReads -eq 0 -and $saved.Status -ceq 'Failed') 'Forced provenance route inspected after release.'}
        elseif($mode -ceq 'reg-unclosed'){Check ($state.Quarantined -and $context.Lease -and $regReads -eq 0 -and $pinReads -eq 0) 'Unclosed provenance route lost ownership.'}
        elseif($mode -ceq 'reg-release-failed'){Check ($state.Quarantined -and $context.Lease -and $regReads -eq 1 -and $saved.Status -cne 'RegistrationRecordCapturedPendingReview') 'Failed lease release accepted provenance.'}
        else{Check ($saved.Status -ceq 'Failed' -and $state.LeaseReleased -and $regReads -eq 1) ('Missing/nonzero/late provenance record upgraded: '+$mode+'/'+$saved.Status+'/'+$regReads)}
        [AppDomain]::CurrentDomain.SetData('IW7.H1.Quarantine.synthetic',$null)
        Remove-Item -LiteralPath (Join-Path $evidence 'receipt.json')
        if(Test-Path -LiteralPath (Join-Path $evidence 'receipt.deadline-exceeded.json')){Remove-Item -LiteralPath (Join-Path $evidence 'receipt.deadline-exceeded.json')}
        . $core
        function Get-H1Clock {$script:clock}
        function Open-H1Pin($Pin){$script:pinReads++;[IO.MemoryStream]::new()}
    }
    [ordered]@{Status='Passed';Checks=$checks;NativeTypesLoaded=$false;RealLeaseAcquired=$false;NativeProcessStarted=$false;OwnerStockRead=$false}|ConvertTo-Json
}finally{
    foreach($g in $context.Guards){$g.Dispose()}
    $resolved=[IO.Path]::GetFullPath($root)
    $parent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if(!$resolved.StartsWith($parent,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -notmatch '^t7-catalogue-tests-[0-9a-f]{32}$'){throw 'Refuse cleanup outside exact synthetic root.'}
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
