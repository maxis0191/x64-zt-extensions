[CmdletBinding()]
param()
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
. (Join-Path $PSScriptRoot 'T7MaterialParts.Profile.ps1')
. (Join-Path $PSScriptRoot 'T7CatalogueHost.Core.ps1')
# These fixtures exercise real validators only; no runner, native owner or asset.
function Assert-H1Path($Path){if($Path -isnot [string] -or !$Path.StartsWith('C:\')){throw 'Authored canonical path required'}}
$checks=0
function Check($Value,[string]$Message){if(!$Value){throw $Message};$script:checks++}
function Refuses([scriptblock]$Action,[string]$Message){$bad=$false;try{$null=& $Action}catch{$bad=$true};Check $bad $Message}
function Copy-Authored($Value){$Value|ConvertTo-Json -Depth 25|ConvertFrom-Json -Depth 25}
function Report-Text($Value){'T7_SELECTED_MATERIAL_PARTS_METADATA '+($Value|ConvertTo-Json -Depth 20 -Compress)+"`n"}
$physical=@(for($i=0;$i -lt 4;$i++){
    [ordered]@{index=$i;declared_active=$true;level_count_and_size_u32=32;level_count_raw=1;pixel_size_raw=2;
        width=64;height=64;xpak_key_hex='0000000000000000';opaque_descriptor_words_hex=@('0000000000000000','0000000000000001','0000000000000002');
        descriptor_field_semantics_verified=$false;payload_bytes_read=0}
})
$report=[ordered]@{schema='iw7.t7-selected-material-observation/3';pixels_copied=$false;ready=$false;
    allocation_retained=$false;atomic_snapshot_proven=$false;model='p7_fre_platform_cap_02';lod=0;slot=0;
    headers_rechecked=$true;stream_parts_headers_rechecked=$true;stream_parts_header_copies=2;
    image_selection=@{mode='exact_binding_stream_parts';index=4;expected_nameHash=2695565377L};
    textures=@(@{index=4;nameHash=2695565377L;image_header_read=$true;image_read_state='observed';image_name='authored_image';image=@{
        streamed_part_count=4;stream_part_count_in_bounds=$true;format_field_width_runtime_verified=$false;
        format_raw_u32=71;format_raw_byte0=71;streamed_parts=$physical}})}
Check ((ConvertFrom-T7MaterialPartsReport (Report-Text $report) 0).Outcome -ceq 'PartsMetadataObserved') 'Authored positive report refused'
foreach($case in @('schema','pixels','ready','atomic','allocation','model','slot','lod','recheck','partrecheck','copies','namehasharray','selectionhash','selectionindex','texturesobject','texturehash','textureindex','headerread','readstate','partcount','fivephysical','partindex','active','payload','semantics','key32','opaque32','wordtype','formatverified','formatbyte','rawnegative')){
    $p=Copy-Authored $report
    switch($case){
        schema {$p.schema='iw7.t7-selected-material-observation/2'}
        pixels {$p.pixels_copied=$true}
        ready {$p.ready=$true}
        atomic {$p.atomic_snapshot_proven=$true}
        allocation {$p.allocation_retained=$true}
        model {$p.model=@('p7_fre_platform_cap_02')}
        slot {$p.slot=1}
        lod {$p.lod='0'}
        recheck {$p.headers_rechecked=$false}
        partrecheck {$p.stream_parts_headers_rechecked=1}
        copies {$p.stream_parts_header_copies=3}
        namehasharray {$p.image_selection.expected_nameHash=@(2695565377L)}
        selectionhash {$p.image_selection.expected_nameHash=4}
        selectionindex {$p.image_selection.index=0}
        texturesobject {$p.textures=$p.textures[0]}
        texturehash {$p.textures[0].nameHash=@(2695565377L)}
        textureindex {$p.textures[0].index=3}
        headerread {$p.textures[0].image_header_read='true'}
        readstate {$p.textures[0].image_read_state='unread'}
        partcount {$p.textures[0].image.streamed_part_count=5}
        fivephysical {$p.textures[0].image.streamed_parts+=@($p.textures[0].image.streamed_parts[0])}
        partindex {$p.textures[0].image.streamed_parts[1].index=0}
        active {$p.textures[0].image.streamed_parts[0].declared_active=$false}
        payload {$p.textures[0].image.streamed_parts[0].payload_bytes_read=1}
        semantics {$p.textures[0].image.streamed_parts[0].descriptor_field_semantics_verified=$true}
        key32 {$p.textures[0].image.streamed_parts[0].xpak_key_hex='a0ab1041'}
        opaque32 {$p.textures[0].image.streamed_parts[0].opaque_descriptor_words_hex[0]='a0ab1041'}
        wordtype {$p.textures[0].image.streamed_parts[0].opaque_descriptor_words_hex[0]=0}
        formatverified {$p.textures[0].image.format_field_width_runtime_verified=$true}
        formatbyte {$p.textures[0].image.format_raw_byte0=72}
        rawnegative {$p.textures[0].image.streamed_parts[0].pixel_size_raw=-1}
    }
    Refuses {ConvertFrom-T7MaterialPartsReport (Report-Text $p) 0} "Invalid report accepted: $case"
}
Refuses {ConvertFrom-T7MaterialPartsReport ((Report-Text $report)+(Report-Text $report)) 0} 'Duplicate metadata record accepted'
Refuses {ConvertFrom-T7MaterialPartsReport 'No metadata record' 0} 'Missing record accepted'
Refuses {ConvertFrom-T7MaterialPartsReport (Report-Text $report) 1} 'Nonzero successful-report exit accepted'
$refused=Copy-Authored $report;$refused|Add-Member NoteProperty refused $true
Check ((ConvertFrom-T7MaterialPartsReport (Report-Text $refused) 1).Outcome -ceq 'PartsMetadataRefused') 'Refused diagnostic lost'
Refuses {ConvertFrom-T7MaterialPartsReport (Report-Text $refused) 0} 'Refused report with zero exit accepted'
$refused.refused='true';Refuses {ConvertFrom-T7MaterialPartsReport (Report-Text $refused) 1} 'Untyped refusal accepted'

$marker=[ordered]@{Schema='iw7.t7-material-parts-probe/1'}
$bindings=@()
foreach($row in @(
    @('SourceManifest',331468,'ed972cfad8de6985b9c307f65b56a0fe03de6cba442e590eebdddb0b7869db28'),
    @('HostWitness',606,'9b1879b319d5acf9cbdfaa47322e57bc36f9cc05bb8a2a87dc9ef4e38a5ac061'),
    @('ClosureWitness',1264,'9018cc01cf90db101b291f56affa99c376a22e9adccdde7d8651bb61762c623c'),
    @('PartsHeader',8380,'f2dbec9ad952978ef5d88dafd608a0aef6417fd649b0f04fa7088732c822fbb5'),
    @('PartsEntry',2589,'dd1ed27601e23ba3eace1115b84cfa7c85404497451b8a41eb194e6df9764f4c'),
    @('PartsContract',838,'b01c9c8f57816b26a8a09b72e2799cda5858083bde4a332fdb7d8ed5ccb89e9e'))){
    $pin=[ordered]@{Path=('C:\authored\'+$row[0]);Bytes=$row[1];SHA256=$row[2]};$marker[$row[0]]=$pin
    $bindings+=@([ordered]@{Path=$pin.Path;Bytes=$pin.Bytes;SHA256=$pin.SHA256;IsText=$true})
}
foreach($row in @(@('BuildPlan',372668,'cfeb5610dd5322d9137eaa9804590cf023a865236a1132e95e354919ef23084e'),@('BuildReceipt',25651,'e81604ea36272540d2a62df7aaa236dcdd92bb0d04821ab9b2f887636a074a25'))){
    $bindings+=@([ordered]@{Path=('C:\authored\'+$row[0]);Bytes=$row[1];SHA256=$row[2];IsText=$true})
}
$plan=[ordered]@{Operation='MaterialPartsV1';CandidateProfile='t7-material-parts-v1';SelectedMaterialPartsV1=$marker;
    BootstrapPolicy='QualifiedCollectionV3';Bootstraps=@(1..23);SharedQualification=@{};
    Arguments=@('-t7-iw7-material-parts-v1','mp_freerun_04','p7_fre_platform_cap_02','0');OutputKey='t7_iw7_material_parts_v1';ReportLimitBytes=65536;
    TraceStderrLimitBytes=16384;CandidateBytes=21963264;CandidateSHA256='cce8bbb8f068b4897a391880db316bd1d7586f26f7ec0c1cee2316d76c8644b3';
    ExpectedBuildPlanSHA256='cfeb5610dd5322d9137eaa9804590cf023a865236a1132e95e354919ef23084e';ExpectedBuildReceiptSHA256='e81604ea36272540d2a62df7aaa236dcdd92bb0d04821ab9b2f887636a074a25';
    BuildPlan='C:\authored\BuildPlan';BuildReceipt='C:\authored\BuildReceipt';Bindings=$bindings;InputMetadata=@()}
$p=Copy-Authored $plan;$null=Assert-T7MaterialPartsPlan $p;$checks++
Check ((Get-T7CatalogueHostSchema $p 'run') -ceq 'iw7.t7-material-parts-run/1') 'Parts host schema lost'
Check ((Get-T7CatalogueHostOutcomeName $p) -ceq 'PartsOutcome') 'Parts host outcome lost'
foreach($case in @('operation','profile','legacy-bootstrap','missing-bootstrap','markerextra','mixedexport','extraargument','lodarray','name','candidate','planhash','receipthash','bindingpath','bindingsha','bindingbytes','pinpath','pinsha','duplicatebinding','missingbinding','metadataarray')){
    $p=Copy-Authored $plan
    switch($case){
        operation {$p.Operation='Catalogue'}
        profile {$p.CandidateProfile=@('t7-material-parts-v1')}
        legacy-bootstrap {$p.BootstrapPolicy='Legacy'}
        missing-bootstrap {$p.Bootstraps=@(1..22)}
        markerextra {$p.SelectedMaterialPartsV1|Add-Member NoteProperty Extra 1}
        mixedexport {$p|Add-Member NoteProperty ExportRequest @{} }
        extraargument {$p.Arguments+=@('streamed-request.json')}
        lodarray {$p.Arguments[3]=@('0')}
        name {$p.Arguments[2]='another_model'}
        candidate {$p.CandidateSHA256='f'*64}
        planhash {$p.ExpectedBuildPlanSHA256='f'*64}
        receipthash {$p.ExpectedBuildReceiptSHA256='f'*64}
        bindingpath {$p.Bindings[0].Path=@($p.Bindings[0].Path)}
        bindingsha {$p.Bindings[0].SHA256=@($p.Bindings[0].SHA256)}
        bindingbytes {$p.Bindings[0].Bytes='331468'}
        pinpath {$p.SelectedMaterialPartsV1.SourceManifest.Path=@($p.SelectedMaterialPartsV1.SourceManifest.Path)}
        pinsha {$p.SelectedMaterialPartsV1.SourceManifest.SHA256=@($p.SelectedMaterialPartsV1.SourceManifest.SHA256)}
        duplicatebinding {$p.Bindings+=@($p.Bindings[0])}
        missingbinding {$p.Bindings=@($p.Bindings|Select-Object -Skip 1)}
        metadataarray {$p.InputMetadata=@([pscustomobject]@{Path=@('C:\authored\input')})}
    }
    Refuses {Assert-T7MaterialPartsPlan $p} "Invalid parts plan accepted: $case"
}
Refuses {Read-T7MaterialPartsReport $null $null ([pscustomobject]@{Closed=$false;Lease=$null})} 'Unclosed metadata read accepted'
Refuses {Read-T7MaterialPartsReport $null $null ([pscustomobject]@{Closed=$true;Lease=$null})} 'Unadmitted metadata read accepted'
[pscustomobject]@{Schema='iw7.t7-material-parts-recipient-source-tests/1';Checks=$checks;Passed=$true;NativeExecuted=$false;OpaqueRead=$false;LeaseAcquired=$false}|ConvertTo-Json -Compress
