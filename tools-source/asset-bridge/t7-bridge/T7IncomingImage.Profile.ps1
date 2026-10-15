# Pending finite Source interface. No compiled candidate or operational mode exists.
function Assert-T7IncomingImageSourcePlan($Plan) {
    foreach($name in 'Schema','Operation','CandidateProfile'){
        if($Plan.$name -isnot [string]){throw 'Typed incoming Source selectors required.'}
    }
    if($Plan.Schema -cne 'iw7.t7-incoming-image-source-plan/1' -or $Plan.Operation -cne 'IncomingImageObservationV1' -or
       $Plan.CandidateProfile -cne 't7-incoming-image-header-observation-v1'){throw 'Exact incoming Source schema/operation/profile required.'}
    $marker=$Plan.SelectedIncomingImageObservationV1
    Assert-T7CatalogueFields $marker @('Schema','SourceRevision','Contract','NativeSchema','SlotOrder','SourceOnlyPending','CPPQualified','NativeObserved','QualifiedObjectMipCount','Ready')
    foreach($name in 'Schema','SourceRevision','NativeSchema'){
        if($marker.$name -isnot [string]){throw 'Typed incoming Source descriptor texts required.'}
    }
    if($marker.Schema -cne 'iw7.t7-incoming-image-proposal/1' -or
       $marker.NativeSchema -cne 'iw7.t7-incoming-image-header-observation/1'){throw 'Exact pending incoming Source basis required.'}
    # Keep the frozen proposal distinct from the corrected fixture prerequisite.
    $contractSHA=switch -CaseSensitive ($marker.SourceRevision){
        '4873ef4a4ce8478020d8533651f123f8feadfa95' {'1f672f51533f90ea10d396bd28a8298f6070d39df938b0bf4033c4754dc4659f'}
        '41e595f09dabdd6dff14439f09bd701bddd4a235' {'a2cdaf54b7387616bd56d9a78538e7a273ec35e9eb2f6f6ac1e130ecd3851323'}
        default {throw 'Exact pending incoming Source revision required.'}
    }
    $pin=$marker.Contract;Assert-T7CatalogueFields $pin @('Path','Bytes','SHA256')
    if($pin.Path -isnot [string] -or ![IO.Path]::IsPathFullyQualified($pin.Path) -or [IO.Path]::GetFullPath($pin.Path) -cne $pin.Path -or
       $pin.Path.StartsWith('\\') -or $pin.Path.Substring(2).Contains(':') -or $pin.Path -match '["\x00-\x1f]' -or
       [IO.Path]::GetFileName($pin.Path) -cne 'incoming-image-source-contract.json' -or
       !(Test-T7CatalogueInteger $pin.Bytes 8KB) -or $pin.Bytes -ne 4613 -or
       $pin.SHA256 -isnot [string] -or $pin.SHA256 -cne $contractSHA){
        throw 'Exact incoming Source contract text pin required.'
    }
    $slots=@('bootstrap/reference','bootstrap/ordinary','map_load/reference','map_load/ordinary')
    if($marker.SlotOrder -isnot [array] -or $marker.SlotOrder.Count -ne 4){throw 'Exact four incoming Source slots required.'}
    for($i=0;$i -lt 4;$i++){if($marker.SlotOrder[$i] -isnot [string] -or $marker.SlotOrder[$i] -cne $slots[$i]){throw 'Exact incoming Source slot order required.'}}
    if($marker.SourceOnlyPending -isnot [bool] -or !$marker.SourceOnlyPending){throw 'Incoming descriptor must remain Source pending.'}
    foreach($name in 'CPPQualified','NativeObserved','Ready'){
        if($marker.$name -isnot [bool] -or $marker.$name){throw 'Incoming Source cannot promote compiled/native/Ready proof.'}
    }
    if(![object]::ReferenceEquals($null,$marker.QualifiedObjectMipCount)){throw 'Incoming Source mip fact must remain NULL.'}
    foreach($name in 'CandidateSource','CandidateBytes','CandidateSHA256','BuildPlan','BuildReceipt','ExpectedBuildPlanSHA256','ExpectedBuildReceiptSHA256'){
        if(!$Plan.PSObject.Properties[$name] -or ![object]::ReferenceEquals($null,$Plan.$name)){throw 'Incoming unqualified candidate/build fields must remain NULL.'}
    }
    foreach($name in 'SelectedImageProvenanceV1','SelectedRegistrationImageHeaderV1','SelectedMaterialPartsV1','SelectedXpakProvider','ExportRequest','ExportRequestFile',
        'SelectedStreamedRenderOnlyV2','SelectedMeshMaterialObservation','ResidentMultiSurfaceV2','ResidentSurfaceCountDiagnostic','SelectedStreamedStaticV1','ZombiesObservationC','ZombiesAddObservationC2'){
        if($Plan.PSObject.Properties[$name]){throw 'Incoming Source cannot select another operation/provider.'}
    }
    $expected=@('-t7-iw7-incoming-image-header-v1','mp_freerun_04','p7_fre_platform_cap_02','0')
    if($Plan.Arguments -isnot [array] -or $Plan.Arguments.Count -ne 4){throw 'Exact incoming Source arguments required.'}
    for($i=0;$i -lt 4;$i++){if($Plan.Arguments[$i] -isnot [string] -or $Plan.Arguments[$i] -cne $expected[$i]){throw 'Exact incoming Source arguments required.'}}
}
function Assert-T7IncomingImageOperationalGate {
    throw 'Incoming observation awaits a new actual closed CPP cohort; operational DEFAULT and Run are unavailable.'
}

