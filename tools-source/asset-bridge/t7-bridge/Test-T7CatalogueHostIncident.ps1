# Synthetic failed-receipt closure. No engine, game payload, native type or lease.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
. (Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1')
. (Join-Path $PSScriptRoot 'T7CatalogueHost.Core.ps1')
$script:checks=0
function Check([bool]$Value,[string]$Why){if(!$Value){throw $Why};$script:checks++}
function Refuses([scriptblock]$Body,[string]$Pattern){
    $caught=$false;try{& $Body}catch{$caught=$true;Check ($_.Exception.Message -match $Pattern) ('Unexpected refusal: '+$_.Exception.Message)}
    Check $caught ('Expected refusal: '+$Pattern)
}
function Write-Json([string]$Path,$Value){[IO.File]::WriteAllText($Path,($Value|ConvertTo-Json -Depth 12))}
$temporary=Join-Path ([IO.Path]::GetTempPath()) ('t7-host-incident-tests-'+[guid]::NewGuid().ToString('N'))
$null=[IO.Directory]::CreateDirectory($temporary)
$script:actualOpenPin=${function:Open-H1Pin}
$script:actualWrite=${function:Write-T7CatalogueHostEvidence}
try {
    & {
        function Test-IW7ResourceIdentity($Expected,$Actual){$Expected.PID -eq $Actual.PID -and $Expected.Image -ceq $Actual.Image -and ([datetimeoffset]$Expected.CreatedUtc).UtcTicks -eq ([datetimeoffset]$Actual.CreatedUtc).UtcTicks}
        function Get-T7CatalogueBootstraps($Plan){$Plan.Bootstraps}
        function Get-IW7ResourceStatus {$script:status}
        function Get-IW7ResourceProcesses {$script:processes}
        function Get-T7CatalogueHostIdentity {$script:currentHost}
        function Assert-T7CatalogueMain($Plan){if($script:mainDrift){throw 'Main drift'};[pscustomobject]@{Baseline='Stopped'}}
        function Assert-T7CatalogueMetadata($Row){$script:metadataReads.Add($Row.Path);if($script:metadataDrift){throw 'Metadata drift'}}
        function Get-T7CatalogueFileId([string]$Path){$script:idReads.Add($Path);if($script:idDrift){return 'wrong-id'};$script:fileIds[$Path]}
        function Open-H1Pin($Pin){
            Check ($Pin.Path -ceq $script:receiptPath) 'Incident attempted to hash anything except its bounded receipt.'
            $script:receiptHashReads++
            if($script:receiptDisposeFailure -or $script:receiptDisposeNoop){
                $guard=[pscustomobject]@{SafeFileHandle=[pscustomobject]@{IsClosed=$false}}
                $guard|Add-Member ScriptMethod Dispose {if($script:receiptDisposeFailure){throw 'Receipt disposal failed'}}
                return $guard
            }
            & $script:actualOpenPin $Pin
        }
        function Write-T7CatalogueHostEvidence([string]$Path,$Value){
            $script:publicationAttempts++
            if($script:publicationAttempts -eq $script:failPublication){throw 'Evidence publication failed'}
            & $script:actualWrite $Path $Value
            if($script:publicationAttempts -eq $script:failAfterPublication){throw 'Evidence failed after publication'}
        }
        function Save-Receipt {
            Write-Json $script:receiptPath $script:receipt
            $script:receiptHash=(Get-FileHash -LiteralPath $script:receiptPath -Algorithm SHA256).Hash.ToLowerInvariant()
        }
        function Reset-Case([int]$ExtraCount=0){
            $previous=[AppDomain]::CurrentDomain.GetData('IW7.T7CatalogueHost')
            if($previous){foreach($guard in $previous.Guards){try{$guard.Dispose()}catch{}}}
            [AppDomain]::CurrentDomain.SetData('IW7.H1.Quarantine.'+('a'*32),$null)
            $caseRoot=Join-Path $temporary ([guid]::NewGuid().ToString('N'))
            $runRoot=Join-Path $caseRoot 'run';$work=Join-Path $runRoot 'work';$stage=Join-Path $runRoot 'evidence'
            $null=[IO.Directory]::CreateDirectory($stage)
            $hostIdentity=[pscustomobject]@{PID=100;CreatedUtc='2026-10-12T20:00:00Z';Image='C:\synthetic\pwsh.exe'}
            $metadata=@('candidate','engine','steam','donor'|ForEach-Object {[pscustomobject]@{Path=(Join-Path $caseRoot $_);Bytes=1}})
            $plan=[pscustomobject]@{RunRoot=$runRoot;StageRoot=$stage;WorkingDirectory=$work;
                Image=(Join-Path $work 't7-zonetool-candidate.exe');CandidateSource=$metadata[0].Path;EngineSource=$metadata[1].Path;
                SteamSource=$metadata[2].Path;Zone=[pscustomobject]@{Path=$metadata[3].Path;RelativePath='zone/donor.ff'};
                Bootstraps=@();InputMetadata=$metadata}
            $guards=[Collections.Generic.List[object]]::new()
            foreach($index in 0..1){
                $path=Join-Path $caseRoot ('source-'+$index+'.txt');[IO.File]::WriteAllText($path,'synthetic frozen source')
                $guards.Add((& $script:actualOpenPin ([pscustomobject]@{Path=$path;Bytes=(Get-Item -LiteralPath $path).Length;SHA256=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()})))
            }
            $script:state=[pscustomobject]@{Plan=$plan;PlanPath=(Join-Path $caseRoot 'plan.json');PlanSHA256=('b'*64);RunRoot=$runRoot;
                ContractPath=(Join-Path $caseRoot 'contract.json');ContractSHA256=('c'*64);EntryPath='C:\synthetic\Invoke-T7CatalogueHost.ps1';
                Host=$hostIdentity;Contract=[pscustomobject]@{HostImage=$hostIdentity.Image;PreservedProcesses=@([pscustomobject]@{PID=200;CreatedUtc='2026-10-11T10:00:00Z';Image='C:\synthetic\python.exe'})};
                Guards=$guards;Phase='ClosurePending';RunnerReturned=$true;RunnerReturnedUtc='2026-10-12T20:00:10Z';
                RunnerError='Synthetic engine failure';CanExit=$false;ClosureError='Receipt lacks closure proof: InputsReverified';
                IncidentAttempted=$false;IncidentCanExit=$false;IncidentError=$null}
            $originals=@();$aliases=@();$script:fileIds=@{}
            $relative=@('t7-zonetool-candidate.exe','BlackOps3_UnrankedDedicatedServer.exe','steam_api64.dll','zone/donor.ff')
            for($index=0;$index -lt $ExtraCount;$index++){
                $path=Join-Path $caseRoot ('bootstrap-'+$index+'.ff');$aliasRelative='zone/bootstrap-'+$index+'.ff'
                $plan.Bootstraps+=,[pscustomobject]@{Path=$path;RelativePath=$aliasRelative}
                $plan.InputMetadata+=,[pscustomobject]@{Path=$path;Bytes=1};$relative+=,$aliasRelative
            }
            for($index=0;$index -lt $plan.InputMetadata.Count;$index++){
                $id='id-'+$index;$path=$plan.InputMetadata[$index].Path;$aliasPath=Join-Path $work $relative[$index]
                $originals+=,[pscustomobject]@{Path=$path;FileId=$id};$aliases+=,[pscustomobject]@{Path=$aliasPath;FileId=$id}
                $script:fileIds[$path]=$id;$script:fileIds[$aliasPath]=$id
            }
            $script:receipt=[pscustomobject]@{Schema='iw7.t7-catalogue-run/1';PlanSHA256=$script:state.PlanSHA256;
                TreeClosureConfirmed=$true;LeaseReleased=$true;InputsReverified=$false;Quarantined=$false;
                Identity=[pscustomobject]@{PID=300;Image=$plan.Image;CreatedUtc='2026-10-12T20:00:03Z'};LeaseToken=('a'*32);
                StartedUtc='2026-10-12T20:00:02Z';FinishedUtc='2026-10-12T20:00:09Z';InputFileIds=$originals;Aliases=$aliases;
                Status='Failed';CatalogueOutcome='NoCatalogue';ExitCode=1;TerminationRequested=$true;Ready=$false}
            $script:receiptPath=Join-Path $stage 'receipt.json';Save-Receipt
            $script:attempt=[pscustomobject]@{Schema='iw7.t7-catalogue-attempt/1';PlanSHA256=$script:state.PlanSHA256;StartedUtc='2026-10-12T20:00:01Z'}
            $script:startProof=[pscustomobject]@{Host=$hostIdentity;PlanSHA256=$script:state.PlanSHA256;ContractSHA256=$script:state.ContractSHA256}
            $script:returnProof=[pscustomobject]@{Host=$hostIdentity;PlanSHA256=$script:state.PlanSHA256;ContractSHA256=$script:state.ContractSHA256;RunnerReturned=$true;RunnerReturnedUtc=$script:state.RunnerReturnedUtc}
            Write-Json (Join-Path $runRoot 'attempt.json') $script:attempt
            Write-Json ($runRoot+'.host-start.json') $script:startProof
            Write-Json ($runRoot+'.host-return.json') $script:returnProof
            $script:currentHost=$hostIdentity;$script:status=[pscustomobject]@{Leases=@()}
            $script:processes=@([pscustomobject]@{PID=100;ParentPID=50;CreatedUtc=$hostIdentity.CreatedUtc;Image=$hostIdentity.Image;Name='pwsh.exe';Lab=$false},
                [pscustomobject]@{PID=200;ParentPID=40;CreatedUtc='2026-10-11T10:00:00Z';Image='C:\synthetic\python.exe';Name='python.exe';Lab=$false})
            $script:metadataDrift=$false;$script:idDrift=$false;$script:mainDrift=$false
            $script:receiptDisposeFailure=$false;$script:receiptDisposeNoop=$false;$script:receiptHashReads=0;$script:publicationAttempts=0
            $script:failPublication=0;$script:failAfterPublication=0
            $script:metadataReads=[Collections.Generic.List[string]]::new();$script:idReads=[Collections.Generic.List[string]]::new()
            [AppDomain]::CurrentDomain.SetData('IW7.T7CatalogueHost',$script:state)
        }
        function StillRetained {
            Check (!$script:state.CanExit -and !$script:state.IncidentCanExit) 'Refusal granted exit.'
            Check ($script:state.Guards.Count -eq 2 -and !@($script:state.Guards|Where-Object {$_.SafeFileHandle.IsClosed}).Count) 'Validation failure disposed wrapper guards.'
            Check ((Get-FileHash -LiteralPath $script:receiptPath).Hash.ToLowerInvariant() -ceq $script:receiptHash) 'Failed receipt was changed.'
        }
        foreach($count in @(0,1,8,20)){
            Reset-Case $count
            $originalError=$script:state.ClosureError;$guardSnapshot=@($script:state.Guards|ForEach-Object {$_})
            Refuses {Complete-T7CatalogueHost $script:state} 'closure proof: InputsReverified'
            $result=Complete-T7CatalogueHostIncident $script:state $script:receiptHash|ConvertFrom-Json
            Check ($result.IncidentCanExit -and !$result.CanExit -and !$result.InputsReverified -and !$result.Ready) 'Incident altered success/exit semantics.'
            Check ($result.RuntimeStatus -ceq 'Failed' -and $result.CatalogueOutcome -ceq 'NoCatalogue') 'Incident invented a catalogue result.'
            Check ($script:state.Phase -ceq 'IncidentClosed' -and $script:state.IncidentAttempted -and $script:state.Guards.Count -eq 0) 'Incident did not consume/dispose its wrapper guards.'
            Check (!@($guardSnapshot|Where-Object {!$_.SafeFileHandle.IsClosed}).Count) 'Actual wrapper handles were not disposed.'
            Check ($script:metadataReads.Count -eq 4+$count -and $script:idReads.Count -eq 2*(4+$count)) 'Incident embeds fixed input counts.'
            Check ($script:state.ClosureError -ceq $originalError -and $script:state.RunnerError -ceq 'Synthetic engine failure') 'Incident erased normal failure history.'
            $pre=Read-H1SmallJson ($script:state.RunRoot+'.host-incident-preflight.json')
            $post=Read-H1SmallJson ($script:state.RunRoot+'.host-incident-postflight.json')
            Check ($pre.MetadataCount -eq 4+$count -and $post.ObservedClosedWrapperGuards -eq 2 -and $post.ObservedOpenWrapperGuards -eq 0 -and $post.ReceiptGuardClosed) 'Incident evidence lacks observed guard disposal.'
            Check (!$post.ActualPTYExitObserved -and $post.IndependentAbsencePending -and !$post.FailedReceiptChanged) 'Sidecar overclaimed exit or changed receipt.'
            Check ($script:receiptHashReads -eq 1 -and (Get-FileHash -LiteralPath $script:receiptPath).Hash.ToLowerInvariant() -ceq $script:receiptHash) 'Payload hash or receipt mutation.'
            Refuses {Complete-T7CatalogueHostIncident $script:state $script:receiptHash} 'no re-entry'
            Check $script:state.IncidentCanExit 'Rejected duplicate incident lost proven permission.'
            Refuses {Complete-T7CatalogueHost $script:state} 'no re-entry'
            Check (!$script:state.CanExit) 'Normal Finish adopted incident permission.'
        }
        foreach($case in @('hash','status','reverified','tree','lease-proof','schema','plan','quarantined','quarantine-domain','identity','lifetime','count','alias','duplicate',
            'lease-live','native-live','native-reused','root-live','ambiguous','heavy','host-reused','host-missing','preserved','metadata','ids','main','client','host-child','native-child','ancestry',
            'start','return','attempt','preexisting','closed-guard','active-runner','different-state')){
            Reset-Case
            $pattern=switch($case){
                'hash' {'Bound input hash'}
                'status' {$script:receipt.Status='CatalogueObservedPendingDonorReview';'requires Failed'}
                'reverified' {$script:receipt.InputsReverified=$true;'requires Failed'}
                'tree' {$script:receipt.TreeClosureConfirmed=$false;'incident closure proof'}
                'lease-proof' {$script:receipt.LeaseReleased=$false;'incident closure proof'}
                'schema' {$script:receipt.Schema='wrong';'another plan'}
                'plan' {$script:receipt.PlanSHA256='wrong';'another plan'}
                'quarantined' {$script:receipt.Quarantined=$true;'native identity or quarantine'}
                'quarantine-domain' {[AppDomain]::CurrentDomain.SetData('IW7.H1.Quarantine.'+('a'*32),[object]::new());'quarantine remains'}
                'identity' {$script:receipt.Identity.Image='C:\wrong.exe';'native identity'}
                'lifetime' {$script:receipt.FinishedUtc='2026-10-12T20:01:00Z';'lifetime'}
                'count' {$script:receipt.Aliases=@();'identity count'}
                'alias' {$script:receipt.Aliases[0].FileId='wrong';'alias identity'}
                'duplicate' {$script:receipt.InputFileIds[1].FileId='id-0';'original identity'}
                'lease-live' {$script:status.Leases=@('occupied');'lease remains'}
                'native-live' {$script:processes+=,[pscustomobject]@{PID=300;ParentPID=100;Image=$script:state.Plan.Image;Name='t7-native.exe';Lab=$false};'Native root'}
                'native-reused' {$script:processes+=,[pscustomobject]@{PID=300;ParentPID=99;Image='C:\other.exe';Name='other.exe';Lab=$false};'reused PID'}
                'root-live' {$script:processes+=,[pscustomobject]@{PID=500;ParentPID=99;Image=(Join-Path $script:state.RunRoot 'other.exe');Name='other.exe';Lab=$false};'Native root'}
                'ambiguous' {$script:processes+=,[pscustomobject]@{PID=500;ParentPID=99;Image=$null;Name='t7-zonetool-candidate.exe';Lab=$false};'ambiguous'}
                'heavy' {$script:processes+=,[pscustomobject]@{PID=500;ParentPID=99;Image='C:\cl.exe';Name='cl.exe';Lab=$false};'Heavy process'}
                'host-reused' {$script:currentHost=[pscustomobject]@{PID=100;CreatedUtc='2026-10-12T21:00:00Z';Image='C:\synthetic\pwsh.exe'};'PID reuse'}
                'host-missing' {$script:processes=@($script:processes|Where-Object PID -NE 100);'Scheduler host'}
                'preserved' {$script:processes[1].CreatedUtc='2026-10-12T20:00:00Z';'Preserved process'}
                'metadata' {$script:metadataDrift=$true;'Metadata drift'}
                'ids' {$script:idDrift=$true;'file identity changed'}
                'main' {$script:mainDrift=$true;'Main drift'}
                'client' {$script:processes+=,[pscustomobject]@{PID=500;ParentPID=99;Image='C:\BlackOps3.exe';Name='BlackOps3.exe';Lab=$false};'Client or original'}
                'host-child' {$script:processes+=,[pscustomobject]@{PID=500;ParentPID=100;Image='C:\other.exe';Name='other.exe';Lab=$false};'Client or original'}
                'native-child' {$script:processes+=,[pscustomobject]@{PID=500;ParentPID=300;Image='C:\other.exe';Name='other.exe';Lab=$false};'Client or original'}
                'ancestry' {$script:processes[0].PSObject.Properties.Remove('ParentPID');'ancestry unavailable'}
                'start' {$script:startProof.ContractSHA256='wrong';Write-Json ($script:state.RunRoot+'.host-start.json') $script:startProof;'start/return proof'}
                'return' {$script:returnProof.RunnerReturned=$false;Write-Json ($script:state.RunRoot+'.host-return.json') $script:returnProof;'return proof'}
                'attempt' {$script:attempt.PlanSHA256='wrong';Write-Json (Join-Path $script:state.RunRoot 'attempt.json') $script:attempt;'Attempt marker'}
                'preexisting' {[IO.File]::WriteAllText(($script:state.RunRoot+'.host-incident-postflight.json'),'preserve me');'evidence already exists'}
                'closed-guard' {$script:state.Guards[0].Dispose();'guard lost'}
                'active-runner' {$script:state.RunnerReturned=$false;'Same returned'}
                'different-state' {[AppDomain]::CurrentDomain.SetData('IW7.T7CatalogueHost',[object]::new());'Same returned'}
            }
            Save-Receipt
            $hash=if($case -ceq 'hash'){'0'*64}else{$script:receiptHash}
            Refuses {Complete-T7CatalogueHostIncident $script:state $hash} $pattern
            if($case -cne 'closed-guard'){StillRetained}else{Check (!$script:state.CanExit -and !$script:state.IncidentCanExit) 'Lost guard granted exit.'}
            Check (!$script:state.IncidentAttempted -and $script:publicationAttempts -eq 0) 'Validation refusal attempted evidence/disposal.'
            # Restore only the synthetic registry so Reset-Case can dispose fixtures.
            [AppDomain]::CurrentDomain.SetData('IW7.T7CatalogueHost',$script:state)
        }
        foreach($case in @('preflight-publication','postflight-publication','partial-publication','postflight-partial-publication',
            'partial-disposal','wrapper-still-open','receipt-disposal','receipt-still-open')){
            Reset-Case
            $pattern=switch($case){
                'preflight-publication' {$script:failPublication=1;'publication failed'}
                'postflight-publication' {$script:failPublication=2;'publication failed'}
                'partial-publication' {$script:failAfterPublication=1;'after publication'}
                'postflight-partial-publication' {$script:failAfterPublication=2;'after publication'}
                'partial-disposal' {
                    $broken=[pscustomobject]@{SafeFileHandle=[pscustomobject]@{IsClosed=$false}}
                    $broken|Add-Member ScriptMethod Dispose {throw 'Wrapper disposal failed'}
                    $script:state.Guards.Add($broken);'Wrapper disposal failed'
                }
                'receipt-disposal' {$script:receiptDisposeFailure=$true;'Receipt disposal failed'}
                'wrapper-still-open' {
                    $broken=[pscustomobject]@{SafeFileHandle=[pscustomobject]@{IsClosed=$false}}
                    $broken|Add-Member ScriptMethod Dispose {}
                    $script:state.Guards.Add($broken);'Host guards remain open'
                }
                'receipt-still-open' {$script:receiptDisposeNoop=$true;'Incident receipt guard remains open'}
            }
            Refuses {Complete-T7CatalogueHostIncident $script:state $script:receiptHash} $pattern
            Check ($script:state.IncidentAttempted -and $script:state.Phase -ceq 'IncidentFailed' -and !$script:state.CanExit -and !$script:state.IncidentCanExit) 'Partial failure granted exit or hid failure.'
            if($case -cin @('postflight-publication','postflight-partial-publication','receipt-disposal','receipt-still-open')){
                Check ($script:state.Guards.Count -eq 0) 'Expected observed wrapper disposal before final evidence failure.'
            }
            Refuses {Complete-T7CatalogueHostIncident $script:state $script:receiptHash} 'no re-entry'
            Refuses {Complete-T7CatalogueHost $script:state} 'no re-entry'
            Check ((Get-FileHash -LiteralPath $script:receiptPath).Hash.ToLowerInvariant() -ceq $script:receiptHash) 'Partial closure changed failed receipt.'
        }
        Reset-Case
        Refuses {Complete-T7CatalogueHostIncident $script:state 'not-a-hash'} 'SHA256 required'
        StillRetained
        Close-T7CatalogueHostGuards $script:state
        [AppDomain]::CurrentDomain.SetData('IW7.T7CatalogueHost',$null)
    }
    # Real entry binding refuses incompatible actions and a different host before
    # importing scheduler/profile functions or invoking a runner.
    $entry=Join-Path $PSScriptRoot 'Invoke-T7CatalogueHost.ps1'
    $parameters=@{PlanPath='C:\synthetic\plan.json';PlanSHA256=('b'*64);RunRoot='C:\synthetic\run';
        HostContractPath='C:\synthetic\contract.json';HostContractSHA256=('c'*64)}
    Refuses {& $entry @parameters -CloseIncident -IncidentReceiptSHA256 ('d'*64)} 'original in-memory host contract'
    Refuses {& $entry @parameters -CloseIncident -Finish -IncidentReceiptSHA256 ('d'*64)} 'Parameter set cannot be resolved'
    Refuses {& $entry @parameters -CloseIncident -Run -IncidentReceiptSHA256 ('d'*64)} 'Parameter set cannot be resolved'
    $command=Get-Command $entry
    $incidentSet=@($command.ParameterSets|Where-Object Name -CEQ 'CloseIncident')
    Check ($incidentSet.Count -eq 1 -and @($incidentSet[0].Parameters|Where-Object {$_.Name -ceq 'IncidentReceiptSHA256' -and $_.IsMandatory}).Count -eq 1) 'Incident receipt digest is not mandatory.'
    Check (!(('IW7HudFileIdentity' -as [type]) -or ('IW7.AnimationProbe.NativeJob' -as [type]) -or ('IW7ResourceMemoryV1' -as [type]))) 'Incident tests loaded native runtime types.'
    [ordered]@{Status='Passed';Checks=$script:checks;SyntheticIncidentLifecycle=$true;NativeRun=$false;NativeTypesLoaded=$false;PayloadRead=$false;LeaseAcquired=$false}|ConvertTo-Json
}finally{
    $left=[AppDomain]::CurrentDomain.GetData('IW7.T7CatalogueHost')
    if($left -and $left.PSObject.Properties['Guards']){foreach($guard in $left.Guards){try{$guard.Dispose()}catch{}}}
    [AppDomain]::CurrentDomain.SetData('IW7.T7CatalogueHost',$null)
    [AppDomain]::CurrentDomain.SetData('IW7.H1.Quarantine.'+('a'*32),$null)
    $resolved=[IO.Path]::GetFullPath($temporary);$tempRoot=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if(!$resolved.StartsWith($tempRoot,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -cnotmatch '^t7-host-incident-tests-[0-9a-f]{32}$'){throw 'Unsafe test cleanup path.'}
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
