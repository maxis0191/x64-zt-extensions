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
$state=$null;$failure=$null;$attempted=$false;$plan=$null;$zonePin=$null;$export=$false;$parts=$false;$provenance=$false;$registration=$false;$incoming=$false;$registrationBindings=$false
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
    $parts=[bool]($plan.PSObject.Properties['SelectedMaterialPartsV1'] -or
        ($plan.PSObject.Properties['Operation'] -and $plan.Operation -ceq 'MaterialPartsV1') -or
        ($plan.PSObject.Properties['CandidateProfile'] -and $plan.CandidateProfile -ceq 't7-material-parts-v1'))
    $provenance=[bool]($plan.PSObject.Properties['SelectedImageProvenanceV1'] -or
        ($plan.PSObject.Properties['Operation'] -and $plan.Operation -ceq 'ImageProvenanceV1') -or
        ($plan.PSObject.Properties['CandidateProfile'] -and $plan.CandidateProfile -ceq 't7-image-provenance-v1'))
    $registration=[bool]($plan.PSObject.Properties['SelectedRegistrationImageHeaderV1'] -or
        ($plan.PSObject.Properties['Operation'] -and $plan.Operation -ceq 'RegistrationImageMetadataV1') -or
        ($plan.PSObject.Properties['CandidateProfile'] -and $plan.CandidateProfile -ceq 't7-registration-image-header-metadata-v1'))
    $incoming=[bool]($plan.PSObject.Properties['SelectedIncomingImageObservationV1'] -or
        ($plan.PSObject.Properties['Operation'] -and $plan.Operation -ceq 'IncomingImageObservationV1') -or
        ($plan.PSObject.Properties['CandidateProfile'] -and $plan.CandidateProfile -ceq 't7-incoming-image-header-observation-v1'))
    $registrationBindings=[bool]($plan.PSObject.Properties['SelectedRegistrationMaterialBindingsV1'] -or
        ($plan.PSObject.Properties['Operation'] -and $plan.Operation -ceq 'RegistrationMaterialBindingsV1') -or
        ($plan.PSObject.Properties['CandidateProfile'] -and $plan.CandidateProfile -ceq 't7-registration-material-bindings-v1') -or
        ($plan.PSObject.Properties['Schema'] -and $plan.Schema -cin @('iw7.t7-registration-bindings-source-plan/1','iw7.t7-registration-bindings-plan/1')) -or
        ($plan.PSObject.Properties['Arguments'] -and $plan.Arguments -ccontains '-t7-iw7-registration-material-bindings-v1'))
    $zombies=[bool]($plan.PSObject.Properties['CandidateProfile'] -and $plan.CandidateProfile -cin @('t7-zombies-catalogue-observation-c','t7-zombies-catalogue-observation-c2'))
    $exportProfile=Join-Path $PSScriptRoot 'T7ResidentExport.Profile.ps1'
    if($export -or $zombies){$required+=@($exportProfile)}
    $partsProfile=Join-Path $PSScriptRoot 'T7MaterialParts.Profile.ps1'
    if($parts){$required+=@($partsProfile)}
    $provenanceProfile=Join-Path $PSScriptRoot 'T7ImageProvenance.Profile.ps1'
    if($provenance -or $registration -or $incoming -or $registrationBindings){$required+=@($provenanceProfile)}
    $registrationProfile=Join-Path $PSScriptRoot 'T7RegistrationImage.Profile.ps1'
    if($registration){$required+=@($registrationProfile)}
    $incomingProfile=Join-Path $PSScriptRoot 'T7IncomingImage.Profile.ps1'
    if($incoming){$required+=@($incomingProfile)}
    foreach($path in $required) {
        $pin=@($plan.Bindings|Where-Object {$_.Path -ceq $path -and $_.IsText -eq $true})
        if($pin.Count -ne 1 -or $pin[0].Bytes -gt 1MB){throw 'Bounded exact source binding missing.'}
        $guards.Add((Open-H1Pin $pin[0]))
    }
    . $prepatchProfile # Functions only; reuse environment/Main checks without changing the diagnostic.
    . $profile
    if($export -or $zombies){. $exportProfile} # C consumes only the shared build qualifier.
    if($parts){. $partsProfile}
    if($provenance -or $registration -or $incoming -or $registrationBindings){. $provenanceProfile} # Existing guarded stdout reader.
    if($registration){. $registrationProfile}
    if($incoming){. $incomingProfile}
    Assert-T7CataloguePlan $plan $repo $PSCommandPath
    $provenance=Test-T7ImageProvenanceCompiledPlan $plan
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
    if($provenance){
        $state.Schema='iw7.t7-image-provenance-run/1';$state.Stage='ImageProvenance';$state.Remove('CatalogueOutcome')
        $state.ProvenanceOutcome='ProvenanceNoReport';$state.SelectedProvenance=$null
        $attemptSchema='iw7.t7-image-provenance-attempt/1';$leaseOwner='T7 F2 image-field provenance metadata only'
    }
    if($registration){
        $state.Schema='iw7.t7-registration-image-run/1';$state.Stage='RegistrationImage';$state.Remove('CatalogueOutcome')
        $state.RegistrationOutcome='RegistrationNoReport';$state.SelectedRegistrationHeader=$null
        $attemptSchema='iw7.t7-registration-image-attempt/1';$leaseOwner='T7 owned registration image-header metadata only'
    }
    if($incoming){
        $state.Schema='iw7.t7-incoming-image-run/1';$state.Stage='IncomingImage';$state.Remove('CatalogueOutcome')
        $state.IncomingObservationOutcome='IncomingNoReport';$state.SelectedIncomingObservation=$null
        $attemptSchema='iw7.t7-incoming-image-attempt/1';$leaseOwner='T7 incoming image-header metadata only'
    }
    if($registrationBindings){
        $state.Schema='iw7.t7-registration-bindings-run/1';$state.Stage='RegistrationBindings';$state.Remove('CatalogueOutcome')
        $state.RegistrationBindingsOutcome='RegistrationBindingsNoReport';$state.SelectedRegistrationBindings=$null
        $attemptSchema='iw7.t7-registration-bindings-attempt/1';$leaseOwner='T7 seven material bindings metadata only'
        $context|Add-Member NoteProperty PublicationGuards ([Collections.Generic.List[object]]::new())
        $context|Add-Member NoteProperty Publications ([Collections.Generic.List[object]]::new())
        $context|Add-Member NoteProperty PreReleasePublished $false
        $context|Add-Member NoteProperty CompletionPublished $false
        $context|Add-Member NoteProperty CanExit $false
    }
    if($parts){
        $state.Schema='iw7.t7-material-parts-run/1';$state.Stage='MaterialParts';$state.Remove('CatalogueOutcome')
        $state.PartsOutcome='NoPartsMetadata';$state.SelectedPartsMetadata=$null
        $attemptSchema='iw7.t7-material-parts-attempt/1';$leaseOwner='T7 selected image-parts metadata only'
    }
    if($export){
        $state.Schema='iw7.t7-resident-export-run/1';$state.Stage='ResidentExport';$state.Remove('CatalogueOutcome')
        $state.ExportOutcome='NoExport';$state.ExportRequest=$plan.ExportRequest
        $state.TraceOutcome='DisabledForResidentExportCLI';$state.MessageOutcome='DisabledForResidentExportCLI'
        $state.SerializedParseVerified=$false;$state.DependencyPayloadsVerified=$false
        $attemptSchema='iw7.t7-resident-export-attempt/1';$leaseOwner='T7 one-model resident export'
    }
    if($registrationBindings -and [AppDomain]::CurrentDomain.GetData('IW7.T7RegistrationBindings.Run')){throw 'Original bindings context already exists.'}
    $context.Lease=Enter-IW7ResourceLease -Scope $plan.RunRoot -Kind Extract -PhysicalBytes 6GB -CommitBytes 8GB -Owner $leaseOwner
    $state.LeaseToken=$context.Lease.Token
    if($registrationBindings){
        [AppDomain]::CurrentDomain.SetData('IW7.T7RegistrationBindings.Run',[pscustomobject]@{Context=$context;State=$state;Guards=$guards})
    }
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
    if($export -and (Get-T7SelectedStreamedExport $plan)){$state.Aliases+=@(New-T7SelectedStreamedAliases $plan $context)}
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
            try{if(!$export -and !$parts -and !$provenance -and !$registration -and !$incoming -and !$registrationBindings){Read-T7CatalogueTrace $plan $state $context}}
            catch{if(!$failure){$failure=$_};$state.TraceError=$_.Exception.Message;$state.Status='Failed'}
            Assert-T7CatalogueEngineOutputs $plan -Closed -Context $context
            $state.EngineOutputsValidated=$true
            if($registrationBindings){$state.RegistrationBindingsOutcome=Read-T7RegistrationBindingsRecord $plan $state $context}
            elseif($incoming){$state.IncomingObservationOutcome=Read-T7IncomingImageRecord $plan $state $context}
            elseif($registration){$state.RegistrationOutcome=Read-T7RegistrationImageRecord $plan $state $context}
            elseif($provenance){$state.ProvenanceOutcome=Read-T7ImageProvenanceRecord $plan $state $context}
            elseif($parts){$state.PartsOutcome=Read-T7MaterialPartsReport $plan $state $context}
            elseif($export){$state.ExportOutcome=Read-T7ResidentExportReport $plan $state $context}
            else{$state.CatalogueOutcome=Read-T7CatalogueReport $plan $state $context}
            $hashAliases=@($state.Aliases|Where-Object {!$_.PSObject.Properties['GuardScope']})
            foreach($pin in @($plan.Bindings)+@($zonePin)+$hashAliases) {
                $guard=Open-H1Pin $pin;try{}finally{$guard.Dispose()};Assert-H1Deadline $script:T7CatalogueGroupStarted 200
            }
            if($export -and (Get-T7SelectedStreamedExport $plan)){
                $null=Open-T7SelectedStreamedProvider $plan $plan.SelectedXpakProvider.Metadata.Path $context
                $null=Open-T7SelectedStreamedProvider $plan (Join-Path $plan.WorkingDirectory $plan.SelectedXpakProvider.RelativePath) $context
                $state.SelectedProviderMetadataReverified=$true;$state.SelectedProviderWholeFileHashed=$false
            }
            foreach($item in $plan.InputMetadata){Assert-T7CatalogueMetadata $item}
            foreach($item in @($state.InputFileIds)+@($state.Aliases)){if((Get-T7CatalogueFileId $item.Path) -cne $item.FileId){throw 'Original/alias file ID changed.'}}
            $state.InputsReverified=$true;$state.OriginalInputMetadataUnchanged=$true;$state.AliasesRetained=$true
            Test-H1Budget $plan $state
            if(!$failure -and $export -and $state.ExportOutcome -cne 'ExportFilesObserved'){throw 'No qualified selective export was produced.'}
            if(!$failure -and $parts -and $state.PartsOutcome -cne 'PartsMetadataObserved'){throw 'No qualified G3 metadata observation was produced.'}
            if(!$failure -and $incoming -and $state.IncomingObservationOutcome -cne 'IncomingRecordCaptured'){throw 'No incoming record was captured for deep review.'}
            if(!$failure -and $registrationBindings -and $state.RegistrationBindingsOutcome -cne 'RegistrationBindingsRecordCaptured'){throw 'No bindings record was captured for the independent typed reader.'}
            if(!$failure -and $registration -and $state.RegistrationOutcome -cne 'RegistrationRecordCaptured'){throw 'No complete owned-registration record was captured.'}
            if(!$failure -and $provenance -and $state.ProvenanceOutcome -cne 'ProvenanceRecordCaptured'){throw 'No complete F2 provenance record was captured.'}
            if(!$failure -and !$export -and !$parts -and !$provenance -and !$registration -and !$incoming -and !$registrationBindings -and $state.CatalogueOutcome -cnotin @('EmptyCatalogue','CatalogueWithNames')){throw 'No qualified catalogue was produced.'}
            if(!$failure -and !$export -and !$parts -and !$provenance -and !$registration -and !$incoming -and !$registrationBindings -and (Get-T7CatalogueCandidateProfile $plan) -cne 'ordinary-d2' -and $state.TraceOutcome -cne 'TraceObserved'){throw 'Trace candidate produced no qualified enabled trace.'}
        }catch{if(!$failure){$failure=$_};$state.ValidationError=$_.Exception.Message;$state.Status='Failed'}
    }
    if($state){
        if($registrationBindings){Complete-H1Stage $context $state -BeforeReleaseCheck {Publish-T7RegistrationBindingsBeforeRelease $plan $state $context}}
        else{Complete-H1Stage $context $state}
    }
    if($state -and $attempted -and $context.Closed) {
        try{$state.MainAfter=Assert-T7CatalogueMain $plan}
        catch{if(!$failure){$failure=$_};$state.MainAfterError=$_.Exception.Message;$state.Status='Failed'}
    }
    if($state -and !$export -and !$parts -and !$provenance -and !$registration -and !$incoming -and !$registrationBindings -and $attempted -and $context.Closed -and !$context.Lease -and !$state.InputsReverified -and $state.TerminationRequested) {
        # After forced closure, inspect only bounded diagnostics, never hash payloads.
        try{Read-T7CatalogueTrace $plan $state $context}catch{$state.TraceError=$_.Exception.Message}
        try{$state.CatalogueOutcome=Read-T7CatalogueReport $plan $state $context}catch{$state.ReportError=$_.Exception.Message}
    }
    if($state -and !$context.Closed){if($registrationBindings){$state.RegistrationBindingsOutcome='NotInspectedWhileJobUnclosed'}elseif($incoming){$state.IncomingObservationOutcome='NotInspectedWhileJobUnclosed'}elseif($registration){$state.RegistrationOutcome='NotInspectedWhileJobUnclosed'}elseif($provenance){$state.ProvenanceOutcome='NotInspectedWhileJobUnclosed'}elseif($parts){$state.PartsOutcome='NotInspectedWhileJobUnclosed'}elseif($export){$state.ExportOutcome='NotInspectedWhileJobUnclosed'}else{$state.CatalogueOutcome='NotInspectedWhileJobUnclosed'}}
    if($state -and $attempted) {
        if($context.Owner -and $context.Closed){$state.ClosureEvidence='Pinned NativeJob CloseConfirmed rechecks original RootExited and ActiveProcesses==0; original ExitCode retained.'}
        $state.FinishedUtc=[DateTime]::UtcNow.ToString('o')
        try {
            if(!$state.Quarantined){Assert-H1Deadline $script:T7CatalogueGroupStarted 200}
            if(!$failure -and $context.Closed -and !$context.Lease -and $state.LeaseReleased -and
               !$state.TerminationRequested -and $state.InputsReverified -and $state.EngineOutputsValidated){
                if($registrationBindings -and $state.RegistrationBindingsOutcome -ceq 'RegistrationBindingsRecordCaptured' -and $state.ExitCode -eq 0 -and
                   !$state.Quarantined -and $state.TreeClosureConfirmed){$state.Status='RegistrationBindingsCapturedPendingReview'}
                elseif($incoming -and $state.IncomingObservationOutcome -ceq 'IncomingRecordCaptured' -and $state.ExitCode -eq 0 -and
                   !$state.Quarantined -and $state.TreeClosureConfirmed){$state.Status='IncomingRecordCapturedPendingReview'}
                elseif($registration -and $state.RegistrationOutcome -ceq 'RegistrationRecordCaptured'){$state.Status='RegistrationRecordCapturedPendingReview'}
                elseif($provenance -and $state.ProvenanceOutcome -ceq 'ProvenanceRecordCaptured'){$state.Status='ProvenanceRecordCapturedPendingReview'}
                elseif($parts -and $state.PartsOutcome -ceq 'PartsMetadataObserved'){$state.Status='PartsMetadataObservedPendingReview'}
                elseif($export -and $state.ExportOutcome -ceq 'ExportFilesObserved'){$state.Status='ExportObservedPendingReadback'}
                elseif(!$export -and !$parts -and !$provenance -and !$registration -and !$incoming -and !$registrationBindings -and $state.CatalogueOutcome -cin @('EmptyCatalogue','CatalogueWithNames')){$state.Status='CatalogueObservedPendingDonorReview'}
            }
        }catch{if(!$failure){$failure=$_};$state.Status='Failed';$state.FinalizationError=$_.Exception.Message}
        try {
            $finalReceipt=Write-H1Receipt $plan $state $plan.StageRoot -PassThru:$registrationBindings
            if($state.Status -cin @('CatalogueObservedPendingDonorReview','ExportObservedPendingReadback','PartsMetadataObservedPendingReview','ProvenanceRecordCapturedPendingReview','RegistrationRecordCapturedPendingReview','IncomingRecordCapturedPendingReview','RegistrationBindingsCapturedPendingReview')) {
                try{Assert-H1Deadline $script:T7CatalogueGroupStarted 200}
                catch {
                    $failure=$_;$state.Status='Failed';$state.FinalizationError=$_.Exception.Message
                    [IO.File]::Move((Join-Path $plan.StageRoot 'receipt.json'),(Join-Path $plan.StageRoot 'receipt.deadline-exceeded.json'))
                    $finalReceipt=Write-H1Receipt $plan $state $plan.StageRoot -PassThru:$registrationBindings
                }
            }
            if($registrationBindings){Complete-T7RegistrationBindingsPublication $finalReceipt $context}
        }catch{if(!$failure){$failure=$_};$state.Status='Failed';Write-Warning ('Receipt publication failed: '+$_.Exception.Message)}
    }
    if($context.Closed -and !$context.Lease -and (!$registrationBindings -or !$state -or (!$attempted -and !$context.Publications.Count) -or ($context.CompletionPublished -and !$context.PublicationGuards.Count))){
        foreach($guard in $guards){$guard.Dispose()};$guards.Clear()
        if($registrationBindings -and $state -and $context.CompletionPublished -and !$context.PublicationGuards.Count){$context.CanExit=$true}
    }
    if($registrationBindings -and $state -and $attempted -and !$context.CanExit){$state.Quarantined=$true;$state.Status='Quarantined'}
}
if($state -and $state.Quarantined) {
    Write-Warning 'Original owner/lease/guards retained in IW7.H1.Quarantine; keep this host for recovery. No retry.'
    while($true){Start-Sleep -Seconds 1}
}
if($state){
    $outcomeName=if($registrationBindings){'RegistrationBindingsOutcome'}elseif($incoming){'IncomingObservationOutcome'}elseif($registration){'RegistrationOutcome'}elseif($provenance){'ProvenanceOutcome'}elseif($parts){'PartsOutcome'}elseif($export){'ExportOutcome'}else{'CatalogueOutcome'}
    [ordered]@{Status=$state.Status;($outcomeName)=$state[$outcomeName];Receipt=(Join-Path $plan.StageRoot 'receipt.json');Ready=$false}|ConvertTo-Json
}
if($failure){throw $failure}
