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
    if($marker.Schema -cne 'iw7.t7-incoming-image-proposal/1' -or $marker.SourceRevision -cne '4873ef4a4ce8478020d8533651f123f8feadfa95' -or
       $marker.NativeSchema -cne 'iw7.t7-incoming-image-header-observation/1'){throw 'Exact pending incoming Source basis required.'}
    $pin=$marker.Contract;Assert-T7CatalogueFields $pin @('Path','Bytes','SHA256')
    if($pin.Path -isnot [string] -or ![IO.Path]::IsPathFullyQualified($pin.Path) -or [IO.Path]::GetFullPath($pin.Path) -cne $pin.Path -or
       $pin.Path.StartsWith('\\') -or $pin.Path.Substring(2).Contains(':') -or $pin.Path -match '["\x00-\x1f]' -or
       [IO.Path]::GetFileName($pin.Path) -cne 'incoming-image-source-contract.json' -or
       !(Test-T7CatalogueInteger $pin.Bytes 8KB) -or $pin.Bytes -ne 4613 -or
       $pin.SHA256 -isnot [string] -or $pin.SHA256 -cne '1f672f51533f90ea10d396bd28a8298f6070d39df938b0bf4033c4754dc4659f'){
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
