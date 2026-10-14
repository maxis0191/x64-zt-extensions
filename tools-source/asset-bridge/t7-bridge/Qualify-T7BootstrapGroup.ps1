# Explicit metadata/source plan only by default. -Run needs a separate group GO.
[CmdletBinding()]
param([Parameter(Mandatory)][string]$PlanPath,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$PlanSHA256,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$ScriptSHA256,[switch]$Run)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
if(!$IsWindows -or [IntPtr]::Size -ne 8 -or $PSVersionTable.PSVersion.Major -lt 7){throw 'Windows x64 PowerShell 7 required.'}
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$core=Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1'

function Assert-QualificationPathSyntax([string]$Path){
    if(![IO.Path]::IsPathFullyQualified($Path) -or [IO.Path]::GetFullPath($Path) -cne $Path -or $Path -match '["\r\n*?]'){throw 'Canonical literal qualification path required.'}
}
function Open-T7QualificationText([string]$Path,[string]$SHA256,[int]$Limit,[Nullable[long]]$ExpectedBytes=$null){
    # Bootstrap only small source/plan text before H1 is trusted. Pins are RAW
    # checkout bytes; no LF/CRLF normalization or historical helper allowlist.
    if($Limit -notin @(32KB,128KB) -or $SHA256 -cnotmatch '\A[0-9a-f]{64}\z' -or
       ($null -ne $ExpectedBytes -and ($ExpectedBytes -le 0 -or $ExpectedBytes -gt $Limit))){throw 'Bounded exact bootstrap text pin required.'}
    Assert-QualificationPathSyntax $Path
    for($part=$Path;$part;$part=[IO.Path]::GetDirectoryName($part)){
        if((Test-Path -LiteralPath $part) -and ([IO.File]::GetAttributes($part) -band [IO.FileAttributes]::ReparsePoint)){throw 'Bootstrap reparse ancestry refused.'}
    }
    $metadata=Get-Item -LiteralPath $Path
    if($metadata.PSIsContainer -or $metadata.Length -le 0 -or $metadata.Length -gt $Limit -or
       ($null -ne $ExpectedBytes -and $metadata.Length -ne $ExpectedBytes)){throw 'Bootstrap text size differs before open.'}
    $guard=[IO.FileStream]::new($Path,'Open','Read','Read')
    try{
        if($guard.Length -ne $metadata.Length -or $guard.Length -gt $Limit){throw 'Bootstrap guarded text size differs.'}
        $bytes=[byte[]]::new([int]$guard.Length);$used=0
        while($used -lt $bytes.Length){$read=$guard.Read($bytes,$used,$bytes.Length-$used);if(!$read){throw 'Short bootstrap text read.'};$used+=$read}
        if($guard.ReadByte() -ne -1 -or $guard.Length -ne $bytes.Length){throw 'Bootstrap text length changed.'}
        if([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant() -cne $SHA256){throw 'Bootstrap text hash differs before H1 import.'}
        $guard.Position=0
        [pscustomobject]@{Guard=$guard;Bytes=$bytes}
    }catch{$guard.Dispose();throw}
}
function Assert-T7QualificationHelperBinding($Pin,[string[]]$Required,[string]$CatalogueProfile) {
    if($Pin.Path -isnot [string] -or $Pin.Path -cnotin $Required -or $Pin.IsText -isnot [bool] -or !$Pin.IsText -or
       ($Pin.Bytes -isnot [int] -and $Pin.Bytes -isnot [long]) -or $Pin.Bytes -le 0 -or
       $Pin.SHA256 -isnot [string] -or $Pin.SHA256 -cnotmatch '\A[0-9a-f]{64}\z'){throw 'Small exact helper source binding required.'}
    if($Pin.Bytes -le 128KB){return}
    # Only this reviewed Catalogue source exceeds the historical helper bound.
    # These are separate RAW LF/CRLF tuples; no production normalization occurs.
    if($Pin.Path -ceq $CatalogueProfile -and (
        ($Pin.Bytes -eq 150096 -and $Pin.SHA256 -ceq '57c9ef83b9eb9535d57f0d8d4fa1fffdff3e389849258892993715382922b6d6') -or
        ($Pin.Bytes -eq 151909 -and $Pin.SHA256 -ceq 'a5d67419a16f246b2f96c51950a0ced538ab48e720322887b39ff4909d348d29') -or
        ($Pin.Bytes -eq 151018 -and $Pin.SHA256 -ceq 'ecf2c14c9b4b063c4e90c0465fcc72f58f58049d3e3b401a5d8cc01ab23cd42d') -or
        ($Pin.Bytes -eq 152840 -and $Pin.SHA256 -ceq '5dcf897e3926697055498844b930eeabe69ea2482fd1bcdaacb019bd4a2ced15'))){return}
    throw 'Oversized helper requires the exact reviewed Catalogue source tuple.'
}
function Assert-T7QualificationGroupPlan($Plan,[string]$Repo,[string]$Runner,[string]$Hash){
    Assert-T7CatalogueFields $Plan @('Schema','Runner','Script','SourceDirectory','RunRoot','Inputs','Bindings','HostImage','Main','PreservedPython','PhysicalBytes','CommitBytes','DeadlineSeconds','RetryAuthorized')
    Assert-T7CatalogueFields $Plan.Script @('Path','Bytes','SHA256')
    if($Plan.Schema -cne 'iw7.t7-bootstrap-group-plan/1' -or $Plan.Runner -cne $Runner -or $Plan.Script.Path -cne $Runner -or
       $Plan.Script.SHA256 -cne $Hash -or !(Test-T7CatalogueInteger $Plan.Script.Bytes 32KB) -or $Plan.Script.Bytes -le 0 -or
       $Plan.PhysicalBytes -ne 6GB -or $Plan.CommitBytes -ne 8GB -or $Plan.DeadlineSeconds -ne 200 -or
       $Plan.RetryAuthorized -isnot [bool] -or $Plan.RetryAuthorized){throw 'Exact bounded group source/budget required.'}
    foreach($path in @($Plan.SourceDirectory,$Plan.RunRoot,$Plan.HostImage)){Assert-QualificationPathSyntax $path}
    if([IO.Path]::GetDirectoryName($Plan.RunRoot) -cne (Join-Path $Repo 'runtime') -or
       [IO.Path]::GetFileName($Plan.RunRoot) -cnotmatch '\At7-bootstrap-group-[a-z][a-z0-9-]*\z' -or
       $Plan.SourceDirectory.StartsWith($Plan.RunRoot,[StringComparison]::OrdinalIgnoreCase)){throw 'Exact separate group root required.'}
    if($Plan.Inputs -isnot [array] -or $Plan.Inputs.Count -lt 1 -or $Plan.Inputs.Count -gt 32){throw 'One through 32 explicit group inputs required.'}
    $paths=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $ids=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase);$total=0L
    foreach($entry in $Plan.Inputs){
        Assert-T7CatalogueFields $entry @('Name','Path','Bytes','FileId','Attributes','CreationUtc','LastWriteUtc')
        foreach($name in 'Name','Path','FileId','Attributes'){if($entry.$name -isnot [string]){throw 'Literal group input strings required.'}}
        if($entry.Name -cnotmatch '\A[a-z][a-z0-9_]{0,62}\.ff\z' -or [IO.Path]::GetFileNameWithoutExtension($entry.Name) -match '\A(con|prn|aux|nul|com[1-9]|lpt[1-9])\z' -or
           $entry.Name -ceq 'mp_freerun_04.ff' -or $entry.Path -cne (Join-Path $Plan.SourceDirectory $entry.Name) -or
           $entry.FileId -cnotmatch '\A[0-9A-F]{8}:[0-9A-F]{16}\z' -or !$entry.Attributes -or
           !$paths.Add($entry.Path) -or !$ids.Add($entry.FileId)){throw 'Distinct canonical group names/paths/identities required.'}
        if(!(Test-T7CatalogueInteger $entry.Bytes 512MB) -or $entry.Bytes -le 0 -or $entry.Bytes -gt 768MB-$total){throw 'Group input/aggregate byte bound exceeded.'}
        $total+=[long]$entry.Bytes
        foreach($name in 'CreationUtc','LastWriteUtc'){
            if($entry.$name -isnot [string] -and $entry.$name -isnot [datetime] -and $entry.$name -isnot [datetimeoffset]){throw 'Explicit input timestamp required.'}
            $null=[datetimeoffset]$entry.$name
        }
    }
    Assert-T7CatalogueFields $Plan.Main @('MainBaseline','PreservedMain')
    $null=Get-T7CatalogueMainBaseline $Plan.Main
    foreach($identity in @($Plan.Main.PreservedMain,$Plan.PreservedPython)){
        Assert-T7CatalogueFields $identity @('PID','CreatedUtc','Image')
        if(!(Test-T7CatalogueInteger $identity.PID ([int]::MaxValue)) -or $identity.PID -le 0){throw 'Preserved identity PID required.'}
        Assert-QualificationPathSyntax $identity.Image;$null=[datetimeoffset]::Parse($identity.CreatedUtc)
    }
    # Syntax/values only: no input paths, process providers or scheduler are read.
    $total
}
function Save-QualificationText([string]$Path,$Value){
    $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($Value|ConvertTo-Json -Depth 12)+"`n")
    if($bytes.Length -gt 32KB){throw 'Qualification receipt exceeds 32 KiB.'}
    $stream=[IO.FileStream]::new($Path,'CreateNew','Write','Read')
    try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
}
function Assert-QualificationPersistentHost([string[]]$Arguments,[string]$Image,[int]$Major,[string]$ScriptPath,[string]$Hash,[string]$PlanPath,[string]$PlanHash,[string]$ExpectedImage){
    $expected=@('-NoLogo','-NoProfile','-NoExit','-File',$ScriptPath,'-PlanPath',$PlanPath,'-PlanSHA256',$PlanHash,'-ScriptSHA256',$Hash,'-Run')
    if($Major -lt 7 -or $Image -cne $ExpectedImage -or $Arguments.Count -ne $expected.Count+1){throw 'Exact PS7 -NoProfile -NoExit -File host required.'}
    for($i=0;$i -lt $expected.Count;$i++){if($Arguments[$i+1] -cne $expected[$i]){throw 'Exact PS7 -NoProfile -NoExit -File host required.'}}
    [ordered]@{Image=$Image;Major=$Major;NoProfile=$true;NoExit=$true;DirectFileLaunch=$true;ExactArgumentsVerified=$true}
}
function Complete-QualificationGuards($Context,$State){
    Complete-H1Stage $Context $State
    if(!$State.Quarantined){
        foreach($guard in @($Context.PayloadGuards.ToArray())+@($Context.Guards.ToArray())){$guard.Dispose()}
        $Context.PayloadGuards.Clear();$Context.Guards.Clear();$State.GuardsClosed=$true
    }else{$State.GuardsClosed=$false;$State.PersistentHostRetentionRequired=$true}
}
function Publish-QualificationReceipt([string]$Path,$State,[Nullable[double]]$Started){
    $deadlineFailure=$null
    if($State.Status -ceq 'IdentityAndHashObservedCompatibilityUnknown'){
        try{if($null -eq $Started){throw 'Missing admitted start time.'};Assert-H1Deadline $Started 200}
        catch{$deadlineFailure=$_.Exception.Message;$State.Status='Failed';$State.FinalizationError=$deadlineFailure}
    }
    Save-QualificationText $Path $State
    if($State.Status -ceq 'IdentityAndHashObservedCompatibilityUnknown'){
        try{Assert-H1Deadline $Started 200}
        catch{
            $deadlineFailure=$_.Exception.Message;$State.Status='Failed';$State.FinalizationError=$deadlineFailure
            Move-Item -LiteralPath $Path -Destination ($Path+'.deadline-exceeded') -ErrorAction Stop
            Save-QualificationText $Path $State
        }
    }
    $deadlineFailure
}
function Wait-QualificationRetention($State){
    if(!$State.Quarantined){return}
    Write-Warning 'Lease and guards retained in IW7.H1.Quarantine; keep this verified NoExit host for recovery. No retry.'
    while($true){Start-Sleep -Seconds 1}
}
function Assert-T7QualificationMemory {
    $memory=Get-IW7ResourceSnapshot
    if((Test-IW7ResourceBudget $memory 0 0).HighWater){throw 'Commit high water during qualification.'}
}
function Open-T7QualificationPass($Spec,$Guards,[double]$Started){
    if(!(Test-T7CatalogueInteger $Spec.Bytes 512MB) -or $Spec.Bytes -le 0){throw 'Explicit bounded group input required before open.'}
    Assert-H1Deadline $Started 200
    Assert-T7CatalogueMetadata $Spec
    $metadata=Get-Item -LiteralPath $Spec.Path
    if($metadata.PSIsContainer -or $metadata.Length -ne $Spec.Bytes){throw 'Group metadata differs before open.'}
    $stream=[IO.FileStream]::new($Spec.Path,'Open','Read','Read');$retained=$false
    try{
        if($stream.Length -ne $Spec.Bytes){throw 'Group guarded input length differs.'}
        $hash=[Security.Cryptography.IncrementalHash]::CreateHash([Security.Cryptography.HashAlgorithmName]::SHA256)
        try{
            $buffer=[byte[]]::new(64KB);$used=0L;$nextMemory=16MB
            while($used -lt $Spec.Bytes){
                Assert-H1Deadline $Started 200
                $read=$stream.Read($buffer,0,[int][math]::Min($buffer.Length,$Spec.Bytes-$used))
                Assert-H1Deadline $Started 200
                if(!$read){throw 'Short streaming qualification read.'}
                $hash.AppendData($buffer,0,$read);$used+=$read
                if($used -ge $nextMemory){Assert-T7QualificationMemory;$nextMemory+=16MB}
            }
            if($stream.ReadByte() -ne -1 -or $stream.Length -ne $Spec.Bytes){throw 'Streaming qualification length changed.'}
            $sha=[Convert]::ToHexString($hash.GetHashAndReset()).ToLowerInvariant()
        }finally{$hash.Dispose()}
        Assert-H1Deadline $Started 200;Assert-H1Path $Spec.Path
        $stream.Position=0;$Guards.Add($stream);$retained=$true
        [pscustomobject]@{Length=$used;SHA256=$sha}
    }finally{if(!$retained){$stream.Dispose()}}
}
function Invoke-T7QualificationInputs($Plan,$Context,$State,[double]$Started){
    # Check every actual input identity before the first payload read.
    foreach($entry in $Plan.Inputs){
        Assert-T7CatalogueMetadata $entry
        if((Get-T7CatalogueFileId $entry.Path) -cne $entry.FileId){throw 'Group input identity differs before read.'}
        Assert-H1Deadline $Started 200
    }
    for($i=0;$i -lt $Plan.Inputs.Count;$i++){
        $entry=$Plan.Inputs[$i]
        $first=Open-T7QualificationPass $entry $Context.PayloadGuards $Started
        $State.DataFileOpened=$true;$State.PayloadHashed=$true
        Assert-T7CatalogueMetadata $entry
        if((Get-T7CatalogueFileId $entry.Path) -cne $entry.FileId){throw 'Group identity differs after first pass.'}
        $second=Open-T7QualificationPass $entry $Context.PayloadGuards $Started
        if($first.Length -ne $second.Length -or $first.SHA256 -cne $second.SHA256){throw 'Group two-pass hash differs.'}
        $metadata=[ordered]@{Bytes=$entry.Bytes;Attributes=$entry.Attributes;CreationUtc=$entry.CreationUtc;LastWriteUtc=$entry.LastWriteUtc;FileId=$entry.FileId}
        $Context.Rows.Add([ordered]@{Schema='iw7.t7-bootstrap-qualification/1';Status='PendingGroupClosure';ScriptSHA256=$Plan.Script.SHA256;
            Input=[ordered]@{Path=$entry.Path;Bytes=$entry.Bytes;Attributes=$entry.Attributes;CreationUtc=$entry.CreationUtc;LastWriteUtc=$entry.LastWriteUtc};
            MetadataBefore=$metadata;MetadataAfter=$metadata;SHA256=$first.SHA256;FileId=$entry.FileId;
            HashProvenance='ObservedUnderLeaseNotDepotVerified';GuardedReadBytesPerPass=$entry.Bytes;GuardedReadPasses=2;
            QualificationGroup=[ordered]@{PlanSHA256=$State.PlanSHA256;InputCount=$Plan.Inputs.Count;InputIndex=$i}})
    }
    # All guards remain held, including both independently opened hash passes.
    foreach($entry in $Plan.Inputs){
        Assert-T7CatalogueMetadata $entry
        if((Get-T7CatalogueFileId $entry.Path) -cne $entry.FileId){throw 'Final group identity differs.'}
        Assert-H1Deadline $Started 200
    }
    $State.MetadataAndIdentityReverifiedUnderGuard=$true;$State.HashReverifiedUnderGuard=$true
}
function Publish-T7QualificationItems($Plan,$Context,$State,[double]$Started){
    if($State.Status -cne 'IdentityAndHashObservedCompatibilityUnknown' -or !$State.LeaseReleased -or !$State.GuardsClosed -or
       $State.Quarantined -or !$State.TreeClosureConfirmed -or $Context.Rows.Count -ne $Plan.Inputs.Count){throw 'Whole group must close before item publication.'}
    $common=@('Host','DataFileOpened','PayloadHashed','LeaseAcquired','LeaseReleased','GuardsClosed','TreeClosureConfirmed',
        'MetadataAndIdentityReverifiedUnderGuard','HashReverifiedUnderGuard','PreservedPythonIdentityUnchanged','Quarantined','HeaderSemanticsKnown',
        'HeaderPrefixCaptured','ContentCompatibilityProven','DepotVerified','EngineLookupPathProven','NativeEngineExecuted','NativeJobCreated',
        'PayloadCopiedToDisk','PayloadHashesReadAfterRelease','Ready')
    for($i=0;$i -lt $Context.Rows.Count;$i++){
        Assert-H1Deadline $Started 200
        $row=$Context.Rows[$i];foreach($name in $common){$row[$name]=$State[$name]}
        $row.Status='IdentityAndHashObservedCompatibilityUnknown'
        $path=Join-Path $Plan.RunRoot ($Plan.Inputs[$i].Name+'.receipt.json')
        Save-QualificationText $path $row
        # Only the tiny new receipt is hashed after release; never a payload.
        $pin=[ordered]@{Path=$path;Bytes=(Get-Item -LiteralPath $path).Length;SHA256=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()}
        $State.Items+=@([ordered]@{Path=$row.Input.Path;Bytes=$row.Input.Bytes;SHA256=$row.SHA256;FileId=$row.FileId;QualificationReceipt=$pin})
    }
    Assert-H1Deadline $Started 200;$State.GroupComplete=$true
}

