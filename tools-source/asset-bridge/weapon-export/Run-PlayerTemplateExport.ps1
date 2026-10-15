# Finite Shredder/PAP caller; existing H1 job and Stock35 transactions own effects.
[CmdletBinding()]
param([Parameter(Mandatory)][string]$PlanPath,[Parameter(Mandatory)][string]$PlanSHA256,[switch]$Run)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
function Test-PlayerHostCreation([datetime]$CimCreated,[datetime]$KernelCreated){
    # Compare integral UTC microseconds; retain original kernel100ns separately.
    [long]$cimTicks=$CimCreated.ToUniversalTime().Ticks
    [long]$kernelTicks=$KernelCreated.ToUniversalTime().Ticks
    ($cimTicks-($cimTicks%10)) -eq ($kernelTicks-($kernelTicks%10))
}
function Read-PlayerExportSource([string]$Path,[string]$SHA256,[long]$Bytes=-1,[Collections.Generic.List[object]]$Keep=$null,
 [ValidateSet('Plan','Runner','Provider','Metadata','Request','StockManifest','Receipt')][string]$Role='Metadata'){
    # Role/path/extension checks precede Get-Item and, crucially, FileStream.
    if($SHA256 -cnotmatch '^[0-9a-f]{64}$' -or $Path -cnotmatch '^[A-Za-z]:\\' -or
       ![IO.Path]::IsPathFullyQualified($Path) -or [IO.Path]::GetFullPath($Path) -cne $Path -or
       $Path.Substring(2).Contains(':') -or $Path -match '[\x00-\x1f]' -or
       @($Path.Substring(3) -split '[\\/]'|Where-Object {$_ -in @('.','..') -or $_.TrimEnd(' ','.') -cne $_ -or $_ -match '^(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)'}).Count){throw 'Ordinary role-bound Source path required before open.'}
    $extension=[IO.Path]::GetExtension($Path).ToLowerInvariant();$name=[IO.Path]::GetFileName($Path)
    $allowed=if($Role -in @('Plan','StockManifest','Receipt')){@('.json')}elseif($Role -eq 'Request'){@('.csv')}elseif($Role -eq 'Provider'){@('.ps1','.cs','.py')}elseif($Role -eq 'Runner'){@('.ps1')}else{@('.json','.jsonl')}
    $providers=@('H1Native.Core.ps1','Resource-Scheduler.Core.ps1','T7Build.Profile.ps1','Stock-Links.Core.ps1','BeaconFF.Core.ps1','OriginalArena.Process.ps1',
        'Lab-Paths.ps1','StockLinks.cs','Resource-Memory.ps1','Resource-RecorderOwnedProcess.Core.ps1','ResourceMemory.cs',
        'H1Native.Compiler.ps1','LoadDiagnostic.Core.ps1','modal_window.py','recipient_dialog.py','iw7_capture.py','iw7_debugger.py')
    if($extension -cnotin $allowed -or ($Role -eq 'Runner' -and $name -cne 'Run-PlayerTemplateExport.ps1') -or
       ($Role -eq 'Provider' -and $name -cnotin $providers)){throw 'Text Source role/suffix/name refused before open.'}
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
function New-PlayerPublicationStream([string]$Path){
    [IO.File]::Open($Path,'CreateNew','ReadWrite','Read')
}
function Write-PlayerPublication([string]$Path,[byte[]]$Raw){
    $playerRoot=$script:PlayerTemplateExportOriginalRoot
    if($Raw.Length -gt $playerRoot.Plan.MetadataReserveBytes){throw 'Publication metadata reserve exceeded.'}
    $stream=New-PlayerPublicationStream $Path
    # Enrol the actual stream before any write/flush/readback can fail. Never
    # dispose it here: the original root retains it through all final checks.
    $playerRoot.PublicationGuards.Add($stream)
    $stream.Write($Raw,0,$Raw.Length);$stream.Flush($true);$stream.Position=0
    $buffer=[byte[]]::new($Raw.Length+1);$used=0
    do{$count=$stream.Read($buffer,$used,$buffer.Length-$used);$used+=$count}while($count -gt 0 -and $used -lt $buffer.Length)
    $expected=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($Raw)).ToLowerInvariant()
    if($used -ne $Raw.Length){throw 'Same-stream publication length differs.'}
    $actual=[byte[]]::new($used);[Array]::Copy($buffer,$actual,$used)
    if([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($actual)).ToLowerInvariant() -cne $expected){throw 'Same-stream publication hash differs.'}
    $expected
}
function Get-PlayerOriginalGuardHandle([object]$Guard){
    # Source/output pins use FileStream; OpenStock's sentinel is already the
    # actual SafeFileHandle. Refuse foreign shapes before disposing any guard.
    if($Guard -is [Microsoft.Win32.SafeHandles.SafeFileHandle]){return $Guard}
    if($Guard -is [IO.FileStream]){return $Guard.SafeFileHandle}
    throw 'Unexpected original publication/source guard type; retain original references.'
}
function Test-PlayerModalPlan($Plan){
    if(!$Plan.PSObject.Properties['ModalDiagnostic']){return $false}
    $modal=$Plan.ModalDiagnostic
    if(!$modal -or $modal.Mode -isnot [string] -or $modal.Mode -cne 'global-mp-modal-only' -or
       (@($modal.PSObject.Properties.Name|Sort-Object)-join '|') -cne 'HelperSeconds|ModalSource|Mode|Python|RunRoot|WindowRecordBytes' -or
       $modal.HelperSeconds -isnot [long] -or $modal.HelperSeconds -ne 10 -or
       $modal.WindowRecordBytes -isnot [long] -or $modal.WindowRecordBytes -ne 65536 -or $Plan.ToolSeconds -ne 120){throw 'Exact existing one-modal diagnostic contract required.'}
    if($modal.Python.Path -isnot [string] -or $modal.Python.Path -cnotmatch '^[A-Za-z]:\\' -or
       [IO.Path]::GetFullPath($modal.Python.Path) -cne $modal.Python.Path -or $modal.Python.Path.Substring(2).Contains(':') -or
       [IO.Path]::GetFileName($modal.Python.Path) -cne 'python.exe' -or $modal.Python.Bytes -isnot [long] -or
       $modal.Python.Bytes -lt 1 -or $modal.Python.Bytes -gt 64MB -or $modal.Python.SHA256 -isnot [string] -or
       $modal.Python.SHA256 -cnotmatch '^[0-9a-f]{64}$' -or (@($modal.Python.PSObject.Properties.Name|Sort-Object)-join '|') -cne 'Bytes|Path|SHA256'){throw 'Declared original Python binding required without DEFAULT opaque open.'}
    if($modal.ModalSource -isnot [string] -or [IO.Path]::GetFileName($modal.ModalSource) -cne 'modal_window.py'){throw 'Exact existing modal adapter required.'}
    $package=$modal.ModalSource;for($i=0;$i -lt 5;$i++){$package=[IO.Path]::GetDirectoryName($package)}
    # The existing Python local_output validator only permits this package's
    # runtime. Keep its rule and declare a separate, fresh owned output subtree.
    if($modal.RunRoot -isnot [string] -or $modal.RunRoot -cne (Join-Path $package 'runtime/player-template-modal')){throw 'Exact package-owned modal runtime required.'}
    if(Test-Path -LiteralPath $modal.RunRoot){throw 'Fresh package-owned modal runtime required.'}
    $closure=@{
        H1Compiler='tools-source/asset-bridge/h1-fixture/H1Native.Compiler.ps1';LoadDiagnostic='tools-source/asset-bridge/world/original-arena/LoadDiagnostic.Core.ps1';
        Modal='tools-source/asset-bridge/world/original-arena/modal_window.py';Recipient='tools-source/asset-bridge/recipient/recipient_dialog.py';
        Capture='ops/iw7_capture.py';Debugger='ops/iw7_debugger.py'}
    foreach($name in $closure.Keys){
        $expected=Join-Path $package $closure[$name]
        if(@($Plan.SourceBindings|Where-Object {$_.Path -ceq $expected -and $_.Role -ceq 'Provider'}).Count -ne 1){throw 'Exact imported modal Source package layout required.'}
        if($name -in @('H1Compiler','LoadDiagnostic') -and $Plan.Providers.$name -cne $expected){throw 'Exact modal provider path required.'}
    }
    foreach($name in @('H1Compiler','LoadDiagnostic')){
        if(@($Plan.SourceBindings|Where-Object {$_.Path -ceq $Plan.Providers.$name -and $_.Role -ceq 'Provider'}).Count -ne 1){throw 'Exact existing modal provider Source pin required.'}
    }
    $names=@('H1Native.Compiler.ps1','LoadDiagnostic.Core.ps1','modal_window.py','recipient_dialog.py','iw7_capture.py','iw7_debugger.py')
    foreach($name in $names){if(@($Plan.SourceBindings|Where-Object {$_.Role -ceq 'Provider' -and [IO.Path]::GetFileName($_.Path) -ceq $name}).Count -ne 1){throw 'Complete fixed modal Source closure required.'}}
    if($modal.ModalSource -cne (Join-Path $package $closure.Modal)){throw 'Exact existing modal adapter required.'}
    $true
}
function Get-PlayerRetailProfile($Plan){
    if(!$Plan.PSObject.Properties['RetailProfile']){
        return [pscustomobject]@{Name='legacy70';Aliases=70;Sources=39;Counts='7|31|32';PakNames=@('assetfile1.pak')}
    }
    if($Plan.RetailProfile -isnot [string] -or $Plan.RetailProfile -cne 'fixed33-pak'){throw 'Exact explicit fixed33-pak retail profile required.'}
    # Names only from World M7's fixed namespace. No historical retail IDs/hashes
    # or World 104-input qualifier are reused by this Stock35 caller.
    $numbers=@(1,17,19,21,25,26,36,37,52,53,68,69,84,85,100,101,116,117,132,133,148,149,164,165,180,181,196,197,212,213,228,229,244)
    [pscustomobject]@{Name='fixed33-pak';Aliases=102;Sources=71;Counts='7|31|64';PakNames=@($numbers|ForEach-Object {'assetfile'+$_+'.pak'})}
}
function Get-PlayerRetailByteLimit($Plan,[string]$Path){
    $profile=Get-PlayerRetailProfile $Plan
    $name=[IO.Path]::GetFileName($Path)
    if($profile.Name -ceq 'fixed33-pak' -and $name -cin $profile.PakNames -and
       $Path -ceq (Join-Path $Plan.StockSourceRoot $name)){return [long]1GB}
    [long]256MB # Existing code/TLS/sentinel pins and legacy retail remain unchanged.
}
function Test-PlayerRetailManifests($Plan,$Profile){
    if($Profile.Name -cne 'fixed33-pak'){return}
    if(($Plan.RetailAliasCount -isnot [int] -and $Plan.RetailAliasCount -isnot [long]) -or
       ($Plan.UniqueRetailSources -isnot [int] -and $Plan.UniqueRetailSources -isnot [long]) -or
       $Plan.RunRoot -isnot [string] -or $Plan.WorkRoot -isnot [string] -or $Plan.StockSourceRoot -isnot [string] -or
       $Plan.WorkRoot -cne (Join-Path $Plan.RunRoot 'work') -or $Plan.SourceBaselines -isnot [array] -or $Plan.SourceBaselines.Count -ne 71){throw 'Exact owned fixed33 layout and 71 baseline declarations required.'}
    $identities=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach($baseline in $Plan.SourceBaselines){
        if($baseline.Identity -isnot [string] -or !$baseline.Identity -or !$identities.Add($baseline.Identity) -or
           ($baseline.Links -isnot [int] -and $baseline.Links -isnot [long]) -or $baseline.Links -lt 1){throw 'Distinct scalar historical baseline declarations required.'}
    }
    $sources=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $targets=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $paks=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach($pin in $Plan.StockManifests){
        $manifest=Read-PlayerExportSource $pin.Path $pin.SHA256 $pin.Bytes -Role StockManifest|ConvertFrom-Json -Depth 20
        if($pin.Name -isnot [string] -or $pin.Name -cnotin @('root','main','zone') -or $pin.Target -isnot [string] -or
           ($pin.Count -isnot [int] -and $pin.Count -isnot [long])){throw 'Scalar fixed33 manifest declaration required.'}
        $target=if($pin.Name -ceq 'root'){$Plan.WorkRoot}else{Join-Path $Plan.WorkRoot $pin.Name}
        if($manifest.target -isnot [string] -or $manifest.source -isnot [string] -or $pin.Target -cne $target -or
           $manifest.target -cne $target -or $manifest.source -cne $Plan.StockSourceRoot -or
           ($manifest.planned_files -isnot [int] -and $manifest.planned_files -isnot [long]) -or
           $manifest.files -isnot [array] -or $manifest.files.Count -ne $pin.Count -or $manifest.planned_files -ne $pin.Count){throw 'Exact fixed33 manifest source/target/count required.'}
        foreach($row in $manifest.files){
            if($row.relative -isnot [string] -or !$row.relative -or [IO.Path]::GetFileName($row.relative) -cne $row.relative -or $row.relative -match '[\\/:]' -or
               $row.relative -match '^(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)' -or
               $row.relative.TrimEnd(' ','.') -cne $row.relative -or !$targets.Add($pin.Name+'/'+$row.relative) -or
               ($row.bytes -isnot [int] -and $row.bytes -isnot [long]) -or $row.bytes -le 0 -or
               $row.bytes -gt (Get-PlayerRetailByteLimit $Plan (Join-Path $Plan.StockSourceRoot $row.relative))){throw 'Finite fixed33 row path/size/uniqueness required.'}
            $null=$sources.Add($row.relative)
            if($row.relative -match '(?i)\.pak$'){
                if($pin.Name -cne 'zone' -or $row.relative -cnotin $Profile.PakNames -or !$paks.Add($row.relative)){throw 'Only the exact 33 zone assetfiles are allowed.'}
            }
        }
    }
    if($targets.Count -ne 102 -or $sources.Count -ne 71 -or $paks.Count -ne 33){throw 'Exact fixed33 102-alias/71-source closure required.'}
}
$plan=Read-PlayerExportSource $PlanPath $PlanSHA256 -Role Plan|ConvertFrom-Json -Depth 30
$pairProfile=($null -ne $plan.PSObject.Properties['PairProfile'])
$pairDefinitions=($null -ne $plan.PSObject.Properties['PairDefinitions'])
if($pairProfile -and ($plan.PairProfile -isnot [bool] -or !$plan.PairProfile)){throw 'Explicit true pair profile opt-in required.'}
if($pairDefinitions -and ($plan.PairDefinitions -isnot [bool] -or !$plan.PairDefinitions)){throw 'Explicit true neutral definition opt-in required.'}
$modalSelected=Test-PlayerModalPlan $plan
if($pairProfile -and $modalSelected){throw 'Pair profile and modal diagnostics cannot mix.'}
if($pairDefinitions -and ($pairProfile -or $modalSelected)){throw 'Neutral definitions, profile and modal modes cannot mix.'}
$retailProfile=Get-PlayerRetailProfile $plan
if($plan.Schema -cne 'iw7.player-template-export-source/1' -or $plan.Ready -or $plan.CandidateExecuted -or
 $plan.StockContentQualified -or $plan.RetailAliasCount -ne $retailProfile.Aliases -or $plan.UniqueRetailSources -ne $retailProfile.Sources -or
 $plan.RunnerBinding.Path -cne $PSCommandPath -or $plan.GroupSeconds -ne 600 -or $plan.ToolSeconds -ne $(if($modalSelected){120}else{240}) -or
 $plan.GeneratedLimitBytes -ne 16777216 -or $plan.MetadataReserveBytes -ne 1048576){throw 'Exact unexecuted finite export plan required.'}
