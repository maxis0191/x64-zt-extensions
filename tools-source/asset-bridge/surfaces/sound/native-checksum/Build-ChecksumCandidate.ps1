param([Parameter(Mandatory)][string]$PlanPath,[Parameter(Mandatory)][string]$PlanSHA256,[switch]$Build)
$ErrorActionPreference='Stop'
# No imported code executes before its retained read guard and exact byte hash.
$bootstrap=@{Guards=[Collections.Generic.List[IDisposable]]::new();Files=@{};Retain=$false}
function Open-ChecksumBootstrap([string]$Path,[long]$Maximum) {
    if(![IO.Path]::IsPathFullyQualified($Path) -or $Path.Contains('"')){throw 'Absolute literal bootstrap path required.'}
    $full=[IO.Path]::GetFullPath($Path)
    for($p=$full;$p;$p=Split-Path $p -Parent){
        if((Test-Path -LiteralPath $p) -and (Get-Item -LiteralPath $p -Force).Attributes.HasFlag([IO.FileAttributes]::ReparsePoint)){throw 'Redirected bootstrap path refused.'}
    }
    if(!$bootstrap.Files.ContainsKey($full)){
        $stream=[IO.File]::Open($full,'Open','Read','Read');$bootstrap.Guards.Add($stream);$bootstrap.Files[$full]=$stream
    }
    $stream=$bootstrap.Files[$full]
    if($stream.Length -le 0 -or $stream.Length -gt $Maximum){throw 'Bounded bootstrap file required.'}
    $stream
}
function Get-ChecksumBootstrapHash($Stream) {
    $Stream.Position=0;[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($Stream)).ToLowerInvariant()
}
function Read-ChecksumBootstrapJson($Stream) {
    $Stream.Position=0;$reader=[IO.StreamReader]::new($Stream,[Text.UTF8Encoding]::new($false,$true),$true,4096,$true)
    try{$text=$reader.ReadToEnd()}finally{$reader.Dispose()}
    function CheckKeys($Element,[ref]$Nodes) {
        $Nodes.Value++;if($Nodes.Value -gt 30000){throw 'Bootstrap JSON node bound exceeded.'}
        if($Element.ValueKind -eq [System.Text.Json.JsonValueKind]::Object){
            $keys=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
            foreach($p in $Element.EnumerateObject()){if(!$keys.Add($p.Name)){throw 'Duplicate bootstrap JSON key.'};CheckKeys $p.Value $Nodes}
        }elseif($Element.ValueKind -eq [System.Text.Json.JsonValueKind]::Array){foreach($child in $Element.EnumerateArray()){CheckKeys $child $Nodes}}
    }
    $document=[System.Text.Json.JsonDocument]::Parse($text)
    try{$nodes=0;CheckKeys $document.RootElement ([ref]$nodes)}finally{$document.Dispose()}
    ConvertFrom-Json -InputObject $text -AsHashtable -DateKind String -Depth 64
}
try {
    $planStream=Open-ChecksumBootstrap $PlanPath 2MB
    $core=Join-Path $PSScriptRoot 'BuildCandidate.Core.ps1';$receipt=Join-Path $PSScriptRoot 'BuildReceipt.Core.ps1'
    foreach($path in @($PSCommandPath,$core,$receipt)){$null=Open-ChecksumBootstrap $path 256KB}
    if($PlanSHA256 -cnotmatch '^[a-f0-9]{64}$' -or (Get-ChecksumBootstrapHash $planStream) -cne $PlanSHA256){throw 'Reviewed sound build Plan changed.'}
    $plan=Read-ChecksumBootstrapJson $planStream
    if($plan.schema -cne 'iw7.sound-checksum-build-plan/1' -or @($plan.source_pins).Count -gt 64 -or @($plan.providers).Count -ne 6){throw 'Bounded exact sound Plan required.'}
    foreach($pin in @($plan.source_pins)+@($plan.providers)){$null=Open-ChecksumBootstrap $pin.path 1MB}
    foreach($path in @($PSCommandPath,$core,$receipt,$plan.scheduler,$plan.worker,(Join-Path $PSScriptRoot 'build_contract.py'))){
        if(@($plan.source_pins|Where-Object path -IEQ $path).Count -ne 1){throw 'Entry/core/worker/scheduler not bound by source pins.'}
    }
    foreach($pin in @($plan.source_pins)+@($plan.providers)){
        $stream=$bootstrap.Files[[IO.Path]::GetFullPath($pin.path)]
        if($stream.Length -ne $pin.bytes -or (Get-ChecksumBootstrapHash $stream) -cne $pin.sha256){throw 'Guarded build source/provider changed.'}
    }
    $sealStream=Open-ChecksumBootstrap $plan.seal 4MB;$stateStream=Open-ChecksumBootstrap $plan.seal_result 16KB
    if((Get-ChecksumBootstrapHash $sealStream) -cne $plan.seal_sha256 -or
        (Get-ChecksumBootstrapHash $stateStream) -cne $plan.seal_result_sha256){throw 'Input seal or final lifecycle changed.'}
    $seal=Read-ChecksumBootstrapJson $sealStream;$sealState=Read-ChecksumBootstrapJson $stateStream
    . $core
    Assert-ChecksumBuildPlan $plan $seal $sealState
    if(Test-Path -LiteralPath $plan.candidate){throw 'Fresh candidate required; prior evidence must be preserved.'}
    if(!$Build){
        [ordered]@{Status='PlanOnly';PlanSHA256=$PlanSHA256;Files=$seal.FileCount;InputBytes=$seal.TotalBytes;
            Commands=14;PhysicalBytes=4GB;CommitBytes=6GB;StopBytes=512MB;PlanningCeilingBytes=768MB;
            NativeStarted=$false;NativeTypesLoaded=$false;AdmissionRequested=$false;Ready=$false}|ConvertTo-Json
        return
    }
    . $plan.scheduler
    foreach($role in 'supervision','residual_policy','completion','diagnostics'){
        $provider=@($plan.providers|Where-Object role -CEQ $role)[0];. $provider.path
    }
    . $receipt
    Invoke-ChecksumBuild $plan $seal $PlanPath $PlanSHA256 $bootstrap|ConvertTo-Json -Depth 20
} finally {
    if($bootstrap.Retain){$script:ChecksumRetainedBootstrap=$bootstrap}
    else{foreach($guard in $bootstrap.Guards){$guard.Dispose()}}
}
