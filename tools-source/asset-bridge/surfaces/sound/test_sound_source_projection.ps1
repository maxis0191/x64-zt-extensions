param([Parameter(Mandatory)][string]$CandidateRoot,[Parameter(Mandatory)][string]$ImmutablePlanPath,[Parameter(Mandatory)][string]$ImmutableStatePath)
$ErrorActionPreference='Stop'
. "$PSScriptRoot/SoundFF.Core.ps1"
function Check([bool]$Value,[string]$Message){if(!$Value){throw $Message}}
$script:payloadAttempts=0
function Get-FileHash {param([string]$LiteralPath)
    if([IO.Path]::GetExtension($LiteralPath) -iin @('.exe','.dll','.lib','.pdb','.ff','.sabl','.sabs','.flac','.wav')){$script:payloadAttempts++;throw 'Test forbids payload hashing.'}
    Microsoft.PowerShell.Utility\Get-FileHash -LiteralPath $LiteralPath -Algorithm SHA256
}
$evidenceBefore=@(Get-SoundFFPin $ImmutablePlanPath;Get-SoundFFPin $ImmutableStatePath)
$historical=Get-Content -LiteralPath $ImmutablePlanPath -Raw|ConvertFrom-Json
$historicalBefore=$historical|ConvertTo-Json -Depth 25 -Compress
$temp=Join-Path ([IO.Path]::GetTempPath()) ('iw7-sound-projection-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($temp)|Out-Null
try {
    $out=Join-Path $temp 'plan.json';$run=Join-Path $temp 'not-created'
    $result=& "$PSScriptRoot/Prepare-SoundFF.ps1" -StandardMod -CandidateRoot $CandidateRoot -ImmutablePlanPath $ImmutablePlanPath -ImmutableStatePath $ImmutableStatePath -RunRoot $run -OutputPath $out|ConvertFrom-Json
    $base=Get-Content -LiteralPath $out -Raw|ConvertFrom-Json
    $null=& "$PSScriptRoot/Build-SoundFF.ps1" -PlanPath $out -PlanSHA256 $result.SHA256
    Check (@($base.SourceProjection.Entries).Count -eq 26) 'Closed source projection must contain exactly 26 helpers.'
    $helpers=Get-Content -LiteralPath "$PSScriptRoot/sab_ff_helpers.json" -Raw|ConvertFrom-Json
    foreach($relative in $helpers.files.PSObject.Properties.Name){
        Check ($relative -cin $base.SourceProjection.Entries.Relative) 'Shared manifest helper missing from the closed projection.'
    }
    $null=New-SoundFFSourceProjection $historical $base.ImmutableFF.PlanSHA256
    $shared='tools-source/asset-bridge/model/BuildJob.cs'
    $sharedRow=@($base.SourceProjection.Entries|Where-Object Relative -CEQ $shared)[0]
    Check ($sharedRow.HistoricalPin.SHA256 -ieq 'f6be2a4cafddb78b5e07a6802354575ada418cb7643d96a3abd0a4c063bc6387') 'Historical shared-job identity lost.'
    Check (([datetimeoffset]$sharedRow.CurrentPin.ModifiedUtc).UtcTicks -eq ([datetimeoffset](Get-SoundFFPin $sharedRow.CurrentPin.Path).ModifiedUtc).UtcTicks) 'Current metadata was not independently observed.'
    $newRow=@($base.SourceProjection.Entries|Where-Object Relative -CLike '*/SoundBuildJob.cs')[0]
    Check ($null -eq $newRow.HistoricalPin) 'New local helper invented historical evidence.'
    $outside=@($base.HashInputs|Where-Object Path -Like '*codec-checkpoint-2026-10-12.json')[0].Path
    $cases=@('MissingProjection','WrongSchema','WrongBasis','ExtraRow','MissingRow','DuplicateRow','HistoricalHash','HistoricalMetadata',
        'NewHelperHistory','PathToPayload','MissingCurrentPin','DuplicateCurrentPin','CurrentHash','CurrentMetadata','HistoricalEvidenceMetadata',
        'MissingHistoricalEvidence','PayloadMetadata','StockMetadata')
    foreach($case in $cases){
        $p=$base|ConvertTo-Json -Depth 25|ConvertFrom-Json
        $row=@($p.SourceProjection.Entries|Where-Object Relative -CEQ $shared)[0]
        $bound=@($p.HashInputs|Where-Object Path -IEQ $row.CurrentPin.Path)[0]
        switch($case){
            'MissingProjection' {$p.PSObject.Properties.Remove('SourceProjection')}
            'WrongSchema' {$p.SourceProjection.Schema='other'}
            'WrongBasis' {$p.SourceProjection.BasisPlanSHA256='0'*64}
            'ExtraRow' {$p.SourceProjection.Entries+=,$row}
            'MissingRow' {$p.SourceProjection.Entries=@($p.SourceProjection.Entries|Where-Object Relative -CNE $shared)}
            'DuplicateRow' {$p.SourceProjection.Entries[0]=$row}
            'HistoricalHash' {$row.HistoricalPin.SHA256='0'*64}
            'HistoricalMetadata' {$row.HistoricalPin.ModifiedUtc='2000-01-01T00:00:00.0000000Z'}
            'NewHelperHistory' {($p.SourceProjection.Entries|Where-Object Relative -CLike '*/SoundBuildJob.cs').HistoricalPin=$row.HistoricalPin}
            'PathToPayload' {$row.CurrentPin.Path=$p.PayloadInputs[0].Path}
            'MissingCurrentPin' {$p.HashInputs=@($p.HashInputs|Where-Object Path -INE $bound.Path)}
            'DuplicateCurrentPin' {$p.HashInputs+=,$bound}
            'CurrentHash' {$row.CurrentPin.SHA256='0'*64;$bound.SHA256='0'*64}
            'CurrentMetadata' {$row.CurrentPin.ModifiedUtc='2000-01-01T00:00:00.0000000Z';$bound.ModifiedUtc=$row.CurrentPin.ModifiedUtc}
            'HistoricalEvidenceMetadata' {($p.HashInputs|Where-Object Path -IEQ $outside).ModifiedUtc='2000-01-01T00:00:00.0000000Z'}
            'MissingHistoricalEvidence' {$p.HashInputs=@($p.HashInputs|Where-Object Path -INE $outside)}
            'PayloadMetadata' {$p.PayloadInputs[0].ModifiedUtc='2000-01-01T00:00:00.0000000Z'}
            'StockMetadata' {$p.StockInputs[0].ModifiedUtc='2000-01-01T00:00:00.0000000Z'}
        }
        $refused=$false;try{Assert-SoundFFExecutionPlan $p $PSScriptRoot}catch{$refused=$true}
        Check $refused ('Projection mutation accepted: '+$case)
    }
    foreach($pin in $evidenceBefore){Assert-SoundFFPin $pin}
    Check (($historical|ConvertTo-Json -Depth 25 -Compress) -ceq $historicalBefore) 'Historical in-memory evidence was mutated.'
    Check (!(Test-Path -LiteralPath $run)) 'Default Plan created RunRoot.'
    Check ($script:payloadAttempts -eq 0) 'Projection attempted a payload hash.'
    foreach($name in 'IW7.SoundFFTelemetryV1.BuildJob','IW7.CommunityBuild.BuildJob','IW7HudFileIdentity','IW7ResourceMemoryV1'){
        Check (!($name -as [type])) 'Source-only projection loaded a native type.'
    }
    [ordered]@{MutationRefusals=$cases.Count;DefaultPlanPassed=$true;ProjectedSources=26;HistoricalEvidenceUnchanged=$true;
        PayloadHashes=0;NativeInvocations=0;Reservations=0;Ready=$false}|ConvertTo-Json
}finally{
    $resolved=[IO.Path]::GetFullPath($temp);$parent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    if(!$resolved.StartsWith($parent,[StringComparison]::OrdinalIgnoreCase) -or (Split-Path $resolved -Leaf) -notlike 'iw7-sound-projection-*'){throw 'Unsafe fixture cleanup'}
    foreach($entry in @(Get-ChildItem -LiteralPath $resolved -Recurse -Force)){
        if($entry.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Redirected fixture entry'}
        if(!$entry.PSIsContainer){Remove-Item -LiteralPath $entry.FullName}
    }
    foreach($directory in @(Get-ChildItem -LiteralPath $resolved -Directory -Recurse|Sort-Object {$_.FullName.Length} -Descending)){Remove-Item -LiteralPath $directory.FullName}
    Remove-Item -LiteralPath $resolved
}