$null=Read-PlayerExportSource $plan.RunnerBinding.Path $plan.RunnerBinding.SHA256 $plan.RunnerBinding.Bytes -Role Runner
foreach($pin in $plan.SourceBindings){$null=Read-PlayerExportSource $pin.Path $pin.SHA256 $pin.Bytes -Role $pin.Role}
foreach($name in 'Core','Scheduler','Profile','StockCore','BeaconCore','ArenaProcess'){
    if(@($plan.SourceBindings|Where-Object Path -CEQ $plan.Providers.$name).Count -ne 1){throw 'Exact existing provider Source binding required.'}
}
$request=Read-PlayerExportSource $plan.Request.Path $plan.Request.SHA256 $plan.Request.Bytes -Role Request
if($request -cne "weapon,iw7_shredder_zm`nattachment,shredderpap1`n" -or $plan.Request.Bytes -ne 47){throw 'Exact two-row request required.'}
$expectedPack=if($pairDefinitions){'paris_enemy_cp_zmb_raygun_pair_definitions_a'}elseif($pairProfile){'paris_enemy_cp_zmb_raygun_pair_profile_a'}else{'paris_enemy_cp_zmb_raygun_template_a_player_weapon_source'}
if($plan.Pack -isnot [string] -or $plan.Pack -cne $expectedPack -or
 (@($plan.StockManifests.Name)-join '|') -cne 'root|main|zone' -or (@($plan.StockManifests|ForEach-Object {$_.Count})-join '|') -cne $retailProfile.Counts){throw 'Fixed pair/layout required.'}
