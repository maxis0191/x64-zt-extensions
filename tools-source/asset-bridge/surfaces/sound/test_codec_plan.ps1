param([Parameter(Mandatory)][string]$PlanPath,[Parameter(Mandatory)][string]$PlanSHA256)
$ErrorActionPreference='Stop'
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
try{
    foreach($kind in 'MissingPin','Arguments','ExistingRoot'){
        $plan=Get-Content -LiteralPath $PlanPath -Raw|ConvertFrom-Json
        switch($kind){
            MissingPin {$plan.HashInputs=@($plan.HashInputs|Where-Object {$_.Path -notlike '*codec_worker.py'})}
            Arguments {$plan.CodecArguments=@('-y')+@($plan.CodecArguments)}
            ExistingRoot {$plan.RunRoot=$temp}
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
"$checks Plan controls passed; no native classes, reservation or codec launched."
