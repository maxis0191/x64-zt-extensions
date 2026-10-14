# Source interface only. No actual full-CLI cohort has been qualified.
function Assert-T7ImageProvenanceSourceContract($Contract) {
    Assert-T7CatalogueFields $Contract @('schema','source_profile','files','main','cli')
    if($Contract.schema -isnot [string] -or $Contract.schema -cne 'iw7.t7-image-provenance-source/1' -or
       $Contract.source_profile -isnot [string] -or $Contract.source_profile -cne 't7-image-provenance-v1'){
        throw 'Exact image provenance source contract required.'
    }
    Assert-T7CatalogueFields $Contract.files @('selected_image_provenance.hpp','native_image_provenance.inc','selected_image_provenance_fixture.cpp')
    $sourcePins=@(
        @('selected_image_provenance.hpp',15069,'d8b3f07f787f03dbda7c0305e2aad685c131130fbe43a839145e869858925c16'),
        @('native_image_provenance.inc',1254,'360bcf806e2d69f3ecba2d2422b99c8c86a775397438117607115ed0d8b5573e'),
        @('selected_image_provenance_fixture.cpp',14626,'10d8c7508ceb49038f2432f6ed9ee2758deee2062f81643257c35ab77dd3f589'))
    foreach($row in $sourcePins){
        $item=$Contract.files.($row[0]);Assert-T7CatalogueFields $item @('lf_bytes','lf_sha256')
        if(!(Test-T7CatalogueInteger $item.lf_bytes 16KB) -or $item.lf_bytes -ne $row[1] -or
           $item.lf_sha256 -isnot [string] -or $item.lf_sha256 -cne $row[2]){throw 'Exact image provenance source pin required.'}
    }
    foreach($row in @(
        @('main',43370,'13052a66ba89d5e66253c6931b81cb120aaa5acac37d6a4b15ab57cac4c10900'),
        @('cli',130246,'15d03375dcd65f428ed10522ed238fe24c8ab407716780188ce341b87e1cbcf1'))){
        $item=$Contract.($row[0]);Assert-T7CatalogueFields $item @('bytes','sha256')
        if(!(Test-T7CatalogueInteger $item.bytes 128KB) -or $item.bytes -ne $row[1] -or
           $item.sha256 -isnot [string] -or $item.sha256 -cne $row[2]){throw 'Exact image provenance rendered source pair required.'}
    }
}
function Assert-T7ImageProvenanceSourcePlan($Plan) {
    if($Plan.Operation -isnot [string] -or $Plan.Operation -cne 'ImageProvenanceV1' -or
       $Plan.CandidateProfile -isnot [string] -or $Plan.CandidateProfile -cne 't7-image-provenance-v1' -or
       $Plan.Schema -isnot [string] -or $Plan.Schema -cne 'iw7.t7-image-provenance-source-plan/1'){
        throw 'Image provenance operation/profile/source schema must be paired.'
    }
    $marker=$Plan.SelectedImageProvenanceV1
    Assert-T7CatalogueFields $marker @('Schema','SourceRevision','Contract','NativeSchema')
    if($marker.Schema -isnot [string] -or $marker.Schema -cne 'iw7.t7-image-provenance-proposal/1' -or
       $marker.SourceRevision -isnot [string] -or $marker.SourceRevision -cne 'f2ee0df49352e8414c4998ea0e50657ad23cab82' -or
       $marker.NativeSchema -isnot [string] -or $marker.NativeSchema -cne 'iw7.t7-selected-image-provenance/1'){
        throw 'Exact pending image provenance source basis required.'
    }
    Assert-T7ImageProvenanceSourceContract $marker.Contract
    foreach($name in 'CandidateSource','CandidateBytes','CandidateSHA256','BuildPlan','BuildReceipt',
        'ExpectedBuildPlanSHA256','ExpectedBuildReceiptSHA256'){
        if(!$Plan.PSObject.Properties[$name] -or ![object]::ReferenceEquals($null,$Plan.$name)){
            throw 'Unqualified image provenance candidate and build fields must remain NULL.'
        }
    }
    foreach($name in 'SelectedMaterialPartsV1','ResidentSurfaceCountDiagnostic','ResidentMultiSurfaceV2',
        'SelectedMeshMaterialObservation','SelectedStreamedStaticV1','SelectedStreamedRenderOnlyV2',
        'SelectedXpakProvider','ExportRequest','ExportRequestFile','ZombiesObservationC','ZombiesAddObservationC2'){
        if($Plan.PSObject.Properties[$name]){throw 'Image provenance cannot select another operation or provider.'}
    }
    $expected=@('-t7-iw7-image-provenance-v1','mp_freerun_04','p7_fre_platform_cap_02','0')
    if($Plan.Arguments -isnot [array] -or $Plan.Arguments.Count -ne 4){throw 'Exact image provenance arguments required.'}
    for($i=0;$i -lt 4;$i++){
        if($Plan.Arguments[$i] -isnot [string] -or $Plan.Arguments[$i] -cne $expected[$i]){throw 'Exact image provenance arguments required.'}
    }
}
function Assert-T7ImageProvenanceOperationalGate {
    throw 'Image provenance awaits actual F53, merged source API and a qualified full-CLI CPP cohort; operational DEFAULT and Run are unavailable.'
}