$sourceGuards=[Collections.Generic.List[object]]::new();$payloadGuards=[Collections.Generic.List[IO.FileStream]]::new()
$context=[pscustomobject]@{Owner=$null;Closed=$true;Lease=$null;Guards=$sourceGuards;PayloadGuards=$payloadGuards;Host=$null;Rows=[Collections.Generic.List[object]]::new()}
$state=$null;$plan=$null;$failure=$null;$started=$null;$attempted=$false
try{
    $planText=Open-T7QualificationText $PlanPath $PlanSHA256 32KB;$sourceGuards.Add($planText.Guard)
    $plan=[Text.UTF8Encoding]::new($false,$true).GetString($planText.Bytes)|ConvertFrom-Json -Depth 20
    $scriptText=Open-T7QualificationText $PSCommandPath $ScriptSHA256 32KB;$sourceGuards.Add($scriptText.Guard)
    $corePin=@($plan.Bindings|Where-Object {$_.Path -ceq $core -and $_.IsText -is [bool] -and $_.IsText})
    if($corePin.Count -ne 1 -or ($corePin[0].Bytes -isnot [int] -and $corePin[0].Bytes -isnot [long]) -or
       $corePin[0].SHA256 -isnot [string]){throw 'One exact H1 source pin required before import.'}
    $coreText=Open-T7QualificationText $core $corePin[0].SHA256 128KB $corePin[0].Bytes;$sourceGuards.Add($coreText.Guard)
    . $core # Exact raw plan pin verified and read/share-read guard retained.
    $required=@($core,(Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1'),(Join-Path $PSScriptRoot 'T7Prepatch.Profile.ps1'),
        (Join-Path $repo 'ops/Resource-Scheduler.Core.ps1'),(Join-Path $repo 'ops/Resource-Memory.ps1'),
        (Join-Path $repo 'ops/Resource-RecorderOwnedProcess.Core.ps1'),(Join-Path $repo 'ops/native/ResourceMemory.cs'),(Join-Path $repo 'ops/hud-lab/HudFileIdentity.cs'))
    if($plan.Bindings -isnot [array] -or $plan.Bindings.Count -ne $required.Count -or @($plan.Bindings.Path|Sort-Object -Unique).Count -ne $required.Count){throw 'Eight exact helper source bindings required.'}
    foreach($pin in $plan.Bindings){
        Assert-T7QualificationHelperBinding $pin $required (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
        if($pin.Path -cne $core){$sourceGuards.Add((Open-H1Pin $pin))}
    }
    . (Join-Path $PSScriptRoot 'T7Prepatch.Profile.ps1')
    . (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
    $total=Assert-T7QualificationGroupPlan $plan $repo $PSCommandPath $ScriptSHA256
    if($plan.Script.Bytes -ne (Get-Item -LiteralPath $PSCommandPath).Length){throw 'Exact group script length required.'}
    if(!$Run){
        [ordered]@{Status='QualificationGroupCheckedPendingGO';InputCount=$plan.Inputs.Count;InputBytes=$total;DataFileOpened=$false;
            PayloadHashed=$false;LiveProvidersCalled=$false;NativeTypesLoaded=$false;LeaseAcquired=$false;Ready=$false}|ConvertTo-Json
        return
    }
    if(('IW7ResourceMemoryV1' -as [type]) -or ('IW7HudFileIdentity' -as [type])){throw 'Fresh qualification host required.'}
    Assert-H1Path $plan.RunRoot
    if(Test-Path -LiteralPath $plan.RunRoot){throw 'Group already attempted; preserve it, no retry.'}
    $process=[Diagnostics.Process]::GetCurrentProcess()
    $contract=Assert-QualificationPersistentHost ([Environment]::GetCommandLineArgs()) $process.MainModule.FileName $PSVersionTable.PSVersion.Major $PSCommandPath $ScriptSHA256 $PlanPath $PlanSHA256 $plan.HostImage
    $context.Host=[ordered]@{PID=$PID;CreatedUtc=$process.StartTime.ToUniversalTime().ToString('o');Image=$process.MainModule.FileName;Contract=$contract}
    $state=[ordered]@{Schema='iw7.t7-bootstrap-group-qualification/1';Status='Preflight';PlanSHA256=$PlanSHA256;ScriptSHA256=$ScriptSHA256;Host=$context.Host;
        StartedUtc=[DateTime]::UtcNow.ToString('o');Items=@();GroupComplete=$false;HeaderSemanticsKnown=$false;HeaderPrefixCaptured=$false;
        ContentCompatibilityProven=$false;DepotVerified=$false;EngineLookupPathProven=$false;NativeEngineExecuted=$false;NativeJobCreated=$false;
        PayloadCopiedToDisk=$false;PayloadHashesReadAfterRelease=$false;DataFileOpened=$false;PayloadHashed=$false;LeaseAcquired=$false;
        LeaseReleased=$false;Quarantined=$false;GuardsClosed=$false;MetadataAndIdentityReverifiedUnderGuard=$false;HashReverifiedUnderGuard=$false;
        PreservedPythonIdentityUnchanged=$false;Ready=$false}
    . (Join-Path $repo 'ops/Resource-Scheduler.Core.ps1')
    $main=Assert-T7CatalogueMain $plan.Main
    $status=Get-IW7ResourceStatus;$processes=@(Get-IW7ResourceProcesses)
    $python=@($processes|Where-Object PID -EQ $plan.PreservedPython.PID)
    $heavy=@($processes|Where-Object {$_.Lab -or $_.Name -match '^(zonetool.*|t7-.*|MSBuild|cl|link|java|DepotDownloader|steamcmd)\.exe$'})
    $budget=Test-IW7ResourceBudget $status.Snapshot 6GB 8GB
    $state.Preflight=[ordered]@{Main=$main;LeaseCount=@($status.Leases).Count;HeavyCount=$heavy.Count;Budget=$budget;Snapshot=$status.Snapshot}
    if(@($status.Leases).Count -or $heavy.Count -or $python.Count -ne 1 -or !(Test-IW7ResourceIdentity $plan.PreservedPython $python[0]) -or
       !$budget.Allowed -or $budget.HighWater -or $budget.PhysicalReserve -ne 0){throw 'Fresh group qualification preflight refused.'}
    $context.Lease=Enter-IW7ResourceLease -Scope $plan.RunRoot -Kind Extract -PhysicalBytes 6GB -CommitBytes 8GB -Owner 'T7 explicit bootstrap group qualification'
    $state.LeaseAcquired=$true;$state.LeaseToken=$context.Lease.Token;$started=Get-H1Clock
    [IO.Directory]::CreateDirectory($plan.RunRoot)|Out-Null;$attempted=$true
    Save-QualificationText (Join-Path $plan.RunRoot 'attempt.json') ([ordered]@{PlanSHA256=$PlanSHA256;ScriptSHA256=$ScriptSHA256;InputCount=$plan.Inputs.Count;InputBytes=$total})
    Add-Type -Path (Join-Path $repo 'ops/hud-lab/HudFileIdentity.cs')
    Invoke-T7QualificationInputs $plan $context $state $started
    $state.MainAfter=Assert-T7CatalogueMain $plan.Main
    $python=@(Get-IW7ResourceProcesses|Where-Object PID -EQ $plan.PreservedPython.PID)
    if($python.Count -ne 1 -or !(Test-IW7ResourceIdentity $plan.PreservedPython $python[0])){throw 'Preserved Python identity changed.'}
    $state.PreservedPythonIdentityUnchanged=$true
    Assert-T7QualificationMemory;Assert-H1Deadline $started 200
    $state.Status='IdentityAndHashObservedCompatibilityUnknown'
}catch{$failure=$_;if($null -ne $state){$state.Status='Failed';$state.Error=$_.Exception.Message}}
finally{
    if($null -ne $state){
        Complete-QualificationGuards $context $state
        if($attempted){
            try{
                if($state.Status -ceq 'IdentityAndHashObservedCompatibilityUnknown'){Publish-T7QualificationItems $plan $context $state $started}
            }catch{$failure=$_;$state.Status='Failed';$state.Error=$_.Exception.Message}
            $state.FinishedUtc=[DateTime]::UtcNow.ToString('o')
            try{$late=Publish-QualificationReceipt (Join-Path $plan.RunRoot 'group-receipt.json') $state $started;if($late){$failure=$late}}catch{$failure=$_}
        }
    }else{foreach($guard in $sourceGuards){$guard.Dispose()};$sourceGuards.Clear()}
}
if($null -ne $state){$state|ConvertTo-Json -Depth 12}
if($null -ne $state -and $state.Quarantined){Wait-QualificationRetention $state}
if($failure){throw $failure}
