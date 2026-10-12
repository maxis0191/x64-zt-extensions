param([Parameter(Mandatory)][string]$PlanPath,[Parameter(Mandatory)][string]$PlanSHA256)
$ErrorActionPreference='Stop'
$allowedReads=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
[void]$allowedReads.Add([IO.Path]::GetFullPath($PlanPath))
function Get-FileHash {
    param([string]$LiteralPath,[string]$Algorithm='SHA256')
    if(!$allowedReads.Contains([IO.Path]::GetFullPath($LiteralPath))){throw ('Plan tried a non-plan hash: '+$LiteralPath)}
    Microsoft.PowerShell.Utility\Get-FileHash -LiteralPath $LiteralPath -Algorithm $Algorithm
}
function Get-Content {
    param([string]$LiteralPath,[switch]$Raw)
    if(!$allowedReads.Contains([IO.Path]::GetFullPath($LiteralPath))){throw ('Plan tried a non-plan read: '+$LiteralPath)}
    Microsoft.PowerShell.Management\Get-Content -LiteralPath $LiteralPath -Raw:$Raw
}
$scriptPath=Join-Path $PSScriptRoot 'Invoke-SoundCodec.ps1'
$rootBefore=Get-Content -LiteralPath $PlanPath -Raw|ConvertFrom-Json
if(('IW7.CommunityBuild.BuildJob' -as [type]) -or ('IW7ResourceMemoryV1' -as [type])){throw 'Fresh Plan test host required.'}
$actual=& $scriptPath -PlanPath $PlanPath -PlanSHA256 $PlanSHA256 | ConvertFrom-Json
if($actual.Schema -cne $rootBefore.Schema -or (Test-Path -LiteralPath $actual.RunRoot)){throw 'Default Plan wrote a RunRoot or changed schema.'}
$checks=1;$expectedFailure=$false
try{& $scriptPath -PlanPath $PlanPath -PlanSHA256 ('0'*64)|Out-Null}catch{$expectedFailure=$true}
if(!$expectedFailure){throw 'Changed plan hash accepted.'};$checks++
$temp=Join-Path ([IO.Path]::GetTempPath()) ('iw7-codec-plan-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($temp)|Out-Null
$testFile=Join-Path $temp 'refused-plan.json'
[void]$allowedReads.Add($testFile)
try{
    foreach($kind in 'MissingPin','Arguments','ExistingRoot','LegacySchema','MissingProfile','UnknownProfile','BooleanProfile',
        'ProfileHashSwap','ChangedInputPath','WrongOriginState','DuplicatePin','ExtraPin','BudgetType','LogLimit','WavLimit','Resampling'){
        $plan=Get-Content -LiteralPath $PlanPath -Raw|ConvertFrom-Json
        switch($kind){
            MissingPin {$plan.HashInputs=@($plan.HashInputs|Where-Object {$_.Path -notlike '*codec_worker.py'})}
            Arguments {$plan.CodecArguments=@('-y')+@($plan.CodecArguments)}
            ExistingRoot {$plan.RunRoot=$temp}
            LegacySchema {$plan.Schema='iw7.original-sound-codec-execution/1'}
            MissingProfile {$plan.PSObject.Properties.Remove('InputProfile')}
            UnknownProfile {$plan.InputProfile='nativedumpf'}
            BooleanProfile {$plan.InputProfile=$true}
            ProfileHashSwap {($plan.HashInputs|Where-Object Path -IEQ $plan.InputFLAC).SHA256=if($plan.InputProfile -ceq 'NativeDumpF'){'9f807b3f4dfee213dfd44e3f60b9109075327b233f321bdf38f594c3a0c47bbb'}else{'a4e9276568dfeaf42d39deefe243b1efc2b9095b2f558bcb3512b98c417154d9'}}
            ChangedInputPath {$plan.InputFLAC=$plan.OriginalWAV}
            WrongOriginState {$plan.NativeDumpState=$plan.SourceManifest}
            DuplicatePin {$plan.HashInputs+=,$plan.HashInputs[0]}
            ExtraPin {$plan.HashInputs+=,[pscustomobject]@{Path=(Join-Path $temp 'extra.bin');Bytes=1;SHA256=('0'*64)}}
            BudgetType {$plan.DeadlineMs='10000'}
            LogLimit {$plan.LogLimitEachBytes=65536}
            WavLimit {$plan.WavWatchdogStopBytes=262144}
            Resampling {$plan.CodecArguments=@('-ar','48000')+@($plan.CodecArguments)}
        }
        [IO.File]::WriteAllText($testFile,($plan|ConvertTo-Json -Depth 12))
        $failed=$false
        try{& $scriptPath -PlanPath $testFile -PlanSHA256 (Get-FileHash -LiteralPath $testFile).Hash|Out-Null}catch{$failed=$true}
        if(!$failed){throw ('Plan guard accepted '+$kind)}
        $checks++
    }
}finally{
    if(Test-Path -LiteralPath $testFile){Remove-Item -LiteralPath $testFile}
    Remove-Item -LiteralPath $temp
}
if(('IW7.CommunityBuild.BuildJob' -as [type]) -or ('IW7ResourceMemoryV1' -as [type]) -or (Test-Path -LiteralPath $rootBefore.RunRoot)){
    throw 'Plan loaded native classes or created the codec root.'
}
$checks++
"$checks Plan controls passed; only plan JSON content/hash read, no payload hashes, native classes, reservation or codec launched."
