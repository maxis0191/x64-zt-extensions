# Finite E/G3 metadata adapter. Native ownership, aliases and teardown stay in H1.
function Test-T7MaterialPartsPlan($Plan) {
    [bool]($Plan.PSObject.Properties['SelectedMaterialPartsV1'] -or
        ($Plan.PSObject.Properties['Operation'] -and $Plan.Operation -ceq 'MaterialPartsV1') -or
        ($Plan.PSObject.Properties['CandidateProfile'] -and $Plan.CandidateProfile -ceq 't7-material-parts-v1'))
}
function Assert-T7MaterialPartsPlan($Plan) {
    if(!(Test-T7MaterialPartsPlan $Plan)){return}
    if($Plan.Operation -isnot [string] -or $Plan.Operation -cne 'MaterialPartsV1' -or
       $Plan.CandidateProfile -isnot [string] -or $Plan.CandidateProfile -cne 't7-material-parts-v1'){
        throw 'Parts operation/profile/marker must be paired.'
    }
    if($Plan.BootstrapPolicy -isnot [string] -or $Plan.BootstrapPolicy -cne 'QualifiedCollectionV3' -or
       $Plan.Bootstraps -isnot [array] -or $Plan.Bootstraps.Count -ne 23 -or !$Plan.PSObject.Properties['SharedQualification']){
        throw 'Parts requires the explicit 23-member qualified V3 collection.'
    }
    $marker=$Plan.SelectedMaterialPartsV1
    Assert-T7CatalogueFields $marker @('Schema','SourceManifest','HostWitness','ClosureWitness','PartsHeader','PartsEntry','PartsContract')
    if($marker.Schema -isnot [string] -or $marker.Schema -cne 'iw7.t7-material-parts-probe/1'){
        throw 'Exact parts metadata marker required.'
    }
    foreach($name in 'ResidentSurfaceCountDiagnostic','ResidentMultiSurfaceV2','SelectedMeshMaterialObservation',
        'SelectedStreamedStaticV1','SelectedStreamedRenderOnlyV2','SelectedXpakProvider','ExportRequest',
        'ExportRequestFile','ZombiesObservationC','ZombiesAddObservationC2'){
        if($Plan.PSObject.Properties[$name]){throw 'Parts cannot select an export, provider or another observation.'}
    }
    $arguments=@('-t7-iw7-material-parts-v1','mp_freerun_04','p7_fre_platform_cap_02','0')
    if(@($Plan.Arguments).Count -ne 4){throw 'Exact four parts arguments required.'}
    for($i=0;$i -lt 4;$i++){
        if($Plan.Arguments[$i] -isnot [string] -or $Plan.Arguments[$i] -cne $arguments[$i]){throw 'Exact selected parts command required.'}
    }
    if($Plan.OutputKey -isnot [string] -or $Plan.OutputKey -cne 't7_iw7_material_parts_v1' -or
       !(Test-T7CatalogueInteger $Plan.ReportLimitBytes 65536) -or $Plan.ReportLimitBytes -ne 65536 -or
       !(Test-T7CatalogueInteger $Plan.TraceStderrLimitBytes 16384) -or $Plan.TraceStderrLimitBytes -ne 16384 -or
       !(Test-T7CatalogueInteger $Plan.CandidateBytes 64MB) -or $Plan.CandidateBytes -ne 21963264 -or $Plan.CandidateSHA256 -isnot [string] -or
       $Plan.CandidateSHA256 -cne 'cce8bbb8f068b4897a391880db316bd1d7586f26f7ec0c1cee2316d76c8644b3' -or
       $Plan.ExpectedBuildPlanSHA256 -isnot [string] -or $Plan.ExpectedBuildPlanSHA256 -cne 'cfeb5610dd5322d9137eaa9804590cf023a865236a1132e95e354919ef23084e' -or
       $Plan.ExpectedBuildReceiptSHA256 -isnot [string] -or $Plan.ExpectedBuildReceiptSHA256 -cne 'e81604ea36272540d2a62df7aaa236dcdd92bb0d04821ab9b2f887636a074a25'){
        throw 'Exact closed E candidate and metadata-only bounds required.'
    }
    foreach($pin in $Plan.Bindings){
        if($pin.Path -isnot [string] -or $pin.SHA256 -isnot [string] -or $pin.IsText -isnot [bool] -or
           !(Test-T7CatalogueInteger $pin.Bytes ([long]::MaxValue)) -or $pin.Bytes -le 0){throw 'Scalar typed parts binding required.'}
    }
    foreach($name in 'BuildPlan','BuildReceipt'){if($Plan.$name -isnot [string]){throw 'Scalar build text path required.'}}
    foreach($item in $Plan.InputMetadata){if($item.Path -isnot [string]){throw 'Scalar parts input metadata path required.'}}
    $specs=@(
        @($Plan.BuildPlan,372668,'cfeb5610dd5322d9137eaa9804590cf023a865236a1132e95e354919ef23084e'),
        @($Plan.BuildReceipt,25651,'e81604ea36272540d2a62df7aaa236dcdd92bb0d04821ab9b2f887636a074a25'))
    foreach($row in $specs){
        $pin=[pscustomobject]@{Path=$row[0];Bytes=$row[1];SHA256=$row[2]}
        Assert-T7CatalogueTextPin $pin $Plan.Bindings
    }
    foreach($row in @(
        @('SourceManifest',331468,'ed972cfad8de6985b9c307f65b56a0fe03de6cba442e590eebdddb0b7869db28'),
        @('HostWitness',606,'9b1879b319d5acf9cbdfaa47322e57bc36f9cc05bb8a2a87dc9ef4e38a5ac061'),
        @('ClosureWitness',1264,'9018cc01cf90db101b291f56affa99c376a22e9adccdde7d8651bb61762c623c'),
        @('PartsHeader',8380,'f2dbec9ad952978ef5d88dafd608a0aef6417fd649b0f04fa7088732c822fbb5'),
        @('PartsEntry',2589,'dd1ed27601e23ba3eace1115b84cfa7c85404497451b8a41eb194e6df9764f4c'),
        @('PartsContract',838,'b01c9c8f57816b26a8a09b72e2799cda5858083bde4a332fdb7d8ed5ccb89e9e'))){
        $pin=$marker.($row[0])
        if($pin.Path -isnot [string] -or $pin.SHA256 -isnot [string] -or
           !(Test-T7CatalogueInteger $pin.Bytes 1MB) -or $pin.Bytes -ne $row[1] -or $pin.SHA256 -cne $row[2]){
            throw 'Exact E source/closure pin required.'
        }
        Assert-T7CatalogueTextPin $pin $Plan.Bindings
    }
}
function Assert-T7MaterialPartsBuild($Plan,$Receipt) {
    Assert-T7MaterialPartsPlan $Plan
    # All these texts have been opened by the runner's existing read guards.
    $build=Read-H1SmallJson $Plan.BuildPlan 1MB
    $manifest=Read-H1SmallJson $Plan.SelectedMaterialPartsV1.SourceManifest.Path 1MB
    $host=Read-H1SmallJson $Plan.SelectedMaterialPartsV1.HostWitness.Path 4096
    $closure=Read-H1SmallJson $Plan.SelectedMaterialPartsV1.ClosureWitness.Path 8192
    if($build.BuildProfile.Name -cne 't7-material-parts-v1' -or $build.SourceCommit -cne 'fab935826c898806855376662a8a03317b3ad8f1' -or
       $manifest.revisions.'x64-zt-extensions' -cne 'a8ecff7cb61323cd0e6f75d10e596d55e63a7753' -or
       $host.Host.PID -ne 16544 -or $host.Parent.PID -ne 9964 -or $host.WrapperRun -isnot [bool] -or $host.WrapperRun -or
       $closure.OriginalSession -ne 16448 -or $closure.TruePTYChunk -cne '8dd283' -or
       !(Test-T7CatalogueInteger $closure.TruePTYExitCode 0) -or @($closure.OwnedProcesses).Count -or @($closure.Leases).Count -or
       @($Receipt.Stages).Count -ne 3 -or (@($Receipt.Stages.Name)-join ',') -cne 'main,zonetool11,link'){
        throw 'Exact E source and original-host closure required.'
    }
    foreach($stage in $Receipt.Stages){
        if(!(Test-T7CatalogueInteger $stage.ExitCode 0) -or $stage.TreeClosureConfirmed -isnot [bool] -or !$stage.TreeClosureConfirmed -or
           $stage.CompilerTelemetry.Completed -isnot [bool] -or !$stage.CompilerTelemetry.Completed -or
           !(Test-T7CatalogueInteger $stage.CompilerTelemetry.AfterStop.ActiveProcesses 0)){
            throw 'Closed original compiler and telemetry jobs required.'
        }
    }
    foreach($name in 'Wiring','PreparedMain','BaseBuildPlan','BaseBuildReceipt','LinkResponse'){
        Assert-T7CatalogueTextPin $build.BuildProfile.$name $Plan.Bindings
    }
    $dependencies=@($Receipt.Stages[0].Artifacts|Where-Object {[IO.Path]::GetFileName($_.Path) -ceq 'dependencies.json'})
    if($dependencies.Count -ne 1){throw 'Exact original main dependency text required.'}
    Assert-T7CatalogueTextPin $dependencies[0] $Plan.Bindings
}
function ConvertFrom-T7MaterialPartsReport([string]$Text,[int]$ExitCode) {
    $matches=[regex]::Matches($Text,'(?m)^.*?T7_SELECTED_MATERIAL_PARTS_METADATA (\{[^\r\n]*\})\r?$')
    if($matches.Count -ne 1 -or [Text.Encoding]::UTF8.GetByteCount($matches[0].Groups[1].Value) -gt 65536){
        throw 'One bounded selected parts metadata record required.'
    }
    $report=$matches[0].Groups[1].Value|ConvertFrom-Json -Depth 20
    if($report -isnot [pscustomobject] -or $report.schema -isnot [string] -or $report.schema -cne 'iw7.t7-selected-material-observation/3'){
        throw 'Exact G3 metadata schema required.'
    }
    foreach($name in 'pixels_copied','ready','allocation_retained','atomic_snapshot_proven'){
        if($report.$name -isnot [bool] -or $report.$name){throw 'Metadata-only G3 assertions required.'}
    }
    if($report.PSObject.Properties['refused']){
        if($report.refused -isnot [bool]){throw 'Typed G3 refusal required.'}
        if($report.refused){if($ExitCode -eq 0){throw 'Refused observation cannot have successful native exit.'};return [pscustomobject]@{Outcome='PartsMetadataRefused';Metadata=$report}}
    }
    if($ExitCode -ne 0 -or $report.model -isnot [string] -or $report.model -cne 'p7_fre_platform_cap_02' -or
       !(Test-T7CatalogueInteger $report.lod 0) -or !(Test-T7CatalogueInteger $report.slot 0) -or
       $report.headers_rechecked -isnot [bool] -or !$report.headers_rechecked -or
       $report.stream_parts_headers_rechecked -isnot [bool] -or !$report.stream_parts_headers_rechecked -or
       !(Test-T7CatalogueInteger $report.stream_parts_header_copies 2) -or $report.stream_parts_header_copies -ne 2 -or
       $report.image_selection.mode -isnot [string] -or $report.image_selection.mode -cne 'exact_binding_stream_parts' -or
       !(Test-T7CatalogueInteger $report.image_selection.index 4) -or $report.image_selection.index -ne 4 -or
       !(Test-T7CatalogueInteger $report.image_selection.expected_nameHash 4294967295) -or $report.image_selection.expected_nameHash -ne 2695565377){
        throw 'Exact selected/rechecked G3 observation required.'
    }
    if($report.textures -isnot [array]){throw 'Texture metadata array required.'}
    $selected=@($report.textures|Where-Object {(Test-T7CatalogueInteger $_.index 4) -and $_.index -eq 4})
    if($selected.Count -ne 1 -or !(Test-T7CatalogueInteger $selected[0].nameHash 4294967295) -or $selected[0].nameHash -ne 2695565377 -or $selected[0].image_header_read -isnot [bool] -or
       !$selected[0].image_header_read -or $selected[0].image_read_state -cne 'observed' -or $selected[0].image_name -isnot [string] -or
       $selected[0].image_name.Length -le 0 -or $selected[0].image_name.Length -ge 256){
        throw 'One observed selected image required.'
    }
    $image=$selected[0].image
    if(!(Test-T7CatalogueInteger $image.streamed_part_count 4) -or $image.stream_part_count_in_bounds -isnot [bool] -or !$image.stream_part_count_in_bounds -or
       $image.format_field_width_runtime_verified -isnot [bool] -or $image.format_field_width_runtime_verified -or
       !(Test-T7CatalogueInteger $image.format_raw_u32 4294967295) -or !(Test-T7CatalogueInteger $image.format_raw_byte0 255) -or
       ($image.format_raw_u32 -band 255) -ne $image.format_raw_byte0 -or
       $image.streamed_parts -isnot [array] -or @($image.streamed_parts).Count -ne 4){throw 'Four physical descriptors and raw format fields required.'}
    for($i=0;$i -lt 4;$i++){
        $part=$image.streamed_parts[$i]
        if(!(Test-T7CatalogueInteger $part.index 3) -or $part.index -ne $i -or $part.declared_active -isnot [bool] -or
           $part.declared_active -ne ($i -lt $image.streamed_part_count) -or
           $part.descriptor_field_semantics_verified -isnot [bool] -or $part.descriptor_field_semantics_verified -or
           !(Test-T7CatalogueInteger $part.payload_bytes_read 0) -or $part.xpak_key_hex -isnot [string] -or
           $part.xpak_key_hex -cnotmatch '\A[0-9a-f]{16}\z' -or @($part.opaque_descriptor_words_hex).Count -ne 3){throw 'Exact physical part metadata required.'}
        foreach($name in 'level_count_and_size_u32','level_count_raw','pixel_size_raw','width','height'){
            if(!(Test-T7CatalogueInteger $part.$name 4294967295)){throw 'Unsigned raw descriptor scalar required.'}
        }
        foreach($word in $part.opaque_descriptor_words_hex){if($word -isnot [string] -or $word -cnotmatch '\A[0-9a-f]{16}\z'){throw 'Canonical opaque descriptor word required.'}}
    }
    [pscustomobject]@{Outcome='PartsMetadataObserved';Metadata=$report}
}
function Read-T7MaterialPartsReport($Plan,$State,$Context) {
    if(!$Context.Closed -or !$Context.Lease){throw 'Original job must be closed with admission retained before metadata reads.'}
    $path=Join-Path $Plan.StageRoot 'stdout.log';Assert-H1Path $path
    $stream=[IO.FileStream]::new($path,'Open','Read','Read')
    try{
        if($stream.Length -le 0 -or $stream.Length -gt $Plan.LogLimitBytes){throw 'Bounded metadata stdout required.'}
        $sha=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($stream)).ToLowerInvariant()
        $pin=[pscustomobject]@{Path=$path;Bytes=$stream.Length;SHA256=$sha};$stream.Position=0
        $reader=[IO.StreamReader]::new($stream,[Text.Encoding]::UTF8,$true,4096,$true)
        try{$text=$reader.ReadToEnd()}finally{$reader.Dispose()}
        $Context.Guards.Add($stream);$stream=$null;$State.Report=$pin
    }finally{if($stream){$stream.Dispose()}}
    $result=ConvertFrom-T7MaterialPartsReport $text $State.ExitCode
    # Keep the complete bounded record in guarded stdout. The receipt carries
    # only the selected image, avoiding an entire material table in its reserve.
    $metadata=$result.Metadata
    if($result.Outcome -ceq 'PartsMetadataObserved'){
        $selected=@($metadata.textures|Where-Object {$_.index -eq 4})[0]
        $State.SelectedPartsMetadata=[ordered]@{Schema=$metadata.schema;Model=$metadata.model;LOD=$metadata.lod;Slot=$metadata.slot;
            Selection=$metadata.image_selection;ImageName=$selected.image_name;Image=$selected.image;
            HeadersRechecked=$metadata.headers_rechecked;StreamHeadersRechecked=$metadata.stream_parts_headers_rechecked;
            HeaderCopies=$metadata.stream_parts_header_copies;PixelsCopied=$false;Ready=$false;AllocationRetained=$false;AtomicSnapshotProven=$false}
    }else{$State.SelectedPartsMetadata=[ordered]@{Schema=$metadata.schema;Refused=$true;PixelsCopied=$false;Ready=$false}}
    $result.Outcome
}