# Shell capture only. Consumer150 owns DTO/counter/copy semantics and deep outcomes.
function Assert-T7IncomingImageJsonNames($Element) {
    if($Element.ValueKind -eq [Text.Json.JsonValueKind]::Object){
        $names=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        foreach($property in $Element.EnumerateObject()){
            if(!$names.Add($property.Name)){throw 'Duplicate incoming JSON property refused.'}
            Assert-T7IncomingImageJsonNames $property.Value
        }
    }elseif($Element.ValueKind -eq [Text.Json.JsonValueKind]::Array){
        foreach($item in $Element.EnumerateArray()){Assert-T7IncomingImageJsonNames $item}
    }
}
function ConvertFrom-T7IncomingImageRecord($Text,$ExitCode) {
    if($Text -isnot [string] -or [Text.Encoding]::UTF8.GetByteCount($Text) -gt 1MB){throw 'Bounded incoming stdout text required.'}
    if(($ExitCode -isnot [int] -and $ExitCode -isnot [long]) -or $ExitCode -lt -2147483648L -or $ExitCode -gt 4294967295L){
        throw 'Typed original incoming native exit required.'
    }
    $markers=[regex]::Matches($Text,'T7_INCOMING_IMAGE_METADATA')
    if(!$markers.Count){return [pscustomobject]@{Outcome='IncomingNoReport';Record=$null}}
    $records=[regex]::Matches($Text,'(?m)^[^\r\n]*?T7_INCOMING_IMAGE_METADATA (\{[^\r\n]*\})\r?$')
    if($markers.Count -ne 1 -or $records.Count -ne 1 -or [Text.Encoding]::UTF8.GetByteCount($records[0].Groups[1].Value) -gt 32KB){
        throw 'One bounded incoming JSON object record required.'
    }
    $json=$records[0].Groups[1].Value
    $options=[Text.Json.JsonDocumentOptions]::new();$options.MaxDepth=25
    $document=[Text.Json.JsonDocument]::Parse($json,$options)
    try{Assert-T7IncomingImageJsonNames $document.RootElement}finally{$document.Dispose()}
    $r=ConvertFrom-Json -InputObject $json -Depth 25
    $falseFields=@('allocation_retained','atomic_snapshot_proven','descriptor_admissible','lifetime_proven','model_binding_correlated',
        'pixels_copied','ready','renderer_binding_proven','runtime_abi_proven','same_object_proven','same_pointer_proven','source_asset_name_association_proven')
    $boolFields=@('bootstrap_complete','cap_refused','exact_argv_validated_before_arm','map_complete','ordinary_name_observed','reference_name_observed','refused','window_complete')
    Assert-T7CatalogueFields $r ($falseFields+$boolFields+@('arm_generation','arm_phase','callback_limit','capture_phase','cases','image_callbacks',
        'name_comparison_rule','native_source_commit','non_target_callbacks','ordinary_absence_scope','ordinary_name_events','payload_bytes_read',
        'qualified_object_mip_count','read_bytes','read_limit','reason','reference_events','schema','source_profile','target_case_limit_per_phase','target_name','zone'))
    $texts=@{schema='iw7.t7-incoming-image-header-observation/1';source_profile='t7-incoming-image-header-observation-v1';
        native_source_commit='fab935826c898806855376662a8a03317b3ad8f1';zone='mp_freerun_04';target_name='$camo_base_normal';
        arm_phase='before_db_add_hook_create';capture_phase='before_image_bypass';name_comparison_rule='strip_one_leading_comma_then_exact_case_and_dollar'}
    foreach($name in $texts.Keys){if($r.$name -isnot [string] -or $r.$name -cne $texts[$name]){throw 'Exact typed incoming Source identity/phases required.'}}
    foreach($name in $falseFields){if($r.$name -isnot [bool] -or $r.$name){throw 'Incoming capture cannot promote descriptor/runtime/pixel proof.'}}
    foreach($name in $boolFields){if($r.$name -isnot [bool]){throw 'Typed incoming observation flags required.'}}
    if($null -ne $r.qualified_object_mip_count){throw 'Incoming capture mip fact must remain NULL.'}
    foreach($pair in @(@('arm_generation',1),@('callback_limit',65536),@('target_case_limit_per_phase',16),@('read_limit',2097152),@('payload_bytes_read',0))){
        if(!(Test-T7CatalogueInteger $r.($pair[0]) $pair[1]) -or $r.($pair[0]) -ne $pair[1]){throw 'Exact typed incoming scope and zero payload required.'}
    }
    foreach($pair in @(@('image_callbacks',65537),@('non_target_callbacks',65536),@('reference_events',34),@('ordinary_name_events',34),@('read_bytes',2097152))){
        if(!(Test-T7CatalogueInteger $r.($pair[0]) $pair[1])){throw 'Bounded typed incoming counters required.'}
    }
    if(!$r.exact_argv_validated_before_arm -or ($r.map_complete -and !$r.bootstrap_complete) -or
       $r.window_complete -eq $r.refused -or (!$r.refused -and !$r.map_complete) -or ($r.cap_refused -and !$r.refused)){
        throw 'Incoming arming/window/refusal flags contradict.'
    }
    if($r.refused){
        if($ExitCode -eq 0){throw 'Incoming refusal contradicts native exit zero.'}
        if($r.reason -isnot [string] -or [Text.Encoding]::UTF8.GetByteCount($r.reason) -gt 191){throw 'Bounded incoming refusal reason required.'}
    }elseif($null -ne $r.reason){throw 'Complete incoming window cannot carry a refusal reason.'}
    if($null -ne $r.ordinary_absence_scope -and ($r.ordinary_absence_scope -isnot [string] -or
       $r.ordinary_absence_scope -cnotin @('partial_or_refused_callback_window','not_observed_in_this_bounded_callback_window'))){throw 'Typed bounded incoming absence scope required.'}
    if($r.cases -isnot [array] -or $r.cases.Count -ne 4){throw 'Four ordered incoming capture slots required.'}
    for($i=0;$i -lt 4;$i++){
        $row=$r.cases[$i]
        Assert-T7CatalogueFields $row @('callback_ordinal','conflict_absence_proven','descriptor_admissible','effective_name','leading_comma_reference',
            'matching_events_in_phase','name_category','nonzero_descriptor_scalar_fields','phase','raw_name','repeated_headers_compared',
            'single_event_observed_in_phase','snapshot','state','unique_in_phase')
        $phase=if($i -lt 2){'bootstrap'}else{'map_load'};$category=if($i % 2 -eq 0){'reference'}else{'ordinary'}
        if($row.phase -isnot [string] -or $row.phase -cne $phase -or $row.name_category -isnot [string] -or $row.name_category -cne $category){throw 'Exact incoming capture slot order required.'}
        foreach($name in 'conflict_absence_proven','descriptor_admissible','repeated_headers_compared','single_event_observed_in_phase','unique_in_phase'){
            if($row.$name -isnot [bool]){throw 'Typed incoming case flags required.'}
        }
        if($row.conflict_absence_proven -or $row.descriptor_admissible -or $row.repeated_headers_compared){throw 'Incoming case cannot promote descriptor/conflict/comparison proof.'}
        foreach($name in 'raw_name','effective_name'){
            if($null -ne $row.$name -and ($row.$name -isnot [string] -or [Text.Encoding]::UTF8.GetByteCount($row.$name) -gt 129)){throw 'Typed bounded incoming names required.'}
        }
        if($null -ne $row.leading_comma_reference -and $row.leading_comma_reference -isnot [bool]){throw 'Typed nullable incoming reference flag required.'}
        foreach($pair in @(@('callback_ordinal',65537),@('nonzero_descriptor_scalar_fields',13))){
            if($null -ne $row.($pair[0]) -and !(Test-T7CatalogueInteger $row.($pair[0]) $pair[1])){throw 'Typed nullable incoming case counters required.'}
        }
        if(!(Test-T7CatalogueInteger $row.matching_events_in_phase 17) -or $row.state -isnot [string] -or
           $row.state -cnotin @('not_observed','target_matched_sample_refused','first_complete_sample','repeated_target_ambiguous')){throw 'Typed incoming case count/state required.'}
        if($null -ne $row.snapshot){
            $shot=$row.snapshot
            Assert-T7CatalogueFields $shot @('callback_header_name_rechecked','completed_header_bytes','copy_fault','header_copies','header_observed','header_rechecked','image','name_rechecked','reason','refused')
            foreach($name in 'callback_header_name_rechecked','copy_fault','header_observed','header_rechecked','name_rechecked','refused'){
                if($shot.$name -isnot [bool]){throw 'Typed incoming snapshot flags required.'}
            }
            if(!(Test-T7CatalogueInteger $shot.header_copies 2) -or ($null -ne $shot.completed_header_bytes -and !(Test-T7CatalogueInteger $shot.completed_header_bytes 528)) -or
               ($null -ne $shot.image -and $shot.image -isnot [pscustomobject]) -or
               ($null -ne $shot.reason -and ($shot.reason -isnot [string] -or [Text.Encoding]::UTF8.GetByteCount($shot.reason) -gt 255))){throw 'Typed bounded incoming snapshot fields required.'}
        }
    }
    $outcome=if($r.refused){'IncomingRecordRefused'}elseif($ExitCode -eq 0){'IncomingRecordCaptured'}else{'IncomingRecordFromFailedProcess'}
    [pscustomobject]@{Outcome=$outcome;Record=$r}
}
function Read-T7IncomingImageRecord($Plan,$State,$Context) {
    if($Context.Closed -isnot [bool] -or !$Context.Closed -or !$Context.Owner -or !$Context.Lease -or
       $State.TreeClosureConfirmed -isnot [bool] -or !$State.TreeClosureConfirmed -or
       $State.TerminationRequested -isnot [bool] -or $State.TerminationRequested -or $State.Quarantined -isnot [bool] -or $State.Quarantined){
        throw 'Original incoming job must close normally with admission retained.'
    }
    if(($State.ExitCode -isnot [int] -and $State.ExitCode -isnot [long]) -or $State.ExitCode -lt -2147483648L -or $State.ExitCode -gt 4294967295L){
        throw 'Typed original incoming native exit required before stdout read.'
    }
    $text=Read-T7ImageMetadataStdout $Plan $State $Context
    $result=ConvertFrom-T7IncomingImageRecord $text $State.ExitCode
    $State.SelectedIncomingObservation=[ordered]@{Schema='iw7.t7-incoming-image-header-observation/1';RecordPresent=($null -ne $result.Record);
        ConsumerSchema='iw7.t7-incoming-image-consumer/1';InterpretationPending=$true;DeepMetadataOutcome=$null;
        NativeExitCode=$State.ExitCode;DescriptorAdmissible=$false;QualifiedObjectMipCount=$null;PixelsCopied=$false;Ready=$false}
    $result.Outcome
}
