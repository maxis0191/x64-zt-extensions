param([Parameter(Mandatory)][string]$ProviderRoot,[switch]$Flac)
$ErrorActionPreference='Stop'
. "$PSScriptRoot/BuildCandidate.Core.ps1"
. "$PSScriptRoot/../../../../../ops/Resource-Scheduler.Core.ps1"
if((Get-FileHash -LiteralPath (Join-Path $ProviderRoot 'supervision.ps1')).Hash -ine 'b6125dfaa4c6b16e4ebc6f54f160369788cfe5290f4c734edb925101af4f3471'){throw 'Exact v6 supervision required.'}
. (Join-Path $ProviderRoot 'supervision.ps1')
$script:checks=0
function Check($Value,[string]$Message){$script:checks++;if(!$Value){throw $Message}}
function Get-IW7ResourceSnapshot { @{PhysicalTotal=1GB;PhysicalAvailable=0;CommitLimit=1GB;Committed=1GB} }
function Enter-IW7ResourceLease {param($Scope,$Kind,$PhysicalBytes,$CommitBytes,$Owner)
    if($PhysicalBytes -ne $plan.physical_bytes -or $CommitBytes -ne $plan.commit_bytes){throw 'Reviewed build estimates changed.'}
    $script:admissions++;@{Token=$script:fixtureToken}
}
function Exit-IW7ResourceLease { $script:releases++;if($script:mode -ceq 'release-failure'){throw 'fixture refused release'} }
function Add-IW7ResourceProcess { $script:registrations++ }
function Initialize-ChecksumBuildTypes { $script:typeMocks++;if($script:mode -ceq 'late-helper'){$script:clock+=3600001} }
function Open-FlacBuildSdkInputs {if($script:admissions -ne 1 -or $script:releases){throw 'SDK guard mock reached outside admitted lifetime'}}
function Wait-AuditPoll { throw 'Fixture must finish without polling' }
function New-ChecksumBuildOwner {
    param($Plan,$Arguments)
    $script:factoryCalls++
    if($script:mode -ceq 'factory-failure'){throw 'fixture factory failed'}
    $job=[pscustomobject]@{PID=43210;Image=$Plan.python;CreatedUtc='2026-10-12T00:00:00.0000000Z';Priority=0x4000;
        Exited=$false;Active=1;ExitCode=0;Resumed=$false;Disposed=$false;Stopped=$false}
    $job|Add-Member ScriptMethod Resume {$this.Resumed=$true;$this.Exited=$true;$this.Active=0;if($script:mode -ceq 'nonzero'){$this.ExitCode=1}}
    $job|Add-Member ScriptMethod Stop {$this.Stopped=$true;if($script:mode -ceq 'closure-failure'){throw 'fixture closure unavailable'};$this.Exited=$true;$this.Active=0}
    $job|Add-Member ScriptMethod Dispose {$this.Disposed=$true}
    $script:fixtureJob=$job
    if($script:mode -ceq 'identity-failure'){$job.Priority=0}
    if($script:mode -ceq 'closure-failure'){$job|Add-Member ScriptMethod Resume {throw 'fixture resume failed'} -Force}
    if($script:mode -ceq 'late-prepare'){$script:clock+=3600001}
    if($script:mode -ceq 'late-identity'){
        $job|Add-Member NoteProperty FixtureImage $Plan.python
        $job|Add-Member ScriptProperty Image {$script:clock+=3600001;$this.FixtureImage} -Force
    }
    return $job
}
function Complete-ChecksumBuildEvidence {
    param($Owner,$Record,$Started,$Plan,$Context,$Measure,$Residual)
    $Record.QualifiedClosure=@{AcceptanceGranted=$true}
    $Context.AcceptedReceipt=@{artifacts=@{}}
    if($Flac){
        $roles=@{candidate_exe='bin/candidate.exe';candidate_pdb='bin/candidate.pdb';common_library='common/common.lib';
            probe_original='probe/original.exe';probe_patched='probe/patched.exe';probe_flac='probe/flac-header.exe'}
        foreach($role in $roles.Keys){
            $path=Join-Path $Plan.candidate $roles[$role]
            [IO.Directory]::CreateDirectory((Split-Path $path -Parent))|Out-Null
            [IO.File]::WriteAllBytes($path,[byte[]](1,2,3))
            $hash=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()
            $Context.AcceptedReceipt.artifacts[$role]=@{relative=$roles[$role];bytes=3;sha256=$hash}
            [void]$script:flacFinalPaths.Add($path)
            if($script:mode -ceq ('final-artifact-'+$role)){[IO.File]::WriteAllBytes($path,[byte[]](3,2,1))}
        }
    }
    $script:completionCalls++
}
function Get-ChecksumBuildClock { $script:clock }
function Get-AuditMonotonicMs { $script:clock }
function Read-ChecksumBuildChunk($Stream,[byte[]]$Buffer) {
    $script:readCalls++
    if([IO.Path]::GetFileName($Stream.Name) -ceq 'input.bin'){$script:sourceReadCalls++}
    if($script:mode -ceq 'post-proof-failure' -and $script:sourceReadCalls -eq 3){throw 'fixture post-proof read failure'}
    $n=$Stream.Read($Buffer,0,$Buffer.Length)
    if($script:mode -ceq 'late-read'){$script:clock+=3600001}
    $n
}
$script:hashImplementation=(Get-Item Function:\Get-ChecksumBuildHash).ScriptBlock
function Get-ChecksumBuildHash($Stream,$Context) {
    if($Flac -and $script:flacFinalPaths.Contains($Stream.Name)){
        Check ($script:fixtureJob.Exited -and $script:fixtureJob.Active -eq 0) 'final artifact read before positive original-job closure'
        Check ($script:admissions -eq 1 -and $script:releases -eq 0 -and $Context.Record.RetainedLeaseToken -ceq $script:fixtureToken) 'final artifact read outside original reservation'
        Check (!$Context.Record.Success -and $Context.Record.DeferredArtifactProofPending -and !$Context.Record.FinalArtifactsVerified) 'success or proof advertised before final hashes'
        $writeDenied=$false
        try{$writer=[IO.File]::Open($Stream.Name,'Open','Write','ReadWrite');$writer.Dispose()}catch [IO.IOException]{$writeDenied=$true}
        Check $writeDenied 'artifact not under retained deny-write guard'
        [void]$script:flacFinalChecked.Add($Stream.Name)
    }
    & $script:hashImplementation $Stream $Context
}
$script:measureImplementation=(Get-Item Function:\Measure-ChecksumBuildOutput).ScriptBlock
function Measure-ChecksumBuildOutput([string]$Root) {
    $n=& $script:measureImplementation $Root
    if($script:mode -ceq 'late-final-state' -and (Test-Path -LiteralPath (Join-Path $Root 'supervisor-state.json'))){$script:clock+=3600001}
    $n
}
$temp=Join-Path ([IO.Path]::GetTempPath()) ('sound-build-lifecycle-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($temp)|Out-Null
try {
    $source=Join-Path $temp 'input.bin';[IO.File]::WriteAllBytes($source,[byte[]](1,2,3,4))
    $f=Get-Item -LiteralPath $source
    $entry=@{Path=$source;Bytes=$f.Length;Attributes=[int]$f.Attributes;ModifiedUtcTicks=$f.LastWriteTimeUtc.Ticks;
        SHA256=(Get-FileHash -LiteralPath $source).Hash.ToLowerInvariant()}
    $cases=@('success','nonzero','factory-failure','identity-failure','closure-failure','release-failure','input-drift','late-read','post-proof-failure','late-final-state','late-helper','late-prepare','late-identity')
    if($Flac){$cases+=@('candidate_exe','candidate_pdb','common_library','probe_original','probe_patched','probe_flac')|ForEach-Object {'final-artifact-'+$_}}
    foreach($case in $cases){
        $script:mode=$case;$script:admissions=0;$script:releases=0;$script:registrations=0;$script:typeMocks=0;$script:completionCalls=0;$script:fixtureJob=$null
        $script:clock=1000L;$script:readCalls=0;$script:sourceReadCalls=0;$script:factoryCalls=0
        $script:flacFinalPaths=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        $script:flacFinalChecked=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        $script:fixtureToken='fixture-sound-'+[guid]::NewGuid().ToString('N')
        $candidate=Join-Path $temp $case
        $plan=@{candidate=$candidate;physical_bytes=1;commit_bytes=512MB;python=(Join-Path $temp 'python.exe');worker=(Join-Path $temp 'worker.py');seal_sha256=('a'*64);
            environment=@{SystemRoot=$env:SystemRoot;TEMP=$env:TEMP;TMP=$env:TMP}}
        if($Flac){$plan.schema='iw7.sound-flac-dump-build-plan/1';$plan.flac=@{sources=@()}}
        $bootstrap=@{Retain=$false}
        $copy=$entry.Clone();if($case -ceq 'input-drift'){$copy.SHA256='b'*64}
        $failure=$null
        try{$null=Invoke-ChecksumBuild $plan @{Inputs=@($copy)} (Join-Path $temp 'plan.json') ('c'*64) $bootstrap}
        catch{$failure=$_.Exception.Message}
        $state=Get-Content -Raw -LiteralPath (Join-Path $candidate 'supervisor-state.json')|ConvertFrom-Json
        Check ($script:admissions -eq 1) "$case admitted more than once"
        Check ($state.OutputBytes -eq (Measure-ChecksumBuildOutput $candidate)) "$case final output accounting differs"
        if($case -ceq 'success'){
            Check (!$failure -and $state.Success -and $state.LeaseReleased) 'successful mock lifecycle failed'
            $expectedRead=if($Flac){26}else{8}
            Check ($state.InputsVerifiedBefore -and $state.InputsVerifiedAfter -and $state.ProofBytesRead -eq $expectedRead) 'two guarded source proofs or artifact bytes missing'
            if($Flac){Check ($script:flacFinalChecked.Count -eq 6 -and $state.FinalArtifactsVerified -and !$state.DeferredArtifactProofPending) 'all six post-closure artifacts were not proved'}
            Check ($script:fixtureJob.Resumed -and $script:fixtureJob.Disposed -and !$script:fixtureJob.Stopped) 'natural closure changed'
            Check ($script:completionCalls -eq 1 -and $script:releases -eq 1) 'completion/release count differs'
        }else{
            Check ($failure -and !$state.Success) "$case accidentally accepted"
            if($case.StartsWith('final-artifact-')){Check (!$state.FinalArtifactsVerified -and $state.DeferredArtifactProofPending) 'failed final artifact promoted success'}
            if($case -in 'factory-failure','closure-failure','post-proof-failure'){
                Check (!$state.LeaseReleased -and $bootstrap.Retain -and $script:releases -eq 0) "$case unknown closure released its lease"
            }elseif($case -ceq 'release-failure'){
                Check (!$state.LeaseReleased -and $state.RetainedLeaseToken -ceq $script:fixtureToken) 'release failure lost token'
            }else{Check ($state.LeaseReleased -and $script:releases -eq 1) "$case closed failure did not release"}
            if($case -ceq 'late-read'){Check ($state.ProofBytesRead -eq 4 -and !$state.NativeRootResumed) 'late read lost byte accounting or resumed native'}
            if($case -ceq 'late-final-state'){Check ($state.ElapsedMs -ge 3600000) 'late final state accepted stale clock'}
            if($case -in 'late-helper','late-prepare','late-identity'){
                Check (!$state.NativeRootResumed -and $script:registrations -eq 0) "$case resumed or registered an expired root"
                if($case -ceq 'late-helper'){Check ($script:factoryCalls -eq 0) 'late helper reached Prepare'}
                else{Check ($script:factoryCalls -eq 1 -and !$script:fixtureJob.Resumed -and $script:fixtureJob.Stopped -and $script:fixtureJob.Disposed) "$case did not stop the original suspended root"}
            }
        }
        if($state.QuarantineKey){
            $held=[AppDomain]::CurrentDomain.GetData($state.QuarantineKey)
            try {
                Check ([object]::ReferenceEquals($held.Owner,$script:fixtureJob) -and [object]::ReferenceEquals($held.Bootstrap,$bootstrap)) 'host quarantine changed owner/bootstrap identity'
                Check ([object]::ReferenceEquals($held.InputGuards,$held.Context.InputGuards) -and $held.Lease.Token -ceq $script:fixtureToken) 'host quarantine omitted guards/reservation'
            }finally{
                foreach($guard in $held.InputGuards){$guard.Dispose()}
                if($held.Owner){$held.Owner.Dispose()}
                if($state.QuarantineKey -cne ('IW7.SoundChecksum.Quarantine.'+$script:fixtureToken)){throw 'Unexpected fixture quarantine key'}
                [AppDomain]::CurrentDomain.SetData($state.QuarantineKey,$null)
            }
        }
    }
    # Prove the narrow dynamic callback dispatch without modifying the provider.
    . "$PSScriptRoot/BuildReceipt.Core.ps1"
    function Assert-ChecksumReceipt { 'sound-callback' }
    function Complete-AuditBuildEvidence { Assert-AuditCompletionReceipt }
    Check ((Complete-ChecksumBuildEvidence $null @{} 0 @{} @{} {} $false) -ceq 'sound-callback') 'dynamic sound receipt callback not used'
    Check (!('IW7.CommunityBuild.BuildJob' -as [type]) -and !('IW7.AnimationRig.JobMembers' -as [type])) 'tests loaded native types'
    [ordered]@{Cases=$cases.Count;Assertions=$script:checks;Flac17=[bool]$Flac;NativeTypesLoaded=$false;RealReservations=0}|ConvertTo-Json
}finally{
    # Exact disposable fixture root only; never a candidate/runtime root.
    $resolved=[IO.Path]::GetFullPath($temp);$parent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if(!$resolved.StartsWith($parent,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -notlike 'sound-build-lifecycle-*'){throw 'Unsafe fixture cleanup path'}
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
