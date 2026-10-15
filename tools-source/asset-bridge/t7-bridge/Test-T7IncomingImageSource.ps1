$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
. (Join-Path $PSScriptRoot 'T7CatalogueHost.Core.ps1')
. (Join-Path $PSScriptRoot 'T7IncomingImage.Profile.ps1')
$checks=0
function Check($Value,[string]$Message){if(!$Value){throw $Message};$script:checks++}
function Refuses([scriptblock]$Action,[string]$Message){$caught=$false;try{& $Action}catch{$caught=$_.Exception.Message.Contains($Message)};Check $caught ('Expected refusal: '+$Message)}
function New-IncomingSourcePlan {
    [pscustomobject]@{Schema='iw7.t7-incoming-image-source-plan/1';Operation='IncomingImageObservationV1';CandidateProfile='t7-incoming-image-header-observation-v1';
        Arguments=@('-t7-iw7-incoming-image-header-v1','mp_freerun_04','p7_fre_platform_cap_02','0');
        CandidateSource=$null;CandidateBytes=$null;CandidateSHA256=$null;BuildPlan=$null;BuildReceipt=$null;ExpectedBuildPlanSHA256=$null;ExpectedBuildReceiptSHA256=$null;
        SelectedIncomingImageObservationV1=[pscustomobject]@{Schema='iw7.t7-incoming-image-proposal/1';SourceRevision='4873ef4a4ce8478020d8533651f123f8feadfa95';NativeSchema='iw7.t7-incoming-image-header-observation/1';
            Contract=[pscustomobject]@{Path='C:\authored\incoming-image-source-contract.json';Bytes=4613;SHA256='1f672f51533f90ea10d396bd28a8298f6070d39df938b0bf4033c4754dc4659f'};
            SlotOrder=@('bootstrap/reference','bootstrap/ordinary','map_load/reference','map_load/ordinary');SourceOnlyPending=$true;CPPQualified=$false;NativeObserved=$false;QualifiedObjectMipCount=$null;Ready=$false}}
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
