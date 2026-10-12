param([Parameter(Mandatory)][string]$PlanPath)
$ErrorActionPreference='Stop'
. "$PSScriptRoot/SoundFF.Core.ps1"
$base=Get-Content -LiteralPath $PlanPath -Raw|ConvertFrom-Json
$temp=[IO.Path]::GetFullPath((Join-Path ([IO.Path]::GetTempPath()) ('iw7-sound-plan-'+[guid]::NewGuid().ToString('N'))))
[IO.Directory]::CreateDirectory($temp)|Out-Null
try {
    foreach($case in 'Valid','PlanHash','CoreHash','BudgetString','LowerBudget','MissingSABS','WrongPhasePath','HelperRawHash',
        'CandidateReceiptHash','CandidateStateHash','MissingCandidateEvidence','OldToolHash'){
        $plan=$base|ConvertTo-Json -Depth 25|ConvertFrom-Json
        switch($case){
            'CoreHash' {($plan.HashInputs|Where-Object Path -Like '*SoundFF.Core.ps1').SHA256='0'*64}
            'BudgetString' {$plan.PhysicalBytes=[string]$plan.PhysicalBytes}
            'LowerBudget' {$plan.CommitBytes=1GB}
            'MissingSABS' {$plan.MutableOutputs=@($plan.MutableOutputs|Where-Object {!$_.EndsWith('.sabs')})}
            'WrongPhasePath' {$plan.Review.phase_specs[2].cwd=$temp}
            'HelperRawHash' {($plan.HashInputs|Where-Object Path -Like '*MaterialV2.Core.ps1').SHA256='0'*64}
            'CandidateReceiptHash' {$plan.CandidateReceiptSHA256='0'*64}
            'CandidateStateHash' {$plan.CandidateStateSHA256='0'*64}
            'MissingCandidateEvidence' {$plan.HashInputs=@($plan.HashInputs|Where-Object Path -INE (Join-Path $plan.CandidateRoot 'supervisor-state.json'))}
            'OldToolHash' {$plan.Review.phase_specs[0].sha256='e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04'}
        }
        $path=Join-Path $temp ($case+'.json');[IO.File]::WriteAllText($path,($plan|ConvertTo-Json -Depth 25))
        $hash=(Get-FileHash -LiteralPath $path).Hash;if($case -eq 'PlanHash'){$hash='0'*64}
        $failed=$false
        try{$result=& "$PSScriptRoot/Build-SoundFF.ps1" -PlanPath $path -PlanSHA256 $hash|ConvertFrom-Json}catch{$failed=$true}
        if($failed -ne ($case -ne 'Valid')){throw "Wrong default Plan outcome: $case"}
        if(Test-Path -LiteralPath $plan.RunRoot){throw 'Default Plan created native root'}
        if($case -eq 'Valid' -and ($result.HeavyExecutionAuthorizedByPlan -or $result.Ready)){throw 'Default Plan overclaims authorization'}
    }
    # The PowerShell gate must agree with Python about canonical source identity,
    # but must still reject newline conversion against an existing runtime pin.
    $manifest=Get-Content -LiteralPath "$PSScriptRoot/sab_ff_helpers.json" -Raw|ConvertFrom-Json
    $fake=Join-Path $temp 'helpers';[IO.Directory]::CreateDirectory($fake)|Out-Null
    foreach($newline in "`n","`r`n"){
        $pins=@(foreach($entry in $manifest.files.PSObject.Properties){
            $path=Join-Path $fake $entry.Name;[IO.Directory]::CreateDirectory((Split-Path $path))|Out-Null
            $raw=[IO.File]::ReadAllBytes((Join-Path $base.SharedRepo $entry.Name))
            $utf8=[Text.UTF8Encoding]::new($false,$true)
            [IO.File]::WriteAllBytes($path,$utf8.GetBytes($utf8.GetString($raw).Replace("`r`n","`n").Replace("`n",$newline)))
            Get-SoundFFPin $path
        })
        Assert-SoundFFHelperSources $PSScriptRoot $fake $pins
    }
    $changed=Join-Path $fake 'tools-source/asset-bridge/surfaces/MaterialV2.Core.ps1'
    $raw=[IO.File]::ReadAllBytes($changed);[IO.File]::WriteAllBytes($changed,$utf8.GetBytes($utf8.GetString($raw).Replace("`r`n","`n")))
    $failed=$false;try{Assert-SoundFFHelperSources $PSScriptRoot $fake $pins}catch{$failed=$true}
    if(!$failed){throw 'Newline conversion bypassed exact runtime pin'}
    [IO.File]::AppendAllText($changed,' ')
    $pins=@($pins|ForEach-Object {Get-SoundFFPin $_.Path})
    $failed=$false;try{Assert-SoundFFHelperSources $PSScriptRoot $fake $pins}catch{$failed=$true}
    if(!$failed){throw 'Rehashed real source mutation bypassed canonical pin'}
    if(('IW7.CommunityBuild.BuildJob' -as [type]) -or ('IW7HudFileIdentity' -as [type]) -or ('IW7ResourceMemoryV1' -as [type])){throw 'Default Plan loaded a native type'}
    '16 default-Plan and source-identity cases passed; no native type, job, lease, stock or RunRoot.'
}finally{
    $resolved=[IO.Path]::GetFullPath($temp)
    if(!$resolved.StartsWith([IO.Path]::GetFullPath([IO.Path]::GetTempPath()),[StringComparison]::OrdinalIgnoreCase) -or
        (Split-Path $resolved -Leaf) -notlike 'iw7-sound-plan-*'){throw 'Unsafe test cleanup target'}
    foreach($entry in @(Get-ChildItem -LiteralPath $resolved -Recurse -Force)){
        if($entry.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Unexpected redirected test entry'}
        if(!$entry.PSIsContainer){Remove-Item -LiteralPath $entry.FullName}
    }
    foreach($directory in @(Get-ChildItem -LiteralPath $resolved -Directory -Recurse|Sort-Object {$_.FullName.Length} -Descending)){Remove-Item -LiteralPath $directory.FullName}
    Remove-Item -LiteralPath $resolved
}
