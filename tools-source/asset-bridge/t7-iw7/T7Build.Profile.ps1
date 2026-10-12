# Only the fixed T7 artifact/deadline profile. Original-job ownership, compiler
# telemetry qualification, process identity, stop and quarantine remain H1 code.
function Open-T7Pin($Pin,$Context) {
    Assert-H1Path $Pin.Path
    if($Pin.SHA256 -cnotmatch '^[0-9a-f]{64}$' -or $Pin.Bytes -le 0 -or $Pin.Bytes -gt 256MB){throw 'Invalid T7 input/artifact pin.'}
    $stream=[IO.FileStream]::new($Pin.Path,'Open','Read','Read')
    try {
        if($stream.Length -ne $Pin.Bytes){throw 'T7 input length differs.'}
        $hash=[Security.Cryptography.IncrementalHash]::CreateHash([Security.Cryptography.HashAlgorithmName]::SHA256)
        try {
            $buffer=[byte[]]::new(1MB)
            while(($count=$stream.Read($buffer,0,$buffer.Length)) -gt 0) {
                $hash.AppendData($buffer,0,$count)
                Assert-H1Deadline $script:T7GroupStarted 600
            }
            $actual=[Convert]::ToHexString($hash.GetHashAndReset()).ToLowerInvariant()
        }finally{$hash.Dispose()}
        if($actual -cne $Pin.SHA256 -or $stream.Length -ne $Pin.Bytes){throw 'T7 input hash/length differs.'}
        $stream.Position=0;$Context.Guards.Add($stream)
    }catch{$stream.Dispose();throw}
}

$script:T7H1Budget=${function:Test-H1Budget}
function Test-H1Budget($Plan,$State) {
    Assert-H1Deadline $script:T7GroupStarted $Plan.GroupDeadlineSeconds
    & $script:T7H1Budget $Plan $State
}

function Get-H1CompilerArtifacts($Plan,$Context) {
    # H1 calls this before any accepted cl/vctip cleanup. It is also called
    # after ordinary closure. Each stage has its own PDB; prior guards stay open.
    foreach($name in $script:T7CurrentStage.Artifacts) {
        $path=Join-Path (Join-Path $Plan.RunRoot $script:T7CurrentStage.Name) $name
        Assert-H1Path $path
        $item=Get-Item -LiteralPath $path
        $limit=if($script:T7CurrentStage.Stage -ceq 'Link'){192MB}else{32MB}
        if($item.Length -le 0 -or $item.Length -gt $limit){throw 'T7 stage artifact absent/oversized.'}
        $pin=[pscustomobject]@{Path=$path;Bytes=$item.Length;SHA256=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()}
        Open-T7Pin $pin $Context
        $pin
    }
}

function Assert-T7Dependencies($Plan,$StageRoot) {
    $deps=Read-H1SmallJson (Join-Path $StageRoot 'dependencies.json') 1MB
    $known=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($pin in @($Plan.Bindings)+@($Plan.Inputs)){$null=$known.Add([IO.Path]::GetFullPath($pin.Path))}
    foreach($path in @($deps.Data.Source)+@($deps.Data.Includes)) {
        if(!$known.Contains([IO.Path]::GetFullPath($path))){throw ('Compiler consumed input outside guarded set: '+$path)}
    }
    if(@($deps.Data.Includes).Count -gt 2048){throw 'Compiler dependency count exceeded.'}
}

function New-T7Start($Plan,$Stage,[string]$StageRoot) {
    $start=[Diagnostics.ProcessStartInfo]::new($Stage.Image)
    $start.UseShellExecute=$false;$start.CreateNoWindow=$true;$start.WindowStyle='Hidden';$start.WorkingDirectory=$StageRoot
    $start.Environment.Clear()
    foreach($property in $Plan.Environment.PSObject.Properties){$start.Environment[$property.Name]=[string]$property.Value}
    $start.Environment['TEMP']=$StageRoot;$start.Environment['TMP']=$StageRoot
    foreach($argument in $Stage.Arguments){$start.ArgumentList.Add([string]$argument)}
    $start
}
