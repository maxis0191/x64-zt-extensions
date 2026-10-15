$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path (Split-Path $PSScriptRoot -Parent) 'h1-fixture/H1Native.Core.ps1')
. (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
. (Join-Path $PSScriptRoot 'T7CatalogueHost.Core.ps1')
. (Join-Path $PSScriptRoot 'T7IncomingImage.Profile.ps1')
$checks=0
function Check($Value,[string]$Message){if(!$Value){throw $Message};$script:checks++}
function Refuses([scriptblock]$Action,[string]$Message){$caught=$false;try{& $Action}catch{$caught=$_.Exception.Message.Contains($Message)};Check $caught ('Expected refusal: '+$Message)}
function New-IncomingSourcePlan([switch]$Corrected) {
    $plan=[pscustomobject]@{Schema='iw7.t7-incoming-image-source-plan/1';Operation='IncomingImageObservationV1';CandidateProfile='t7-incoming-image-header-observation-v1';
        Arguments=@('-t7-iw7-incoming-image-header-v1','mp_freerun_04','p7_fre_platform_cap_02','0');
        CandidateSource=$null;CandidateBytes=$null;CandidateSHA256=$null;BuildPlan=$null;BuildReceipt=$null;ExpectedBuildPlanSHA256=$null;ExpectedBuildReceiptSHA256=$null;
        SelectedIncomingImageObservationV1=[pscustomobject]@{Schema='iw7.t7-incoming-image-proposal/1';SourceRevision='4873ef4a4ce8478020d8533651f123f8feadfa95';NativeSchema='iw7.t7-incoming-image-header-observation/1';
            Contract=[pscustomobject]@{Path='C:\authored\incoming-image-source-contract.json';Bytes=4613;SHA256='1f672f51533f90ea10d396bd28a8298f6070d39df938b0bf4033c4754dc4659f'};
            SlotOrder=@('bootstrap/reference','bootstrap/ordinary','map_load/reference','map_load/ordinary');SourceOnlyPending=$true;CPPQualified=$false;NativeObserved=$false;QualifiedObjectMipCount=$null;Ready=$false}}
    if($Corrected){
        $plan.SelectedIncomingImageObservationV1.SourceRevision='41e595f09dabdd6dff14439f09bd701bddd4a235'
        $plan.SelectedIncomingImageObservationV1.Contract.SHA256='a2cdaf54b7387616bd56d9a78538e7a273ec35e9eb2f6f6ac1e130ecd3851323'
    }
    $plan
}
$plan=New-IncomingSourcePlan;Assert-T7IncomingImageSourcePlan $plan;Check $true 'Exact pending Source plan refused.'
Check (Test-T7IncomingImageIntent $plan) 'Incoming Source intent not detected.'
Check ((Get-T7CatalogueOperation $plan) -ceq 'IncomingImageObservationV1') 'Incoming operation unknown.'
Check ((Get-T7CatalogueCandidateProfile $plan) -ceq 't7-incoming-image-header-observation-v1') 'Incoming profile unknown.'
Check ((Get-T7CatalogueHostSchema $plan 'host-closure') -ceq 'iw7.t7-incoming-image-host-closure/1') 'Incoming host schema fell through.'
Check ((Get-T7CatalogueHostOutcomeName $plan) -ceq 'IncomingObservationOutcome') 'Incoming outcome fell through.'
function New-T7PrepatchStart {throw 'Reached process setup'}
Refuses {Assert-T7CataloguePlan $plan 'unused' 'unused'} 'new actual closed CPP cohort'
Refuses {Assert-T7CatalogueBuild $plan $null} 'new actual closed CPP cohort'
Refuses {New-T7CatalogueStart $plan} 'new actual closed CPP cohort'
$corrected=New-IncomingSourcePlan -Corrected
Assert-T7IncomingImageSourcePlan $corrected;Check $true 'Corrected Source prerequisite refused.'
Refuses {Assert-T7CataloguePlan $corrected 'unused' 'unused'} 'new actual closed CPP cohort'
Refuses {Assert-T7CatalogueBuild $corrected $null} 'new actual closed CPP cohort'
Refuses {New-T7CatalogueStart $corrected} 'new actual closed CPP cohort'
foreach($pair in @(@($false,'a2cdaf54b7387616bd56d9a78538e7a273ec35e9eb2f6f6ac1e130ecd3851323'),
                  @($true,'1f672f51533f90ea10d396bd28a8298f6070d39df938b0bf4033c4754dc4659f'))){
    $useCorrected=[bool]$pair[0]
    $mixed=New-IncomingSourcePlan -Corrected:$useCorrected;$mixed.SelectedIncomingImageObservationV1.Contract.SHA256=$pair[1]
    Refuses {Assert-T7IncomingImageSourcePlan $mixed} 'contract text pin required'
}
$mixed=New-IncomingSourcePlan -Corrected;$mixed.SelectedIncomingImageObservationV1.SourceRevision='2057a2c7704b5fbb914268721da4be852c746e75'
Refuses {Assert-T7IncomingImageSourcePlan $mixed} 'Source revision required'
$mixed=New-IncomingSourcePlan -Corrected;$mixed.CandidateSHA256='eeeca36f26ff2c76b98a608fe17a6b47259401b1cd800f73fe886bd099ac6dbc'
Refuses {Assert-T7IncomingImageSourcePlan $mixed} 'must remain NULL'
foreach($name in 'CandidateSource','CandidateBytes','CandidateSHA256','BuildPlan','BuildReceipt','ExpectedBuildPlanSHA256','ExpectedBuildReceiptSHA256'){
    foreach($bad in @('eeeca36f',0,$false,[object[]]@($null))){$plan=New-IncomingSourcePlan;$plan.$name=$bad;Refuses {Assert-T7IncomingImageSourcePlan $plan} 'must remain NULL'}
    $plan=New-IncomingSourcePlan;$plan.PSObject.Properties.Remove($name);Refuses {Assert-T7IncomingImageSourcePlan $plan} 'must remain NULL'
}
foreach($name in 'Schema','Operation','CandidateProfile'){
    $plan=New-IncomingSourcePlan;$plan.$name=@($plan.$name);Refuses {Assert-T7IncomingImageSourcePlan $plan} 'Typed incoming Source selectors'
    $plan=New-IncomingSourcePlan;$plan.$name='RegistrationImageMetadataV1';Refuses {Assert-T7IncomingImageSourcePlan $plan} 'Exact incoming Source schema'
}
foreach($name in 'Schema','SourceRevision','NativeSchema'){
    $plan=New-IncomingSourcePlan;$plan.SelectedIncomingImageObservationV1.$name=@($plan.SelectedIncomingImageObservationV1.$name)
    Refuses {Assert-T7IncomingImageSourcePlan $plan} 'Typed incoming Source descriptor texts'
}
foreach($name in 'CPPQualified','NativeObserved','Ready'){
    $plan=New-IncomingSourcePlan;$plan.SelectedIncomingImageObservationV1.$name=$true;Refuses {Assert-T7IncomingImageSourcePlan $plan} 'cannot promote'
    $plan=New-IncomingSourcePlan;$plan.SelectedIncomingImageObservationV1.$name='false';Refuses {Assert-T7IncomingImageSourcePlan $plan} 'cannot promote'
}
$plan=New-IncomingSourcePlan;$plan.SelectedIncomingImageObservationV1.SourceOnlyPending=$false;Refuses {Assert-T7IncomingImageSourcePlan $plan} 'must remain Source pending'
$plan=New-IncomingSourcePlan;$plan.SelectedIncomingImageObservationV1.QualifiedObjectMipCount=1;Refuses {Assert-T7IncomingImageSourcePlan $plan} 'mip fact must remain NULL'
foreach($name in 'SelectedImageProvenanceV1','SelectedRegistrationImageHeaderV1','SelectedMaterialPartsV1','SelectedXpakProvider','ExportRequest'){
    $plan=New-IncomingSourcePlan;$plan|Add-Member $name $false;Refuses {Assert-T7IncomingImageSourcePlan $plan} 'another operation/provider'
}
for($i=0;$i -lt 4;$i++){
    $plan=New-IncomingSourcePlan;$plan.Arguments[$i]='wrong';Refuses {Assert-T7IncomingImageSourcePlan $plan} 'Source arguments required'
    $plan=New-IncomingSourcePlan;$plan.SelectedIncomingImageObservationV1.SlotOrder[$i]='wrong';Refuses {Assert-T7IncomingImageSourcePlan $plan} 'Source slot order required'
}
$plan=New-IncomingSourcePlan;$plan.Arguments[3]=0;Refuses {Assert-T7IncomingImageSourcePlan $plan} 'Source arguments required'
$plan=New-IncomingSourcePlan;$plan.Arguments+='extra';Refuses {Assert-T7IncomingImageSourcePlan $plan} 'Source arguments required'
foreach($path in @('C:\authored\candidate.exe:incoming-image-source-contract.json','\\?\C:\authored\incoming-image-source-contract.json','C:\authored\other.json')){
    $plan=New-IncomingSourcePlan;$plan.SelectedIncomingImageObservationV1.Contract.Path=$path;Refuses {Assert-T7IncomingImageSourcePlan $plan} 'contract text pin required'
}
$plan=New-IncomingSourcePlan;$plan.SelectedIncomingImageObservationV1.Contract.Bytes='4613';Refuses {Assert-T7IncomingImageSourcePlan $plan} 'contract text pin required'
$plan=New-IncomingSourcePlan;$plan.SelectedIncomingImageObservationV1.Contract.SHA256='old';Refuses {Assert-T7IncomingImageSourcePlan $plan} 'contract text pin required'
foreach($operation in 'Catalogue','ResidentExportV1','MaterialPartsV1','ImageProvenanceV1','RegistrationImageMetadataV1'){
    $legacy=[pscustomobject]@{Operation=$operation;CandidateProfile='ordinary-d2'}
    Check (!(Test-T7IncomingImageIntent $legacy)) 'Existing mode selected incoming.'
    Check ((Get-T7CatalogueOperation $legacy) -ceq $operation) 'Existing operation changed.'
}
# Authored CPP87 bodies; these tests never launch a fixture or inspect an artifact.
function New-IncomingCompiledPlan {
    $c=Get-T7IncomingImageCohort;$root='C:\authored\cpp87';$bindings=@()
    $m=[ordered]@{Schema='iw7.t7-incoming-image-cpp87/1';ReviewedPrerequisiteSource=$c.ReviewedPrerequisiteSource;CompiledExtensionSource=$c.Source}
    foreach($name in 'Contract','SourceManifest','HostWitness','ClosureWitness','FixtureStdout','FreshWitness'){
        $pin=[pscustomobject]@{Path=(Join-Path $root ($name+'.json'));Bytes=$c[$name][0];SHA256=$c[$name][1]}
        $m[$name]=$pin;$bindings+=,[pscustomobject]@{Path=$pin.Path;Bytes=$pin.Bytes;SHA256=$pin.SHA256;IsText=$true}
    }
    foreach($pair in @(@('Plan','plan.json'),@('Receipt','receipt.json'))){
        $bindings+=,[pscustomobject]@{Path=(Join-Path $root $pair[1]);Bytes=$c[$pair[0]][0];SHA256=$c[$pair[0]][1];IsText=$true}
    }
    [pscustomobject]@{Schema='iw7.t7-incoming-image-plan/1';Operation='IncomingImageObservationV1';CandidateProfile='t7-incoming-image-header-observation-v1';
        BootstrapPolicy='QualifiedCollectionV3';Bootstraps=@(1..23);SharedQualification=[pscustomobject]@{};CandidateBytes=$c.EXEBytes;CandidateSHA256=$c.EXESHA256;
        CandidateSource=(Join-Path $root 'link/zonetool-t7.exe');BuildPlan=(Join-Path $root 'plan.json');BuildReceipt=(Join-Path $root 'receipt.json');
        ExpectedBuildPlanSHA256=$c.Plan[1];ExpectedBuildReceiptSHA256=$c.Receipt[1];OutputKey='t7_iw7_incoming_image_observation_v1';TraceStderrLimitBytes=16384;
        Arguments=@('-t7-iw7-incoming-image-header-v1','mp_freerun_04','p7_fre_platform_cap_02','0');Bindings=$bindings;SelectedIncomingImageObservationV1=[pscustomobject]$m}
}
function New-IncomingCppFixture {
    $c=Get-T7IncomingImageCohort;$plan=New-IncomingCompiledPlan
    $profile=[pscustomobject]@{Name='t7-incoming-image-header-observation-v1';Option='-t7-iw7-incoming-image-header-v1';ArgumentCount=5;
        ObservationSchema='iw7.t7-incoming-image-header-observation/1';IncomingSchema='iw7.t7-incoming-image-header-observation/1';
        RegistrationSchema='iw7.t7-registration-image-header-metadata/1';
        RegistrationFixtureChecks=39;IncomingFixtureChecks=48;SourceOnlyPending=$false;RegistrationCPPQualified=$false;IncomingCPPQualified=$false}
    $stages=@(foreach($name in 'registration-fixture-compile','registration-fixture-test','main','zonetool11','link'){
        [pscustomobject]@{Name=$name;Stage=$(if($name -ceq 'registration-fixture-test'){'Probe'}elseif($name -ceq 'link'){'Link'}else{'Compile'});
            ExitCode=0;TreeClosureConfirmed=$true;Artifacts=@();CompilerTelemetry=[pscustomobject]@{Completed=($name -cne 'registration-fixture-test');
                AfterStop=[pscustomobject]@{RootExited=$true;RootExitCode=0;ActiveProcesses=0};AfterStopMembers=[pscustomobject]@{Members=@()}}}
    })
    $stages[1]|Add-Member LegacyRegistrationChecks 39;$stages[1]|Add-Member IncomingChecks 48;$stages[1]|Add-Member EngineInvoked $false
    $stages[-1].Artifacts=@([pscustomobject]@{Path=$plan.CandidateSource;Bytes=$c.EXEBytes;SHA256=$c.EXESHA256})
    $receipt=[pscustomobject]@{Schema='iw7.t7-minimal-build/1';Status='Passed';PlanSHA256=$c.Plan[1];InputsReverified=$true;TreeClosureConfirmed=$true;
        LeaseReleased=$true;Quarantined=$false;CandidateExecuted=$false;RegistrationFixturePassed=$true;IncomingFixturePassed=$true;
        RegistrationCPPQualified=$true;IncomingCPPQualified=$true;Stages=$stages;CompilerTelemetry=[pscustomobject]@{Completed=$false}}
    $known=@(for($i=0;$i -lt 11;$i++){[pscustomobject]@{PID=$c.OriginalIDs[$i];Image='C:\authored\original.exe';CreationFileTime=([long]134365054277439850+$i)}})
    $known[9].Image='C:\authored\pwsh.exe';$known[9].CreationFileTime=[long]134365054277439850
    $known[10].Image='C:\authored\pwsh.exe';$known[10].CreationFileTime=[long]134365054279170774
    $observations=@($known|ForEach-Object {[pscustomobject]@{Expected=[pscustomobject]@{PID=$_.PID;Image=$_.Image;CreationFileTime=$_.CreationFileTime};OriginalIdentityPresent=$false;Live=$null}})
    $witness=[pscustomobject]@{Schema='iw7.t7-incoming-image-cpp-preexit/1';SourceCommit=$c.Source;Status='Passed';BuildGuards=0;CallerSourceGuards=0;
        Host=[pscustomobject]@{PID=19212;CreationFileTime=[long]134365054279170774;Image='C:\authored\pwsh.exe';EntryAssembly='C:\authored\pwsh.dll';Invocation='.';
            NoExitVerified=$true;VerifiedBeforeImportsAndAdmission=$true;Arguments=@('C:\authored\pwsh.dll','-NoLogo','-NoProfile','-NoExit','-Command','. authored.ps1')};
        Parent=[pscustomobject]@{PID=26324;CreationFileTime=[long]134365054277439850;Image='C:\authored\pwsh.exe'};KnownOriginalIdentities=$known;
        CandidateExecuted=$false;NativeCLIExecuted=$false;StockRead=$false;Ready=$false;PhaseProjectionIncomplete=$false}
    foreach($name in 'SameActualCallerAppDomain','SameOriginalContextPSVariable','SameOriginalStatePSVariable','SameOriginalGuardsPSVariable','SameOriginalOwnerReference',
        'OriginalContextClosed','OriginalOwnerClosed','CallerSourcePinsReverified','LeaseNull','CanExit','InputsReverified','LeaseReleased','TreeClosureConfirmed',
        'RegistrationFixturePassed','IncomingFixturePassed','RegistrationCPPQualified','IncomingCPPQualified','ExactCreationFILETIMEsInt64','FourCompilerStageTelemetryCompleted','ProbeCompilerTelemetryNotApplicable'){$witness|Add-Member $name $true}
    $closure=[pscustomobject]@{Schema='iw7.t7-incoming-image-cpp-closure/1';SourceCommit=$c.Source;Status='Passed';ActualTruePTYSession=50444;ActualTruePTYExitCode=0;
        ActualCompletionChunk='1ae1c5';Receipt=[pscustomobject]@{SHA256=$c.Receipt[1]};SameOriginalContextProof=[pscustomobject]@{SHA256=$c.HostWitness[1]};
        FreshObservation=[pscustomobject]@{SHA256=$c.FreshWitness[1]};LeaseRegistryCount=0;OriginalIdentityObservations=$observations;
        CandidateExecuted=$false;NativeCLIExecuted=$false;StockRead=$false;Ready=$false;ContextReconstructed=$false}
    foreach($name in 'AllElevenOriginalIdentitiesAbsent','InputsReverified','LeaseReleased','TreeClosureConfirmed','RegistrationCPPQualified','IncomingCPPQualified','NoOpaqueArtifactReopened'){$closure|Add-Member $name $true}
    [pscustomobject]@{Plan=$plan;Build=[pscustomobject]@{SourceCommit=$c.NativeSource;RunRoot='C:\authored\cpp87';BuildProfile=$profile};Receipt=$receipt;
        Manifest=[pscustomobject]@{revisions=[pscustomobject]@{'x64-zt-extensions'=$c.Source}};Witness=$witness;Closure=$closure;
        Fresh=[pscustomobject]@{Schema='iw7.t7-incoming-image-cpp-fresh-identities/1';OriginalPIDs=$c.OriginalIDs;RegistryVersion=1;RegistryLeaseCount=0;NoProcessStopped=$true;LiveAtOriginalPIDs=@();CompilerOrVCTIP=@()}}
}
function Qualify-Incoming($f){Assert-T7IncomingImageCpp87 $f.Plan $f.Build $f.Receipt $f.Manifest $f.Witness $f.Closure $f.Fresh}
$compiled=New-IncomingCompiledPlan;Assert-T7IncomingImagePlan $compiled;Check (Test-T7IncomingImageCompiledPlan $compiled) 'Compiled incoming selector failed.'
function New-T7PrepatchStart {[Diagnostics.ProcessStartInfo]::new()}
$start=New-T7CatalogueStart $compiled
Check (($start.ArgumentList -join '|') -ceq ($compiled.Arguments -join '|')) 'Incoming argv fell through to catalogue.'
$f=New-IncomingCppFixture;Qualify-Incoming $f;Check $true 'Authored closed CPP87 refused.'
foreach($case in 'candidate','old-plan','old-receipt','doc-source','old-source','native-source','profile-array','count','stage-order','stage-exit','stage-unclosed',
    'compiler-placeholder','active','members','probe39','probe48','probe-engine','inputs','receipt-qualified','context','guards','lease','host-generation','host-argv',
    'pty','live','identity-generation','closure-qualified','reconstructed','fresh-lease','fresh-compiler','artifact','host-argument-array','closure-hash-array','fresh-pid-string'){
    $f=New-IncomingCppFixture
    switch($case){
        candidate {$f.Plan.CandidateSHA256='eeeca36f26ff2c76b98a608fe17a6b47259401b1cd800f73fe886bd099ac6dbc'} old-plan {$f.Plan.ExpectedBuildPlanSHA256='old'}
        old-receipt {$f.Plan.ExpectedBuildReceiptSHA256='old'} doc-source {$f.Manifest.revisions.'x64-zt-extensions'='b20bdb5c4cd20d64da7e7fa9cf6cbd24cf938f43'}
        old-source {$f.Manifest.revisions.'x64-zt-extensions'='2057a2c7704b5fbb914268721da4be852c746e75'} native-source {$f.Build.SourceCommit='old'}
        profile-array {$f.Build.BuildProfile.Name=@($f.Build.BuildProfile.Name)} count {$f.Build.BuildProfile.ArgumentCount='5'}
        stage-order {$f.Receipt.Stages=@($f.Receipt.Stages[1],$f.Receipt.Stages[0])+$f.Receipt.Stages[2..4]} stage-exit {$f.Receipt.Stages[2].ExitCode=2}
        stage-unclosed {$f.Receipt.Stages[3].TreeClosureConfirmed=$false} compiler-placeholder {$f.Receipt.Stages[2].CompilerTelemetry.Completed=$false}
        active {$f.Receipt.Stages[4].CompilerTelemetry.AfterStop.ActiveProcesses=1} members {$f.Receipt.Stages[0].CompilerTelemetry.AfterStopMembers.Members=@(1)}
        probe39 {$f.Receipt.Stages[1].LegacyRegistrationChecks=38} probe48 {$f.Receipt.Stages[1].IncomingChecks=47} probe-engine {$f.Receipt.Stages[1].EngineInvoked=$true}
        inputs {$f.Receipt.InputsReverified='true'} receipt-qualified {$f.Receipt.IncomingCPPQualified=$false} context {$f.Witness.SameOriginalOwnerReference=$false}
        guards {$f.Witness.BuildGuards=1} lease {$f.Witness.LeaseNull=$false} host-generation {$f.Witness.Host.CreationFileTime++}
        host-argv {$f.Witness.Host.Arguments[3]='-Exit'} pty {$f.Closure.ActualTruePTYExitCode=1} live {$f.Closure.OriginalIdentityObservations[0].OriginalIdentityPresent=$true}
        identity-generation {$f.Closure.OriginalIdentityObservations[0].Expected.CreationFileTime++} closure-qualified {$f.Closure.IncomingCPPQualified=$false}
        reconstructed {$f.Closure.ContextReconstructed=$true} fresh-lease {$f.Fresh.RegistryLeaseCount=1} fresh-compiler {$f.Fresh.CompilerOrVCTIP=@(1)}
        artifact {$f.Receipt.Stages[-1].Artifacts[0].SHA256='old'}
        host-argument-array {$f.Witness.Host.Arguments[5]=@('. authored.ps1')} closure-hash-array {$f.Closure.Receipt.SHA256=@($f.Closure.Receipt.SHA256)}
        fresh-pid-string {$f.Fresh.OriginalPIDs[0]=[string]$f.Fresh.OriginalPIDs[0]}
    }
    Refuses {Qualify-Incoming $f} ''
}
foreach($name in 'Contract','SourceManifest','HostWitness','ClosureWitness','FixtureStdout','FreshWitness'){
    foreach($field in 'Bytes','SHA256'){
        $compiled=New-IncomingCompiledPlan;$compiled.SelectedIncomingImageObservationV1.$name.$field=@($compiled.SelectedIncomingImageObservationV1.$name.$field)
        Refuses {Assert-T7IncomingImagePlan $compiled} 'typed closed CPP87 text pin'
    }
}
$compiled=New-IncomingCompiledPlan;$compiled.SelectedIncomingImageObservationV1.CompiledExtensionSource=(Get-T7IncomingImageCohort).ReviewedPrerequisiteSource
Refuses {Assert-T7IncomingImagePlan $compiled} 'collection/tuple'
$jsonPath=Join-Path ([IO.Path]::GetTempPath()) ('iw7-incoming-source-'+[guid]::NewGuid().ToString('N')+'.json')
try{
    [IO.File]::WriteAllText($jsonPath,('{"SourceFixture":true}'+(' '*49139)),[Text.UTF8Encoding]::new($false))
    Check ((Read-H1SmallJson $jsonPath 1MB).SourceFixture) 'CPP receipt-sized text refused by existing CPP reader.'
    Refuses {Read-H1SmallJson $jsonPath 32KB} 'exceeds bound'
}finally{if([IO.File]::Exists($jsonPath)){[IO.File]::Delete($jsonPath)}}
# Authored Source records. Capture acceptance deliberately does not run consumer150.
function New-IncomingRecord {
    $r=[ordered]@{}
    foreach($name in 'allocation_retained','atomic_snapshot_proven','descriptor_admissible','lifetime_proven','model_binding_correlated',
        'pixels_copied','ready','renderer_binding_proven','runtime_abi_proven','same_object_proven','same_pointer_proven','source_asset_name_association_proven',
        'cap_refused','ordinary_name_observed','reference_name_observed','refused'){$r[$name]=$false}
    foreach($name in 'bootstrap_complete','exact_argv_validated_before_arm','map_complete','window_complete'){$r[$name]=$true}
    $r.schema='iw7.t7-incoming-image-header-observation/1';$r.source_profile='t7-incoming-image-header-observation-v1'
    $r.native_source_commit='fab935826c898806855376662a8a03317b3ad8f1';$r.zone='mp_freerun_04';$r.target_name='$camo_base_normal'
    $r.arm_phase='before_db_add_hook_create';$r.capture_phase='before_image_bypass';$r.name_comparison_rule='strip_one_leading_comma_then_exact_case_and_dollar'
    $r.arm_generation=1;$r.callback_limit=65536;$r.target_case_limit_per_phase=16;$r.read_limit=2097152
    foreach($name in 'image_callbacks','non_target_callbacks','ordinary_name_events','payload_bytes_read','read_bytes','reference_events'){$r[$name]=0}
    $r.qualified_object_mip_count=$null;$r.reason=$null;$r.ordinary_absence_scope='not_observed_in_this_bounded_callback_window'
    $r.cases=@(for($i=0;$i -lt 4;$i++){
        [pscustomobject]@{phase=$(if($i -lt 2){'bootstrap'}else{'map_load'});name_category=$(if($i % 2 -eq 0){'reference'}else{'ordinary'});
            callback_ordinal=$null;conflict_absence_proven=$false;descriptor_admissible=$false;effective_name=$null;leading_comma_reference=$null;
            matching_events_in_phase=0;nonzero_descriptor_scalar_fields=$null;raw_name=$null;repeated_headers_compared=$false;
            single_event_observed_in_phase=$false;snapshot=$null;state='not_observed';unique_in_phase=$false}
    })
    [pscustomobject]$r
}
function New-IncomingSnapshot {
    [pscustomobject]@{callback_header_name_rechecked=$true;completed_header_bytes=528;copy_fault=$false;header_copies=2;header_observed=$true;
        header_rechecked=$true;image=[pscustomobject]@{UninterpretedSourceFixture=$true};name_rechecked=$true;reason=$null;refused=$false}
}
function Encode-Incoming($Record){'T7_INCOMING_IMAGE_METADATA '+(ConvertTo-Json -InputObject $Record -Compress -Depth 25)}
$record=New-IncomingRecord
$contract=Get-Content -LiteralPath (Join-Path $PSScriptRoot '../t7-iw7/incoming-image-source-contract.json') -Raw|ConvertFrom-Json
Assert-T7CatalogueFields $record $contract.outer_keys
foreach($row in $record.cases){Assert-T7CatalogueFields $row $contract.case_keys}
Assert-T7CatalogueFields (New-IncomingSnapshot) $contract.snapshot_keys
$parsed=ConvertFrom-T7IncomingImageRecord (Encode-Incoming $record) 0
Check ($parsed.Outcome -ceq 'IncomingRecordCaptured') 'Bounded zero-matching window was mistaken for NoReport.'
Check ($null -eq $parsed.Record.cases[0].snapshot -and $null -eq $parsed.Record.cases[0].raw_name) 'Absent sample fabricated.'
Check ((ConvertFrom-T7IncomingImageRecord (Encode-Incoming $record) 7).Outcome -ceq 'IncomingRecordFromFailedProcess') 'Complete nonzero promoted.'
Check ((ConvertFrom-T7IncomingImageRecord 'ordinary log' 0).Outcome -ceq 'IncomingNoReport') 'Missing record fabricated.'
Check ($null -eq (ConvertFrom-T7IncomingImageRecord '' ([long]-2147483648)).Record) 'Original signed exit refused.'
Check ((ConvertFrom-T7IncomingImageRecord '' ([long]4294967295)).Outcome -ceq 'IncomingNoReport') 'Original unsigned-range exit refused.'
foreach($bad in @($null,$false,'0',0.0,[object[]]@(0),-2147483649L,4294967296L)){
    Refuses {ConvertFrom-T7IncomingImageRecord '' $bad} 'Typed original'
}
Refuses {ConvertFrom-T7IncomingImageRecord @('log') 0} 'stdout text'
foreach($bad in @('T7_INCOMING_IMAGE_METADATA null','T7_INCOMING_IMAGE_METADATA []','T7_INCOMING_IMAGE_METADATA {broken}',
    ((Encode-Incoming $record)+"`n"+(Encode-Incoming $record)))){
    Refuses {ConvertFrom-T7IncomingImageRecord $bad 0} ''
}
$encoded=Encode-Incoming $record
Refuses {ConvertFrom-T7IncomingImageRecord ($encoded.Replace('"schema":','"schema":"duplicate","schema":')) 0} 'Duplicate incoming JSON'
Refuses {ConvertFrom-T7IncomingImageRecord ($encoded.Replace('"schema":','"SCHEMA":"duplicate","schema":')) 0} 'Duplicate incoming JSON'
Refuses {ConvertFrom-T7IncomingImageRecord ($encoded.Replace('"read_bytes":0','"read_bytes":NaN')) 0} ''
foreach($name in $contract.outer_keys){
    $record=New-IncomingRecord;$record.PSObject.Properties.Remove($name)
    Refuses {ConvertFrom-T7IncomingImageRecord (Encode-Incoming $record) 0} ''
}
foreach($name in 'schema','source_profile','native_source_commit','zone','target_name','arm_phase','capture_phase','name_comparison_rule'){
    $record=New-IncomingRecord;$record.$name=@($record.$name)
    Refuses {ConvertFrom-T7IncomingImageRecord (Encode-Incoming $record) 0} 'Exact typed'
}
foreach($name in 'allocation_retained','atomic_snapshot_proven','descriptor_admissible','lifetime_proven','model_binding_correlated','pixels_copied',
    'ready','renderer_binding_proven','runtime_abi_proven','same_object_proven','same_pointer_proven','source_asset_name_association_proven'){
    $record=New-IncomingRecord;$record.$name=$true
    Refuses {ConvertFrom-T7IncomingImageRecord (Encode-Incoming $record) 0} 'cannot promote'
}
foreach($name in 'bootstrap_complete','cap_refused','exact_argv_validated_before_arm','map_complete','ordinary_name_observed','reference_name_observed','refused','window_complete'){
    $record=New-IncomingRecord;$record.$name='false'
    Refuses {ConvertFrom-T7IncomingImageRecord (Encode-Incoming $record) 0} 'Typed incoming observation flags'
}
$record=New-IncomingRecord;$record.qualified_object_mip_count=1
Refuses {ConvertFrom-T7IncomingImageRecord (Encode-Incoming $record) 0} 'mip fact'
$record=New-IncomingRecord;$record.payload_bytes_read=1
Refuses {ConvertFrom-T7IncomingImageRecord (Encode-Incoming $record) 0} 'zero payload'
$record=New-IncomingRecord;$record.window_complete=$false;$record.refused=$true;$record.reason='Authored refusal'
Check ((ConvertFrom-T7IncomingImageRecord (Encode-Incoming $record) 9).Outcome -ceq 'IncomingRecordRefused') 'Refusal diagnostics lost.'
Refuses {ConvertFrom-T7IncomingImageRecord (Encode-Incoming $record) 0} 'contradicts native exit zero'
foreach($name in 'exact_argv_validated_before_arm','map_complete','window_complete','bootstrap_complete'){
    $record=New-IncomingRecord;$record.$name=$false
    Refuses {ConvertFrom-T7IncomingImageRecord (Encode-Incoming $record) 0} 'flags contradict'
}
for($i=0;$i -lt 4;$i++){
    $record=New-IncomingRecord;$record.cases[$i].phase='wrong'
    Refuses {ConvertFrom-T7IncomingImageRecord (Encode-Incoming $record) 0} 'slot order'
    $record=New-IncomingRecord;$record.cases[$i].name_category=@('reference')
    Refuses {ConvertFrom-T7IncomingImageRecord (Encode-Incoming $record) 0} 'slot order'
}
foreach($name in $contract.case_keys){
    $record=New-IncomingRecord;$record.cases[0].PSObject.Properties.Remove($name)
    Refuses {ConvertFrom-T7IncomingImageRecord (Encode-Incoming $record) 0} ''
}
foreach($name in $contract.snapshot_keys){
    $record=New-IncomingRecord;$record.cases[0].snapshot=New-IncomingSnapshot;$record.cases[0].snapshot.PSObject.Properties.Remove($name)
    Refuses {ConvertFrom-T7IncomingImageRecord (Encode-Incoming $record) 0} ''
}
foreach($name in 'callback_header_name_rechecked','copy_fault','header_observed','header_rechecked','name_rechecked','refused'){
    $record=New-IncomingRecord;$record.cases[0].snapshot=New-IncomingSnapshot;$record.cases[0].snapshot.$name=@($true)
    Refuses {ConvertFrom-T7IncomingImageRecord (Encode-Incoming $record) 0} 'snapshot flags'
}
# Nested DTO/counter consistency is deliberately not claimed by this shell boundary.
$record=New-IncomingRecord;$record.cases[0].snapshot=New-IncomingSnapshot
$parsed=ConvertFrom-T7IncomingImageRecord (Encode-Incoming $record) 0
Check ($parsed.Outcome -ceq 'IncomingRecordCaptured' -and !$parsed.Record.ready) 'Capture pretended to classify the deep DTO.'
$encoded=Encode-Incoming $record
Refuses {ConvertFrom-T7IncomingImageRecord ($encoded.Replace('"UninterpretedSourceFixture":true','"x":0,"x":1')) 0} 'Duplicate incoming JSON'
$record.cases[0].snapshot.image=[pscustomobject]@{padding=('é'*17000)}
Refuses {ConvertFrom-T7IncomingImageRecord (Encode-Incoming $record) 0} 'One bounded'
$script:stdoutReads=0
function Read-T7ImageMetadataStdout($Plan,$State,$Context){$script:stdoutReads++;Encode-Incoming (New-IncomingRecord)}
function New-IncomingReadState {[ordered]@{ExitCode=0;TreeClosureConfirmed=$true;TerminationRequested=$false;Quarantined=$false;SelectedIncomingObservation=$null}}
function New-IncomingReadContext {[pscustomobject]@{Closed=$true;Owner=[object]::new();Lease=[object]::new()}}
$state=New-IncomingReadState;$context=New-IncomingReadContext
Check ((Read-T7IncomingImageRecord $null $state $context) -ceq 'IncomingRecordCaptured') 'Source read seam lost capture.'
Check ($state.SelectedIncomingObservation.InterpretationPending -and $null -eq $state.SelectedIncomingObservation.DeepMetadataOutcome -and
    $null -eq $state.SelectedIncomingObservation.QualifiedObjectMipCount -and !$state.SelectedIncomingObservation.Ready) 'Read seam promoted deep proof.'
foreach($case in 'unclosed','untyped','owner','lease','tree','forced','quarantined'){
    $state=New-IncomingReadState;$context=New-IncomingReadContext;$before=$script:stdoutReads
    switch($case){unclosed {$context.Closed=$false} untyped {$context.Closed='true'} owner {$context.Owner=$null} lease {$context.Lease=$null} tree {$state.TreeClosureConfirmed=$false}
        forced {$state.TerminationRequested=$true} quarantined {$state.Quarantined=$true}}
    Refuses {Read-T7IncomingImageRecord $null $state $context} 'close normally'
    Check ($script:stdoutReads -eq $before) 'Unclosed/unadmitted path read stdout.'
}
foreach($bad in @($null,'0',@([int]0))){
    $state=New-IncomingReadState;$state.ExitCode=$bad;$context=New-IncomingReadContext;$before=$script:stdoutReads
    Refuses {Read-T7IncomingImageRecord $null $state $context} 'before stdout read'
    Check ($script:stdoutReads -eq $before) 'Unknown original exit read stdout.'
}
[ordered]@{Status='Passed';Checks=$checks;SourceOnly=$true;CPPExecuted=$false;NativeExecuted=$false;LeaseAcquired=$false;OpaqueRead=$false;OperationalDEFAULTExecuted=$false}|ConvertTo-Json