foreach($manifest in $plan.StockManifests){$null=Read-PlayerExportSource $manifest.Path $manifest.SHA256 $manifest.Bytes -Role StockManifest}
Test-PlayerRetailManifests $plan $retailProfile
if(Test-Path $plan.RunRoot){throw 'Fresh owned runtime required.'}
if(!$Run){[ordered]@{Schema='iw7.player-export-default/1';PlanSHA256=$PlanSHA256;RetailAliases=$retailProfile.Aliases;UniqueRetailSources=$retailProfile.Sources;
 NativeTypesLoaded=$false;OpaqueInputsRead=$false;LeaseAcquired=$false;RuntimeCreated=$false;CandidateExecuted=$false;Ready=$false}|ConvertTo-Json;return}
$hostArgs=[Environment]::GetCommandLineArgs();$commandIndex=[Array]::IndexOf($hostArgs,'-Command')
$bundled='C:\Users\ezvalo\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$managed=Join-Path (Split-Path $bundled -Parent) 'pwsh.dll'
if($hostArgs.Count -ne 6 -or $hostArgs[0] -cne $managed -or $hostArgs[1] -cne '-NoLogo' -or $hostArgs[2] -cne '-NoProfile' -or
 $hostArgs[3] -cne '-NoExit' -or $commandIndex -ne 4 -or $hostArgs[5] -cne $plan.ExpectedHostCommand -or
 $plan.ExpectedHostCommand -cne (". '"+$plan.CapsulePath+"' -Run") -or $MyInvocation.InvocationName -cne '.' -or
 [Reflection.Assembly]::GetEntryAssembly().Location -cne $managed){throw 'Physical fresh NoExit/dot managed invocation required.'}
$physical=Get-CimInstance Win32_Process -Filter "ProcessId=$PID"
$currentProcess=[Diagnostics.Process]::GetCurrentProcess()
try{$physicalImage=$currentProcess.MainModule.FileName;$kernelCreated=$currentProcess.StartTime.ToUniversalTime();$physicalCreated=$kernelCreated.ToString('o')}finally{$currentProcess.Dispose()}
if($physical.ExecutablePath -cne $bundled -or $physicalImage -cne $bundled -or !$physical.CreationDate -or
 !(Test-PlayerHostCreation $physical.CreationDate $kernelCreated) -or $physical.CommandLine -notmatch '(?i)-NoExit\b' -or
 ('IW7.AnimationProbe.NativeJob' -as [type]) -or ('IW7StockLinksV1.Ntfs' -as [type])){throw 'Fresh original host identity required.'}
$guards=[Collections.Generic.List[object]]::new()
$context=[pscustomobject]@{Owner=$null;Closed=$true;Lease=$null;Guards=$guards;Work=$plan.WorkRoot}
$state=[ordered]@{Schema='iw7.player-template-export/1';Status='Pending';PlanSHA256=$PlanSHA256;CanExit=$false;Ready=$false;
 Host=[ordered]@{PID=$PID;Image=$physical.ExecutablePath;CreatedUtc=$physicalCreated;CimCreatedUtc=$physical.CreationDate.ToUniversalTime().ToString('o')};
 Inputs=[Collections.Generic.List[object]]::new();ContentPins=[Collections.Generic.List[object]]::new();
 CreatedCopies=[Collections.Generic.List[object]]::new();UnknownCopyCreation=$false;LeaseReleased=$false;GuardsDisposed=$false;
 MeasuredReadback=$false;FinalReadback=$false;PublicationGuardsDisposed=$false;
 CandidateStarted=$false;NativeExportComplete=$false;NeutralCaptureComplete=$false;FullDefinitionsObserved=$false;NeutralManifest=$null;CandidateExecuted=$false}
