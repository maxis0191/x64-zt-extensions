param([Parameter(Mandatory)][string]$SpecPath,
    [Parameter(Mandatory)][ValidatePattern('^[a-f0-9]{64}$')][string]$SpecSHA256,[switch]$Run)
# Plan only by default; a separate coordinator GO is required for future -Run.
$ErrorActionPreference='Stop'
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
function Assert-WatchPath([string]$Path,[switch]$New) {
    if(![IO.Path]::IsPathFullyQualified($Path) -or $Path -notmatch '^[A-Za-z]:[\\/]'){throw 'Local absolute path required.'}
    $full=[IO.Path]::GetFullPath($Path);$cursor=$full
    if($New -and (Test-Path -LiteralPath $full)){throw 'Fresh output root required.'}
    while($cursor){
        if(Test-Path -LiteralPath $cursor){if((Get-Item -LiteralPath $cursor -Force).Attributes.HasFlag([IO.FileAttributes]::ReparsePoint)){throw 'Reparse ancestry refused.'}}
        $cursor=Split-Path $cursor -Parent
    }
    return $full
}
function Read-WatchJson([string]$Path,[long]$Limit=16384) {
    $share=[IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete
    $stream=[IO.File]::Open($Path,'Open','Read',$share)
    try{
        if($stream.Length -gt $Limit){throw 'Bounded JSON required.'}
        $reader=[IO.StreamReader]::new($stream,[Text.UTF8Encoding]::new($false,$true))
        try{$reader.ReadToEnd()|ConvertFrom-Json}finally{$reader.Dispose()}
    }finally{$stream.Dispose()}
}
function Write-WatchJson([string]$Path,$Value) {
    $raw=$Value|ConvertTo-Json -Depth 18
    if([Text.Encoding]::UTF8.GetByteCount($raw) -gt 65536){throw 'State exceeds 64 KiB.'}
    $temporary=$Path+'.tmp'
    [IO.File]::WriteAllText($temporary,$raw,[Text.UTF8Encoding]::new($false))
    [IO.File]::Move($temporary,$Path,$true)
}
function Assert-WatchFixtureSpec($Spec) {
    $names=@('Schema','Mode','ResourceProfile','Nonce','RunRoot','ProviderRoot','PythonExe','PythonSHA256','CdbExe','SourceBindings')
    $properties=@($Spec.PSObject.Properties)
    if(!$Spec -or $properties.Count -ne $names.Count -or @($properties|Where-Object {$_.Name -cnotin $names}).Count){
        throw 'Exact fixture v4 fields required; free budgets, target paths, existing PIDs and commands are unavailable.'
    }
    if($Spec.Schema -cne 'iw7.rig-watch-fixture-plan/4' -or $Spec.Mode -cne 'fixture' -or
       $Spec.ResourceProfile -cne 'iw7.rig-watch-python-cdb-fixture/1' -or $Spec.Nonce -cnotmatch '^[a-f0-9]{32}$'){
        throw 'Only the fixed Python/CDB fixture profile is supported; retail mode is unavailable.'
    }
    [ordered]@{Id='iw7.rig-watch-python-cdb-fixture/1';Mode='fixture';PhysicalBytes=4GB;CommitBytes=6GB;
        EstimateOnly=$true;MeasuredPeaks=$false;RetailCompatible=$false}
}
function Get-ReviewedWatchSourceBindings($Expected,[string]$Root,$Guards,[switch]$Hold) {
    $names=@('Run-WatchFixture.ps1','Watchpoint.Core.ps1','WatchpointDeadline.cs','capture.py',
        'cdb_transport.py','debug_fixture.py','owned_fixture.py','fixture-providers.json')
    $properties=@($Expected.PSObject.Properties)
    if(!$Expected -or $properties.Count -ne $names.Count -or
       @($properties|Where-Object {$_.Name -cnotin $names}).Count){throw 'Spec must bind exactly eight reviewed rig-abi sources.'}
    $result=[ordered]@{};$firstGuard=$Guards.Count
    try{
        foreach($name in $names){
            $hash=$Expected.$name
            if($hash -isnot [string] -or $hash -cnotmatch '^[a-f0-9]{64}$'){throw "Reviewed source hash required: $name"}
            $path=Assert-WatchPath (Join-Path $Root $name)
            if($Hold){$Guards.Add([IO.File]::Open($path,'Open','Read','Read'))}
            $item=Get-Item -LiteralPath $path -Force
            if($item.PSIsContainer -or $item.Length -gt 1MB -or (Get-FileHash -LiteralPath $path).Hash -ine $hash){
                throw "Reviewed source changed before import: $name"
            }
            $result[$path]=$hash
        }
        return $result
    }catch{
        for($index=$Guards.Count-1;$index -ge $firstGuard;$index--){$Guards[$index].Dispose();$Guards.RemoveAt($index)}
        throw
    }
}
$SpecPath=Assert-WatchPath $SpecPath
if((Get-Item -LiteralPath $SpecPath -Force).Length -gt 16384){throw 'Spec exceeds 16 KiB.'}
if((Get-FileHash -LiteralPath $SpecPath).Hash -ine $SpecSHA256){throw 'Spec binding differs.'}
$spec=Read-WatchJson $SpecPath
$fixtureProfile=Assert-WatchFixtureSpec $spec
$sourceGuards=[Collections.Generic.List[IDisposable]]::new();$state=$null
try{
$reviewedSources=Get-ReviewedWatchSourceBindings $spec.SourceBindings $PSScriptRoot $sourceGuards -Hold:$Run
$runRoot=Assert-WatchPath $spec.RunRoot -New
$runtime=[IO.Path]::GetFullPath((Join-Path $repo 'runtime')).TrimEnd('\')+'\'
if(!$runRoot.StartsWith($runtime,[StringComparison]::OrdinalIgnoreCase)){throw 'Fresh root must stay within this checkout runtime.'}
$provider=Assert-WatchPath $spec.ProviderRoot
$python=Assert-WatchPath $spec.PythonExe;$cdb=Assert-WatchPath $spec.CdbExe
if((Split-Path $python -Leaf) -ine 'python.exe' -or (Split-Path $cdb -Leaf) -ine 'cdb.exe' -or $spec.PythonSHA256 -cnotmatch '^[a-f0-9]{64}$'){throw 'Explicit Python/CDB tool identities required.'}
$providerPins=Get-Content -LiteralPath "$PSScriptRoot/fixture-providers.json" -Raw|ConvertFrom-Json -AsHashtable
$pins=[ordered]@{$SpecPath=$SpecSHA256}
foreach($relative in $providerPins.Keys){
    $path=Assert-WatchPath (Join-Path $provider $relative)
    if($Run){$sourceGuards.Add([IO.File]::Open($path,'Open','Read','Read'))}
    if((Get-FileHash -LiteralPath $path).Hash -ine $providerPins[$relative]){throw "Source provider changed: $relative"}
    $pins[$path]=$providerPins[$relative]
}
foreach($path in $reviewedSources.Keys){$pins[$path]=$reviewedSources[$path]}
$pins[$python]=$spec.PythonSHA256
$pins[$cdb]='5f54abafca3ae5638bbf807d402fabb350a64575c1dfa9fbfc7f5732df5bee67'
$pins[(Join-Path (Split-Path $cdb) 'dbgeng.dll')]='4352756685e7325288e54abb3281e768637987517be8575ec4450e4b4421842f'
$pins[(Join-Path (Split-Path $cdb) 'dbghelp.dll')]='ea639fc67cc1430b66b71ef63a2ec72ea92879cca7e665bb10ae33c4468094f9'
if(!$Run){
    [ordered]@{Schema='iw7.rig-watch-fixture-source-plan/4';RunRoot=$runRoot;SourceBindings=$pins;
        ResourceProfile=$fixtureProfile;PhysicalBytes=$fixtureProfile.PhysicalBytes;CommitBytes=$fixtureProfile.CommitBytes;
        OverallMilliseconds=240000;ArmedMilliseconds=10000;CleanupMilliseconds=30000;OutputBytes=1MB;
        Mode='fixture';CreationModel='new-suspended-original-handles-attach/1';ExistingPIDAllowed=$false;
        MembershipBeforeAttach=2;MembershipBeforeResume=3;UnprovenClosureRetainsLease=$true;
        Ready=$false;NativeExecuted=$false;NativeTypesLoaded=$false;LeaseAcquired=$false;
        Next='Independent source review of owned suspended creation/attachment, then separate fixture GO.'}|ConvertTo-Json -Depth 8
    return
}
foreach($name in @('IW7.CommunityBuild.BuildJob','IW7.AnimationRig.JobMembers','IW7.RigWatch.OriginalJobDeadline','IW7ResourceMemoryV1')){
    if($name -as [type]){throw 'Fresh PowerShell host required for source-bound runtime types.'}
}
. (Join-Path $provider 'tools-source/asset-bridge/animation/AnimationFF.Core.ps1')
foreach($path in @((Join-Path $provider 'sdk/modding/BeaconFF.Core.ps1'),"$PSScriptRoot/Watchpoint.Core.ps1")){
    Assert-AnimationPureImport $path;. $path
}
. (Join-Path $provider 'ops/Resource-Scheduler.Core.ps1')
$state=New-RigWatchFixtureState $spec.Nonce
$state.Context.Guards=$sourceGuards
$state.Context.Baselines=[Collections.Generic.List[object]]::new()
$state.Context.Transport=$null;$state.Context.SpecPath=$null
$state.Context.TransportFailure=$null
$hooks=[ordered]@{
    Now={[Environment]::TickCount64}
    Acquire={param($s,$physical,$commit)
        if($physical -ne $fixtureProfile.PhysicalBytes -or $commit -ne $fixtureProfile.CommitBytes){throw 'Fixture profile/transaction budget differs.'}
        Enter-IW7ResourceLease -Scope $runRoot -Kind Extract -PhysicalBytes $physical -CommitBytes $commit -Owner 'Rig Python CDB fixture qualification only'
    }
    Stage={param($s)
        foreach($path in $pins.Keys){
            $null=Assert-WatchPath $path
            if((Get-Item -LiteralPath $path -Force).Length -gt 32MB){throw 'Pinned fixture input exceeds 32 MiB bound.'}
            $guard=[IO.File]::Open($path,'Open','Read','Read');$s.Context.Guards.Add($guard)
            if((Get-FileHash -LiteralPath $path).Hash -ine $pins[$path]){throw 'Source/tool pin changed after admission.'}
            $item=Get-Item -LiteralPath $path
            $s.Context.Baselines.Add(@{Path=$path;SHA256=$pins[$path];Bytes=$item.Length;ModifiedUtc=$item.LastWriteTimeUtc.ToString('o')})
        }
        Add-Type -LiteralPath (Join-Path $provider 'tools-source/asset-bridge/model/BuildJob.cs')
        Add-Type -LiteralPath (Join-Path $provider 'tools-source/asset-bridge/animation/rig/Rig.JobMembers.cs')
        Add-Type -LiteralPath "$PSScriptRoot/WatchpointDeadline.cs"
        $null=Assert-WatchPath $runRoot -New
        New-Item -ItemType Directory -Path $runRoot -ErrorAction Stop|Out-Null
        $transport=[ordered]@{mode='fixture';nonce=$s.Nonce;lease_token=$s.Lease.Token;python=$python;python_sha256=$spec.PythonSHA256;
            cdb=$cdb;cdb_sha256=$pins[$cdb];fixture_sha256=$pins[(Join-Path $PSScriptRoot 'debug_fixture.py')]}
        $path=Join-Path $runRoot 'transport-spec.json';Write-WatchJson $path $transport
        $s.Context.SpecPath=$path;$s.Context.SpecSHA256=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()
        $s.Context.Guards.Add([IO.File]::Open($path,'Open','Read','Read'))
    }
    Prepare={param($s)
        $args=ConvertTo-AnimationArguments @('-I','-B',"$PSScriptRoot/cdb_transport.py",'--spec',$s.Context.SpecPath,
            '--spec-sha256',$s.Context.SpecSHA256,'--run-fixture')
        [IW7.CommunityBuild.BuildJob]::Prepare($python,$args,$runRoot)
    }
    Identity={param($s)
        $id=Get-BeaconJobIdentity $s.Owner $python 'rig-watch-fixture';$id['OriginalHandles']=$true;return $id
    }
    Deadline={param($owner,$due) [IW7.RigWatch.OriginalJobDeadline]::new($owner,$due)}
    Register={param($s) $null=Register-AnimationPhase $s.Owner $s.Lease.Token {Assert-RigWatchTime $s $hooks}}
    Poll={param($s)
        $path=Join-Path $runRoot 'transport.json'
        if(!(Test-Path -LiteralPath $path)){return [pscustomobject]@{Nonce=$s.Nonce;Healthy=$true;Bytes=0;Status='Loading'}}
        $event=Read-WatchJson $path
        Assert-RigWatchFixtureTransportEvent $event $s
        if($event.Status -cne 'TargetCreatedStopped'){Assert-RigWatchWorkers $event.Workers}
        if(($event.Status -ceq 'TargetCreatedStopped' -and !$s.AttachmentAuthorized) -or
           $event.Status -cin @('AttachedStopped','ArmedStopped','CaptureStopped')){
            $s.DescendantClosureUnproven=$true
            $s.Context.MembershipPhase=$event.Status
            try{
                $observation=[IW7.AnimationRig.JobMembers]::Capture($s.Owner)
                Confirm-RigWatchFixtureMembers $s $event $observation $python $cdb
            }catch{$s.Context.MembershipError=$_.Exception.Message;throw}
        }
        $s.Context.Transport=$event
        return $event
    }
    Attach={param($s)
        $path=Join-Path $runRoot 'attach-fixture.json'
        if(Test-Path -LiteralPath $path){throw 'Attachment already authorized.'}
        Write-WatchJson $path ([ordered]@{Nonce=$s.Nonce;Command='attach-owned-fixture-once';
            TargetPID=$s.Context.TargetCreation.pid;TargetCreatedFileTime=$s.Context.TargetCreation.created_filetime})
    }
    Startup={param($s)
        $path=Join-Path $runRoot 'start-fixture.json'
        if(Test-Path -LiteralPath $path){throw 'Startup already authorized.'}
        Write-WatchJson $path ([ordered]@{Nonce=$s.Nonce;Command='start-fixture-once';DebuggerPID=$s.Context.DebuggerIdentity.PID;
            TargetPID=$s.Context.TargetCreation.pid;TargetCreatedFileTime=$s.Context.TargetCreation.created_filetime})
    }
    Continue={param($s)
        $path=Join-Path $runRoot 'continue.json'
        if(Test-Path -LiteralPath $path){throw 'Continuation already exists.'}
        Write-WatchJson $path ([ordered]@{Nonce=$s.Nonce;Command='continue-once'})
    }
    Seal={param($s)
        $path=Join-Path $runRoot 'sealed.log';$s.Context.Guards.Add([IO.File]::Open($path,'Open','Read','Read'))
        $witness=Read-WatchJson (Join-Path $runRoot 'witness.json')
        $hash=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant();$bytes=(Get-Item -LiteralPath $path).Length
        if($hash -cne $s.Context.Transport.SealedSHA256 -or $bytes -ne $s.Context.Transport.SealedBytes -or
           $witness.log_sha256 -cne $hash -or $witness.run_id -cne $s.Nonce -or $witness.fixture_only -ne $true -or
           $witness.new_category -cne 'equals_current_name_address' -or $witness.semantic_acceptance -ne $false){throw 'Fixture witness binding differs.'}
        [pscustomobject]@{Nonce=$s.Nonce;SHA256=$hash;Bytes=$bytes;WitnessParsed=$true;FixtureOnly=$true}
    }
    Budget={param($s)
        $files=@(Get-ChildItem -LiteralPath $runRoot -Recurse -Force -File)
        if($files.Count -gt 32 -or @($files|Where-Object {$_.Attributes.HasFlag([IO.FileAttributes]::ReparsePoint)}).Count -or
           ($files|Measure-Object Length -Sum).Sum -gt 1MB){throw 'Fixture evidence cap exceeded.'}
        $memory=Get-IW7ResourceSnapshot
        if($memory.Committed -gt $memory.CommitLimit*0.85){throw 'Commit pressure exceeded runtime limit.'}
    }
    Save={param($s)
        if(Test-Path -LiteralPath $runRoot){
            $record=[ordered]@{};foreach($key in $s.Keys){if($key -notin @('Owner','Deadline','Context')){$record[$key]=$s[$key]}}
            $record['SourceBindings']=$pins;$record['FixtureOnly']=$true;$record['StockMutated']=$false
            $record['LastMembership']=$s.Context.LastMembership
            foreach($field in @('CreationMembership','AttachedMembership','MembershipPhase','MembershipError','TargetCreation','DebuggerIdentity')){
                $record[$field]=$s.Context[$field]
            }
            $record['TransportFailure']=$s.Context.TransportFailure
            if($s.Deadline){$record['DeadlineStop']=@{Attempted=$s.Deadline.StopAttempted;Completed=$s.Deadline.StopCompleted;ObservedMs=$s.Deadline.StopObservedMs;Failure=$s.Deadline.StopFailure}}
            Write-WatchJson (Join-Path $runRoot 'state.local.json') $record
        }
    }
    VerifySources={param($s)
        foreach($item in $s.Context.Baselines){
            $file=Get-Item -LiteralPath $item.Path
            if($file.Length -ne $item.Bytes -or $file.LastWriteTimeUtc.ToString('o') -cne $item.ModifiedUtc -or
               (Get-FileHash -LiteralPath $item.Path).Hash -ine $item.SHA256){throw 'Guarded source changed.'}
        }
    }
    Restore={param($s)
        # Fresh fixture output only: preserve evidence; there is no stock/profile
        # transaction to delete or roll back. Release guards only after closure.
        foreach($guard in $s.Context.Guards){$guard.Dispose()};return $true
    }
    Release={param($s) Exit-IW7ResourceLease -Token $s.Lease.Token;return $true}
    Quarantine={param($s)
        [AppDomain]::CurrentDomain.SetData(('IW7.RigWatch.Quarantine.'+$s.Nonce),$s)
        try{& $hooks.Save $s}catch{Write-Warning 'Quarantine retained in host; state save failed.'}
    }
    Delay={Start-Sleep -Milliseconds 50}
}
$result=Invoke-RigWatchFixtureTransaction $hooks $state
[ordered]@{Status=$result.Status;DiagnosticCaptured=$result.DiagnosticCaptured;OriginalJobClosed=$result.OriginalJobClosed;
    DescendantClosureUnproven=$result.DescendantClosureUnproven;Closed=$result.Closed;Restored=$result.Restored;
    LeaseReleased=$result.LeaseReleased;Quarantined=$result.Quarantined;FixtureOnly=$true;RetailRuntimeReady=$false;
    StatePath=(Join-Path $runRoot 'state.local.json');Failure=$result.Failure;CleanupFailure=$result.CleanupFailure}|ConvertTo-Json
if(!$result.DiagnosticCaptured){exit 2}
}finally{
    # Before admission, no native owner can exist. After admission the original
    # transaction owns these same guards through restoration or quarantine.
    if(!$state -or !$state.Lease){foreach($guard in $sourceGuards){$guard.Dispose()}}
}
