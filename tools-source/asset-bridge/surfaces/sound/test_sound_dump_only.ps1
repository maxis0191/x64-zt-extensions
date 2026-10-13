param([Parameter(Mandatory)][string]$CandidateRoot,[Parameter(Mandatory)][string]$ImmutablePlanPath,[Parameter(Mandatory)][string]$ImmutableStatePath)
$ErrorActionPreference='Stop'
. "$PSScriptRoot/SoundFF.Core.ps1"
$receiptRaw=Get-Content -LiteralPath (Join-Path $CandidateRoot 'build-receipt.json') -Raw
$stateRaw=Get-Content -LiteralPath (Join-Path $CandidateRoot 'supervisor-state.json') -Raw
$cases=@('Valid','Failed','InputBefore','InputAfter','Artifacts','Deferred','Tree','Lease','Token','GuardOpened','GuardDisposed',
    'Exit','Active','Acceptance','Closure','Completion','Generation','Steps','StepExit','StepEOF','Probe','Promoted','Candidate','ArtifactMismatch')
foreach($case in $cases){
    $r=$receiptRaw|ConvertFrom-Json;$s=$stateRaw|ConvertFrom-Json
    switch($case){
        'Failed' {$s.Success=$false}
        'InputBefore' {$s.InputsVerifiedBefore=$false}
        'InputAfter' {$s.InputsVerifiedAfter=$false}
        'Artifacts' {$s.FinalArtifactsVerified=$false}
        'Deferred' {$s.DeferredArtifactProofPending=$true}
        'Tree' {$s.TreeClosed=$false}
        'Lease' {$s.LeaseReleased=$false}
        'Token' {$s.RetainedLeaseToken='held-fixture'}
        'GuardOpened' {$s.InputGuardsOpened=1417}
        'GuardDisposed' {$s.InputGuardsDisposed=1417}
        'Exit' {$s.RootExitCode=1}
        'Active' {$s.JobActiveAtClose=1}
        'Acceptance' {$s.QualifiedClosure.AcceptanceGranted=$false}
        'Closure' {$s.QualifiedClosure.ClosureVerified=$false}
        'Completion' {$s.QualifiedClosure.CompletionVerified=$false}
        'Generation' {$s.RunID='other-fixture'}
        'Steps' {$r.steps=@($r.steps|Select-Object -First 16)}
        'StepExit' {$r.steps[0].exit_code=1}
        'StepEOF' {$r.steps[0].normal_eof=$false}
        'Probe' {$r.probes.'probe-flac-run'.cases=102}
        'Promoted' {$r.ready=$true}
        'Candidate' {$r.artifacts.candidate_exe.sha256='0'*64}
        'ArtifactMismatch' {$s.Artifacts.probe_flac.bytes++}
    }
    $failed=$false;try{$null=Assert-SoundFFFlacEvidence $r $s}catch{$failed=$true}
    if($failed -ne ($case -cne 'Valid')){throw "Candidate evidence outcome differs: $case"}
}
$temp=Join-Path ([IO.Path]::GetTempPath()) ('iw7-dump-only-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($temp)|Out-Null
$hashCalls=[Collections.Generic.List[string]]::new()
function Get-FileHash {param([string]$LiteralPath)
    if([IO.Path]::GetExtension($LiteralPath) -iin @('.exe','.dll','.lib','.pdb','.ff','.sabl','.sabs','.flac','.wav')){throw ('Payload read before admission: '+$LiteralPath)}
    $hashCalls.Add($LiteralPath)
    Microsoft.PowerShell.Utility\Get-FileHash -LiteralPath $LiteralPath -Algorithm SHA256
}
try {
    $out=Join-Path $temp 'plan.json';$run=Join-Path $temp 'not-created'
    $failed=$false
    try{& "$PSScriptRoot/Prepare-SoundFF.ps1" -DumpOnly -CandidateRoot (Join-Path $temp 'missing-candidate') -ImmutablePlanPath 'absent' -ImmutableStatePath 'absent' -RunRoot $run -OutputPath $out|Out-Null}catch{$failed=$true}
    if(!$failed -or (Test-Path $out) -or (Test-Path $run)){throw 'Unqualified candidate generated output'}
    $result=& "$PSScriptRoot/Prepare-SoundFF.ps1" -DumpOnly -CandidateRoot $CandidateRoot -ImmutablePlanPath $ImmutablePlanPath -ImmutableStatePath $ImmutableStatePath -RunRoot $run -OutputPath $out|ConvertFrom-Json
    $base=Get-Content -LiteralPath $out -Raw|ConvertFrom-Json
    $null=& "$PSScriptRoot/Build-SoundFF.ps1" -PlanPath $out -PlanSHA256 $result.SHA256
    if(($base.Review.phase_specs.phase -join ',') -cne 'dump,read' -or @($base.PayloadInputs).Count -ne 3 -or @($base.MutableOutputs).Count){throw 'DumpOnly shape differs'}
    $mutations=@('Order','Build','ExtraPhase','Candidate','MissingProof','PayloadInBootstrap','MissingPayload','MissingSourceText','MutableFF','ChangedFF','ChangedStock','ReaderProfile','OutputOverlap')
    foreach($case in $mutations){
        $p=$base|ConvertTo-Json -Depth 25|ConvertFrom-Json
        switch($case){
            'Order' {$p.Review.phase_specs=@($p.Review.phase_specs[1],$p.Review.phase_specs[0])}
            'Build' {$p.Review.phase_specs[0].phase='build';$p.Review.phase_specs[0].arguments[3]='-buildzone'}
            'ExtraPhase' {$p.Review.phase_specs+=,$p.Review.phase_specs[0]}
            'Candidate' {$p.CandidateReceiptSHA256='0'*64}
            'MissingProof' {$p.HashInputs=@($p.HashInputs|Where-Object Path -INE $p.ImmutableFF.StatePath)}
            'PayloadInBootstrap' {$p.HashInputs+=,$p.PayloadInputs[0]}
            'MissingPayload' {$p.PayloadInputs=@($p.PayloadInputs|Select-Object -First 2)}
            'MissingSourceText' {$p.HashInputs=@($p.HashInputs|Where-Object {$_.Path -inotlike '*soundbank*all.json'})}
            'MutableFF' {$p.MutableOutputs=@('zone/sdk_original_sound_v1.ff')}
            'ChangedFF' {$p.ImmutableFF.Artifacts[0].SHA256='0'*64}
            'ChangedStock' {$p.StockInputs[0].ExpectedSHA256='0'*64}
            'ReaderProfile' {$p.Review.phase_specs[1].arguments[-1]='NativeDumpF'}
            'OutputOverlap' {$p.RunRoot=Split-Path $p.ImmutableFF.StatePath;$p.Work=Join-Path $p.RunRoot 'work'}
        }
        $failed=$false;try{Assert-SoundFFExecutionPlan $p $PSScriptRoot}catch{$failed=$true}
        if(!$failed){throw "Changed dump plan accepted: $case"}
    }
    # Admission refusal must not fall through to the payload verification branch
    # during either setup or the existing cleanup path.
    function Import-SoundFFHelpers {}
    function Enter-IW7ResourceLease {throw 'fixture admission refusal'}
    $failed=$false
    try{Invoke-SoundFFTransaction $base $out $result.SHA256|Out-Null}catch{$failed=$_.Exception.Message -like '*fixture admission refusal*'}
    if(!$failed -or (Test-Path $run)){throw 'Admission refusal lifecycle differs'}
    if(('IW7.CommunityBuild.BuildJob' -as [type]) -or ('IW7HudFileIdentity' -as [type]) -or ('IW7ResourceMemoryV1' -as [type])){throw 'Source-only tests loaded native types'}
    [ordered]@{CandidateCases=$cases.Count;PlanMutationCases=$mutations.Count;DefaultPlanPassed=$true;AdmissionRefusalPassed=$true;
        PayloadHashes=0;NativeInvocations=0;Reservations=0;Ready=$false}|ConvertTo-Json
}finally{
    $resolved=[IO.Path]::GetFullPath($temp);$parent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    if(!$resolved.StartsWith($parent,[StringComparison]::OrdinalIgnoreCase) -or (Split-Path $resolved -Leaf) -notlike 'iw7-dump-only-*'){throw 'Unsafe fixture cleanup'}
    foreach($f in Get-ChildItem -LiteralPath $resolved -File){Remove-Item -LiteralPath $f.FullName}
    Remove-Item -LiteralPath $resolved
}
