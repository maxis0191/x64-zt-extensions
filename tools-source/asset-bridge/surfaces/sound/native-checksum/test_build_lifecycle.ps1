param([Parameter(Mandatory)][string]$ProviderRoot)
$ErrorActionPreference='Stop'
. "$PSScriptRoot/BuildCandidate.Core.ps1"
if((Get-FileHash -LiteralPath (Join-Path $ProviderRoot 'supervision.ps1')).Hash -ine 'b6125dfaa4c6b16e4ebc6f54f160369788cfe5290f4c734edb925101af4f3471'){throw 'Exact v6 supervision required.'}
. (Join-Path $ProviderRoot 'supervision.ps1')
$script:checks=0
function Check($Value,[string]$Message){$script:checks++;if(!$Value){throw $Message}}
function Get-IW7ResourceSnapshot { @{CommitLimit=16GB;Committed=2GB} }
function Enter-IW7ResourceLease { $script:admissions++;@{Token=$script:fixtureToken} }
function Exit-IW7ResourceLease { $script:releases++;if($script:mode -ceq 'release-failure'){throw 'fixture refused release'} }
function Add-IW7ResourceProcess { $script:registrations++ }
function Initialize-ChecksumBuildTypes { $script:typeMocks++;if($script:mode -ceq 'late-helper'){$script:clock+=3600001} }
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
    $script:completionCalls++
}
function Get-ChecksumBuildClock { $script:clock }
function Get-AuditMonotonicMs { $script:clock }
function Read-ChecksumBuildChunk($Stream,[byte[]]$Buffer) {
    $script:readCalls++
    if($script:mode -ceq 'post-proof-failure' -and $script:readCalls -eq 3){throw 'fixture post-proof read failure'}
    $n=$Stream.Read($Buffer,0,$Buffer.Length)
    if($script:mode -ceq 'late-read'){$script:clock+=3600001}
    $n
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
    foreach($case in 'success','nonzero','factory-failure','identity-failure','closure-failure','release-failure','input-drift','late-read','post-proof-failure','late-final-state','late-helper','late-prepare','late-identity'){
        $script:mode=$case;$script:admissions=0;$script:releases=0;$script:registrations=0;$script:typeMocks=0;$script:completionCalls=0;$script:fixtureJob=$null
        $script:clock=1000L;$script:readCalls=0;$script:factoryCalls=0
        $script:fixtureToken='fixture-sound-'+[guid]::NewGuid().ToString('N')
        $candidate=Join-Path $temp $case
        $plan=@{candidate=$candidate;python=(Join-Path $temp 'python.exe');worker=(Join-Path $temp 'worker.py');seal_sha256=('a'*64);
            environment=@{SystemRoot=$env:SystemRoot;TEMP=$env:TEMP;TMP=$env:TMP}}
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
            Check ($state.InputsVerifiedBefore -and $state.InputsVerifiedAfter -and $state.ProofBytesRead -eq 8) 'two guarded source proofs missing'
            Check ($script:fixtureJob.Resumed -and $script:fixtureJob.Disposed -and !$script:fixtureJob.Stopped) 'natural closure changed'
            Check ($script:completionCalls -eq 1 -and $script:releases -eq 1) 'completion/release count differs'
        }else{
            Check ($failure -and !$state.Success) "$case accidentally accepted"
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
    [ordered]@{Cases=13;Assertions=$script:checks;NativeTypesLoaded=$false;RealReservations=0}|ConvertTo-Json
}finally{
    # Exact disposable fixture root only; never a candidate/runtime root.
    $resolved=[IO.Path]::GetFullPath($temp);$parent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if(!$resolved.StartsWith($parent,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -notlike 'sound-build-lifecycle-*'){throw 'Unsafe fixture cleanup path'}
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