$root=@{Context=$context;State=$state;Plan=$plan;Key='IW7.PlayerTemplateExport.Original';StockContexts=[Collections.Generic.List[object]]::new();CopyStreams=[Collections.Generic.List[object]]::new();ContentGuards=@{};PublicationGuards=[Collections.Generic.List[object]]::new();ModalOptions=$null;ModalEvidence=$null}
$global:IW7PlayerTemplateExport=$root;[AppDomain]::CurrentDomain.SetData($root.Key,$root)
$script:PlayerTemplateExportOriginalRoot=$root
$failure=$null;$created=$false
function Assert-PlayerExportClock{Assert-H1Deadline $script:T7GroupStarted $script:PlayerTemplateExportOriginalRoot.Plan.GroupSeconds}
function Assert-PlayerExportCaller($Token,$Target){
    $playerRoot=$script:PlayerTemplateExportOriginalRoot
    if(![object]::ReferenceEquals([AppDomain]::CurrentDomain.GetData($playerRoot.Key),$playerRoot) -or
       $null -eq $playerRoot.Context.Lease -or $playerRoot.Context.Lease.Token -cne $Token -or
       $PID -ne $playerRoot.State.Host.PID){throw 'Original admitted export root required.'}
    Assert-PlayerExportClock
}
function New-PlayerStockTransaction($Manifest,$LinkPlan){
    $playerRoot=$script:PlayerTemplateExportOriginalRoot;$slot='Stock_'+$Manifest.Name
    try{
        New-IW7StockLinkTransaction -Plan $LinkPlan -OwnerRoot $playerRoot -RetentionKey $playerRoot.Key -TransactionSlot $slot -LeaseToken $playerRoot.Context.Lease.Token -ValidateCaller {param($Token,$Target) Assert-PlayerExportCaller $Token $Target} -JournalPath (Join-Path $playerRoot.Plan.RunRoot ('stock-'+$Manifest.Name+'.jsonl'))
    }finally{
        # Stock35 publishes the actual transaction before its callback can throw.
        # Retain that same object even when the factory never returns to us.
        if($playerRoot.Contains($slot)){
            $published=$playerRoot[$slot]
            if(![object]::ReferenceEquals($published.OwnerRoot,$playerRoot) -or $published.TransactionSlot -cne $slot){throw 'Original published stock slot differs.'}
            if(!@($playerRoot.StockContexts|Where-Object {[object]::ReferenceEquals($_,$published)}).Count){$playerRoot.StockContexts.Add($published)}
        }
    }
}
function Pin-PlayerOpaque($Pin){Open-T7Pin $Pin $script:PlayerTemplateExportOriginalRoot.Context}
function Get-PlayerRetailStreamSHA($Stream,[long]$Bytes,[long]$Limit){
    Assert-PlayerExportClock
    if(!$Stream.CanRead -or !$Stream.CanSeek -or $Bytes -lt 1 -or $Bytes -gt $Limit -or $Stream.Length -ne $Bytes){throw 'Bounded original retail stream required.'}
    $Stream.Position=0;$used=0L
    $hash=[Security.Cryptography.IncrementalHash]::CreateHash([Security.Cryptography.HashAlgorithmName]::SHA256)
    try{
        $buffer=[byte[]]::new(1MB)
        while(($n=$Stream.Read($buffer,0,$buffer.Length)) -gt 0){
            $used+=$n;if($used -gt $Bytes){throw 'Retail stream grew beyond its declared bound.'}
            $hash.AppendData($buffer,0,$n);Assert-PlayerExportClock
        }
        if($used -ne $Bytes -or $Stream.Length -ne $Bytes){throw 'Original retail stream length changed.'}
        [Convert]::ToHexString($hash.GetHashAndReset()).ToLowerInvariant()
    }finally{$hash.Dispose();$Stream.Position=0}
}
function Confirm-PlayerRetailContent($Pin){
    $playerRoot=$script:PlayerTemplateExportOriginalRoot
    $held=$playerRoot.ContentGuards[$Pin.Path]
    if(!$held -or !$held.Stream -or $held.Stream.SafeFileHandle.IsClosed -or $held.Stream.SafeFileHandle.IsInvalid){throw 'Actual retained retail content stream required.'}
    $sha=Get-PlayerRetailStreamSHA $held.Stream $Pin.Bytes (Get-PlayerRetailByteLimit $playerRoot.Plan $Pin.Path)
    if($sha -cne $Pin.SHA256){throw 'Original retail content hash differs.'}
}
function Get-PlayerSourceHandle($Source){
    $held=$script:PlayerTemplateExportOriginalRoot.ContentGuards[$Source.Path]
    if(!$held -or $held.Identity -cne $Source.Before.Identity -or !$held.Stream -or
       $held.Stream.SafeFileHandle.IsClosed -or $held.Stream.SafeFileHandle.IsInvalid){throw 'Original held content guard required after stock apply.'}
    $held.Stream.SafeFileHandle
}
function Record-PlayerCandidateStart($Ctx,$Current){
    $playerRoot=$script:PlayerTemplateExportOriginalRoot
    if(![object]::ReferenceEquals($Ctx,$playerRoot.Context) -or !$Ctx.Owner -or !$Current.Identity -or $Ctx.Owner.PID -le 0 -or $Ctx.Owner.CreationFileTime -le 0 -or
       $Current.Identity.PID -ne $Ctx.Owner.PID -or $Current.Identity.Image -cne $Ctx.Owner.Image -or
       $Current.Identity.CreatedUtc -cne [datetime]::FromFileTimeUtc($Ctx.Owner.CreationFileTime).ToString('o') -or
       $Ctx.Owner.Image -cne (Join-Path $playerRoot.Plan.WorkRoot 'zonetool-iw7-player.exe')){throw 'Original started candidate identity required.'}
    # H1 publishes Identity only after its original Start returned successfully.
    # Record that fact before the output observer can throw; completion is separate.
    $playerRoot.State.CandidateStarted=$true;$playerRoot.State.CandidateIdentity=$Current.Identity
}
function Invoke-PlayerOriginalPoll($Ctx,$Current,$Logs){
    Record-PlayerCandidateStart $Ctx $Current
    Test-PlayerGenerated $Current
    $playerRoot=$script:PlayerTemplateExportOriginalRoot
    if($playerRoot.ModalOptions){
        Invoke-ArenaLoadDiagnostic $Ctx $Current $Logs $playerRoot.ModalOptions $playerRoot.ModalEvidence
        Test-PlayerGenerated $Current
    }
}
function Read-PlayerModalRecord([string]$Path){
    $playerRoot=$script:PlayerTemplateExportOriginalRoot
    if(!$playerRoot.ModalOptions -or $Path -cne (Join-Path $playerRoot.ModalOptions.RunRoot 'load-diagnostic/modal-window.json')){throw 'Exact original modal output required.'}
    $read=Read-PlayerOutput $Path 65536
    $playerRoot.State.ModalRecord=[ordered]@{Path=$read.Path;Bytes=$read.Bytes;SHA256=$read.SHA256}
    $read.Text # Its actual read-only stream stays in the main context's guards.
}
function Close-PlayerOriginalJobs{
    $playerRoot=$script:PlayerTemplateExportOriginalRoot;$main=$playerRoot.Context
    $jobs=@($main)
    if($main.PSObject.Properties['DiagnosticContext']){$jobs+=@($main.DiagnosticContext)}
    $allClosed=$true
    foreach($jobContext in $jobs){
        if($jobContext.Owner -and !$jobContext.Owner.Closed){$jobContext.Closed=$false}
        if(!$jobContext.Closed){
            if(!$jobContext.Owner){$allClosed=$false;continue}
            try{$jobContext.Owner.StopAndConfirm(5000);$jobContext.Closed=$jobContext.Owner.Closed}catch{$playerRoot.State.ClosureError=$_.Exception.Message}
        }
        if(!$jobContext.Closed){$allClosed=$false}
    }
    # Closing the main owner cannot attest an unknown diagnostic child.
    $main.Closed=$allClosed;$playerRoot.State.OriginalJobsClosed=$allClosed
}
function Copy-PlayerOwned($Pin,[string]$Target,[switch]$Mutable){
    $root=$script:PlayerTemplateExportOriginalRoot;$state=$root.State
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
    $root=$script:PlayerTemplateExportOriginalRoot;$plan=$root.Plan;$state=$root.State
    $totals=@{}
    foreach($tx in $root.StockContexts){
        Assert-IW7StockLinkContext $tx
        if($tx.UnknownCreation -or ![object]::ReferenceEquals($tx.OwnerRoot,$root)){throw 'Original known stock context required.'}
        if(!$tx.Prepared){
            if($tx.Phase -cne 'PublishedBeforePreflight' -or $tx.Guards.Count -or $tx.Sources.Count -or
               $tx.CreatedLinks.Count -or $tx.CreatedDirectories.Count -or $null -ne $tx.JournalStream){throw 'Unprepared stock effects are retained.'}
            continue
        }
        foreach($source in $tx.Sources){if(!$totals.ContainsKey($source.Before.Identity)){$totals[$source.Before.Identity]=0};$totals[$source.Before.Identity]++}
    }
    foreach($tx in $root.StockContexts){foreach($source in $tx.Sources){
        $base=@($plan.SourceBaselines|Where-Object Identity -CEQ $source.Before.Identity)[0]
        # Stock35 closes its own source guards after a successful Apply.
        # Our original content stream was held before Apply and stays owned.
        Assert-IW7StockStableMetadata ([IW7StockLinksV1.Ntfs]::Inspect((Get-PlayerSourceHandle $source))) $source.Before ($base.Links+$totals[$source.Before.Identity])
        Assert-IW7StockStableMetadata (Get-IW7StockLinkMetadata $source.Path) $source.Before ($base.Links+$totals[$source.Before.Identity])
        Assert-IW7StockStableMetadata (Get-IW7StockLinkMetadata $source.Target) $source.Before ($base.Links+$totals[$source.Before.Identity])
    }}
    foreach($pin in $state.ContentPins){
        if($plan.PSObject.Properties['RetailProfile']){Confirm-PlayerRetailContent $pin}else{Pin-PlayerOpaque $pin}
    }
    foreach($pin in @($plan.Candidate,$plan.TLS,$plan.Sentinel)){Pin-PlayerOpaque $pin}
    foreach($copy in $state.CreatedCopies){
        if((Get-IW7StockLinkMetadata $copy.Path).Identity -cne $copy.Identity){throw 'Original owned-copy identity differs.'}
        if($copy.Path -cne (Join-Path $plan.WorkRoot 'main/fileSysCheck.cfg')){Pin-PlayerOpaque $copy}
    }
    Assert-PlayerExportClock
}
function Test-PlayerGenerated($Current,[long]$Limit=$script:PlayerTemplateExportOriginalRoot.Plan.GeneratedLimitBytes){
    $root=$script:PlayerTemplateExportOriginalRoot;$plan=$root.Plan;$state=$root.State
    Assert-PlayerExportClock
    $items=[Collections.Generic.List[object]]::new();$queue=[Collections.Generic.Queue[string]]::new();$queue.Enqueue($plan.RunRoot)
    if($plan.PSObject.Properties['ModalDiagnostic']){
        Assert-H1Path $plan.ModalDiagnostic.RunRoot
        if(Test-Path -LiteralPath $plan.ModalDiagnostic.RunRoot){$queue.Enqueue($plan.ModalDiagnostic.RunRoot)}
    }
    while($queue.Count){
        $directory=$queue.Dequeue();Assert-H1Path $directory
        foreach($path in [IO.Directory]::EnumerateFileSystemEntries($directory)){
            Assert-H1Path $path;$item=Get-Item -LiteralPath $path -Force;$items.Add($item)
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
    $logRoots=@((Join-Path $plan.RunRoot 'owned-player-template'))
    if($plan.PSObject.Properties['ModalDiagnostic']){$logRoots+=@(Join-Path $plan.ModalDiagnostic.RunRoot 'owned-load-modal')}
    foreach($logRoot in $logRoots){foreach($name in 'stdout.log','stderr.log'){
        $path=Join-Path $logRoot $name
        if((Test-Path $path) -and (Get-Item -LiteralPath $path -Force).Length -gt 2MB){throw 'Sampled stream threshold exceeded.'}
    }
    }
    Assert-PlayerExportClock
}
function Read-PlayerOutput([string]$Path,[int]$Cap){
    $guards=$script:PlayerTemplateExportOriginalRoot.Context.Guards
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
function Convert-PlayerPairProfileJson([string]$Text){
    if([Text.Encoding]::UTF8.GetByteCount($Text) -gt 16384){throw 'Pair profile byte cap exceeded.'}
    $document=[Text.Json.JsonDocument]::Parse($Text)
    try{
        $v=$document.RootElement
        foreach($entry in @(@($v,@('schema','donor','native_source_pin','weapon','pap_attachment','source_offsets','observed','association','source_layout_only','templates_exported','projectile_author_eligible','runtime_abi_verified','weapon_granted','projectile_damage_verified','physics_qualified','retail_pap_transaction_verified','gameplay_accepted')),
            @($v.GetProperty('source_offsets'),@('base_type','pap_type','pap_flag')),
            @($v.GetProperty('observed'),@('base_type','pap_type','pap_flag_raw','pap_flag')),
            @($v.GetProperty('association'),@('status','counts','readable','occurrences')))){
            $obj=$entry[0];$keys=$entry[1]
            if($obj.ValueKind -ne [Text.Json.JsonValueKind]::Object){throw 'Pair profile object required.'}
            $names=@($obj.EnumerateObject()|ForEach-Object Name)
            if($names.Count -ne $keys.Count -or @($names|Sort-Object -Unique).Count -ne $names.Count -or
               @($names|Where-Object {$_ -cnotin $keys}).Count){throw 'Closed unique pair profile keys required.'}
        }
        $strings=@{schema='iw7.player-pair-profile/1';donor='cp_zmb';native_source_pin='fab935826c898806855376662a8a03317b3ad8f1';weapon='iw7_shredder_zm';pap_attachment='shredderpap1'}
        foreach($key in $strings.Keys){$p=$v.GetProperty($key);if($p.ValueKind -ne [Text.Json.JsonValueKind]::String -or $p.GetString() -cne $strings[$key]){throw 'Pair profile identity differs.'}}
        if($v.GetProperty('source_layout_only').ValueKind -ne [Text.Json.JsonValueKind]::True){throw 'Source layout-only literal true required.'}
        foreach($key in @('templates_exported','projectile_author_eligible','runtime_abi_verified','weapon_granted','projectile_damage_verified','physics_qualified','retail_pap_transaction_verified','gameplay_accepted')){
            if($v.GetProperty($key).ValueKind -ne [Text.Json.JsonValueKind]::False){throw 'Pair profile qualification must remain literal false.'}
        }
        $offsets=$v.GetProperty('source_offsets');$wanted=@{base_type=556;pap_type=28;pap_flag=20}
        foreach($key in $wanted.Keys){$p=$offsets.GetProperty($key);[int]$n=0;if($p.ValueKind -ne [Text.Json.JsonValueKind]::Number -or $p.GetRawText() -cnotmatch '^(0|[1-9][0-9]*)$' -or !$p.TryGetInt32([ref]$n) -or $n -ne $wanted[$key]){throw 'Exact Source offsets required.'}}
        $observed=$v.GetProperty('observed')
        foreach($key in @('base_type','pap_type','pap_flag_raw')){$p=$observed.GetProperty($key);[int]$n=0;if($p.ValueKind -ne [Text.Json.JsonValueKind]::Number -or $p.GetRawText() -cnotmatch '^-?(0|[1-9][0-9]*)$' -or !$p.TryGetInt32([ref]$n) -or ($key -ceq 'pap_flag_raw' -and ($n -lt 0 -or $n -gt 255))){throw 'Observed scalar int32/raw byte required.'}}
        $raw=$observed.GetProperty('pap_flag_raw').GetInt32();$flag=$observed.GetProperty('pap_flag')
        if(($raw -eq 0 -and $flag.ValueKind -ne [Text.Json.JsonValueKind]::False) -or
           ($raw -eq 1 -and $flag.ValueKind -ne [Text.Json.JsonValueKind]::True) -or
           ($raw -gt 1 -and $flag.ValueKind -ne [Text.Json.JsonValueKind]::Null)){throw 'Raw PAP byte must not be coerced.'}
        $association=$v.GetProperty('association');$counts=$association.GetProperty('counts');$readable=$association.GetProperty('readable');$bounded=$true;[long]$total=0
        if($counts.ValueKind -ne [Text.Json.JsonValueKind]::Array -or $counts.GetArrayLength() -ne 6 -or
           $readable.ValueKind -ne [Text.Json.JsonValueKind]::Array -or $readable.GetArrayLength() -ne 6){throw 'Six exact association slots required.'}
        for($i=0;$i -lt 6;$i++){$p=$counts[$i];[uint32]$n=0
            if($p.ValueKind -ne [Text.Json.JsonValueKind]::Number -or $p.GetRawText() -cnotmatch '^(0|[1-9][0-9]*)$' -or !$p.TryGetUInt32([ref]$n) -or
               $readable[$i].ValueKind -notin @([Text.Json.JsonValueKind]::True,[Text.Json.JsonValueKind]::False) -or
               ($n -eq 0 -and $readable[$i].ValueKind -ne [Text.Json.JsonValueKind]::True) -or
               ($n -gt 64 -and $readable[$i].ValueKind -ne [Text.Json.JsonValueKind]::False)){throw 'Exact count/readability scalar required.'}
            if($n -gt 64 -or $readable[$i].ValueKind -eq [Text.Json.JsonValueKind]::False){$bounded=$false};$total+=$n
        }
        $status=$association.GetProperty('status');$occurrences=$association.GetProperty('occurrences');[int]$found=0
        if($status.ValueKind -ne [Text.Json.JsonValueKind]::String -or $status.GetString() -cne $(if($bounded){'bounded'}else{'refused_bounds_or_readability'})){throw 'Association status contradicts bounds.'}
        if($bounded){if($occurrences.ValueKind -ne [Text.Json.JsonValueKind]::Number -or $occurrences.GetRawText() -cnotmatch '^(0|[1-9][0-9]*)$' -or !$occurrences.TryGetInt32([ref]$found) -or $found -gt $total){throw 'Bounded observed occurrence count required.'}}
        elseif($occurrences.ValueKind -ne [Text.Json.JsonValueKind]::Null){throw 'Unread association must stay null.'}
        $Text|ConvertFrom-Json -Depth 20
    }finally{$document.Dispose()}
}
function Convert-PlayerDefinitionJson([string]$Text,[string]$Kind,$Manifest=$null){
    $cap=if($Kind -ceq 'manifest'){16384}else{2MB}
    if([Text.Encoding]::UTF8.GetByteCount($Text) -gt $cap){throw 'Neutral definition JSON byte cap exceeded.'}
    $document=[Text.Json.JsonDocument]::Parse($Text)
    try{
        $v=$document.RootElement
        if($v.ValueKind -ne [Text.Json.JsonValueKind]::Object){throw 'Neutral definition object required.'}
        $queue=[Collections.Generic.Queue[Text.Json.JsonElement]]::new();$queue.Enqueue($v);$nodes=0
        while($queue.Count){
            $node=$queue.Dequeue();$nodes++;if($nodes -gt 32768){throw 'Neutral JSON node cap exceeded.'}
            if($node.ValueKind -eq [Text.Json.JsonValueKind]::Object){
                $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
                foreach($p in $node.EnumerateObject()){if(!$seen.Add($p.Name)){throw 'Duplicate neutral JSON field.'};$queue.Enqueue($p.Value)}
            }elseif($node.ValueKind -eq [Text.Json.JsonValueKind]::Array){
                if($node.GetArrayLength() -gt 8192){throw 'Neutral JSON array cap exceeded.'}
                foreach($child in $node.EnumerateArray()){$queue.Enqueue($child)}
            }
        }
        $closed={param($Object,$Keys)
            if($Object.ValueKind -ne [Text.Json.JsonValueKind]::Object){throw 'Closed neutral object required.'}
            $names=@($Object.EnumerateObject()|ForEach-Object Name)
            if($names.Count -ne $Keys.Count -or @($names|Where-Object {$_ -cnotin $Keys}).Count){throw 'Closed neutral keys required.'}
        }
        $integer={param($Value,[long]$Minimum,[long]$Maximum)
            [long]$number=0
            if($Value.ValueKind -ne [Text.Json.JsonValueKind]::Number -or $Value.GetRawText() -cnotmatch '^(0|[1-9][0-9]*)$' -or
                !$Value.TryGetInt64([ref]$number) -or $number -lt $Minimum -or $number -gt $Maximum){throw 'Bounded neutral scalar integer required.'}
        }
        if($Kind -ceq 'manifest'){
            $strings=@{schema='iw7.registered-player-definition-pair/1';donor='cp_zmb';native_source_pin='fab935826c898806855376662a8a03317b3ad8f1';weapon='iw7_shredder_zm';pap_attachment='shredderpap1'}
            $trueFlags=@('source_layout_only','templates_exported','full_definitions_observed')
            $falseFlags=@('projectile_author_eligible','dependency_bodies_captured','runtime_abi_verified','lifetime_verified','roundtrip_verified','weapon_granted','projectile_damage_verified','physics_qualified','retail_pap_transaction_verified','gameplay_accepted')
            & $closed $v (@($strings.Keys)+$trueFlags+$falseFlags+@('observed','readset','files'))
            foreach($key in $strings.Keys){$p=$v.GetProperty($key);if($p.ValueKind -ne [Text.Json.JsonValueKind]::String -or $p.GetString() -cne $strings[$key]){throw 'Neutral definition identity differs.'}}
            foreach($key in $trueFlags){if($v.GetProperty($key).ValueKind -ne [Text.Json.JsonValueKind]::True){throw 'Neutral observation flag must be literal true.'}}
            foreach($key in $falseFlags){if($v.GetProperty($key).ValueKind -ne [Text.Json.JsonValueKind]::False){throw 'Neutral qualification flag must be literal false.'}}
            $observed=$v.GetProperty('observed');$wanted=@{base_type=1;pap_type=0;pap_flag_raw=1;occurrences=1}
            & $closed $observed (@($wanted.Keys)+@('pap_flag'))
            foreach($key in $wanted.Keys){& $integer ($observed.GetProperty($key)) $wanted[$key] $wanted[$key]}
            if($observed.GetProperty('pap_flag').ValueKind -ne [Text.Json.JsonValueKind]::True){throw 'Observed PAP flag must be literal true.'}
            $readset=$v.GetProperty('readset')
            & $closed $readset @('bytes','elements','script_calls','copied_text_bytes','json_estimate','allocation_estimate','native_string_matrices','flat_empty_string_arrays')
            foreach($entry in @(@('bytes',1,1048576),@('elements',1,8192),@('script_calls',0,2048),@('copied_text_bytes',0,1048576),@('json_estimate',1,2097152),@('allocation_estimate',1,16777216),@('flat_empty_string_arrays',0,2))){
                & $integer ($readset.GetProperty($entry[0])) $entry[1] $entry[2]
            }
            if($readset.GetProperty('copied_text_bytes').GetInt64() -gt $readset.GetProperty('bytes').GetInt64()){throw 'Neutral copied text budget contradicts reads.'}
            $matrices=$readset.GetProperty('native_string_matrices');$matrixNames=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
            if($matrices.ValueKind -ne [Text.Json.JsonValueKind]::Array -or $matrices.GetArrayLength() -gt 2){throw 'Bounded native matrix observations required.'}
            foreach($p in $matrices.EnumerateArray()){
                if($p.ValueKind -ne [Text.Json.JsonValueKind]::String -or $p.GetString() -cnotin @('WeaponDef.turretBarrelSpinUpSnd','WeaponDef.turretBarrelSpinDownSnd') -or !$matrixNames.Add($p.GetString())){throw 'Unique native matrix field required.'}
            }
            if($matrices.GetArrayLength()+$readset.GetProperty('flat_empty_string_arrays').GetInt32() -ne 2){throw 'Both native string-array shapes must be observed.'}
            $files=$v.GetProperty('files');$paths=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
            if($files.ValueKind -ne [Text.Json.JsonValueKind]::Array -or $files.GetArrayLength() -ne 2){throw 'Exactly two neutral native JSON files required.'}
            foreach($file in $files.EnumerateArray()){
                & $closed $file @('path','bytes','sha256')
                $path=$file.GetProperty('path');$hash=$file.GetProperty('sha256')
                if($path.ValueKind -ne [Text.Json.JsonValueKind]::String -or $path.GetString() -cnotin @('weapons/iw7_shredder_zm.json','attachments/shredderpap1.json') -or !$paths.Add($path.GetString()) -or
                    $hash.ValueKind -ne [Text.Json.JsonValueKind]::String -or $hash.GetString() -cnotmatch '^[0-9a-f]{64}$'){throw 'Exact unique neutral file path/hash required.'}
                & $integer ($file.GetProperty('bytes')) 1 2097152
            }
        }elseif($Kind -cin @('iw7_shredder_zm','shredderpap1')){
            $name=$v.GetProperty('szInternalName')
            if($name.ValueKind -ne [Text.Json.JsonValueKind]::String -or $name.GetString() -cne $Kind){throw 'Exact neutral native internal name required.'}
            if($Kind -ceq 'iw7_shredder_zm'){
                $definition=$v.GetProperty('weapDef')
                if($definition.ValueKind -ne [Text.Json.JsonValueKind]::Object -or $definition.GetProperty('unk0').ValueKind -ne [Text.Json.JsonValueKind]::Object){throw 'Full native WeaponDef container required.'}
                & $integer ($definition.GetProperty('weapType')) 1 1
                if($null -eq $Manifest){throw 'Previously checked neutral manifest required for native shape readback.'}
                foreach($key in @('turretBarrelSpinUpSnd','turretBarrelSpinDownSnd')){
                    $array=$definition.GetProperty($key);$matrix=('WeaponDef.'+$key) -cin @($Manifest.readset.native_string_matrices)
                    if($array.ValueKind -ne [Text.Json.JsonValueKind]::Array -or $array.GetArrayLength() -ne 4){throw 'Exact native string-array extent required.'}
                    for($row=0;$row -lt 4;$row++){
                        if($matrix){
                            if($array[$row].ValueKind -ne [Text.Json.JsonValueKind]::Array -or $array[$row].GetArrayLength() -ne 4){throw 'Native matrix must preserve all sixteen strings.'}
                            for($column=0;$column -lt 4;$column++){
                                $p=$array[$row][$column]
                                if($p.ValueKind -ne [Text.Json.JsonValueKind]::String -or [Text.Encoding]::UTF8.GetByteCount($p.GetString()) -gt 511 -or
                                    $p.GetString() -cne $array[0][$column].GetString()){throw 'Native matrix rows must preserve the repeated native array.'}
                            }
                        }elseif($array[$row].ValueKind -ne [Text.Json.JsonValueKind]::String -or $array[$row].GetString() -cne ''){throw 'Native null array must remain four empty strings.'}
                    }
                }
            }else{
                & $integer ($v.GetProperty('weaponType')) 0 0
                if($v.GetProperty('papAttachment').ValueKind -ne [Text.Json.JsonValueKind]::True){throw 'Neutral PAP bool must remain literal true.'}
            }
        }else{throw 'Unknown neutral JSON kind.'}
        $Text|ConvertFrom-Json -Depth 100
    }finally{$document.Dispose()}
}
function Confirm-PlayerDefinitionBindings($Manifest,$Artifacts,[string]$Output){
    if(@($Artifacts).Count -ne 3){throw 'Two definition files and manifest readbacks required.'}
    foreach($entry in $Manifest.files){
        $matches=@($Artifacts|Where-Object Path -CEQ (Join-Path $Output $entry.path))
        if($matches.Count -ne 1 -or $matches[0].Bytes -ne $entry.bytes -or $matches[0].SHA256 -cne $entry.sha256){throw 'Neutral definition readback/hash binding differs.'}
    }
}
function Convert-PlayerNativeJson([string]$Text,[string]$Kind){
    $document=[Text.Json.JsonDocument]::Parse($Text)
    try{
        $value=$document.RootElement
        if($value.ValueKind -ne [Text.Json.JsonValueKind]::Object){throw 'Native JSON root must be an object.'}
        $queue=[Collections.Generic.Queue[Text.Json.JsonElement]]::new();$queue.Enqueue($value)
        while($queue.Count){
            $node=$queue.Dequeue()
            if($node.ValueKind -eq [Text.Json.JsonValueKind]::Object){
                $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
                foreach($property in $node.EnumerateObject()){if(!$seen.Add($property.Name)){throw 'Duplicate native JSON field.'};$queue.Enqueue($property.Value)}
            }elseif($node.ValueKind -eq [Text.Json.JsonValueKind]::Array){foreach($child in $node.EnumerateArray()){$queue.Enqueue($child)}}
        }
        if($Kind -cne 'manifest'){
            if($value.GetProperty('szInternalName').ValueKind -ne [Text.Json.JsonValueKind]::String -or
               $value.GetProperty('szInternalName').GetString() -cne $Kind){throw 'Native internal name must be the exact scalar string.'}
        }else{
            $strings=@{schema='iw7.player-weapon-templates/1';donor='cp_zmb';native_source_pin='fab935826c898806855376662a8a03317b3ad8f1';
                weapon='iw7_shredder_zm';pap_attachment='shredderpap1';engine_weapon_type='projectile'}
            $flags=@('bo3_assets_authenticated','weapon_granted','projectile_damage_verified','retail_pap_transaction_verified','gameplay_accepted')
            $keys=@($value.EnumerateObject()|ForEach-Object Name);$required=@($strings.Keys)+$flags+@('files')
            if($keys.Count -ne $required.Count -or @($keys|Where-Object {$_ -cnotin $required}).Count){throw 'Closed native manifest shape required.'}
            foreach($name in $strings.Keys){$property=$value.GetProperty($name);if($property.ValueKind -ne [Text.Json.JsonValueKind]::String -or $property.GetString() -cne $strings[$name]){throw 'Native manifest scalar string differs.'}}
            foreach($name in $flags){if($value.GetProperty($name).ValueKind -ne [Text.Json.JsonValueKind]::False){throw 'Native manifest literal false required.'}}
            $files=$value.GetProperty('files');if($files.ValueKind -ne [Text.Json.JsonValueKind]::Array -or $files.GetArrayLength() -ne 2){throw 'Exact native manifest file array required.'}
            $paths=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
            foreach($file in $files.EnumerateArray()){
                if($file.ValueKind -ne [Text.Json.JsonValueKind]::Object){throw 'Manifest file object required.'}
                $names=@($file.EnumerateObject()|ForEach-Object Name)
                if($names.Count -ne 3 -or @($names|Where-Object {$_ -cnotin @('path','bytes','sha256')}).Count){throw 'Closed manifest file shape required.'}
                $path=$file.GetProperty('path');$hash=$file.GetProperty('sha256');$size=$file.GetProperty('bytes');[long]$bytes=0
                if($path.ValueKind -ne [Text.Json.JsonValueKind]::String -or $path.GetString() -cnotin @('weapons/iw7_shredder_zm.json','attachments/shredderpap1.json') -or !$paths.Add($path.GetString()) -or
                   $hash.ValueKind -ne [Text.Json.JsonValueKind]::String -or $hash.GetString() -cnotmatch '^[0-9a-fA-F]{64}$' -or
                   $size.ValueKind -ne [Text.Json.JsonValueKind]::Number -or !$size.TryGetInt64([ref]$bytes) -or $bytes -lt 1 -or $bytes -gt 2MB){throw 'Manifest path/hash/bounded integer bytes required.'}
            }
        }
        $Text|ConvertFrom-Json -Depth 100
    }finally{$document.Dispose()}
}
try{
    foreach($pin in $plan.SourceBindings){$null=Read-PlayerExportSource $pin.Path $pin.SHA256 $pin.Bytes $guards -Role $pin.Role}
    $null=Read-PlayerExportSource $plan.RunnerBinding.Path $plan.RunnerBinding.SHA256 $plan.RunnerBinding.Bytes $guards -Role Runner
    $null=Read-PlayerExportSource $plan.Request.Path $plan.Request.SHA256 $plan.Request.Bytes $guards -Role Request
    foreach($pin in $plan.StockManifests){$null=Read-PlayerExportSource $pin.Path $pin.SHA256 $pin.Bytes $guards -Role StockManifest}
    . $plan.Providers.Core;. $plan.Providers.Scheduler
    $context.Lease=Enter-IW7ResourceLease -Scope $plan.RunRoot -Kind Extract -PhysicalBytes 8GB -CommitBytes 12GB -Owner 'One Shredder/PAP native template export'
    $state.LeaseToken=$context.Lease.Token;$script:T7GroupStarted=Get-H1Clock
    . $plan.Providers.Profile;. $plan.Providers.StockCore;. $plan.Providers.BeaconCore;. $plan.Providers.ArenaProcess
    if($modalSelected){
        . $plan.Providers.H1Compiler;. $plan.Providers.LoadDiagnostic
        Assert-H1Path $plan.ModalDiagnostic.RunRoot
        if(Test-Path -LiteralPath $plan.ModalDiagnostic.RunRoot){throw 'Fresh package-owned modal runtime required under admission.'}
        $state.ModalRunRoot=$plan.ModalDiagnostic.RunRoot
        Pin-PlayerOpaque $plan.ModalDiagnostic.Python
    }
    Pin-PlayerOpaque $plan.JobAssembly
    [Reflection.Assembly]::LoadFrom($plan.JobAssembly.Path)|Out-Null
    [IO.Directory]::CreateDirectory($plan.RunRoot)|Out-Null;$created=$true
    foreach($manifest in $plan.StockManifests){
        $linkPlan=Read-IW7StockLinkPlan -ManifestPath $manifest.Path -ExpectedManifestSHA256 $manifest.SHA256 -SourceRoot $plan.StockSourceRoot -TargetRoot $manifest.Target
        $tx=New-PlayerStockTransaction $manifest $linkPlan
        Invoke-IW7StockLinkPreflight $tx
        foreach($source in $tx.Sources){
            if(@($state.ContentPins|Where-Object Path -IEQ $source.Path).Count -eq 0){
                # Fresh content evidence now, never a relabelled historical SHA.
                $stream=[IO.FileStream]::new($source.Path,'Open','Read','Read');$guards.Add($stream)
                $root.ContentGuards[$source.Path]=[pscustomobject]@{Stream=$stream;Identity=$source.Before.Identity}
                $limit=Get-PlayerRetailByteLimit $plan $source.Path
                if($stream.Length -ne $source.Before.Bytes -or $stream.Length -gt $limit){throw 'Finite source length differs.'}
                if($retailProfile.Name -ceq 'fixed33-pak'){$sha=Get-PlayerRetailStreamSHA $stream $source.Before.Bytes $limit}else{
                    $hash=[Security.Cryptography.IncrementalHash]::CreateHash([Security.Cryptography.HashAlgorithmName]::SHA256)
                    try{$buffer=[byte[]]::new(1MB);while(($n=$stream.Read($buffer)) -gt 0){$hash.AppendData($buffer,0,$n);Assert-PlayerExportClock};$sha=[Convert]::ToHexString($hash.GetHashAndReset()).ToLowerInvariant()}finally{$hash.Dispose()}
                }
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
    $arguments=@('-headless',$(if($pairDefinitions){'-iw7-player-weapon-pair-definitions'}elseif($pairProfile){'-iw7-player-weapon-pair-profile'}else{'-iw7-player-weapon-templates'}),'cp_zmb',$plan.Request.Path,$plan.Pack)
    if($modalSelected){
        $root.ModalOptions=[pscustomobject]@{StartedMs=(Get-H1Clock);RunRoot=$plan.ModalDiagnostic.RunRoot;DiagnosticZone='global_mp';ModalTextOnly=$true;
            ModalSource=$plan.ModalDiagnostic.ModalSource;Python=$plan.ModalDiagnostic.Python.Path;PythonSHA256=$plan.ModalDiagnostic.Python.SHA256;
            ToolSHA256=$plan.Candidate.SHA256;Inputs=$state.Inputs;ModalRecordReader={param($Path) Read-PlayerModalRecord $Path}}
        $root.ModalEvidence=[ordered]@{Attempted=$false;LastBytes=-1L;LastProgressMs=0L;Outcome='NotTriggered';SymbolsVerified=$false}
        $state.ModalDiagnostic=$root.ModalEvidence
    }
    Test-PlayerGenerated $state # Reject redirects before the existing profile's enumeration.
    # Until H1's successful Start identity reaches our poll, startup is unknown.
    # An Invoke exception must not turn an attempted/partial launch into false.
    $state.CandidateInvocationAttempted=$true;$state.CandidateStarted=$null
    $state.Tool=Invoke-OriginalArenaTool $context $tool $plan.Candidate.SHA256 $arguments $plan.WorkRoot $plan.RunRoot 'player-template' $state.Inputs $plan.ToolSeconds {param($Ctx,$Current,$Logs) Invoke-PlayerOriginalPoll $Ctx $Current $Logs}
    $state.CandidateExecuted=$true
    Test-PlayerGenerated $state.Tool
    $stdout=Read-PlayerOutput $state.Tool.Stdout 2MB
    $marker=$(if($pairDefinitions){'IW7_PLAYER_PAIR_DEFINITIONS donor=cp_zmb weapon=iw7_shredder_zm pap=shredderpap1 count=2 output=dump\'}elseif($pairProfile){'IW7_PLAYER_PAIR_PROFILE donor=cp_zmb weapon=iw7_shredder_zm pap=shredderpap1 count=1 output=dump\'}else{'IW7_PLAYER_WEAPON_TEMPLATES donor=cp_zmb weapon=iw7_shredder_zm pap=shredderpap1 count=2 output=dump\'})+$plan.Pack
    if(@($stdout.Text -split '\r?\n'|Where-Object {$_ -ceq $marker}).Count -ne 1 -or $stdout.Text -match '\[ ERROR \]|\[ FATAL \]|IW7 player/PAP template export failed|IW7 neutral player definitions failed|IW7_PLAYER_DEFINITION_REFUSAL'){throw 'Exact successful native export marker required.'}
    $output=Join-Path $plan.WorkRoot ('dump/'+$plan.Pack)
    if($pairProfile){
        $files=@(Get-ChildItem $output -Recurse -File -Force)
        if($files.Count -ne 1 -or $files[0].FullName -cne (Join-Path $output 'player-pair-profile.json')){throw 'Exact single diagnostic profile output required.'}
        $read=Read-PlayerOutput $files[0].FullName 16384
        $state.PairProfile=Convert-PlayerPairProfileJson $read.Text
        $state.Artifacts=@([pscustomobject]@{Path=$read.Path;Bytes=$read.Bytes;SHA256=$read.SHA256})
    }elseif($pairDefinitions){
        $files=@(Get-ChildItem $output -Recurse -File -Force)
        $expected=@('player-definition-pair-manifest.json','weapons/iw7_shredder_zm.json','attachments/shredderpap1.json')
        if($files.Count -ne 3 -or @($files|Where-Object {([IO.Path]::GetRelativePath($output,$_.FullName).Replace('\','/')) -cnotin $expected}).Count){throw 'Exact neutral two-JSON/manifest output required.'}
        $state.Artifacts=@(foreach($relative in $expected){
            $path=Join-Path $output $relative;$cap=if($relative -ceq 'player-definition-pair-manifest.json'){16384}else{2MB}
            $read=Read-PlayerOutput $path $cap
            $kind=if($relative -ceq 'player-definition-pair-manifest.json'){'manifest'}elseif($relative -like 'weapons/*'){'iw7_shredder_zm'}else{'shredderpap1'}
            $data=Convert-PlayerDefinitionJson $read.Text $kind $state.NeutralManifest
            if($kind -ceq 'manifest'){$state.NeutralManifest=$data}
            [pscustomobject]@{Path=$path;Bytes=$read.Bytes;SHA256=$read.SHA256}
        })
        Confirm-PlayerDefinitionBindings $state.NeutralManifest $state.Artifacts $output
    }else{
    $files=@(Get-ChildItem $output -Recurse -File -Force)
    $expected=@('weapons/iw7_shredder_zm.json','attachments/shredderpap1.json','player-template-manifest.json')
    if($files.Count -ne 3 -or @($files|Where-Object {([IO.Path]::GetRelativePath($output,$_.FullName).Replace('\','/')) -cnotin $expected}).Count){throw 'Exact full two-JSON/manifest output required.'}
    $state.Artifacts=@(foreach($relative in $expected){
        $path=Join-Path $output $relative;$cap=if($relative -ceq 'player-template-manifest.json'){16384}else{2MB}
        $read=Read-PlayerOutput $path $cap
        $pin=[pscustomobject]@{Path=$path;Bytes=$read.Bytes;SHA256=$read.SHA256}
        $kind=if($relative -ceq 'player-template-manifest.json'){'manifest'}elseif($relative -like 'weapons/*'){'iw7_shredder_zm'}else{'shredderpap1'}
        $data=Convert-PlayerNativeJson $read.Text $kind
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
    }
    Confirm-PlayerStock;$state.Status='MeasuredPassed';$state.StockContentQualified=$true
    if($pairDefinitions){$state.NeutralCaptureComplete=$true;$state.FullDefinitionsObserved=$true}elseif($pairProfile){$state.PairProfileComplete=$true}else{$state.NativeExportComplete=$true}
}catch{$failure=$_;$state.Status='Failed';$state.Error=$_.Exception.Message}
finally{
    Close-PlayerOriginalJobs
    if($created -and $context.Closed -and $context.Lease -and !$state.UnknownCopyCreation){
        try{
            Confirm-PlayerStock;Test-PlayerGenerated $state
            $state.OriginalRootAndJobClosed=$context.Closed
            $state.StockTransactions=@($root.StockContexts|ForEach-Object{[ordered]@{Target=$_.Plan.TargetRoot;Phase=$_.Phase;Prepared=$_.Prepared;SourcePreserved=$_.SourcePreserved;UnknownCreation=$_.UnknownCreation;CreatedLinks=$_.CreatedLinks.Count}})
            $path=Join-Path $plan.RunRoot 'measured-before-release.json'
            $raw=[Text.UTF8Encoding]::new($false).GetBytes(($state|ConvertTo-Json -Depth 30)+"`n")
            if($raw.Length -gt $plan.MetadataReserveBytes){throw 'Metadata reserve exceeded.'}
            $sha=Write-PlayerPublication $path $raw;$state.MeasuredReadback=$true;Assert-PlayerExportClock
            Test-PlayerGenerated $state ($plan.GeneratedLimitBytes+$plan.MetadataReserveBytes)
            $before=[ordered]@{Schema='iw7.player-export-before-release/1';PlanSHA256=$PlanSHA256;MeasuredSHA256=$sha;OriginalRootAndJobClosed=$true;
                StockPreparedAndPreserved=($root.StockContexts.Count -eq $plan.StockManifests.Count -and !@($root.StockContexts|Where-Object {!$_.Prepared}).Count);
                StockClosureVerified=$true;OriginalLeaseToken=$context.Lease.Token;SourceGuardsHeld=$guards.Count;CandidateExecuted=$state.CandidateExecuted;Ready=$false}
            $beforeBytes=[Text.UTF8Encoding]::new($false).GetBytes(($before|ConvertTo-Json)+"`n")
            if($raw.Length+$beforeBytes.Length -gt $plan.MetadataReserveBytes){throw 'Reserved metadata exceeded.'}
            $beforePath=Join-Path $plan.RunRoot 'closure-before-release.json'
            $beforeSHA=Write-PlayerPublication $beforePath $beforeBytes;Assert-PlayerExportClock
            foreach($tx in $root.StockContexts){Close-IW7StockLinkGuards $tx}
            # Immutable aliases remain owned/prepared for evidence and later reuse.
            # No base/private-test-server file, metadata or bank is restored/written.
            Exit-IW7ResourceLease -Token $context.Lease.Token;$context.Lease=$null;$state.LeaseReleased=$true
            if($context.PSObject.Properties['DiagnosticContext']){$context.DiagnosticContext.Lease=$null}
            Assert-PlayerExportClock
            $final=[ordered]@{Schema='iw7.player-export-closure/2';Status='ClosedReleasedGuardsHeldPendingReadback';PlanSHA256=$PlanSHA256;MeasuredSHA256=$sha;BeforeReleaseSHA256=$beforeSHA;
                OriginalRootAndJobClosed=$true;LeaseReleased=$true;GuardsDisposed=$false;SourceGuardsHeld=$guards.Count;
                PublicationGuardsHeld=($root.PublicationGuards.Count+1);CandidateExecuted=$state.CandidateExecuted;Ready=$false}
            $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($final|ConvertTo-Json)+"`n")
            if($raw.Length+$beforeBytes.Length+$bytes.Length -gt $plan.MetadataReserveBytes){throw 'Final metadata reserve exceeded.'}
            $path=Join-Path $plan.RunRoot 'final-closure.json'
            $hash=Write-PlayerPublication $path $bytes;$state.FinalReadback=$true;Assert-PlayerExportClock
            Test-PlayerGenerated $state ($plan.GeneratedLimitBytes+$plan.MetadataReserveBytes)
            # Only known final publication/readback/clock/budget success permits
            # disposal. Keep the same lists/references on any earlier failure.
            $publicationHandles=@($root.PublicationGuards|ForEach-Object {Get-PlayerOriginalGuardHandle $_})
            $sourceHandles=@($guards|ForEach-Object {Get-PlayerOriginalGuardHandle $_})
            foreach($guard in $root.PublicationGuards){$guard.Dispose()}
            foreach($guard in $guards){$guard.Dispose()}
            if(@($publicationHandles+$sourceHandles|Where-Object {!$_.IsClosed}).Count){throw 'Original publication/source handles did not close.'}
            $root.PublicationGuards.Clear();$guards.Clear();$state.PublicationGuardsDisposed=$true;$state.GuardsDisposed=$true
            $state.Status=if($failure){'FailedClosed'}else{'Passed'};$state.CanExit=$true
        }catch{$state.FinalizationError=$_.Exception.Message;if(!$failure){$failure=$_}}
    }
    if(!$state.CanExit){$state.Status=if($context.Closed -and $state.LeaseReleased){'ClosedFinalizationIncomplete'}else{'UnknownRetained'}}
    $state|ConvertTo-Json -Depth 10
}
if($failure){throw $failure}
