# Pure invented metadata/receipts and temporary text names. No retail payload or native code.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
. (Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1')
. (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
$script:checks=0;$script:provider=@{};$script:observedId='AABBCCDD:0000000000000001'
function Check([bool]$Value,[string]$Why){if(!$Value){throw $Why};$script:checks++}
function Refuses([scriptblock]$Body,[string]$Pattern='.'){
    $caught=$false;try{& $Body}catch{$caught=$true;Check ($_.Exception.Message -match $Pattern) ('Unexpected error: '+$_.Exception.Message)}
    Check $caught 'Expected rejection.'
}
function Copy-Value($Value){$Value|ConvertTo-Json -Depth 15|ConvertFrom-Json}
function Get-Item($LiteralPath){
    if($script:provider.ContainsKey($LiteralPath)){return $script:provider[$LiteralPath]}
    Microsoft.PowerShell.Management\Get-Item -LiteralPath $LiteralPath
}
function Get-T7CatalogueFileId([string]$Path){$script:observedId}
$root=Join-Path ([IO.Path]::GetTempPath()) ('t7-bootstrap-tests-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($root)|Out-Null
function New-Fixture {
    $script:provider=@{};$script:observedId='AABBCCDD:0000000000000001'
    $fakeRepo=Join-Path $root 'repo';$run=Join-Path $fakeRepo 'runtime/t7-catalog-bootstrap'
    foreach($name in 'work','evidence','temp'){[IO.Directory]::CreateDirectory((Join-Path $run $name))|Out-Null}
    $date='2026-10-12T00:00:00.0000000Z'
    $zone=[pscustomobject]@{Path=(Join-Path $root 'mp_freerun_04.ff');Bytes=16977344;SHA256=$null;RelativePath='zone/mp_freerun_04.ff';HashProvenance='ObserveUnderLease';Attributes='Archive';LastWriteUtc=$date}
    $receiptPin=[pscustomobject]@{Path=(Join-Path $root 'invented-qualification.json');Bytes=100;SHA256=('c'*64)}
    $scriptPin=[pscustomobject]@{Path=(Join-Path $root 'invented-qualification.ps1');Bytes=100;SHA256=('d'*64)}
    $bootstrap=[pscustomobject]@{Path=(Join-Path $root 'en_core_pre_gfx.ff');Bytes=832;SHA256=('b'*64);FileId=$script:observedId;RelativePath='zone/en_core_pre_gfx.ff';HashProvenance='ObservedUnderLeaseNotDepotVerified';QualificationReceipt=$receiptPin;QualificationScript=$scriptPin}
    $bindings=@(
        [pscustomobject]@{Path=(Join-Path $root 'candidate.exe');Bytes=21750272;SHA256=('a'*64);IsText=$false},
        [pscustomobject]@{Path=(Join-Path $root 'engine.exe');Bytes=21737352;SHA256='3df511d71e3690b14517379783bbfb713f6fe2ed2f2e73b445b4878216686156';IsText=$false},
        [pscustomobject]@{Path=(Join-Path $root 'steam_api64.dll');Bytes=235600;SHA256='71af8666392acad2080a816b9f1196fe9ccb950e1db8a549f8312c4d231f55a8';IsText=$false},
        [pscustomobject]@{Path=(Join-Path $root 'NativeJob.dll');Bytes=100;SHA256=('e'*64);IsText=$false},
        [pscustomobject]@{Path=[Diagnostics.Process]::GetCurrentProcess().MainModule.FileName;Bytes=100;SHA256=('f'*64);IsText=$false},
        [pscustomobject]@{Path=$bootstrap.Path;Bytes=832;SHA256=$bootstrap.SHA256;IsText=$false},
        [pscustomobject]@{Path=$receiptPin.Path;Bytes=100;SHA256=$receiptPin.SHA256;IsText=$true},
        [pscustomobject]@{Path=$scriptPin.Path;Bytes=100;SHA256=$scriptPin.SHA256;IsText=$true})
    $metadata=@($bindings[0..2]|ForEach-Object {[pscustomobject]@{Path=$_.Path;Bytes=$_.Bytes;Attributes='Archive';LastWriteUtc=$date}})+@($zone)
    $bootstrapMetadata=[pscustomobject]@{Path=$bootstrap.Path;Bytes=832;Attributes='Archive';CreationUtc=$date;LastWriteUtc=$date};$metadata+=@($bootstrapMetadata)
    foreach($row in @($bindings)+@($zone)){$script:provider[$row.Path]=[pscustomobject]@{PSIsContainer=$false;Length=$row.Bytes;Attributes='Archive';CreationTimeUtc=([datetimeoffset]$date).UtcDateTime;LastWriteTimeUtc=([datetimeoffset]$date).UtcDateTime}}
    $plan=[pscustomobject]@{Schema='iw7.t7-catalogue-plan/1';EngineOutputProfile='ObservedStartupA';Runner='synthetic-runner';CandidateProfile='t7-catalog-message';TraceStderrLimitBytes=8192;PhysicalBytes=6GB;CommitBytes=8GB;GroupDeadlineSeconds=200;DeadlineSeconds=120;MutableOutputLimitBytes=64MB;MetadataReserveBytes=64KB;CleanupSeconds=5;ReportLimitBytes=512KB;LogLimitBytes=1MB;OutputLimitBytes=127810264;RetryAuthorized=$false;RunRoot=$run;WorkingDirectory=(Join-Path $run 'work');StageRoot=(Join-Path $run 'evidence');Image=(Join-Path $run 'work/t7-zonetool-candidate.exe');Arguments=@('-t7-iw7-catalog','mp_freerun_04');OutputKey='t7_iw7_catalog_1d7749fdf2454720fad852816e9ddde027a157a4cc486aa18b3eb8fd4a25c2ce';Bindings=$bindings;InputMetadata=$metadata;Zone=$zone;CandidateSource=$bindings[0].Path;CandidateBytes=21750272;CandidateSHA256=$bindings[0].SHA256;EngineSource=$bindings[1].Path;SteamSource=$bindings[2].Path;JobAssembly=$bindings[3].Path;Bootstrap=$bootstrap}
    $observed=[pscustomobject]@{Bytes=832;Attributes='Archive';CreationUtc=$date;LastWriteUtc=$date;FileId=$bootstrap.FileId}
    $receipt=[pscustomobject]@{Schema='iw7.t7-bootstrap-qualification/1';Status='IdentityAndHashObservedCompatibilityUnknown';ScriptSHA256=$scriptPin.SHA256;SHA256=$bootstrap.SHA256;FileId=$bootstrap.FileId;HashProvenance=$bootstrap.HashProvenance;GuardedReadBytesPerPass=832;GuardedReadPasses=2;Input=(Copy-Value $bootstrapMetadata);MetadataBefore=(Copy-Value $observed);MetadataAfter=(Copy-Value $observed);Host=[pscustomobject]@{Contract=[pscustomobject]@{NoProfile=$true;NoExit=$true;DirectFileLaunch=$true;ExactArgumentsVerified=$true}}}
    foreach($name in 'DataFileOpened','PayloadHashed','LeaseAcquired','LeaseReleased','GuardsClosed','TreeClosureConfirmed','MetadataAndIdentityReverifiedUnderGuard','HashReverifiedUnderGuard','PreservedPythonIdentityUnchanged'){$receipt|Add-Member NoteProperty $name $true}
    foreach($name in 'Quarantined','HeaderSemanticsKnown','HeaderPrefixCaptured','ContentCompatibilityProven','DepotVerified','EngineLookupPathProven','NativeEngineExecuted','NativeJobCreated','PayloadCopiedToDisk','PayloadHashesReadAfterRelease','Ready'){$receipt|Add-Member NoteProperty $name $false}
    [pscustomobject]@{Plan=$plan;Receipt=$receipt;Repo=$fakeRepo}
}
try {
    Check ($null -eq (Get-T7CatalogueBootstrap ([pscustomobject]@{}))) 'Historical absence rejected.'
    $f=New-Fixture;Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner';$checks++
    # One selected-zone success and independent binding changes; existing factory stays fixed.
    $oldZonePath=$f.Plan.Zone.Path
    $f.Plan.Zone.Path=Join-Path $root 'zm_common.ff';$f.Plan.Zone.Bytes=36332480
    $f.Plan.Zone.RelativePath='zone/zm_common.ff';$f.Plan.InputMetadata[3]=$f.Plan.Zone
    $script:provider[$f.Plan.Zone.Path]=Copy-Value $script:provider[$oldZonePath]
    $script:provider[$f.Plan.Zone.Path].Length=36332480
    $f.Plan.Arguments[1]='zm_common'
    $f.Plan.OutputKey='t7_iw7_catalog_74d24f210d6f255a1e1f63a978bc4cc643496107d00de87211ef84e565de1a88'
    $f.Plan.OutputLimitBytes+=19355136
    Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner';$checks++
    Check ($f.Plan.OutputLimitBytes -eq 147165400) 'Zombies catalogue exact byte accounting differs.'
    foreach($case in 'arguments','arguments-array','output-key','output-key-array','relative-path','relative-path-array','filename-case','filename-extension','unknown-zone','zone-size','zone-size-string','zone-binding','budget'){
        $bad=Copy-Value $f
        switch($case){
            arguments {$bad.Plan.Arguments[1]='mp_freerun_04'}
            arguments-array {$bad.Plan.Arguments[1]=@('zm_common')}
            output-key {$bad.Plan.OutputKey='t7_iw7_catalog_1d7749fdf2454720fad852816e9ddde027a157a4cc486aa18b3eb8fd4a25c2ce'}
            output-key-array {$bad.Plan.OutputKey=@($bad.Plan.OutputKey)}
            relative-path {$bad.Plan.Zone.RelativePath='zone/mp_freerun_04.ff'}
            relative-path-array {$bad.Plan.Zone.RelativePath=@($bad.Plan.Zone.RelativePath)}
            filename-case {$bad.Plan.Zone.Path=Join-Path $root 'ZM_COMMON.ff'}
            filename-extension {$bad.Plan.Zone.Path=Join-Path $root 'zm_common.FF'}
            unknown-zone {$bad.Plan.Zone.Path=Join-Path $root 'unknown_zone.ff'}
            zone-size {$bad.Plan.Zone.Bytes++}
            zone-size-string {$bad.Plan.Zone.Bytes='36332480'}
            zone-binding {$bad.Plan.Bindings+=@([pscustomobject]@{Path=$bad.Plan.Zone.Path;Bytes=36332480;SHA256=('0'*64);IsText=$false})}
            budget {$bad.Plan.OutputLimitBytes++}
        }
        Refuses {Assert-T7CataloguePlan $bad.Plan $bad.Repo 'synthetic-runner'}
    }
    $bad=Copy-Value $f;$bad.Plan|Add-Member NoteProperty Operation 'ResidentExportV1'
    Refuses {Get-T7CataloguePlanZoneSpec $bad.Plan} 'Resident export'
    $f=New-Fixture
    Assert-T7CatalogueBootstrapReceipt $f.Plan $f.Receipt;$checks++
    Assert-T7CatalogueBootstrapIdentity $f.Plan;$checks++
    foreach($field in 'Path','RelativePath','Bytes','SHA256','FileId','HashProvenance'){
        $f=New-Fixture
        $f.Plan.Bootstrap.$field=if($field -ceq 'Bytes'){833}else{'unexpected'}
        Refuses {Get-T7CatalogueBootstrap $f.Plan}
    }
    foreach($value in @($null,@())){$f=New-Fixture;$f.Plan.Bootstrap=$value;Refuses {Get-T7CatalogueBootstrap $f.Plan}}
    $f=New-Fixture;$f.Plan.Bootstrap|Add-Member NoteProperty Extra 'forbidden';Refuses {Get-T7CatalogueBootstrap $f.Plan}
    foreach($profile in 'ordinary-d2','t7-catalog-trace','t7-catalog-exit-context','t7-catalog-callers'){$f=New-Fixture;$f.Plan.CandidateProfile=$profile;Refuses {Get-T7CatalogueBootstrap $f.Plan}}
    $f=New-Fixture;$f.Plan.OutputLimitBytes-=832;Refuses {Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner'} 'Fixed catalogue'
    $f=New-Fixture;$f.Plan.TraceStderrLimitBytes=8193;Refuses {Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner'} 'Exact trace stderr'
    foreach($case in 'missing-metadata','duplicate-metadata','missing-binary','wrong-binary-hash','text-binary','missing-receipt','missing-script','extra-binary'){
        $f=New-Fixture
        switch($case){
            missing-metadata {$f.Plan.InputMetadata=@($f.Plan.InputMetadata|Where-Object Path -CNE $f.Plan.Bootstrap.Path)}
            duplicate-metadata {$f.Plan.InputMetadata+=@($f.Plan.InputMetadata[-1])}
            missing-binary {$f.Plan.Bindings=@($f.Plan.Bindings|Where-Object Path -CNE $f.Plan.Bootstrap.Path)}
            wrong-binary-hash {$f.Plan.Bindings[5].SHA256='0'*64}
            text-binary {$f.Plan.Bindings[5].IsText=$true}
            missing-receipt {$f.Plan.Bindings=@($f.Plan.Bindings|Where-Object Path -CNE $f.Plan.Bootstrap.QualificationReceipt.Path)}
            missing-script {$f.Plan.Bindings=@($f.Plan.Bindings|Where-Object Path -CNE $f.Plan.Bootstrap.QualificationScript.Path)}
            extra-binary {$extra=Copy-Value $f.Plan.Bindings[5];$extra.Path=Join-Path $root 'guessed.ff';$f.Plan.Bindings+=@($extra);$script:provider[$extra.Path]=$script:provider[$f.Plan.Bootstrap.Path]}
        }
        Refuses {Assert-T7CataloguePlan $f.Plan $f.Repo 'synthetic-runner'}
    }
    foreach($field in 'Status','ScriptSHA256','SHA256','FileId','HashProvenance','GuardedReadBytesPerPass','GuardedReadPasses'){
        $f=New-Fixture;$f.Receipt.$field='unexpected';Refuses {Assert-T7CatalogueBootstrapReceipt $f.Plan $f.Receipt}
    }
    foreach($field in 'DataFileOpened','PayloadHashed','LeaseAcquired','LeaseReleased','GuardsClosed','TreeClosureConfirmed','MetadataAndIdentityReverifiedUnderGuard','HashReverifiedUnderGuard','PreservedPythonIdentityUnchanged'){
        $f=New-Fixture;$f.Receipt.$field=$false;Refuses {Assert-T7CatalogueBootstrapReceipt $f.Plan $f.Receipt} 'lifecycle'
        $f=New-Fixture;$f.Receipt.PSObject.Properties.Remove($field);Refuses {Assert-T7CatalogueBootstrapReceipt $f.Plan $f.Receipt} 'lifecycle'
    }
    foreach($field in 'Quarantined','HeaderSemanticsKnown','HeaderPrefixCaptured','ContentCompatibilityProven','DepotVerified','EngineLookupPathProven','NativeEngineExecuted','NativeJobCreated','PayloadCopiedToDisk','PayloadHashesReadAfterRelease','Ready'){
        $f=New-Fixture;$f.Receipt.$field=$true;Refuses {Assert-T7CatalogueBootstrapReceipt $f.Plan $f.Receipt} 'overclaims'
    }
    foreach($field in 'NoProfile','NoExit','DirectFileLaunch','ExactArgumentsVerified'){
        $f=New-Fixture;$f.Receipt.Host.Contract.$field=$false;Refuses {Assert-T7CatalogueBootstrapReceipt $f.Plan $f.Receipt} 'persistent'
    }
    foreach($field in 'Error','CleanupError','FinalizationError'){$f=New-Fixture;$f.Receipt|Add-Member NoteProperty $field 'late';Refuses {Assert-T7CatalogueBootstrapReceipt $f.Plan $f.Receipt} 'successful'}
    foreach($row in 'Input','MetadataBefore','MetadataAfter'){
        foreach($field in 'Bytes','Attributes','CreationUtc','LastWriteUtc'){
            $f=New-Fixture;$f.Receipt.$row.$field=if($field -ceq 'Bytes'){831}elseif($field -ceq 'Attributes'){'ReadOnly'}else{'2026-10-13T00:00:00Z'}
            Refuses {Assert-T7CatalogueBootstrapReceipt $f.Plan $f.Receipt} 'metadata'
        }
    }
    foreach($row in 'MetadataBefore','MetadataAfter'){$f=New-Fixture;$f.Receipt.$row.FileId='AABBCCDD:0000000000000002';Refuses {Assert-T7CatalogueBootstrapReceipt $f.Plan $f.Receipt} 'identity'}
    $f=New-Fixture;$script:observedId='AABBCCDD:0000000000000002';Refuses {Assert-T7CatalogueBootstrapIdentity $f.Plan} 'qualified file identity'
    $f=New-Fixture;$script:provider[$f.Plan.Bootstrap.Path].CreationTimeUtc=[datetime]'2026-10-13T00:00:00Z';Refuses {Assert-T7CatalogueBootstrapIdentity $f.Plan} 'creation metadata'
    $f=New-Fixture;$zoneDir=Join-Path $f.Plan.WorkingDirectory 'zone';[IO.Directory]::CreateDirectory($zoneDir)|Out-Null
    $bootstrapAlias=Join-Path $zoneDir 'en_core_pre_gfx.ff';[IO.File]::WriteAllText($bootstrapAlias,'invented bytes, no real receipt or hash')
    Assert-T7CatalogueEngineOutputs $f.Plan;$checks++
    $historical=Copy-Value $f.Plan;$historical.PSObject.Properties.Remove('Bootstrap')
    Refuses {Assert-T7CatalogueEngineOutputs $historical} 'Unexpected zone'
    $unexpected=Join-Path $zoneDir 'guessed.ff';[IO.File]::WriteAllText($unexpected,'invented')
    Refuses {Assert-T7CatalogueEngineOutputs $f.Plan} 'Unexpected zone'
    $runner=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Run-T7Catalogue.ps1') -Raw
    Check ($runner.IndexOf('Assert-T7CatalogueBootstrapReceipt') -lt $runner.IndexOf('if(!$Run)')) 'Qualification not checked before default return.'
    Check ($runner.IndexOf('Assert-T7CatalogueBootstrapIdentity') -gt $runner.IndexOf('Add-Type -Path $fileIdentity')) 'File ID checked before admitted native support.'
    Check ($runner.Contains('New-T7CatalogueAlias $bootstrapPin (Join-Path $plan.WorkingDirectory $bootstrap.RelativePath) $context')) 'Explicit guarded bootstrap alias missing.'
    Check (!('IW7ResourceMemoryV1' -as [type]) -and !('IW7HudFileIdentity' -as [type]) -and !('IW7.AnimationProbe.NativeJob' -as [type])) 'Pure checks loaded native types.'
    [ordered]@{Status='Passed';Checks=$checks;Fixtures='Invented in-memory qualification only';NativeTypesLoaded=$false;RealLeaseAcquired=$false;NativeProcessStarted=$false;OwnerStockRead=$false;OperationalPlanCreated=$false}|ConvertTo-Json
}finally{
    $full=[IO.Path]::GetFullPath($root);$temp=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if(!$full.StartsWith($temp,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($full) -cnotmatch '^t7-bootstrap-tests-[0-9a-f]{32}$'){throw 'Unexpected synthetic cleanup root.'}
    Remove-Item -LiteralPath $full -Recurse -Force
}
