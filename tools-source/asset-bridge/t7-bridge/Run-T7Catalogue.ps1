# Default: bounded text/metadata validation. -Run needs a separate exact-plan GO.
[CmdletBinding()]
param([Parameter(Mandatory)][string]$PlanPath,[Parameter(Mandatory)][string]$PlanSHA256,[switch]$Run)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
if(!$IsWindows -or [IntPtr]::Size -ne 8 -or $PSVersionTable.PSVersion.Major -lt 7){throw 'Windows x64 PowerShell 7 required.'}
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$core=Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1'
. $core
$guards=[Collections.Generic.List[object]]::new()
$context=[pscustomobject]@{Owner=$null;Closed=$true;Lease=$null;Guards=$guards}
$state=$null;$failure=$null;$attempted=$false;$plan=$null;$zonePin=$null;$export=$false
try {
    $size=(Get-Item -LiteralPath $PlanPath).Length
    if($size -gt 128KB){throw 'Catalogue plan exceeds 128 KiB.'}
    $guards.Add((Open-H1Pin ([pscustomobject]@{Path=$PlanPath;Bytes=$size;SHA256=$PlanSHA256})))
    $plan=Read-H1SmallJson $PlanPath
    $profile=Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1'
    $prepatchProfile=Join-Path $PSScriptRoot 'T7Prepatch.Profile.ps1'
    $scheduler=Join-Path $repo 'ops/Resource-Scheduler.Core.ps1'
    $fileIdentity=Join-Path $repo 'ops/hud-lab/HudFileIdentity.cs'
    $required=@($PSCommandPath,$profile,$prepatchProfile,$core,$scheduler,$fileIdentity,
        (Join-Path $repo 'ops/Resource-Memory.ps1'),(Join-Path $repo 'ops/Resource-RecorderOwnedProcess.Core.ps1'),(Join-Path $repo 'ops/native/ResourceMemory.cs'))
    $export=[bool]($plan.PSObject.Properties['Operation'] -and $plan.Operation -ceq 'ResidentExportV1')
    $exportProfile=Join-Path $PSScriptRoot 'T7ResidentExport.Profile.ps1'
    if($export){$required+=@($exportProfile)}
    foreach($path in $required) {
        $pin=@($plan.Bindings|Where-Object {$_.Path -ceq $path -and $_.IsText -eq $true})
        if($pin.Count -ne 1 -or $pin[0].Bytes -gt 1MB){throw 'Bounded exact source binding missing.'}
        $guards.Add((Open-H1Pin $pin[0]))
    }
    . $prepatchProfile # Functions only; reuse environment/Main checks without changing the diagnostic.
    . $profile
    if($export){. $exportProfile}
    Assert-T7CataloguePlan $plan $repo $PSCommandPath
    foreach($pin in $plan.Bindings|Where-Object IsText){if($pin.Path -cnotin $required){$guards.Add((Open-H1Pin $pin))}}
    if($export){Assert-T7ResidentExportCatalogue $plan}
    $bootstraps=@(Get-T7CatalogueBootstraps $plan)
    foreach($bootstrap in $bootstraps){Assert-T7CatalogueBootstrapReceipt $plan (Read-H1SmallJson $bootstrap.QualificationReceipt.Path 32KB) $bootstrap.Path}
    $job=@($plan.Bindings|Where-Object {$_.Path -ceq $plan.JobAssembly -and !$_.IsText})
    if($job.Count -ne 1 -or $job[0].SHA256 -cne '5f613ebb83019dbf4bfa4f6a93c5329098343729b70acc2cfa70aa8b64f195f8'){throw 'Existing witnessed NativeJob pin required.'}
    $shell=[Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
    if(@($plan.Bindings|Where-Object {$_.Path -ceq $shell -and !$_.IsText}).Count -ne 1){throw 'Exact current PowerShell host pin required.'}
    $build=@($plan.Bindings|Where-Object {$_.Path -ceq $plan.BuildReceipt -and $_.IsText})
    $candidateProfile=Get-T7CatalogueCandidateProfile $plan
    $receiptHash=if($candidateProfile -ceq 'ordinary-d2'){'c609bc56523654d8bca4b855024a463393185aab8e19ed4eae94c1ff8f6a09c2'}else{$plan.ExpectedBuildReceiptSHA256}
    if($receiptHash -cnotmatch '\A[0-9a-f]{64}\z' -or $build.Count -ne 1 -or $build[0].SHA256 -cne $receiptHash){throw 'Exact catalogue build receipt binding required.'}
    Assert-T7CatalogueBuild $plan (Read-H1SmallJson $plan.BuildReceipt 1MB)
    if(!$Run) {
        [ordered]@{Status='PlanCheckedPendingGO';NativeTypesLoaded=$false;BinaryInputsHashed=$false;
            ZoneHashObserved=$false;LeaseAcquired=$false;FilesCreated=$false;Ready=$false}|ConvertTo-Json
        return
    }
    if(('IW7.AnimationProbe.NativeJob' -as [type]) -or ('IW7ResourceMemoryV1' -as [type]) -or ('IW7HudFileIdentity' -as [type])){throw 'Fresh PowerShell host required.'}
    . $scheduler
    $before=Assert-T7CatalogueMain $plan
    $state=[ordered]@{Schema='iw7.t7-catalogue-run/1';Status='Running';PlanSHA256=$PlanSHA256;CandidateProfile=$candidateProfile;MainBaseline=(Get-T7CatalogueMainBaseline $plan);Stage='Catalogue';
        DeadlineSeconds=120;MaxObservedOutputBytes=0L;Identity=$null;ExitCode=$null;TreeClosureConfirmed=$true;
        LeaseReleased=$false;Quarantined=$false;TerminationRequested=$false;CatalogueOutcome='NoCatalogue';
        CompatibilityProven=$false;Ready=$false;MainBefore=$before;InputsReverified=$false;EngineOutputsValidated=$false;Aliases=@();InputFileIds=@()}
    $attemptSchema='iw7.t7-catalogue-attempt/1';$leaseOwner='T7 single-zone catalogue'
    if($export){
        $state.Schema='iw7.t7-resident-export-run/1';$state.Stage='ResidentExport';$state.Remove('CatalogueOutcome')
        $state.ExportOutcome='NoExport';$state.ExportRequest=$plan.ExportRequest
        $state.TraceOutcome='DisabledForResidentExportCLI';$state.MessageOutcome='DisabledForResidentExportCLI'
        $state.SerializedParseVerified=$false;$state.DependencyPayloadsVerified=$false
        $attemptSchema='iw7.t7-resident-export-attempt/1';$leaseOwner='T7 one-model resident export'
    }
    $context.Lease=Enter-IW7ResourceLease -Scope $plan.RunRoot -Kind Extract -PhysicalBytes 6GB -CommitBytes 8GB -Owner $leaseOwner
    $state.LeaseToken=$context.Lease.Token
    Enable-T7CatalogueRuntimeProfile $plan
    Assert-T7CataloguePlan $plan $repo $PSCommandPath
    $marker=[IO.FileStream]::new((Join-Path $plan.RunRoot 'attempt.json'),'CreateNew','Write','Read')
    try{$attempted=$true;$bytes=[Text.Encoding]::UTF8.GetBytes((([ordered]@{Schema=$attemptSchema;PlanSHA256=$PlanSHA256;StartedUtc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json -Compress)+"`n"));$marker.Write($bytes,0,$bytes.Length)}finally{$marker.Dispose()}
    foreach($pin in $plan.Bindings|Where-Object {!$_.IsText}){$guards.Add((Open-H1Pin $pin));Assert-H1Deadline $script:T7CatalogueGroupStarted 200}
    Add-Type -Path $fileIdentity # Existing tiny file-ID helper, only after admission; no external compiler process.
    Assert-T7CatalogueBootstrapIdentity $plan
    $zonePin=Open-T7CatalogueZone $plan.Zone $context
    $state.ObservedZone=$zonePin
    if($export){Assert-T7ResidentExportZone $plan $zonePin}
    Assert-H1Deadline $script:T7CatalogueGroupStarted 200
    foreach($item in $plan.InputMetadata){Assert-T7CatalogueMetadata $item;$state.InputFileIds+=@([pscustomobject]@{Path=$item.Path;FileId=(Get-T7CatalogueFileId $item.Path)})}
    Assert-T7CatalogueDistinctInputIds $plan $state.InputFileIds
    [IO.Directory]::CreateDirectory((Join-Path $plan.WorkingDirectory 'zone'))|Out-Null
    $links=@(@($plan.CandidateSource,'t7-zonetool-candidate.exe'),@($plan.EngineSource,'BlackOps3_UnrankedDedicatedServer.exe'),@($plan.SteamSource,'steam_api64.dll'))
    foreach($link in $links){
        $pin=@($plan.Bindings|Where-Object Path -CEQ $link[0])[0]
        $state.Aliases+=@(New-T7CatalogueAlias $pin (Join-Path $plan.WorkingDirectory $link[1]) $context)
        Assert-H1Deadline $script:T7CatalogueGroupStarted 200
    }
    $state.Aliases+=@(New-T7CatalogueAlias $zonePin (Join-Path $plan.WorkingDirectory $plan.Zone.RelativePath) $context)
    $bootstrapEvidence=@()
    foreach($bootstrap in $bootstraps){
        $bootstrapPin=@($plan.Bindings|Where-Object Path -CEQ $bootstrap.Path)[0]
        $state.Aliases+=@(New-T7CatalogueAlias $bootstrapPin (Join-Path $plan.WorkingDirectory $bootstrap.RelativePath) $context)
        $bootstrapEvidence+=@([ordered]@{Source=$bootstrap.Path;Bytes=$bootstrap.Bytes;SHA256=$bootstrap.SHA256;QualifiedFileId=$bootstrap.FileId;RelativePath=$bootstrap.RelativePath;QualificationReceipt=$bootstrap.QualificationReceipt;EngineLookupPathProven=$false})
        Assert-H1Deadline $script:T7CatalogueGroupStarted 200
    }
    if($plan.PSObject.Properties['Bootstraps']){$state.Bootstraps=$bootstrapEvidence}
    elseif($bootstrapEvidence.Count){$state.Bootstrap=$bootstrapEvidence[0]}
    foreach($name in 'profile','profile/roaming','profile/local'){[IO.Directory]::CreateDirectory((Join-Path (Join-Path $plan.RunRoot 'temp') $name))|Out-Null}
    $null=[Reflection.Assembly]::LoadFrom($plan.JobAssembly)
    Assert-H1Deadline $script:T7CatalogueGroupStarted 200
    Test-H1Budget $plan $state
    if(Test-Path -LiteralPath (Join-Path $plan.RunRoot 'stop.request')){throw 'Coordinator stop requested before launch.'}
    $state.MainBeforeLaunch=Assert-T7CatalogueMain $plan
    Invoke-H1OwnedStage $plan $state $context (New-T7CatalogueStart $plan) $plan.CandidateSHA256 $plan.StageRoot
}catch{
    $failure=$_
    if($state){$state.Error=$_.Exception.Message;$state.Status='Failed'}
}finally{
    # Ordinary nonzero exits are already closed by H1. Qualify useful diagnostics
    # while guards/admission remain; failure never becomes a successful catalogue.
    if($state -and $attempted -and $context.Owner -and $context.Closed -and $context.Lease) {
        try {
            try{if(!$export){Read-T7CatalogueTrace $plan $state $context}}
            catch{if(!$failure){$failure=$_};$state.TraceError=$_.Exception.Message;$state.Status='Failed'}
            Assert-T7CatalogueEngineOutputs $plan -Closed -Context $context
            $state.EngineOutputsValidated=$true
            if($export){$state.ExportOutcome=Read-T7ResidentExportReport $plan $state $context}
            else{$state.CatalogueOutcome=Read-T7CatalogueReport $plan $state $context}
            foreach($pin in @($plan.Bindings)+@($zonePin)+@($state.Aliases)) {
                $guard=Open-H1Pin $pin;try{}finally{$guard.Dispose()};Assert-H1Deadline $script:T7CatalogueGroupStarted 200
            }
            foreach($item in $plan.InputMetadata){Assert-T7CatalogueMetadata $item}
            foreach($item in @($state.InputFileIds)+@($state.Aliases)){if((Get-T7CatalogueFileId $item.Path) -cne $item.FileId){throw 'Original/alias file ID changed.'}}
            $state.InputsReverified=$true;$state.OriginalInputMetadataUnchanged=$true;$state.AliasesRetained=$true
            Test-H1Budget $plan $state
            if(!$failure -and $export -and $state.ExportOutcome -cne 'ExportFilesObserved'){throw 'No qualified selective export was produced.'}
            if(!$failure -and !$export -and $state.CatalogueOutcome -cnotin @('EmptyCatalogue','CatalogueWithNames')){throw 'No qualified catalogue was produced.'}
            if(!$failure -and !$export -and (Get-T7CatalogueCandidateProfile $plan) -cne 'ordinary-d2' -and $state.TraceOutcome -cne 'TraceObserved'){throw 'Trace candidate produced no qualified enabled trace.'}
        }catch{if(!$failure){$failure=$_};$state.ValidationError=$_.Exception.Message;$state.Status='Failed'}
    }
    if($state){Complete-H1Stage $context $state}
    if($state -and $attempted -and $context.Closed) {
        try{$state.MainAfter=Assert-T7CatalogueMain $plan}
        catch{if(!$failure){$failure=$_};$state.MainAfterError=$_.Exception.Message;$state.Status='Failed'}
    }
    if($state -and !$export -and $attempted -and $context.Closed -and !$context.Lease -and !$state.InputsReverified -and $state.TerminationRequested) {
        # After forced closure, inspect only bounded diagnostics, never hash payloads.
        try{Read-T7CatalogueTrace $plan $state $context}catch{$state.TraceError=$_.Exception.Message}
        try{$state.CatalogueOutcome=Read-T7CatalogueReport $plan $state $context}catch{$state.ReportError=$_.Exception.Message}
    }
    if($state -and !$context.Closed){if($export){$state.ExportOutcome='NotInspectedWhileJobUnclosed'}else{$state.CatalogueOutcome='NotInspectedWhileJobUnclosed'}}
    if($state -and $attempted) {
        if($context.Owner -and $context.Closed){$state.ClosureEvidence='Pinned NativeJob CloseConfirmed rechecks original RootExited and ActiveProcesses==0; original ExitCode retained.'}
        $state.FinishedUtc=[DateTime]::UtcNow.ToString('o')
        try {
            if(!$state.Quarantined){Assert-H1Deadline $script:T7CatalogueGroupStarted 200}
            if(!$failure -and $context.Closed -and !$context.Lease -and $state.LeaseReleased -and
               !$state.TerminationRequested -and $state.InputsReverified -and $state.EngineOutputsValidated){
                if($export -and $state.ExportOutcome -ceq 'ExportFilesObserved'){$state.Status='ExportObservedPendingReadback'}
                elseif(!$export -and $state.CatalogueOutcome -cin @('EmptyCatalogue','CatalogueWithNames')){$state.Status='CatalogueObservedPendingDonorReview'}
            }
        }catch{if(!$failure){$failure=$_};$state.Status='Failed';$state.FinalizationError=$_.Exception.Message}
        try {
            Write-H1Receipt $plan $state $plan.StageRoot
            if($state.Status -cin @('CatalogueObservedPendingDonorReview','ExportObservedPendingReadback')) {
                try{Assert-H1Deadline $script:T7CatalogueGroupStarted 200}
                catch {
                    $failure=$_;$state.Status='Failed';$state.FinalizationError=$_.Exception.Message
                    [IO.File]::Move((Join-Path $plan.StageRoot 'receipt.json'),(Join-Path $plan.StageRoot 'receipt.deadline-exceeded.json'))
                    Write-H1Receipt $plan $state $plan.StageRoot
                }
            }
        }catch{if(!$failure){$failure=$_};$state.Status='Failed';Write-Warning ('Receipt publication failed: '+$_.Exception.Message)}
    }
    if($context.Closed -and !$context.Lease){foreach($guard in $guards){$guard.Dispose()};$guards.Clear()}
}
if($state -and $state.Quarantined) {
    Write-Warning 'Original owner/lease/guards retained in IW7.H1.Quarantine; keep this host for recovery. No retry.'
    while($true){Start-Sleep -Seconds 1}
}
if($state){
    $outcomeName=if($export){'ExportOutcome'}else{'CatalogueOutcome'}
    [ordered]@{Status=$state.Status;($outcomeName)=$state[$outcomeName];Receipt=(Join-Path $plan.StageRoot 'receipt.json');Ready=$false}|ConvertTo-Json
}
if($failure){throw $failure}
