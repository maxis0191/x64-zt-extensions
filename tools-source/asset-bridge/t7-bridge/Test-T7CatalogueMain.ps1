# Pure Main-state snapshots. No live process/provider, file mutation or native types.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
. (Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1')
. (Join-Path $repo 'ops/Resource-Scheduler.Core.ps1')
. (Join-Path $PSScriptRoot 'T7Prepatch.Profile.ps1')
. (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
$script:checks=0;$script:processError=$false;$script:udpError=$false
function Check([bool]$Value,[string]$Why){if(!$Value){throw $Why};$script:checks++}
function Refuses([scriptblock]$Body,[string]$Pattern){
    $caught=$false
    try{& $Body}catch{$caught=$true;Check ($_.Exception.Message -match $Pattern) ('Unexpected error: '+$_.Exception.Message)}
    Check $caught ('Expected refusal: '+$Pattern)
}
function Copy-Value($Value){$Value|ConvertTo-Json -Depth 8|ConvertFrom-Json}
function Get-IW7ResourceProcesses {if($script:processError){throw 'Process snapshot failed'};$script:processes}
function Get-NetUDPEndpoint {
    [CmdletBinding()]param([int]$LocalPort)
    if($script:udpError){throw 'UDP snapshot failed'}
    if($PSBoundParameters.ContainsKey('LocalPort')){$script:udp|Where-Object LocalPort -EQ $LocalPort}else{$script:udp}
}
$original=[pscustomobject]@{PID=123;CreatedUtc='2026-10-12T00:00:00.0000000Z';Image=(Join-Path $repo 'runtime/synthetic-main.exe')}
$running=[pscustomobject]@{PID=$original.PID;CreatedUtc=$original.CreatedUtc;Image=$original.Image;Name='synthetic-main.exe'}
$plan=[pscustomobject]@{PreservedMain=$original}
Check ((Get-T7CatalogueMainBaseline $plan) -ceq 'Running') 'Historical running baseline changed.'
$script:processes=@($running);$script:udp=@([pscustomobject]@{LocalPort=27016;OwningProcess=123})
Check ((Assert-T7CatalogueMain $plan).GenerationAndUDP27016OwnerUnchanged) 'Exact running Main refused.'
foreach($kind in 'missing','generation','image','udp-owner','udp-missing') {
    $script:processes=@((Copy-Value $running));$script:udp=@([pscustomobject]@{LocalPort=27016;OwningProcess=123})
    switch($kind){
        missing {$script:processes=@()}
        generation {$script:processes[0].CreatedUtc='2026-10-12T01:00:00.0000000Z'}
        image {$script:processes[0].Image=Join-Path $repo 'runtime/other.exe'}
        udp-owner {$script:udp[0].OwningProcess=456}
        udp-missing {$script:udp=@()}
    }
    Refuses {Assert-T7CatalogueMain $plan} 'generation/UDP'
}
$plan|Add-Member NoteProperty MainBaseline 'Stopped'
$script:processes=@();$script:udp=@()
$proof=Assert-T7CatalogueMain $plan
Check ($proof.Baseline -ceq 'Stopped' -and $proof.OriginalPID -eq 123 -and $proof.OriginalCreatedUtc -ceq $original.CreatedUtc -and
    $proof.OriginalPIDAbsent -and $proof.ExpectedImageAbsent -and $proof.UDP27016Absent -and $proof.Cause -ceq 'Unknown') 'Stopped proof overclaimed or incomplete.'
$script:processes=@([pscustomobject]@{PID=789;CreatedUtc=$original.CreatedUtc;Image=(Join-Path $repo 'runtime/other/synthetic-main.exe');Name='synthetic-main.exe'})
$script:udp=@([pscustomobject]@{LocalPort=27017;OwningProcess=789})
Check ((Assert-T7CatalogueMain $plan).Baseline -ceq 'Stopped') 'Unrelated known process/port refused.'
foreach($kind in 'original-pid','reused-pid','new-image-pid','case-insensitive-image','inaccessible-image','udp-only','mixed') {
    $script:processes=@();$script:udp=@()
    switch($kind){
        original-pid {$script:processes=@((Copy-Value $running))}
        reused-pid {$r=Copy-Value $running;$r.Image=Join-Path $repo 'runtime/unrelated.exe';$r.CreatedUtc='2026-10-12T01:00:00.0000000Z';$script:processes=@($r)}
        new-image-pid {$r=Copy-Value $running;$r.PID=456;$script:processes=@($r)}
        case-insensitive-image {$r=Copy-Value $running;$r.PID=456;$r.Image=$r.Image.ToLowerInvariant();$script:processes=@($r)}
        inaccessible-image {$r=Copy-Value $running;$r.PID=456;$r.Image=$null;$script:processes=@($r)}
        udp-only {$script:udp=@([pscustomobject]@{LocalPort=27016;OwningProcess=456})}
        mixed {$script:processes=@((Copy-Value $running));$script:udp=@([pscustomobject]@{LocalPort=27016;OwningProcess=456})}
    }
    Refuses {Assert-T7CatalogueMain $plan} 'Stopped Main baseline'
}
$script:processes=@();$script:udp=@();$script:processError=$true
Refuses {Assert-T7CatalogueMain $plan} 'Process snapshot failed'
$script:processError=$false;$script:udpError=$true
Refuses {Assert-T7CatalogueMain $plan} 'UDP snapshot failed'
$script:udpError=$false
foreach($baseline in 'stopped','Absent','',$true){$plan.MainBaseline=$baseline;Refuses {Assert-T7CatalogueMain $plan} 'Unknown Main baseline'}
$plan.MainBaseline='Stopped'
foreach($field in 'PID','CreatedUtc','Image') {
    $plan.PreservedMain=Copy-Value $original;$plan.PreservedMain.$field=$null
    Refuses {Assert-T7CatalogueMain $plan} 'Original Main identity'
}
$plan.PreservedMain=Copy-Value $original;$plan.PreservedMain.CreatedUtc='not-a-date'
Refuses {Assert-T7CatalogueMain $plan} '.'
$plan.PreservedMain=$original
Check ((Assert-T7CatalogueMain $plan).Baseline -ceq 'Stopped') 'Before snapshot failed.'
$script:processes=@((Copy-Value $running));$script:processes[0].PID=456
Refuses {Assert-T7CatalogueMain $plan} 'Stopped Main baseline'
Check (!('IW7ResourceMemoryV1' -as [type]) -and !('IW7.AnimationProbe.NativeJob' -as [type])) 'Native types loaded during pure tests.'
[ordered]@{Status='Passed';Checks=$checks;LiveProvidersCalled=$false;NativeTypesLoaded=$false;RealLeaseAcquired=$false;NativeProcessStarted=$false;OwnerStockRead=$false}|ConvertTo-Json
