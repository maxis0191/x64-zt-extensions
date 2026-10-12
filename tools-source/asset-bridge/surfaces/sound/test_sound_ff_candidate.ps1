param([Parameter(Mandatory)][string]$CandidateRoot)
$ErrorActionPreference='Stop'
. "$PSScriptRoot/SoundFF.Core.ps1"
$receiptRaw=Get-Content -Raw -LiteralPath (Join-Path $CandidateRoot 'build-receipt.json')
$stateRaw=Get-Content -Raw -LiteralPath (Join-Path $CandidateRoot 'supervisor-state.json')
$cases=@('valid','failed','unclosed','unreleased','unverified-artifacts','input-proof','retained-token','exit','active','generation','promoted','old-exe','unverified-probe')
foreach($case in $cases){
    $receipt=$receiptRaw|ConvertFrom-Json;$state=$stateRaw|ConvertFrom-Json
    switch($case){
        'failed' {$state.Success=$false}
        'unclosed' {$state.TreeClosed=$false}
        'unreleased' {$state.LeaseReleased=$false}
        'unverified-artifacts' {$state.FinalArtifactsVerified=$false}
        'input-proof' {$state.InputsVerifiedAfter=$false}
        'retained-token' {$state.RetainedLeaseToken='fixture-held'}
        'exit' {$state.RootExitCode=1}
        'active' {$state.JobActiveAtClose=1}
        'generation' {$state.RunID='fixture-other'}
        'promoted' {$receipt.ready=$true}
        'old-exe' {$receipt.artifacts.candidate_exe.sha256='e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04'}
        'unverified-probe' {$receipt.native_cpp_probes_verified=$false}
    }
    $failure=$null
    try{$null=Assert-SoundFFCandidateEvidence $receipt $state}catch{$failure=$_.Exception.Message}
    if($case -ceq 'valid' -and $failure){throw "Valid candidate evidence failed: $failure"}
    if($case -cne 'valid' -and !$failure){throw "Invalid candidate accepted: $case"}
}
$exe=Join-Path $CandidateRoot 'bin/zonetool-sound-md5.exe'
function Get-FileHash {param($LiteralPath)
    if($LiteralPath -ieq $exe){throw 'Source-only candidate validation hashed binary'}
    Microsoft.PowerShell.Utility\Get-FileHash -LiteralPath $LiteralPath
}
$null=Assert-SoundFFChecksumCandidate $CandidateRoot 'a8253c8efa5b315c7870f27c6732eb6893528c0bd4c8ad3ddcbe7dde407faf62' '5a99ed368636d08d1d4407e3125cab73f5da879344880588c6aa54efcb556ed8'
foreach($pair in @(@(('0'*64),'5a99ed368636d08d1d4407e3125cab73f5da879344880588c6aa54efcb556ed8'),
    @('a8253c8efa5b315c7870f27c6732eb6893528c0bd4c8ad3ddcbe7dde407faf62',('0'*64)))){
    $failed=$false;try{$null=Assert-SoundFFChecksumCandidate $CandidateRoot $pair[0] $pair[1]}catch{$failed=$true}
    if(!$failed){throw 'Changed Build F pin accepted'}
}
[ordered]@{EvidenceCases=$cases.Count;ChangedPinsRefused=2;BinaryHashed=$false;NativeTypesLoaded=$false;RealReservations=0}|ConvertTo-Json
