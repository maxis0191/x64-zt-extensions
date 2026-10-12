# Sound-local binding of existing admission, original job, and file transactions.
# Importing this file loads no native type and starts nothing.
function Assert-SoundFFPath([string]$Path) {
    if(!$Path -or ![IO.Path]::IsPathFullyQualified($Path)){throw 'Absolute sound path required.'}
    for($p=[IO.Path]::GetFullPath($Path);$p;$p=Split-Path $p -Parent){
        if((Test-Path -LiteralPath $p) -and ((Get-Item -LiteralPath $p -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Redirected sound path refused.'}
    }
}
function Get-SoundFFPin([string]$Path) {
    Assert-SoundFFPath $Path;$f=Get-Item -LiteralPath $Path
    if($f.PSIsContainer){throw 'Regular source file required.'}
    [pscustomobject]@{Path=$f.FullName;Bytes=$f.Length;SHA256=(Get-FileHash -LiteralPath $f.FullName).Hash;Attributes=[int]$f.Attributes;ModifiedUtc=$f.LastWriteTimeUtc.ToString('o')}
}
function Assert-SoundFFPin($Pin) {
    Assert-SoundFFPath $Pin.Path;$f=Get-Item -LiteralPath $Pin.Path
    if($Pin.SHA256 -cnotmatch '^[a-fA-F0-9]{64}$' -or $f.PSIsContainer -or (Get-FileHash -LiteralPath $Pin.Path).Hash -ine $Pin.SHA256){throw ('Sound input hash differs: '+$Pin.Path)}
    if($Pin.PSObject.Properties['Bytes'] -and $f.Length -ne $Pin.Bytes){throw 'Sound input size differs.'}
    if($Pin.PSObject.Properties['Attributes'] -and ([int]$f.Attributes -ne $Pin.Attributes -or $f.LastWriteTimeUtc.Ticks -ne ([datetimeoffset]$Pin.ModifiedUtc).UtcDateTime.Ticks)){throw 'Sound input metadata differs.'}
}
function Assert-SoundFFHelperSources([string]$SoundRoot,[string]$Repo,$HashInputs) {
    $helpers=Get-Content -LiteralPath (Join-Path $SoundRoot 'sab_ff_helpers.json') -Raw|ConvertFrom-Json
    if($helpers.schema -cne 'iw7.original-sound-helper-sources/1' -or $helpers.normalization -cne 'utf8-crlf-to-lf-only/1' -or
        @($helpers.files.PSObject.Properties).Count -ne 16){throw 'Explicit helper source identity required.'}
    foreach($entry in $helpers.files.PSObject.Properties){
        $path=Join-Path $Repo $entry.Name;Assert-SoundFFPath $path
        $raw=[IO.File]::ReadAllBytes($path)
        $utf8=[Text.UTF8Encoding]::new($false,$true)
        $canonical=$utf8.GetBytes($utf8.GetString($raw).Replace("`r`n","`n"))
        if([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($canonical)) -ine $entry.Value){throw ('Shared helper source changed: '+$entry.Name)}
        $pin=@($HashInputs|Where-Object Path -IEQ $path)
        if($pin.Count -ne 1){throw 'Exact helper runtime pin required.'}
        Assert-SoundFFPin $pin[0]
    }
}
function Assert-SoundFFExecutionPlan($Plan,[string]$SoundRoot) {
    foreach($entry in @(@('PhysicalBytes',8GB),@('CommitBytes',11GB),@('OutputStopBytes',64MB),@('LogBytesPerStream',2MB),@('CleanupMs',15000))){
        $value=$Plan.($entry[0]);if(($value -isnot [long] -and $value -isnot [int]) -or $value -ne $entry[1]){throw 'Exact typed native 8/11 budget and limits required.'}
    }
    if($Plan.Schema -cne 'iw7.original-sound-ff-execution/1' -or $Plan.HeavyExecutionAuthorizedByPlan -isnot [bool] -or $Plan.HeavyExecutionAuthorizedByPlan){throw 'Sound execution schema differs.'}
    foreach($path in @($Plan.RunRoot,$Plan.Work,$Plan.SharedRepo,$Plan.Python,$Plan.CandidateRoot,$Plan.Review.source)){Assert-SoundFFPath $path}
    if(Test-Path -LiteralPath $Plan.RunRoot){throw 'Fresh absent native RunRoot required; no retry.'}
    if($Plan.Work -ine (Join-Path $Plan.RunRoot 'work')){throw 'Owned work path differs.'}
    if($Plan.Review.phase_adapter -ine (Join-Path $SoundRoot 'sound_ff_phase.py')){throw 'Bound sound phase adapter required.'}
    $staged=@('sound/community_original_sound_v1.all.aliases.csv','sound_assets/community/original_chime_v1.flac','soundbank/community_original_sound_v1.all.json','zone_source/sdk_original_sound_v1.csv')
    if(($Plan.Review.source_stage_relatives|Sort-Object|ConvertTo-Json -Compress) -cne ($staged|Sort-Object|ConvertTo-Json -Compress)){throw 'Exact four original sound source inputs required.'}
    foreach($inputRoot in @($Plan.Review.source,$Plan.Review.stock_root,$Plan.CandidateRoot)){
        $full=[IO.Path]::GetFullPath($inputRoot).TrimEnd('\','/')
        if($Plan.RunRoot -ieq $full -or $Plan.RunRoot.StartsWith($full+'\',[StringComparison]::OrdinalIgnoreCase) -or $full.StartsWith($Plan.RunRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Native root overlaps input root.'}
    }
    $zone='sdk_original_sound_v1';$outputs=@('.ff','.sabl','.sabs'|ForEach-Object {'zone/'+$zone+$_})
    if(($Plan.MutableOutputs|ConvertTo-Json -Compress) -cne ($outputs|ConvertTo-Json -Compress)){throw 'All three owned sound outputs required.'}
    $phases=@($Plan.Review.phase_specs)
    if(($phases.phase -join ',') -cne 'build,verify,dump,read'){throw 'Exact four sound phases required.'}
    $pythonPin=@($Plan.HashInputs|Where-Object Path -IEQ $Plan.Python)
    if($pythonPin.Count -ne 1 -or $pythonPin[0].SHA256 -ine '4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a'){throw 'Reviewed Python required.'}
    foreach($phase in $phases){
        $isRead=$phase.phase -ceq 'read'
        $exe=if($isRead){$Plan.Python}else{Join-Path $Plan.Work 'zonetool.exe'}
        $hash=if($isRead){$pythonPin[0].SHA256}else{'e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04'}
        $args=if($isRead){@('-B',(Join-Path $SoundRoot 'read_sab.py'),'--source',$Plan.Review.source,'--banks',(Join-Path $Plan.Work 'zone'),
            '--contract',(Join-Path $SoundRoot 'sab_contract.json'),'--dump',(Join-Path $Plan.Work ('dump/'+$zone)),
            '--inventory',(Join-Path $Plan.RunRoot 'logs/verify/stdout.log'))}else{@('-headless','-unbuffered-io','-strict-content-sources',('-'+$phase.phase+'zone'),$zone)}
        if($phase.schema -cne 'iw7.material-v2-phase/1' -or $phase.exe -ine $exe -or $phase.sha256 -ine $hash -or $phase.cwd -ine $Plan.Work -or
            $phase.logs -ine (Join-Path $Plan.RunRoot ('logs/'+$phase.phase)) -or ($phase.timeout -isnot [int] -and $phase.timeout -isnot [long]) -or
            $phase.timeout -ne $(if($isRead){30}else{240}) -or ($phase.arguments|ConvertTo-Json -Compress) -cne ($args|ConvertTo-Json -Compress)){throw 'Sound phase command/path/time differs.'}
    }
    if(@($Plan.StockInputs).Count -ne 72 -or @($Plan.StockInputs|Where-Object Mode -CEQ HardLink).Count -ne 71 -or @($Plan.StockInputs|Where-Object Mode -CEQ Copy).Count -ne 1 -or
        @($Plan.StockInputs|Where-Object {$_.Mode -ceq 'Copy' -and $_.Relative -ceq 'main/fileSysCheck.cfg' -and $_.Bytes -eq 77}).Count -ne 1){throw 'Exact reused 71-link/77-byte sentinel profile required.'}
    $required=@('read_sab.py','read_flac.py','sound_ff_phase.py','sab_contract.json','sab_ff_helpers.json','SoundFF.Core.ps1','Build-SoundFF.ps1')|ForEach-Object {Join-Path $SoundRoot $_}
    Assert-SoundFFHelperSources $SoundRoot $Plan.SharedRepo $Plan.HashInputs
    foreach($path in $required){if(@($Plan.HashInputs|Where-Object Path -IEQ $path).Count -ne 1){throw 'Required sound source pin missing.'}}
}
function Save-SoundFFState($Context) {
    if(Test-Path -LiteralPath $Context.Plan.RunRoot){[IO.File]::WriteAllText($Context.StatePath,($Context.State|ConvertTo-Json -Depth 25))}
}
function Get-SoundFFFileId([string]$Path) {[IW7HudFileIdentity]::Read($Path)}
function New-SoundFFJob([string]$Python,[string]$Arguments,[string]$Work) {[IW7.CommunityBuild.BuildJob]::Prepare($Python,$Arguments,$Work)}
function Assert-SoundFFReadback($Read,$Artifacts) {
    if($Read.schema -cne 'iw7.original-sound-sab-read/1' -or $Read.status -cne 'SABBytesVerified' -or
        $Read.loaded.pcm_sha256 -cne '72cb02b5178ce424fd3df3dbfb28b0b9613f69a4da3af71a022b8b542a46ddd9'){throw 'Independent SAB receipt differs.'}
    if(($Read.inventory_asset_count -isnot [int] -and $Read.inventory_asset_count -isnot [long]) -or $Read.inventory_asset_count -ne 2){throw 'Soundbank plus native branding inventory required.'}
    foreach($name in 'source_alias_verified','source_alias_matches_sab_asset','dump_alias_values_verified','inventory_verified','dump_seek_frame_bytes_verified'){
        if($Read.$name -isnot [bool] -or !$Read.$name){throw 'Required sound readback evidence missing.'}
    }
    foreach($name in 'native_alias_index_verified','checksum_checksum_verified','dump_standalone_flac_validated','playback_verified','ready'){
        if($Read.$name -isnot [bool] -or $Read.$name){throw 'Sound readback overclaims acceptance.'}
    }
    foreach($pair in @(@('loaded','.sabl'),@('streamed','.sabs'))){
        $rows=@($Artifacts|Where-Object {$_.Relative.EndsWith($pair[1])});$bank=$Read.($pair[0])
        if($rows.Count -ne 1 -or $bank.sha256 -ine $rows[0].SHA256 -or ($bank.bytes -isnot [long] -and $bank.bytes -isnot [int]) -or $bank.bytes -ne $rows[0].Bytes){throw 'Reader bank bytes do not match retained artifacts.'}
    }
}
function Import-SoundFFHelpers([string]$Repo) {
    foreach($relative in 'ops/Base-Client.Core.ps1','ops/Resource-Scheduler.Core.ps1','ops/model-lab/ModelFF.Core.ps1',
        'sdk/modding/BeaconFF.Core.ps1','tools-source/asset-bridge/common/StockBinding.Core.ps1','tools-source/asset-bridge/surfaces/MaterialV2.Core.ps1'){
        . (Join-Path $Repo $relative)
    }
}
function Initialize-SoundFFNativeTypes([string]$Repo) {
    Add-Type -LiteralPath (Join-Path $Repo 'tools-source/asset-bridge/model/BuildJob.cs')
    Add-Type -LiteralPath (Join-Path $Repo 'ops/hud-lab/HudFileIdentity.cs')
}
function Measure-SoundFFOutputs($Context) {
    $items=@(Get-ChildItem -LiteralPath $Context.Plan.RunRoot -Recurse -Force)
    if(@($items|Where-Object {$_.Attributes -band [IO.FileAttributes]::ReparsePoint}).Count){throw 'Redirected output refused.'}
    $files=@($items|Where-Object {!$_.PSIsContainer})
    $bytes=Measure-MaterialV2OutputFiles $files $Context.Plan.Work $Context.State.Inputs
    Assert-BeaconOutputBudget $bytes;$Context.State.MaxObservedBytes=[math]::Max($Context.State.MaxObservedBytes,$bytes)
    foreach($file in $files){if($file.Name -in 'stdout.log','stderr.log' -and $file.Length -gt 2MB){throw 'Sound phase log exceeded 2 MiB.'}}
    $Context.State.FinalObservedBytes=$bytes
}
function Invoke-SoundFFPhase($Context,$Spec) {
    $plan=$Context.Plan;$state=$Context.State
    $specPath=Join-Path $plan.RunRoot ($Spec.phase+'-spec.json')
    [IO.File]::WriteAllText($specPath,($Spec|ConvertTo-Json -Depth 10));$specHash=(Get-FileHash -LiteralPath $specPath).Hash
    $Context.Guards.Add([IO.File]::Open($specPath,'Open','Read','Read'))
    $arguments=ConvertTo-MaterialV2Arguments @('-B',$plan.Review.phase_adapter,'--spec',$specPath,'--spec-sha256',$specHash,'--shared-repo',$plan.SharedRepo)
    $Context.Owner=New-SoundFFJob $plan.Python $arguments $plan.Work;$Context.Closed=$false
    $identity=Get-BeaconJobIdentity $Context.Owner $plan.Python $Spec.phase;$identity.SpecSHA256=$specHash;$identity.NativeExecutableSHA256=$Spec.sha256
    $state.Phases+=,$identity;Save-SoundFFState $Context
    $started=Start-MaterialV2OwnedPhase $Context.Owner $Context.Lease.Token
    $identity.StartedUtc=$started.StartedUtc;$identity.SchedulerAttached=$started.SchedulerAttached
    Wait-MaterialV2OwnedPhase $Context.Owner $identity $started.StartedMonotonicMs $Spec.timeout {
        param($snapshot,$changed)
        if($changed){Save-SoundFFState $Context}
        if(Test-Path -LiteralPath (Join-Path $plan.RunRoot 'stop.request')){throw 'Central original-job stop requested.'}
        Measure-SoundFFOutputs $Context
        $memory=Get-IW7ResourceSnapshot;if($memory.Committed -gt $memory.CommitLimit*.85){throw 'Commit pressure stop.'}
    }
    $Context.Closed=$true;$Context.Owner.Dispose();$Context.Owner=$null
    Assert-MaterialV2PhaseResult (Read-BeaconJson (Join-Path $Spec.logs 'phase.json') 16384) $Spec.phase $Spec.sha256 $identity
    $receipt=Read-BeaconJson (Join-Path $Spec.logs 'sound-phase.json') 16384
    if($receipt.schema -cne 'iw7.original-sound-ff-phase/1' -or $receipt.phase -cne $Spec.phase -or $receipt.verified -isnot [bool] -or !$receipt.verified -or
        $receipt.explicit_normal_pipe_returns -isnot [bool] -or !$receipt.explicit_normal_pipe_returns -or @($receipt.drain_exception_types).Count -ne 0 -or
        (Get-FileHash -LiteralPath (Join-Path $Spec.logs 'phase.json')).Hash -ine $receipt.existing_runner_receipt_sha256){throw 'Sound phase explicit EOF/native receipt failed.'}
    $identity.SoundReceipt=$receipt;Save-SoundFFState $Context
    # Shared wait already checks a fresh monotonic value after its getter/save
    # callback. Receipt/hash/dispose/final-save time must not escape this bound.
    $identity.PostReceiptDecisionElapsedMs=(Get-MaterialV2MonotonicMs)-$started.StartedMonotonicMs
    if($identity.PostReceiptDecisionElapsedMs -ge ($Spec.timeout+5)*1000){throw 'Sound phase acceptance deadline expired after receipt/save.'}
}
function Complete-SoundFFTransaction($Context) {
    $state=$Context.State;$intact=$true;$disposed=$true
    try {
        if($Context.Owner){
            if(!$Context.Closed){$state.JobCleanup=[ordered]@{};$Context.Closed=Stop-MaterialV2OwnedPhase $Context.Owner $state.JobCleanup}
            try{$Context.Owner.Dispose();$Context.Owner=$null}catch{$disposed=$false;$state.CleanupError=$_.Exception.Message}
        }
        foreach($pin in $Context.Plan.HashInputs){try{Assert-SoundFFPin $pin}catch{$intact=$false;$state.CleanupError=$_.Exception.Message}}
        try{Assert-SoundFFPin ([pscustomobject]@{Path=$Context.PlanPath;SHA256=$Context.PlanSHA256})}catch{$intact=$false;$state.CleanupError=$_.Exception.Message}
        if($Context.InputsGuarded){try{Assert-ModelFFInputs $state.Inputs $Context.Plan.Work -SourceOnly;Assert-FFStockContent $state.Inputs}catch{$intact=$false;$state.CleanupError=$_.Exception.Message}}
        $state.JobClosureVerified=$Context.Closed;$state.JobDisposeCompleted=$disposed
        $state.SourceHashesUnchanged=($intact -and $Context.Closed -and $disposed)
        # Hard links cannot be removed while their source denies delete sharing.
        # Dispose owner first; unknown closure retains lease/evidence, not locks.
        foreach($guard in $Context.Guards){$guard.Dispose()};$Context.Guards.Clear();$state.ReadGuardsReleased=$true
        if(!$state.SourceHashesUnchanged){throw 'Closure or source proof incomplete; quarantine original inputs.'}
        if($Context.Saved){
            $state.RestorationStatus='Validating'
            Assert-ModelFFVacant $Context.Plan.Work
            Assert-ModelFFInputs $state.Inputs $Context.Plan.Work
            Restore-IW7BaseTransaction $state.Transaction
            $state.RestorationStatus='FilesRestoredPendingSourceProof'
            Assert-ModelFFInputs $state.Inputs $Context.Plan.Work -SourceOnly
            # Fresh guards and full content proof after unlink/restoration.
            foreach($entry in $state.Inputs){$Context.Guards.Add([IO.File]::Open($entry.Source,'Open','Read','Read'))}
            Assert-ModelFFInputs $state.Inputs $Context.Plan.Work -SourceOnly
            Assert-FFStockContent $state.Inputs
            foreach($pin in $Context.Plan.HashInputs){Assert-SoundFFPin $pin}
            foreach($artifact in $state.Artifacts){
                $Context.Guards.Add([IO.File]::Open($artifact.ArtifactPath,'Open','Read','Read'))
                Assert-SoundFFPin ([pscustomobject]@{Path=$artifact.ArtifactPath;SHA256=$artifact.SHA256;Bytes=$artifact.Bytes})
            }
            $state.Restored=$true;$state.StockPreserved=$true;$state.RestorationStatus='Confirmed'
        }else{$state.Restored=$true;$state.StockPreserved=$true;$state.RestorationStatus='NotStaged'}
        if(Test-Path -LiteralPath $Context.Plan.RunRoot){Measure-SoundFFOutputs $Context};Save-SoundFFState $Context
        if($Context.Lease){Exit-IW7ResourceLease -Token $Context.Lease.Token;$state.RetainedLeaseToken=$null;$Context.Lease=$null}
    }catch{
        $state.Quarantined=$true;$state.Status='Failed';$state.CleanupError=$_.Exception.Message;$state.SourceHashesUnchanged=$false
        if($state.RestorationStatus -ceq 'FilesRestoredPendingSourceProof'){$state.RestorationStatus='FilesRestoredUnverified'}
        elseif($state.RestorationStatus -cne 'Confirmed'){$state.RestorationStatus='DeferredQuarantine'}
    }
    finally{foreach($guard in $Context.Guards){$guard.Dispose()};$Context.Guards.Clear();$state.ReadGuardsReleased=$true;Save-SoundFFState $Context}
}
function Invoke-SoundFFTransaction($Plan,[string]$PlanPath,[string]$PlanSHA256) {
    $state=[ordered]@{Schema='iw7.original-sound-ff-result/1';Status='Preparing';Work=$Plan.Work;Inputs=@();Phases=@();Artifacts=@();Reader=$null;
        Transaction=$null;Restored=$false;StockPreserved=$false;RestorationStatus='Pending';JobClosureVerified=$false;JobDisposeCompleted=$false;
        SourceHashesUnchanged=$false;ReadGuardsReleased=$false;Quarantined=$false;RetainedLeaseToken=$null;Failure=$null;CleanupError=$null;
        MaxObservedBytes=0L;FinalObservedBytes=$null;JobCleanup=$null;Ready=$false;PlaybackVerified=$false}
    $c=[pscustomobject]@{Plan=$Plan;PlanPath=$PlanPath;PlanSHA256=$PlanSHA256;State=$state;StatePath=(Join-Path $Plan.RunRoot 'state.local.json');
        Lease=$null;Owner=$null;Closed=$true;Saved=$false;InputsGuarded=$false;Guards=[Collections.Generic.List[IDisposable]]::new()}
    try {
        foreach($pin in @($Plan.HashInputs)+@([pscustomobject]@{Path=$PlanPath;SHA256=$PlanSHA256})){
            $c.Guards.Add([IO.File]::Open($pin.Path,'Open','Read','Read'));Assert-SoundFFPin $pin
        }
        . Import-SoundFFHelpers $Plan.SharedRepo
        $c.Lease=Enter-IW7ResourceLease -Scope $Plan.Work -Kind Extract -PhysicalBytes 8GB -CommitBytes 11GB -Owner 'Original sound SAB and FF build verify dump read'
        $state.RetainedLeaseToken=$c.Lease.Token
        [IO.Directory]::CreateDirectory($Plan.RunRoot)|Out-Null;Save-SoundFFState $c
        Initialize-SoundFFNativeTypes $Plan.SharedRepo
        $candidate=Assert-BeaconCandidate $Plan.CandidateRoot $Plan.CandidateReceiptSHA256
        $state.Inputs=@($Plan.StockInputs)
        $stage=@(foreach($relative in $Plan.Review.source_stage_relatives){
            $path=Resolve-IW7BasePath $Plan.Review.source $relative;$pin=@($Plan.HashInputs|Where-Object Path -IEQ $path)
            if($pin.Count -ne 1){throw 'Staged original sound input pin missing.'}
            [pscustomobject]@{Relative=$relative;Source=$path;ExpectedSHA256=$pin[0].SHA256}
        })+@([pscustomobject]@{Relative='zonetool.exe';Source=$candidate.Path;ExpectedSHA256=$candidate.SHA256})
        foreach($entry in $stage){
            if($entry.Relative -iin $state.Inputs.Relative){throw 'Source/stock collision.'}
            $pin=Get-SoundFFPin $entry.Source
            $state.Inputs+=,[pscustomobject]@{Relative=$entry.Relative;Source=$entry.Source;Mode='HardLink';Bytes=$pin.Bytes;ModifiedUtc=$pin.ModifiedUtc;
                Attributes=$pin.Attributes;ExpectedSHA256=$entry.ExpectedSHA256}
        }
        foreach($entry in $state.Inputs){
            $null=Resolve-IW7BasePath (Split-Path $entry.Source) (Split-Path $entry.Source -Leaf)
            $c.Guards.Add([IO.File]::Open($entry.Source,'Open','Read','Read'));$id=Get-SoundFFFileId $entry.Source
            Assert-FFStockIdentity $entry $id;Set-MaterialV2SourceIdentity $entry $id
            if('ExpectedSourceId' -cnotin $entry.PSObject.Properties.Name){$entry|Add-Member NoteProperty ExpectedSourceId $id}
        }
        $c.InputsGuarded=$true;Assert-ModelFFInputs $state.Inputs $Plan.Work -SourceOnly;Assert-FFStockContent $state.Inputs
        [IO.Directory]::CreateDirectory($Plan.Work)|Out-Null
        $state.Transaction=Save-IW7BaseTransaction ([pscustomobject]@{GameRoot=$Plan.Work;MutableFiles=@($state.Inputs.Relative)+@($Plan.MutableOutputs);ProfileDirectory='unused';ProfileDirectories=@()}) (Join-Path $Plan.RunRoot 'backup')
        $c.Saved=$true;Save-SoundFFState $c
        foreach($entry in $state.Inputs){
            $target=Resolve-IW7BasePath $Plan.Work $entry.Relative;[IO.Directory]::CreateDirectory((Split-Path $target))|Out-Null
            if($entry.Mode -ceq 'Copy'){Copy-Item -LiteralPath $entry.Source -Destination $target}else{New-Item -ItemType HardLink -Path $target -Target $entry.Source|Out-Null}
            $entry|Add-Member NoteProperty TargetId (Get-SoundFFFileId $target)
            if($entry.Mode -ceq 'HardLink' -and $entry.TargetId -cne $entry.SourceId){throw 'Staged hardlink identity differs.'}
            if($entry.Mode -ceq 'Copy'){Assert-MaterialV2CopyIdentity $entry $entry.TargetId;(Get-Item -LiteralPath $target).IsReadOnly=$false}
        }
        Assert-ModelFFInputs $state.Inputs $Plan.Work
        [IO.Directory]::CreateDirectory((Join-Path $Plan.RunRoot 'logs'))|Out-Null
        foreach($spec in $Plan.Review.phase_specs){
            Invoke-SoundFFPhase $c $spec
            if($spec.phase -ceq 'build'){
                [IO.Directory]::CreateDirectory((Join-Path $Plan.RunRoot 'artifacts'))|Out-Null
                foreach($relative in $Plan.MutableOutputs){
                    $path=Resolve-IW7BasePath $Plan.Work $relative;$file=Get-Item -LiteralPath $path
                    $wanted=if($relative.EndsWith('.sabl')){114816}elseif($relative.EndsWith('.sabs')){4096}else{0}
                    if(($wanted -and $file.Length -ne $wanted) -or $file.Length -lt 1 -or $file.Length -gt 1MB){throw 'Native sound output size differs.'}
                    $c.Guards.Add([IO.File]::Open($path,'Open','Read','Read'));$hash=(Get-FileHash -LiteralPath $path).Hash
                    $target=Join-Path $Plan.RunRoot ('artifacts/'+$file.Name);if(Test-Path -LiteralPath $target){throw 'Artifact overwrite refused.'}
                    Copy-Item -LiteralPath $path -Destination $target
                    if((Get-FileHash -LiteralPath $target).Hash -ine $hash){throw 'Artifact preservation hash differs.'}
                    $c.Guards.Add([IO.File]::Open($target,'Open','Read','Read'))
                    $state.Artifacts+=,[pscustomobject]@{Relative=$relative;Bytes=$file.Length;SHA256=$hash;ArtifactPath=$target}
                }
            }
        }
        $read=Read-BeaconJson (Join-Path $Plan.RunRoot 'logs/read/stdout.log') 16384
        Assert-SoundFFReadback $read $state.Artifacts
        $state.Reader=$read;$state.Status='SoundSABAndFFBytesVerified';Measure-SoundFFOutputs $c;Save-SoundFFState $c
    }catch{$state.Status='Failed';$state.Failure=$_.Exception.Message}
    finally{Complete-SoundFFTransaction $c}
    if($state.Status -ceq 'Failed' -or !$state.JobClosureVerified -or !$state.SourceHashesUnchanged -or !$state.Restored -or $state.RetainedLeaseToken){throw ('Sound FF incomplete; preserve state/inputs/reservation. '+$state.Failure+' '+$state.CleanupError)}
    $state
}
