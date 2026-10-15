# Finite Shredder/PAP caller; existing H1 job and Stock35 transactions own effects.
[CmdletBinding()]
param([Parameter(Mandatory)][string]$PlanPath,[Parameter(Mandatory)][string]$PlanSHA256,[switch]$Run)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
function Read-PlayerExportSource([string]$Path,[string]$SHA256,[long]$Bytes=-1,[Collections.Generic.List[object]]$Keep=$null){
    if($SHA256 -cnotmatch '^[0-9a-f]{64}$' -or ![IO.Path]::IsPathFullyQualified($Path)){throw 'Exact bounded Source pin required.'}
    for($part=$Path;$part;$part=[IO.Path]::GetDirectoryName($part)){if((Get-Item $part).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Source redirect refused.'}}
    $stream=[IO.FileStream]::new($Path,'Open','Read','Read')
    try{
        if($stream.Length -gt 2MB -or ($Bytes -ge 0 -and $stream.Length -ne $Bytes)){throw 'Source size differs.'}
        $buffer=[byte[]]::new(2MB+1);$used=0
        do{$count=$stream.Read($buffer,$used,$buffer.Length-$used);$used+=$count}while($count -gt 0 -and $used -lt $buffer.Length)
        if($used -gt 2MB){throw 'Source grew above cap before hash/decode.'}
        $raw=[byte[]]::new($used);[Array]::Copy($buffer,$raw,$used)
        if([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($raw)).ToLowerInvariant() -cne $SHA256){throw 'Source hash differs.'}
        $text=[Text.Encoding]::UTF8.GetString($raw)
        if($null -ne $Keep){$stream.Position=0;$Keep.Add($stream);$stream=$null};$text
    }finally{if($stream){$stream.Dispose()}}
}
$plan=Read-PlayerExportSource $PlanPath $PlanSHA256|ConvertFrom-Json -Depth 30
if($plan.Schema -cne 'iw7.player-template-export-source/1' -or $plan.Ready -or $plan.CandidateExecuted -or
 $plan.StockContentQualified -or $plan.RetailAliasCount -ne 70 -or $plan.UniqueRetailSources -ne 39 -or
 $plan.RunnerBinding.Path -cne $PSCommandPath -or $plan.GroupSeconds -ne 600 -or $plan.ToolSeconds -ne 240 -or
 $plan.GeneratedLimitBytes -ne 16777216 -or $plan.MetadataReserveBytes -ne 1048576){throw 'Exact unexecuted finite export plan required.'}
$null=Read-PlayerExportSource $plan.RunnerBinding.Path $plan.RunnerBinding.SHA256 $plan.RunnerBinding.Bytes
foreach($pin in $plan.SourceBindings){$null=Read-PlayerExportSource $pin.Path $pin.SHA256 $pin.Bytes}
foreach($name in 'Core','Scheduler','Profile','StockCore','BeaconCore','ArenaProcess'){
    if(@($plan.SourceBindings|Where-Object Path -CEQ $plan.Providers.$name).Count -ne 1){throw 'Exact existing provider Source binding required.'}
}
$request=Read-PlayerExportSource $plan.Request.Path $plan.Request.SHA256 $plan.Request.Bytes
if($request -cne "weapon,iw7_shredder_zm`nattachment,shredderpap1`n" -or $plan.Request.Bytes -ne 47){throw 'Exact two-row request required.'}
if($plan.Pack -cne 'paris_enemy_cp_zmb_raygun_template_a_player_weapon_source' -or
 (@($plan.StockManifests.Name)-join '|') -cne 'root|main|zone' -or (@($plan.StockManifests|ForEach-Object {$_.Count})-join '|') -cne '7|31|32'){throw 'Fixed pair/layout required.'}
foreach($manifest in $plan.StockManifests){$null=Read-PlayerExportSource $manifest.Path $manifest.SHA256 $manifest.Bytes}
if(Test-Path $plan.RunRoot){throw 'Fresh owned runtime required.'}
if(!$Run){[ordered]@{Schema='iw7.player-export-default/1';PlanSHA256=$PlanSHA256;RetailAliases=70;UniqueRetailSources=39;
 NativeTypesLoaded=$false;OpaqueInputsRead=$false;LeaseAcquired=$false;RuntimeCreated=$false;CandidateExecuted=$false;Ready=$false}|ConvertTo-Json;return}
$hostArgs=[Environment]::GetCommandLineArgs();$commandIndex=[Array]::IndexOf($hostArgs,'-Command')
if('-NoExit' -cnotin $hostArgs -or $commandIndex -lt 0 -or $hostArgs[$commandIndex+1] -notmatch '^\s*\.\s+' -or $MyInvocation.InvocationName -cne '.'){throw 'Physical fresh NoExit/dot host required.'}
$physical=Get-CimInstance Win32_Process -Filter "ProcessId=$PID"
if(!$physical.ExecutablePath -or !$physical.CreationDate -or $physical.CommandLine -notmatch '(?i)-NoExit\b' -or
 ('IW7.AnimationProbe.NativeJob' -as [type]) -or ('IW7StockLinksV1.Ntfs' -as [type])){throw 'Fresh original host identity required.'}
$guards=[Collections.Generic.List[object]]::new()
$context=[pscustomobject]@{Owner=$null;Closed=$true;Lease=$null;Guards=$guards;Work=$plan.WorkRoot}
$state=[ordered]@{Schema='iw7.player-template-export/1';Status='Pending';PlanSHA256=$PlanSHA256;CanExit=$false;Ready=$false;
 Host=[ordered]@{PID=$PID;Image=$physical.ExecutablePath;CreatedUtc=$physical.CreationDate.ToUniversalTime().ToString('o')};
 Inputs=[Collections.Generic.List[object]]::new();ContentPins=[Collections.Generic.List[object]]::new();
 CreatedCopies=[Collections.Generic.List[object]]::new();UnknownCopyCreation=$false;LeaseReleased=$false;GuardsDisposed=$false;CandidateExecuted=$false}
$root=@{Context=$context;State=$state;Plan=$plan;Key='IW7.PlayerTemplateExport.Original';StockContexts=[Collections.Generic.List[object]]::new();CopyStreams=[Collections.Generic.List[object]]::new()}
$global:IW7PlayerTemplateExport=$root;[AppDomain]::CurrentDomain.SetData($root.Key,$root)
$failure=$null;$created=$false
function Assert-PlayerExportClock{Assert-H1Deadline $script:T7GroupStarted $plan.GroupSeconds}
function Pin-PlayerOpaque($Pin){Open-T7Pin $Pin $context}
function Copy-PlayerOwned($Pin,[string]$Target,[switch]$Mutable){
    Assert-PlayerExportClock;Pin-PlayerOpaque $Pin
    $state.UnknownCopyCreation=$true
    $output=[IO.FileStream]::new($Target,'CreateNew','Write','Read')
    $root.CopyStreams.Add($output) # Retain the actual returned creator before inspect/write can fail.
    $record=[pscustomobject]@{Path=$Target;Identity=[IW7StockLinksV1.Ntfs]::Inspect($output.SafeFileHandle).Identity;Bytes=$Pin.Bytes;SHA256=$Pin.SHA256}
    $state.CreatedCopies.Add($record);$state.UnknownCopyCreation=$false
    try{$input=[IO.FileStream]::new($Pin.Path,'Open','Read','Read');try{$input.CopyTo($output);$output.Flush($true)}finally{$input.Dispose()}}finally{$output.Dispose()}
    if(!$Mutable){Pin-PlayerOpaque $record};Assert-PlayerExportClock
}
function Confirm-PlayerStock{
    $totals=@{}
    foreach($tx in $root.StockContexts){
        if(!$tx.Prepared -or $tx.UnknownCreation -or ![object]::ReferenceEquals($tx.OwnerRoot,$root)){throw 'Original prepared stock context required.'}
        foreach($source in $tx.Sources){if(!$totals.ContainsKey($source.Before.Identity)){$totals[$source.Before.Identity]=0};$totals[$source.Before.Identity]++}
    }
    foreach($tx in $root.StockContexts){foreach($source in $tx.Sources){
        $base=@($plan.SourceBaselines|Where-Object Identity -CEQ $source.Before.Identity)[0]
        Assert-IW7StockStableMetadata ([IW7StockLinksV1.Ntfs]::Inspect($source.Guard)) $source.Before ($base.Links+$totals[$source.Before.Identity])
        Assert-IW7StockStableMetadata (Get-IW7StockLinkMetadata $source.Path) $source.Before ($base.Links+$totals[$source.Before.Identity])
        Assert-IW7StockStableMetadata (Get-IW7StockLinkMetadata $source.Target) $source.Before ($base.Links+$totals[$source.Before.Identity])
    }}
    foreach($pin in $state.ContentPins){Pin-PlayerOpaque $pin}
    foreach($pin in @($plan.Candidate,$plan.TLS,$plan.Sentinel)){Pin-PlayerOpaque $pin}
    foreach($copy in $state.CreatedCopies){
        if((Get-IW7StockLinkMetadata $copy.Path).Identity -cne $copy.Identity){throw 'Original owned-copy identity differs.'}
        if($copy.Path -cne (Join-Path $plan.WorkRoot 'main/fileSysCheck.cfg')){Pin-PlayerOpaque $copy}
    }
    Assert-PlayerExportClock
}
function Test-PlayerGenerated($Current,[long]$Limit=$plan.GeneratedLimitBytes){
    Assert-PlayerExportClock
    $items=[Collections.Generic.List[object]]::new();$queue=[Collections.Generic.Queue[string]]::new();$queue.Enqueue($plan.RunRoot)
    while($queue.Count){
        $directory=$queue.Dequeue();Assert-H1Path $directory
        foreach($path in [IO.Directory]::EnumerateFileSystemEntries($directory)){
            Assert-H1Path $path;$item=Get-Item -LiteralPath $path;$items.Add($item)
            if($items.Count -gt 256){throw 'Finite export path count exceeded.'}
            if($item.PSIsContainer){$queue.Enqueue($path)}
        }
    }
    $exempt=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($entry in $state.Inputs){if($entry.TargetId -cne $entry.SourceId){throw 'Same-ID alias proof differs.'};$null=$exempt.Add($entry.Target)}
    # Only the prequalified copied tool is a baseline code input. TLS/sentinel,
    # journals, logs and every generated file remain in the measured allowance.
    $null=$exempt.Add((Join-Path $plan.WorkRoot 'zonetool-iw7-player.exe'))
    $bytes=0L
    foreach($item in $items){
        Assert-H1Path $item.FullName
        if(!$item.PSIsContainer -and !$exempt.Contains($item.FullName)){$bytes+=$item.Length}
    }
    $state.GeneratedObservedBytes=$bytes
    if($bytes -gt $Limit){throw 'Sampled generated output allowance exceeded.'}
    foreach($name in 'stdout.log','stderr.log'){
        $path=Join-Path (Join-Path $plan.RunRoot 'owned-player-template') $name
        if((Test-Path $path) -and (Get-Item $path).Length -gt 2MB){throw 'Sampled stream threshold exceeded.'}
    }
    Assert-PlayerExportClock
}
function Read-PlayerOutput([string]$Path,[int]$Cap){
    Assert-PlayerExportClock;Assert-H1Path $Path
    $stream=[IO.FileStream]::new($Path,'Open','Read','Read');$guards.Add($stream)
    if($stream.Length -le 0 -or $stream.Length -gt $Cap){throw 'Output length exceeds bound.'}
    $buffer=[byte[]]::new($Cap+1);$used=0
    do{$n=$stream.Read($buffer,$used,$buffer.Length-$used);$used+=$n}while($n -gt 0 -and $used -lt $buffer.Length)
    if($used -gt $Cap){throw 'Output grew above cap before hash/decode.'}
    $raw=[byte[]]::new($used);[Array]::Copy($buffer,$raw,$used);$stream.Position=0
    $sha=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($raw)).ToLowerInvariant()
    Assert-PlayerExportClock
    [pscustomobject]@{Path=$Path;Bytes=$used;SHA256=$sha;Text=[Text.Encoding]::UTF8.GetString($raw)}
}
try{
    foreach($pin in @($plan.SourceBindings)+@($plan.RunnerBinding)+@($plan.Request)+@($plan.StockManifests)){
        $null=Read-PlayerExportSource $pin.Path $pin.SHA256 $pin.Bytes $guards
    }
    . $plan.Providers.Core;. $plan.Providers.Scheduler
    $context.Lease=Enter-IW7ResourceLease -Scope $plan.RunRoot -Kind Extract -PhysicalBytes 8GB -CommitBytes 12GB -Owner 'One Shredder/PAP native template export'
    $state.LeaseToken=$context.Lease.Token;$script:T7GroupStarted=Get-H1Clock
    . $plan.Providers.Profile;. $plan.Providers.StockCore;. $plan.Providers.BeaconCore;. $plan.Providers.ArenaProcess
    Pin-PlayerOpaque $plan.JobAssembly
    [Reflection.Assembly]::LoadFrom($plan.JobAssembly.Path)|Out-Null
    [IO.Directory]::CreateDirectory($plan.RunRoot)|Out-Null;$created=$true
    $validate={param($Token,$Target)
        if(![object]::ReferenceEquals([AppDomain]::CurrentDomain.GetData($root.Key),$root) -or $null -eq $context.Lease -or
         $context.Lease.Token -cne $Token -or $PID -ne $state.Host.PID){throw 'Original admitted export root required.'}
        Assert-PlayerExportClock
    }
    foreach($manifest in $plan.StockManifests){
        $linkPlan=Read-IW7StockLinkPlan -ManifestPath $manifest.Path -ExpectedManifestSHA256 $manifest.SHA256 -SourceRoot $plan.StockSourceRoot -TargetRoot $manifest.Target
        $tx=New-IW7StockLinkTransaction -Plan $linkPlan -OwnerRoot $root -RetentionKey $root.Key -TransactionSlot ('Stock_'+$manifest.Name) -LeaseToken $context.Lease.Token -ValidateCaller $validate -JournalPath (Join-Path $plan.RunRoot ('stock-'+$manifest.Name+'.jsonl'))
        $root.StockContexts.Add($tx);Invoke-IW7StockLinkPreflight $tx
        foreach($source in $tx.Sources){
            if(@($state.ContentPins|Where-Object Path -IEQ $source.Path).Count -eq 0){
                # Fresh content evidence now, never a relabelled historical SHA.
                $stream=[IO.FileStream]::new($source.Path,'Open','Read','Read');$guards.Add($stream)
                if($stream.Length -ne $source.Before.Bytes -or $stream.Length -gt 256MB){throw 'Finite source length differs.'}
                $hash=[Security.Cryptography.IncrementalHash]::CreateHash([Security.Cryptography.HashAlgorithmName]::SHA256)
                try{$buffer=[byte[]]::new(1MB);while(($n=$stream.Read($buffer)) -gt 0){$hash.AppendData($buffer,0,$n);Assert-PlayerExportClock};$sha=[Convert]::ToHexString($hash.GetHashAndReset()).ToLowerInvariant()}finally{$hash.Dispose()}
                $stream.Position=0;$state.ContentPins.Add([pscustomobject]@{Path=$source.Path;Bytes=$stream.Length;SHA256=$sha})
            }
        }
        Invoke-IW7StockLinkApply $tx
        foreach($source in $tx.Sources){$state.Inputs.Add([pscustomobject]@{Relative=[IO.Path]::GetRelativePath($plan.WorkRoot,$source.Target).Replace('\','/');Mode='HardLink';Source=$source.Path;Target=$source.Target;SourceId=$source.Before.Identity;TargetId=(Get-IW7StockLinkMetadata $source.Target).Identity})}
        Assert-PlayerExportClock
    }
    Copy-PlayerOwned $plan.Candidate (Join-Path $plan.WorkRoot 'zonetool-iw7-player.exe')
    Copy-PlayerOwned $plan.TLS (Join-Path $plan.WorkRoot 'tlsdll.dll')
    Initialize-IW7StockLinkNtfs
    $sentinel=[IW7StockLinksV1.Ntfs]::OpenStock($plan.Sentinel.Path);$guards.Add($sentinel)
    $actual=[IW7StockLinksV1.Ntfs]::Inspect($sentinel)
    if($actual.Identity -cne $plan.Sentinel.Identity -or $actual.Bytes -ne 77){throw 'Exact current owned sentinel identity required.'}
    Copy-PlayerOwned $plan.Sentinel (Join-Path $plan.WorkRoot 'main/fileSysCheck.cfg') -Mutable
    Confirm-PlayerStock
    $tool=Join-Path $plan.WorkRoot 'zonetool-iw7-player.exe'
    $arguments=@('-headless','-iw7-player-weapon-templates','cp_zmb',$plan.Request.Path,$plan.Pack)
    Test-PlayerGenerated $state # Reject redirects before the existing profile's enumeration.
    $state.CandidateInvocationAttempted=$true
    $state.Tool=Invoke-OriginalArenaTool $context $tool $plan.Candidate.SHA256 $arguments $plan.WorkRoot $plan.RunRoot 'player-template' $state.Inputs $plan.ToolSeconds {param($Ctx,$Current,$Logs) Test-PlayerGenerated $Current}
    $state.CandidateExecuted=$true
    Test-PlayerGenerated $state.Tool
    $stdout=Read-PlayerOutput $state.Tool.Stdout 2MB
    $marker='IW7_PLAYER_WEAPON_TEMPLATES donor=cp_zmb weapon=iw7_shredder_zm pap=shredderpap1 count=2 output=dump\'+$plan.Pack
    if(@($stdout.Text -split '\r?\n'|Where-Object {$_ -ceq $marker}).Count -ne 1 -or $stdout.Text -match '\[ ERROR \]|\[ FATAL \]|IW7 player/PAP template export failed'){throw 'Exact successful native export marker required.'}
    $output=Join-Path $plan.WorkRoot ('dump/'+$plan.Pack)
    $files=@(Get-ChildItem $output -Recurse -File -Force)
    $expected=@('weapons/iw7_shredder_zm.json','attachments/shredderpap1.json','player-template-manifest.json')
    if($files.Count -ne 3 -or @($files|Where-Object {([IO.Path]::GetRelativePath($output,$_.FullName).Replace('\','/')) -cnotin $expected}).Count){throw 'Exact full two-JSON/manifest output required.'}
    $state.Artifacts=@(foreach($relative in $expected){
        $path=Join-Path $output $relative;$cap=if($relative -ceq 'player-template-manifest.json'){16384}else{2MB}
        $read=Read-PlayerOutput $path $cap
        $pin=[pscustomobject]@{Path=$path;Bytes=$read.Bytes;SHA256=$read.SHA256}
        $data=$read.Text|ConvertFrom-Json -Depth 100
        if($relative -ceq 'player-template-manifest.json'){$state.NativeManifest=$data}else{
            $name=if($relative -like 'weapons/*'){'iw7_shredder_zm'}else{'shredderpap1'}
            if($data.szInternalName -cne $name){throw 'Native JSON identity differs.'}
        };$pin
    })
    if($state.NativeManifest.schema -cne 'iw7.player-weapon-templates/1' -or $state.NativeManifest.native_source_pin -cne 'fab935826c898806855376662a8a03317b3ad8f1' -or $state.NativeManifest.donor -cne 'cp_zmb' -or
       $state.NativeManifest.weapon -cne 'iw7_shredder_zm' -or $state.NativeManifest.pap_attachment -cne 'shredderpap1' -or @($state.NativeManifest.files).Count -ne 2){throw 'Native manifest scope differs.'}
    foreach($flag in 'bo3_assets_authenticated','weapon_granted','projectile_damage_verified','retail_pap_transaction_verified','gameplay_accepted'){
        if($state.NativeManifest.$flag -isnot [bool] -or $state.NativeManifest.$flag){throw 'Native manifest overclaims scope.'}
    }
    foreach($entry in $state.NativeManifest.files){$pin=@($state.Artifacts|Where-Object Path -CEQ (Join-Path $output $entry.path))[0];if(!$pin -or $pin.Bytes -ne $entry.bytes -or $pin.SHA256 -cne $entry.sha256.ToLowerInvariant()){throw 'Native manifest file binding differs.'}}
    if((@($state.NativeManifest.files.path|Sort-Object)-join '|') -cne 'attachments/shredderpap1.json|weapons/iw7_shredder_zm.json'){throw 'Native manifest must bind both unique files.'}
    Confirm-PlayerStock;$state.Status='MeasuredPassed';$state.StockContentQualified=$true
}catch{$failure=$_;$state.Status='Failed';$state.Error=$_.Exception.Message}
finally{
    if(!$context.Closed -and $context.Owner){try{$context.Owner.StopAndConfirm(5000);$context.Closed=$context.Owner.Closed}catch{$state.ClosureError=$_.Exception.Message}}
    if($created -and $context.Closed -and $context.Lease -and !$state.UnknownCopyCreation){
        try{
            Confirm-PlayerStock;Test-PlayerGenerated $state
            $state.OriginalRootAndJobClosed=$context.Closed
            $state.StockTransactions=@($root.StockContexts|ForEach-Object{[ordered]@{Target=$_.Plan.TargetRoot;Prepared=$_.Prepared;SourcePreserved=$_.SourcePreserved;UnknownCreation=$_.UnknownCreation;CreatedLinks=$_.CreatedLinks.Count}})
            $path=Join-Path $plan.RunRoot 'measured-before-release.json'
            $raw=[Text.UTF8Encoding]::new($false).GetBytes(($state|ConvertTo-Json -Depth 30)+"`n")
            if($raw.Length -gt $plan.MetadataReserveBytes){throw 'Metadata reserve exceeded.'}
            $stream=[IO.File]::Open($path,'CreateNew','Write','Read');try{$stream.Write($raw);$stream.Flush($true)}finally{$stream.Dispose()}
            $sha=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($raw)).ToLowerInvariant()
            $null=Read-PlayerExportSource $path $sha $raw.Length;Assert-PlayerExportClock
            Test-PlayerGenerated $state ($plan.GeneratedLimitBytes+$plan.MetadataReserveBytes)
            $before=[ordered]@{Schema='iw7.player-export-before-release/1';PlanSHA256=$PlanSHA256;MeasuredSHA256=$sha;OriginalRootAndJobClosed=$true;
                StockPreparedAndPreserved=$true;OriginalLeaseToken=$context.Lease.Token;SourceGuardsHeld=$guards.Count;CandidateExecuted=$state.CandidateExecuted;Ready=$false}
            $beforeBytes=[Text.UTF8Encoding]::new($false).GetBytes(($before|ConvertTo-Json)+"`n")
            if($raw.Length+$beforeBytes.Length -gt $plan.MetadataReserveBytes){throw 'Reserved metadata exceeded.'}
            $beforePath=Join-Path $plan.RunRoot 'closure-before-release.json';$stream=[IO.File]::Open($beforePath,'CreateNew','Write','Read');try{$stream.Write($beforeBytes);$stream.Flush($true)}finally{$stream.Dispose()}
            $beforeSHA=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($beforeBytes)).ToLowerInvariant()
            $null=Read-PlayerExportSource $beforePath $beforeSHA $beforeBytes.Length;Assert-PlayerExportClock
            foreach($tx in $root.StockContexts){Close-IW7StockLinkGuards $tx}
            # Immutable aliases remain owned/prepared for evidence and later reuse.
            # No base/private-test-server file, metadata or bank is restored/written.
            Exit-IW7ResourceLease -Token $context.Lease.Token;$context.Lease=$null;$state.LeaseReleased=$true
            foreach($guard in $guards){$guard.Dispose()};$guards.Clear();$state.GuardsDisposed=$true
            Assert-PlayerExportClock
            $final=[ordered]@{Schema='iw7.player-export-closure/1';Status='ClosedReleasedPendingPostflight';PlanSHA256=$PlanSHA256;MeasuredSHA256=$sha;
                OriginalRootAndJobClosed=$true;LeaseReleased=$true;GuardsDisposed=$true;CandidateExecuted=$state.CandidateExecuted;Ready=$false}
            $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($final|ConvertTo-Json)+"`n")
            if($raw.Length+$beforeBytes.Length+$bytes.Length -gt $plan.MetadataReserveBytes){throw 'Final metadata reserve exceeded.'}
            $path=Join-Path $plan.RunRoot 'final-closure.json';$stream=[IO.File]::Open($path,'CreateNew','Write','Read');try{$stream.Write($bytes);$stream.Flush($true)}finally{$stream.Dispose()}
            $hash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant()
            $null=Read-PlayerExportSource $path $hash $bytes.Length;Assert-PlayerExportClock
            Test-PlayerGenerated $state ($plan.GeneratedLimitBytes+$plan.MetadataReserveBytes)
            $state.Status=if($failure){'FailedClosed'}else{'Passed'};$state.CanExit=$true
        }catch{$state.FinalizationError=$_.Exception.Message;if(!$failure){$failure=$_}}
    }
    if(!$state.CanExit){$state.Status=if($context.Closed -and $state.LeaseReleased){'ClosedFinalizationIncomplete'}else{'UnknownRetained'}}
    $state|ConvertTo-Json -Depth 10
}
if($failure){throw $failure}
