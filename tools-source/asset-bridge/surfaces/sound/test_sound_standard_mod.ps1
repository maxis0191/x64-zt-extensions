param([Parameter(Mandatory)][string]$CandidateRoot,[Parameter(Mandatory)][string]$ImmutablePlanPath,[Parameter(Mandatory)][string]$ImmutableStatePath)
$ErrorActionPreference='Stop'
. "$PSScriptRoot/SoundFF.Core.ps1"
$temp=Join-Path ([IO.Path]::GetTempPath()) ('iw7-standard-mod-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($temp)|Out-Null
function Get-FileHash {param([string]$LiteralPath)
    if([IO.Path]::GetExtension($LiteralPath) -iin @('.exe','.dll','.lib','.pdb','.ff','.sabl','.sabs','.flac','.wav')){throw ('Payload read before admission: '+$LiteralPath)}
    Microsoft.PowerShell.Utility\Get-FileHash -LiteralPath $LiteralPath -Algorithm SHA256
}
try {
    $out=Join-Path $temp 'plan.json';$run=Join-Path $temp 'not-created'
    $result=& "$PSScriptRoot/Prepare-SoundFF.ps1" -StandardMod -CandidateRoot $CandidateRoot -ImmutablePlanPath $ImmutablePlanPath -ImmutableStatePath $ImmutableStatePath -RunRoot $run -OutputPath $out|ConvertFrom-Json
    $base=Get-Content -LiteralPath $out -Raw|ConvertFrom-Json
    $null=& "$PSScriptRoot/Build-SoundFF.ps1" -PlanPath $out -PlanSHA256 $result.SHA256
    if(($base.Review.phase_specs.phase -join ',') -cne 'build,verify,dump,read' -or @($base.PayloadInputs).Count -ne 3 -or
        ($base.MutableOutputs -join ',') -cne 'zone/mod.ff,zone/mod.sabl,zone/mod.sabs'){throw 'StandardMod shape differs'}
    foreach($relative in $base.Review.source_stage_relatives){
        $expected=if($relative -cin @('soundbank/community_original_sound_v1.all.json','zone_source/mod.csv')){Join-Path $PSScriptRoot ('standard-mod/'+$relative)}else{Join-Path $base.Review.source $relative}
        if((Get-SoundFFStageSource $base $relative) -ine $expected){throw 'Original versus overlay staging differs'}
    }
    $mutations=@('Order','Candidate','MissingProof','PayloadInBootstrap','MissingPayload','MissingSourceText','MissingOverlay',
        'WrongFFName','WrongSABLName','WrongSABSName','ChangedFF','ChangedStock','ReaderProfile','PreservedInventory','BuildZone','VerifyZone','DumpZone','ZoneCSVName','OutputOverlap')
    foreach($case in $mutations){
        $p=$base|ConvertTo-Json -Depth 25|ConvertFrom-Json
        switch($case){
            'Order' {$p.Review.phase_specs=@($p.Review.phase_specs[1],$p.Review.phase_specs[0],$p.Review.phase_specs[2],$p.Review.phase_specs[3])}
            'Candidate' {$p.CandidateReceiptSHA256='0'*64}
            'MissingProof' {$p.HashInputs=@($p.HashInputs|Where-Object Path -INE $p.ImmutableFF.StatePath)}
            'PayloadInBootstrap' {$p.HashInputs+=,$p.PayloadInputs[0]}
            'MissingPayload' {$p.PayloadInputs=@($p.PayloadInputs|Select-Object -First 2)}
            'MissingSourceText' {$p.HashInputs=@($p.HashInputs|Where-Object {$_.Path -inotlike '*original-sound-source-b*all.json'})}
            'MissingOverlay' {$p.HashInputs=@($p.HashInputs|Where-Object {$_.Path -inotlike '*standard-mod*all.json'})}
            'WrongFFName' {$p.MutableOutputs[0]='zone/sdk_original_sound_v1.ff'}
            'WrongSABLName' {$p.MutableOutputs[1]='zone/sdk_original_sound_v1.sabl'}
            'WrongSABSName' {$p.MutableOutputs[2]='zone/sdk_original_sound_v1.sabs'}
            'ChangedFF' {$p.ImmutableFF.Artifacts[0].SHA256='0'*64}
            'ChangedStock' {$p.StockInputs[0].ExpectedSHA256='0'*64}
            'ReaderProfile' {$p.Review.phase_specs[3].arguments[-1]='DumpOnlyC'}
            'PreservedInventory' {$p.Review.phase_specs[3].arguments[11]=$p.ImmutableFF.InventoryPath}
            'BuildZone' {$p.Review.phase_specs[0].arguments[-1]='sdk_original_sound_v1'}
            'VerifyZone' {$p.Review.phase_specs[1].arguments[-1]='sdk_original_sound_v1'}
            'DumpZone' {$p.Review.phase_specs[2].arguments[-1]='sdk_original_sound_v1'}
            'ZoneCSVName' {$p.Review.source_stage_relatives[3]='zone_source/sdk_original_sound_v1.csv'}
            'OutputOverlap' {$p.RunRoot=Split-Path $p.ImmutableFF.StatePath;$p.Work=Join-Path $p.RunRoot 'work'}
        }
        $failed=$false;try{Assert-SoundFFExecutionPlan $p $PSScriptRoot}catch{$failed=$true}
        if(!$failed){throw "Changed standard Plan accepted: $case"}
    }
    # Repin a changed *text fixture* to prove the bank.zone semantic gate is
    # separate from disk names and from stale-hash detection. Never edit source B.
    $overlayRoot=Join-Path $temp 'fixture';$relative='soundbank/community_original_sound_v1.all.json'
    $copy=Join-Path $overlayRoot ('standard-mod/'+$relative)
    [IO.Directory]::CreateDirectory((Split-Path $copy))|Out-Null
    $originalPath=Join-Path $PSScriptRoot ('standard-mod/'+$relative)
    [IO.File]::WriteAllText($copy,([IO.File]::ReadAllText($originalPath).Replace('"zone": "mod"','"zone": "sdk_original_sound_v1"')))
    $p=$base|ConvertTo-Json -Depth 25|ConvertFrom-Json
    $p.HashInputs=@($p.HashInputs|Where-Object Path -INE $originalPath)+@((Get-SoundFFPin $copy))
    $failed=$false;try{Assert-SoundFFStandardSources $p $overlayRoot}catch{$failed=$_.Exception.Message -like '*Standard source differs*'}
    if(!$failed){throw 'Repinned bank.zone mutation was not rejected independently'}
    function Import-SoundFFHelpers {}
    function Enter-IW7ResourceLease {throw 'fixture admission refusal'}
    $failed=$false;try{Invoke-SoundFFTransaction $base $out $result.SHA256|Out-Null}catch{$failed=$_.Exception.Message -like '*fixture admission refusal*'}
    if(!$failed -or (Test-Path $run)){throw 'Admission refusal lifecycle differs'}
    if(('IW7.CommunityBuild.BuildJob' -as [type]) -or ('IW7HudFileIdentity' -as [type]) -or ('IW7ResourceMemoryV1' -as [type])){throw 'Source-only tests loaded native types'}
    [ordered]@{PlanMutationCases=$mutations.Count;IndependentBankZoneMutationPassed=$true;DefaultPlanPassed=$true;AdmissionRefusalPassed=$true;
        OriginalAndOverlayStageBindings=4;PayloadHashes=0;NativeInvocations=0;Reservations=0;Ready=$false}|ConvertTo-Json
}finally{
    $resolved=[IO.Path]::GetFullPath($temp);$parent=[IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    if(!$resolved.StartsWith($parent,[StringComparison]::OrdinalIgnoreCase) -or (Split-Path $resolved -Leaf) -notlike 'iw7-standard-mod-*'){throw 'Unsafe fixture cleanup'}
    foreach($f in Get-ChildItem -LiteralPath $resolved -File -Recurse){Remove-Item -LiteralPath $f.FullName}
    foreach($d in Get-ChildItem -LiteralPath $resolved -Directory -Recurse|Sort-Object {$_.FullName.Length} -Descending){Remove-Item -LiteralPath $d.FullName}
    Remove-Item -LiteralPath $resolved
}
