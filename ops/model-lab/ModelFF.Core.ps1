# No mutations/launch on import. Model wrapper uses existing transactions and NTFS identity.
function Assert-ModelFFDistanceCandidate($Metadata) {
    if(($Metadata.lod0_dist -isnot [int] -and $Metadata.lod0_dist -isnot [long] -and $Metadata.lod0_dist -isnot [double]) -or
        $Metadata.lod0_dist -ne 1000000 -or $Metadata.has_lods -isnot [bool] -or !$Metadata.has_lods -or
        $Metadata.shadow_cutoff_lod -ne 6 -or $Metadata.collision_lod -ne 255){throw 'Exact single-LOD distance candidate metadata required.'}
}
function Assert-ModelFFAssetName([string]$Name) {
    if($Name -cnotmatch '^[A-Za-z0-9_][A-Za-z0-9_./-]{0,254}$'){throw 'Portable Model Lab asset name required.'}
    foreach($part in $Name.Split('/')){
        if(!$part -or $part -in @('.','..') -or $part.EndsWith('.') -or $part -match '^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(?:\.|$)'){throw 'Unsafe Model Lab asset path.'}
    }
}
function Get-ModelFFRigidVersion($Metadata) {
    switch -CaseSensitive ($Metadata.geometry_profile) {
        't7-iw7-resident-static-v1' {return 1}
        't7-iw7-resident-static-v2' {return 2}
        't7-iw7-selected-streamed-static-v1' {return 2}
        't7-iw7-selected-streamed-render-only-v2' {return 2}
        default {throw 'Unknown resident geometry profile.'}
    }
}
function Get-ModelFFMaterials($Metadata) {
    if($Metadata.geometry_profile -ceq 'iw7-authored-rigid-v1'){return $Metadata.material_reference}
    if($Metadata.geometry_profile -ceq 'iw7-original-arena-rigid-v1'){return $Metadata.material_reference}
    if((Get-ModelFFRigidVersion $Metadata) -eq 2){$Metadata.material_references}else{$Metadata.material_reference}
}
function Assert-ModelFFOriginalArenaGeometry($Metadata) {
    if($Metadata.geometry_profile -cne 'iw7-original-arena-rigid-v1' -or $Metadata.origin -cne 'authored-arena' -or
        $Metadata.model_name -cne 'paris_original_arena' -or $Metadata.mesh_name -cne 'paris_original_arena_lod0' -or
        $Metadata.material_reference -cne 'mopw/character_park_clown_zombie_shoes'){throw 'Explicit original arena identity/material required.'}
    $counts=$Metadata.selected_counts
    if((@($counts.PSObject.Properties.Name | Sort-Object) -join ',') -cne 'bones,roots,surfaces,triangles,vertices'){throw 'Exact original arena count fields required.'}
    foreach($entry in @(@('bones',1,1),@('roots',1,1),@('surfaces',1,1),@('vertices',24,192),@('triangles',12,96))){
        $value=$counts.($entry[0])
        if(($value -isnot [int] -and $value -isnot [long]) -or $value -lt $entry[1] -or $value -gt $entry[2]){throw 'Original arena count outside small rigid profile.'}
    }
    if($counts.vertices % 24 -ne 0 -or $counts.triangles*2 -ne $counts.vertices){throw 'Original box topology counts differ.'}
}
function Assert-ModelFFOriginalArenaPlan($Plan) {
    Assert-ModelFFOriginalArenaGeometry $Plan
    Assert-ModelFFDistanceCandidate $Plan
    if($Plan.schema -cne 'iw7.model-ff-plan/1' -or $Plan.zone -cne 'paris_model_probe' -or $Plan.recipient -cne 'cp_zmb' -or
        $Plan.material_payload_copied -isnot [bool] -or $Plan.material_payload_copied -or
        $Plan.physics_serialized -isnot [bool] -or $Plan.physics_serialized){throw 'Original arena recipient/reference-only profile required.'}
}
function Assert-ModelFFRigidGeometry($Metadata) {
    $version=Get-ModelFFRigidVersion $Metadata
    $counts=$Metadata.selected_counts
    if((@($counts.PSObject.Properties.Name | Sort-Object) -join ',') -cne 'bones,roots,surfaces,triangles,vertices'){throw 'Exact resident count fields required.'}
    $maxSurfaces=if($version -eq 2){255}else{1}
    foreach($entry in @(@('bones',1,1),@('roots',1,1),@('surfaces',1,$maxSurfaces),@('vertices',3,(65535*$maxSurfaces)),@('triangles',1,(65535*$maxSurfaces)))){
        $value=$counts.($entry[0])
        if(($value -isnot [int] -and $value -isnot [long]) -or $value -lt $entry[1] -or $value -gt $entry[2]){throw 'Rigid geometry count outside resident profile.'}
    }
    if($version -eq 1){
        if($Metadata.material_reference -cne 'mopw/character_park_clown_zombie_shoes' -or
            @('surface_records','geometry_work_bytes_upper_bound','material_references' | Where-Object {$_ -cin $Metadata.PSObject.Properties.Name}).Count){throw 'Strict v1 material/surface profile required.'}
        return
    }
    if('material_reference' -cin $Metadata.PSObject.Properties.Name -or $Metadata.material_references -isnot [array] -or
        $Metadata.surface_records -isnot [array] -or $Metadata.material_references.Count -ne $counts.surfaces -or
        $Metadata.surface_records.Count -ne $counts.surfaces){throw 'Ordered v2 material/surface arrays required.'}
    [long]$vertices=0;[long]$triangles=0
    for($i=0;$i -lt $counts.surfaces;$i++){
        $record=$Metadata.surface_records[$i]
        if((@($record.PSObject.Properties.Name | Sort-Object) -join ',') -cne 'index,material_slot,triangles,vertices'){throw 'Exact surface record fields required.'}
        foreach($entry in @(@('index',$i,$i),@('material_slot',$i,$i),@('vertices',3,65535),@('triangles',1,65535))){
            $value=$record.($entry[0])
            if(($value -isnot [int] -and $value -isnot [long]) -or $value -lt $entry[1] -or $value -gt $entry[2]){throw 'Invalid ordered surface record.'}
        }
        if($Metadata.material_references[$i] -cne 'mopw/character_park_clown_zombie_shoes'){throw 'Unreviewed recipient material.'}
        $vertices+=$record.vertices;$triangles+=$record.triangles
    }
    # Includes the 96-byte T7 surface. Aliases count in full per logical slot.
    [long]$work=256+384*$counts.surfaces+60*$vertices+12*$triangles
    if($vertices -ne $counts.vertices -or $triangles -ne $counts.triangles -or $work -gt 16MB -or
        ($Metadata.geometry_work_bytes_upper_bound -isnot [int] -and $Metadata.geometry_work_bytes_upper_bound -isnot [long]) -or
        $Metadata.geometry_work_bytes_upper_bound -ne $work){throw 'Aggregate resident geometry work exceeds bound or differs.'}
}
function Assert-ModelFFRigidPlan($Plan) {
    Assert-ModelFFAssetName $Plan.model_name;Assert-ModelFFAssetName $Plan.mesh_name
    Assert-ModelFFRigidGeometry $Plan
    $version=Get-ModelFFRigidVersion $Plan
    if($Plan.schema -cne "iw7.model-ff-plan/$version" -or $Plan.zone -cne 'paris_model_probe' -or $Plan.recipient -cne 'cp_zmb' -or
        $Plan.material_payload_copied -isnot [bool] -or $Plan.material_payload_copied -or
        $Plan.has_lods -isnot [bool] -or !$Plan.has_lods -or $Plan.shadow_cutoff_lod -ne 6 -or $Plan.collision_lod -ne 255){throw 'Bounded rigid recipient/LOD profile required.'}
    if(($Plan.lod0_dist -isnot [int] -and $Plan.lod0_dist -isnot [long] -and $Plan.lod0_dist -isnot [double]) -or
        [double]::IsNaN($Plan.lod0_dist) -or [double]::IsInfinity($Plan.lod0_dist) -or $Plan.lod0_dist -gt [float]::MaxValue -or $Plan.lod0_dist -lt 256){
        throw 'LOD distance insufficient for this scene; review explicit --lod-distance 1000000. Export validity and visibility are separate.'}
}
function Get-ModelFFSourceNames($Plan) {
    if('geometry_profile' -cin $Plan.PSObject.Properties.Name -and $Plan.geometry_profile -ceq 'iw7-authored-rigid-v1'){
        Assert-ModelFFAuthoredPlan $Plan
        $Plan.artifact_paths
        @($Plan.source_files.PSObject.Properties.Name | Where-Object {$_ -cnotin $Plan.artifact_paths} | Sort-Object)
        return
    }
    if('geometry_profile' -cin $Plan.PSObject.Properties.Name){
        if($Plan.geometry_profile -ceq 'iw7-original-arena-rigid-v1'){Assert-ModelFFOriginalArenaPlan $Plan}
        else{Assert-ModelFFRigidPlan $Plan}
        "xmodel/$($Plan.model_name).xmb";"xsurface/$($Plan.mesh_name).xsb"
    }else{'xmodel/paris_model_probe.xmb';'xsurface/paris_model_probe_lod0.xsb'}
    'zone_source/paris_model_probe.csv';'zone_source/paris_model_probe_recipient.csv';'netconststrings/ncs_mdl_paris_model_probe.json'
}
function Assert-ModelFFAuthoredPlan($Plan) {
    Assert-ModelFFDistanceCandidate $Plan
    if($Plan.schema -cne 'iw7.model-ff-plan/3' -or $Plan.geometry_profile -cne 'iw7-authored-rigid-v1' -or
        $Plan.origin -cne 'authored-rigid' -or $Plan.recipient -cne 'cp_zmb' -or
        $Plan.material_payload_copied -isnot [bool] -or !$Plan.material_payload_copied -or
        $Plan.material_closure_verified -isnot [bool] -or $Plan.material_closure_verified -or
        $Plan.physics_serialized -isnot [bool] -or $Plan.physics_serialized){throw 'Explicit authored local-payload FF profile required.'}
    foreach($field in @('ff_built','pixels_verified','ready')){
        if($Plan.$field -isnot [bool] -or $Plan.$field){throw 'Authored preparation cannot claim FF/runtime qualification.'}
    }
    foreach($field in @('namespace','zone','model_name','mesh_name')){
        $value=$Plan.$field
        if($value -isnot [string] -or $value -cnotmatch '^[A-Za-z0-9_]{1,63}$'){throw 'Flat authored project identifiers required.'}
        Assert-ModelFFAssetName $value
    }
    if($Plan.ncs_name -cne ('ncs_mdl_'+$Plan.zone)){throw 'Authored NCS/zone identity differs.'}
    foreach($name in @($Plan.material_reference,$Plan.image.name,$Plan.ncs_name)){Assert-ModelFFAssetName $name}
    $counts=$Plan.selected_counts
    if((@($counts.PSObject.Properties.Name | Sort-Object) -join ',') -cne 'bones,roots,surfaces,triangles,vertices'){throw 'Exact authored geometry counts required.'}
    foreach($entry in @(@('bones',1,1),@('roots',1,1),@('surfaces',1,1),@('vertices',3,192),@('triangles',1,96))){
        $value=$counts.($entry[0])
        if(($value -isnot [int] -and $value -isnot [long]) -or $value -lt $entry[1] -or $value -gt $entry[2]){throw 'Authored geometry exceeds native reader envelope.'}
    }
    $paths=@("xmodel/$($Plan.model_name).xmb","xsurface/$($Plan.mesh_name).xsb")
    if($Plan.artifact_paths -isnot [array] -or $Plan.artifact_paths.Count -ne 2 -or ($Plan.artifact_paths -join '|') -cne ($paths -join '|')){throw 'Exact authored artifact paths required.'}
    $files=@($Plan.source_files.PSObject.Properties)
    if($files.Count -lt 8 -or $files.Count -gt 20){throw 'Bounded authored geometry/material source closure required.'}
    foreach($entry in $files){
        Assert-ModelFFAssetName $entry.Name
        if($entry.Value -isnot [string] -or $entry.Value -cnotmatch '^[a-f0-9]{64}$'){throw 'Authored source SHA256 required.'}
    }
    foreach($name in $paths+@("zone_source/$($Plan.zone).csv","zone_source/$($Plan.zone)_recipient.csv","netconststrings/$($Plan.ncs_name).json")){
        if($name -cnotin $files.Name){throw 'Authored source inventory incomplete.'}
    }
    foreach($field in @('writer_provenance_sha256','writer_sha256','geometry_source_sha256')){
        if($Plan.$field -isnot [string] -or $Plan.$field -cnotmatch '^[a-fA-F0-9]{64}$'){throw 'Bound authored writer/source hashes required.'}
    }
    if($Plan.dump_files -isnot [array] -or $Plan.dump_files.Count -lt 4 -or $Plan.dump_files.Count -gt 12 -or
        @($Plan.dump_files | Sort-Object -Unique).Count -ne $Plan.dump_files.Count){throw 'Exact bounded authored dump paths required.'}
    foreach($name in $Plan.dump_files){Assert-ModelFFAssetName $name}
    foreach($name in $paths+@("images/$($Plan.image.name).iw7Image","materials/$($Plan.material_reference).json")){
        if($name -cnotin $Plan.dump_files){throw 'Authored dump closure incomplete.'}
    }
    if($Plan.expected_inventory -isnot [array] -or $Plan.expected_inventory.Count -lt 7 -or $Plan.expected_inventory.Count -gt 262){throw 'Bounded authored inventory required.'}
    $rows=@(foreach($row in $Plan.expected_inventory){
        if($row.type -cnotin @('techset','image','material','xmodelsurfs','xmodel','netconststrings','rawfile') -or $row.name -isnot [string]){throw 'Authored inventory kind/name required.'}
        Assert-ModelFFAssetName $row.name.TrimStart(',')
        $row.type+','+$row.name
    })
    if(@($rows | Sort-Object -Unique).Count -ne $rows.Count -or ('material,'+$Plan.material_reference) -cnotin $rows -or ('material,,'+$Plan.material_reference) -cin $rows){throw 'Local authored material inventory required.'}
}
function Write-ModelFFState($State,[string]$Path) { $State | ConvertTo-Json -Depth 15 | Set-Content -LiteralPath $Path }
function Assert-ModelFFAuthorInputs($Inputs,[string]$ProjectSource) {
    if((@($Inputs.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'ProjectFiles,ProjectSource,Schema,SDKSourceWorkspace,Templates' -or
        $Inputs.Schema -cne 'iw7.authored-model-ff-author-inputs/1' -or $Inputs.ProjectSource -cne $ProjectSource){throw 'Explicit original Source project input metadata required.'}
    $files=@($Inputs.ProjectFiles.PSObject.Properties.Name)
    $scripts=@($files|Where-Object {$_ -cmatch '^[A-Za-z0-9_]+\.gsc$'})
    if($files.Count -ne 6 -or $scripts.Count -ne 1 -or
        @('README.md','authoring.json','color.rgba8.json','geometry.source.json','manifest.json'|Where-Object {$_ -cnotin $files}).Count){throw 'Six reviewed original project Source files required.'}
    if((@($Inputs.Templates.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'cbi,cbt,material,statebits,statebitsmap,stateinfo'){throw 'Six explicit Material C roles required.'}
    foreach($pin in @($Inputs.ProjectFiles.PSObject.Properties.Value)){
        if((@($pin.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'Bytes,SHA256' -or
            ($pin.Bytes -isnot [int] -and $pin.Bytes -isnot [long]) -or $pin.Bytes -lt 1 -or $pin.Bytes -gt 64KB -or
            $pin.SHA256 -isnot [string] -or $pin.SHA256 -cnotmatch '^[a-f0-9]{64}$'){throw 'Bounded original Source file pin required.'}
    }
    foreach($pin in @($Inputs.Templates.PSObject.Properties.Value)+@($Inputs.SDKSourceWorkspace)){
        if((@($pin.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'Bytes,Path,SHA256' -or
            $pin.Path -isnot [string] -or ![IO.Path]::IsPathFullyQualified($pin.Path) -or [IO.Path]::GetFullPath($pin.Path) -cne $pin.Path -or
            ($pin.Bytes -isnot [int] -and $pin.Bytes -isnot [long]) -or $pin.Bytes -lt 1 -or $pin.Bytes -gt 1MB -or
            $pin.SHA256 -isnot [string] -or $pin.SHA256 -cnotmatch '^[a-f0-9]{64}$'){throw 'Finite template/SDK metadata without historical identities required.'}
    }
    if([IO.Path]::GetFileName($Inputs.SDKSourceWorkspace.Path) -cne 'source-workspace.json'){throw 'Existing SDK Source workspace receipt required.'}
}
function Get-ModelFFAuthorStageArguments([string]$ToolsRoot,[string]$Project,[string]$Writer,[string]$Output) {
    # Direct call to SDK31's existing API. No new serializer, script file or CLI.
    $code=@'
import hashlib, importlib.util, json, sys
from pathlib import Path
tools, project, writer, output = map(Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location('sdk_author_stage', tools / 'sdk/modding/creator_authoring.py')
author = importlib.util.module_from_spec(spec)
spec.loader.exec_module(author)
sdk = author.module(tools / 'sdk/modding/manifest.py', 'sdk_stage_manifest')
manifest = sdk.load_manifest(project / 'manifest.json')
contract = sdk.validate(manifest, stage='plan')
if not contract['valid']: raise ValueError(json.dumps(contract['errors']))
report = author.stage_ff_inputs(project, writer, output, tools, manifest=manifest)
plan_path = output / 'model-ff-plan.json'
plan_bytes = plan_path.read_bytes()
report['source_plan_file'] = {'path': str(plan_path), 'bytes': len(plan_bytes), 'sha256': hashlib.sha256(plan_bytes).hexdigest()}
print(json.dumps(report, sort_keys=True, allow_nan=False), flush=True)
'@
    @('-B','-S','-c',$code,$ToolsRoot,$Project,$Writer,$Output)
}
function Get-ModelFFAuthoredStockInputs($Descriptor,[string]$StockRoot) {
    # Names and declared tool/sentinel digests only. The caller obtains all
    # current retail identities/content under its one original admission.
    if((@($Descriptor.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'Schema,Sentinel,SourceRoot,TLS' -or
        $Descriptor.Schema -cne 'iw7.authored-model-ff-main-stock/1' -or $Descriptor.SourceRoot -cne $StockRoot){
        throw 'Explicit current Main authored stock descriptor required.'
    }
    if(![IO.Path]::IsPathFullyQualified($StockRoot) -or [IO.Path]::GetFullPath($StockRoot) -cne $StockRoot){throw 'Canonical Main source root required.'}
    foreach($role in 'TLS','Sentinel'){
        $pin=$Descriptor.$role
        if((@($pin.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'Bytes,Path,SHA256' -or
            $pin.Path -isnot [string] -or ![IO.Path]::IsPathFullyQualified($pin.Path) -or [IO.Path]::GetFullPath($pin.Path) -cne $pin.Path -or
            ($pin.Bytes -isnot [int] -and $pin.Bytes -isnot [long]) -or $pin.Bytes -lt 1 -or
            $pin.SHA256 -isnot [string] -or $pin.SHA256 -cnotmatch '^[a-f0-9]{64}$'){
            throw 'Explicit tool/sentinel metadata without historical file identities required.'
        }
    }
    if($Descriptor.TLS.Bytes -gt 16MB -or $Descriptor.Sentinel.Bytes -gt 4096 -or
        [IO.Path]::GetFileName($Descriptor.TLS.Path) -cne 'tlsdll.dll' -or
        [IO.Path]::GetFileName($Descriptor.Sentinel.Path) -cne 'fileSysCheck.cfg'){throw 'Finite TLS and independent copied sentinel required.'}
    $ff=@('code_post_gfx','code_pre_gfx','common_core_mp','common_cp','common_mp','common','cp_zmb',
        'global_core_mp','global_cp','global_mp','global',
        'patch_code_post_gfx','patch_code_pre_gfx','patch_common_core_mp','patch_common_cp','patch_common_mp','patch_common','patch_cp_zmb',
        'patch_global_core_mp','patch_global_cp','patch_global_mp','patch_global',
        'techsets_common_core_mp','techsets_common_cp','techsets_common_mp','techsets_common','techsets_cp_zmb',
        'techsets_global_core_mp','techsets_global_cp','techsets_global_mp','techsets_global')
    $rows=[Collections.Generic.List[object]]::new()
    foreach($name in $ff){foreach($folder in 'main','zone'){
        $rows.Add([pscustomobject]@{Relative=($folder+'/'+$name+'.ff');Source=(Join-Path $StockRoot ($name+'.ff'));Mode='HardLink'})
    }}
    foreach($index in @(1,17,19,21,25,26,36,37,52,53,68,69,84,85,100,101,116,117,132,133,148,149,164,165,180,181,196,197,212,213,228,229,244)){
        $name='assetfile'+$index+'.pak'
        $rows.Add([pscustomobject]@{Relative=('zone/'+$name);Source=(Join-Path $StockRoot $name);Mode='HardLink'})
    }
    foreach($name in @('iw7_ship.exe','amd_ags_x64.dll','bink2w64.dll','d3dcompiler_46.dll','steam_api.dll','steam_api64.dll','Steam.dll')){
        $rows.Add([pscustomobject]@{Relative=$name;Source=(Join-Path $StockRoot $name);Mode='Copy'})
    }
    foreach($role in 'TLS','Sentinel'){
        $pin=$Descriptor.$role;$relative=if($role -ceq 'TLS'){'tlsdll.dll'}else{'main/fileSysCheck.cfg'}
        $rows.Add([pscustomobject]@{Relative=$relative;Source=$pin.Path;Mode='Copy';DeclaredBytes=$pin.Bytes;DeclaredSHA256=$pin.SHA256})
    }
    if($rows.Count -ne 104 -or @($rows|Where-Object Mode -CEQ HardLink).Count -ne 95 -or
        @($rows|Where-Object Mode -CEQ Copy).Count -ne 9){throw 'Exact authored 104-alias Main/fixed33 profile required.'}
    $rows.ToArray()
}
function Open-ModelFFStockPin($Pin,[Collections.Generic.List[IDisposable]]$Guards,[switch]$Measure) {
    # Only the explicit authored retail-stock role uses this streaming bound.
    # H1's generic 64 MiB input policy is intentionally unchanged.
    Assert-H1Path $Pin.Path
    if(($Pin.Bytes -isnot [int] -and $Pin.Bytes -isnot [long]) -or $Pin.Bytes -lt 1 -or $Pin.Bytes -gt 16GB -or
        $Pin.SHA256 -isnot [string] -or (!$Measure -and $Pin.SHA256 -cnotmatch '^[a-f0-9]{64}$') -or
        ($Pin.SHA256 -and $Pin.SHA256 -cnotmatch '^[a-f0-9]{64}$')){throw 'Finite authored stock byte pin required.'}
    $stream=[IO.FileStream]::new($Pin.Path,'Open','Read','Read')
    $Guards.Add($stream) # Retain the actual handle before length/hash can fail.
    if($stream.Length -ne $Pin.Bytes){throw 'Authored stock stream size differs.'}
    $actual=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($stream)).ToLowerInvariant()
    $stream.Position=0
    if($Pin.SHA256 -and $actual -cne $Pin.SHA256){throw 'Authored stock stream content differs.'}
    if($Measure){$Pin.SHA256=$actual}
}
function Assert-ModelFFVacant([string]$Work) {
    foreach($p in @(Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^(iw7|zonetool).*\.exe$'})) {
        if($p.ExecutablePath -and ([IO.Path]::GetFullPath($p.ExecutablePath)).StartsWith($Work+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Model tool work directory remains occupied; retain inputs and reservation.'}
    }
}
function Assert-ModelFFInputs($Inputs,[string]$Work,[switch]$SourceOnly) {
    foreach($entry in $Inputs){
        $null=Resolve-IW7BasePath (Split-Path $entry.Source -Parent) (Split-Path $entry.Source -Leaf)
        $file=Get-Item -LiteralPath $entry.Source
        if($file.Length -ne $entry.Bytes -or $file.LastWriteTimeUtc.Ticks -ne ([datetimeoffset]$entry.ModifiedUtc).UtcDateTime.Ticks -or
            [int]$file.Attributes -ne $entry.Attributes -or [IW7HudFileIdentity]::Read($entry.Source) -cne $entry.SourceId){throw 'Stock source identity/size/time/attributes changed; restoration refused.'}
        if(!$SourceOnly){
            $target=Resolve-IW7BasePath $Work $entry.Relative
            if('TargetId' -cnotin $entry.PSObject.Properties.Name){if(Test-Path -LiteralPath $target){throw 'Unrecorded staged input exists; retain reservation.'};continue}
            if([IW7HudFileIdentity]::Read($target) -cne $entry.TargetId -or ($entry.Mode -eq 'HardLink' -and (Get-Item -LiteralPath $target).Length -ne $entry.Bytes)){throw 'Owned input identity/size changed; restoration refused.'}
        }
    }
}
function Complete-ModelFFRestore($State,[string]$StatePath,[string]$LeaseToken,[scriptblock]$BeforeReleaseCheck=$null) {
    try {
        Assert-ModelFFVacant $State.Work
        Assert-ModelFFInputs $State.Inputs $State.Work
        Restore-IW7BaseTransaction $State.Transaction
        Assert-ModelFFInputs $State.Inputs $State.Work -SourceOnly
        $State.Restored=$true;$State.StockPreserved=$true;$State.RestorationStatus='Confirmed'
        Write-ModelFFState $State $StatePath
        if($BeforeReleaseCheck){& $BeforeReleaseCheck}
    } catch {
        $State.RestorationStatus='Refused';$State.CleanupError=$_.Exception.Message
        Write-ModelFFState $State $StatePath
        throw
    }
    # Release follows both restore and source-final proof, never from finally.
    Exit-IW7ResourceLease -Token $LeaseToken
    $State.RetainedLeaseToken=$null;Write-ModelFFState $State $StatePath
}
function Get-ModelFFInventory([string]$Log,[string]$ModelName='paris_model_probe',[string]$MeshName='paris_model_probe_lod0',[string[]]$Materials=@('mopw/character_park_clown_zombie_shoes'),$AuthoredPlan=$null) {
    Assert-ModelFFAssetName $ModelName;Assert-ModelFFAssetName $MeshName
    $zone=if($null -ne $AuthoredPlan){Assert-ModelFFAuthoredPlan $AuthoredPlan;$AuthoredPlan.zone}else{'paris_model_probe'}
    if(!$Log.Contains('Loading zone "'+$zone+'"') -or $Log -match 'could not be found|Could not find referenced|\[ ERROR \]|\[ FATAL \]'){throw 'Bootstrap inventory unavailable/recipient reference unresolved.'}
    $rows=@(foreach($line in @($Log -split '\r?\n' | Where-Object {$_ -match 'Loading asset '})){
        if($line -notmatch 'Loading asset "([^"\r\n]+)" of type ([a-z0-9]+)\.$'){throw 'Malformed model inventory callback.'}
        $Matches[2]+','+$Matches[1]
    })
    if($null -ne $AuthoredPlan){$expected=@($AuthoredPlan.expected_inventory | ForEach-Object {$_.type+','+$_.name})}
    else{
        if(!$Materials.Count -or $Materials.Count -gt 255 -or @($Materials | Where-Object {$_ -cne 'mopw/character_park_clown_zombie_shoes'}).Count){throw 'Explicit reviewed material inventory required.'}
        $expected=@(@($Materials | Select-Object -Unique | ForEach-Object {'material,,'+$_}) + @("xmodelsurfs,$MeshName","xmodel,$ModelName",'netconststrings,ncs_mdl_paris_model_probe','rawfile,paris_model_probe'))
    }
    if($rows.Count -ne $expected.Count -or @($rows | Sort-Object -Unique).Count -ne $expected.Count -or @($expected | Where-Object {$_ -cnotin $rows}).Count){throw 'Expected exact assets including unique recipient references.'}
    $rows
}

function Get-ModelFFOutputRelative($Value) {
    if($Value -isnot [string] -or !$Value -or $Value.Length -gt 1024 -or
       [IO.Path]::IsPathRooted($Value) -or $Value -match '[\\:<>"|?*\x00-\x1f]' -or
       ($Value.Split('/')).Count -gt 16){throw 'Literal relative ModelFF output path required.'}
    foreach($part in $Value.Split('/')){
        if(!$part -or $part -in @('.','..') -or $part.TrimEnd(' ','.') -cne $part -or
           $part -match '^(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)'){
            throw 'Canonical ModelFF output path components required.'
        }
    }
    $Value
}

function New-ModelFFOutputNamespace([string]$RunRoot,[string]$SourceRoot,[string]$Zone,
    [object[]]$DeclaredFiles) {
    # This constructor consumes reviewed Source declarations only. It never
    # discovers files, reads payloads or derives a limit from an observed run.
    if(![IO.Path]::IsPathFullyQualified($RunRoot) -or ![IO.Path]::IsPathFullyQualified($SourceRoot) -or
       $Zone -cnotmatch '^[A-Za-z0-9_]{1,63}$' -or !$DeclaredFiles.Count -or $DeclaredFiles.Count -gt 1024){throw 'Bounded pre-run ModelFF namespace declarations required.'}
    $root=[IO.Path]::GetFullPath($RunRoot).TrimEnd('\','/')
    $source=[IO.Path]::GetFullPath($SourceRoot).TrimEnd('\','/')
    if(![IO.Path]::IsPathFullyQualified($root)){throw 'ModelFF RunRoot must be an operation directory, not a volume root.'}
    if(!$source.StartsWith($root+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){
        throw 'Deferred ModelFF Source must remain inside the globally counted RunRoot.'
    }
    $sourceRelative=Get-ModelFFOutputRelative ([IO.Path]::GetRelativePath($root,$source).Replace('\','/'))
    if($sourceRelative.Split('/')[0] -in @('work','author-project','roundtrip','backup') -or
       $sourceRelative.Split('/')[0] -like 'owned-*'){throw 'ModelFF Source scope overlaps another output role.'}
    $files=[Collections.Generic.Dictionary[string,bool]]::new([StringComparer]::OrdinalIgnoreCase)
    $dirs=[Collections.Generic.Dictionary[string,bool]]::new([StringComparer]::OrdinalIgnoreCase)
    $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($raw in $DeclaredFiles){
        $path=Get-ModelFFOutputRelative $raw
        if(!$seen.Add($path)){throw 'Duplicate ModelFF namespace declaration.'}
        if(!$path.StartsWith($sourceRelative+'/',[StringComparison]::OrdinalIgnoreCase) -and
           $path -notmatch '^(author-project|work|roundtrip|backup)/'){
            throw 'Declared ModelFF file is outside its known operation scopes.'
        }
        $files.Add($path,$true)
    }
    $receipts=@('authored-native-run.json','authored-closure.json')
    $known=@('state.local.json','mod.ff','assets.csv','geometry-roundtrip.json','surface-roundtrip.json',
        'backup/recovery.local.json',($sourceRelative+'/model-ff-plan.json'),('work/zone/'+$Zone+'.ff'))
    foreach($phase in @('authored-stage','authored-source','hud-build','hud-offline','hud-roundtrip','model-geometry','model-authored-material')){
        foreach($stream in @('stdout.log','stderr.log')){$known+=('owned-'+$phase+'/'+$stream)}
    }
    foreach($name in $receipts){$known+=$name;$known+=$name.Replace('.json','.pending.json')}
    foreach($path in $known){if(!$files.ContainsKey($path)){$files.Add($path,$true)}}
    foreach($leaf in @($files.Keys)){
        $parent=$leaf
        while($parent.Contains('/')){
            $parent=$parent.Substring(0,$parent.LastIndexOf('/'))
            if(!$dirs.ContainsKey($parent)){$dirs.Add($parent,$true)}
        }
    }
    foreach($path in $dirs.Keys){if($files.ContainsKey($path)){throw 'ModelFF path cannot be both a file and a directory.'}}
    $values=[Collections.Generic.Dictionary[string,object]]::new([StringComparer]::Ordinal)
    $values.Add('Schema','iw7.model-ff-output-namespace/1');$values.Add('RunRoot',$root)
    $values.Add('SourceRelative',$sourceRelative)
    $values.Add('Files',[Collections.ObjectModel.ReadOnlyDictionary[string,bool]]::new($files))
    $values.Add('Directories',[Collections.ObjectModel.ReadOnlyDictionary[string,bool]]::new($dirs))
    $values.Add('EntryLimit',($files.Count+$dirs.Count))
    $values.Add('ReceiptNames',[Collections.ObjectModel.ReadOnlyCollection[string]]::new([string[]]$receipts))
    [Collections.ObjectModel.ReadOnlyDictionary[string,object]]::new($values)
}

function Measure-ModelFFOutputNamespace($Namespace,[string]$Root,[long]$MaximumBytes=268435456) {
    if($Namespace -isnot [Collections.ObjectModel.ReadOnlyDictionary[string,object]] -or
       $Namespace.Schema -cne 'iw7.model-ff-output-namespace/1' -or $MaximumBytes -lt 1 -or $MaximumBytes -gt 256MB -or
       ![IO.Path]::IsPathFullyQualified($Root) -or
       [IO.Path]::GetFullPath($Root).TrimEnd('\','/') -ine $Namespace.RunRoot){throw 'Exact sealed global ModelFF output scope required.'}
    for($part=$Namespace.RunRoot;$part;$part=[IO.Path]::GetDirectoryName($part)){
        if(([IO.File]::GetAttributes($part) -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'ModelFF output reparse ancestry refused.'}
    }
    $pending=[Collections.Generic.Stack[string]]::new();$pending.Push($Namespace.RunRoot)
    $bytes=0L;$count=0;$fileCount=0;$dirCount=0
    while($pending.Count){
        foreach($entry in [IO.Directory]::EnumerateFileSystemEntries($pending.Pop())){
            if(++$count -gt $Namespace.EntryLimit){throw 'ModelFF output entry count exceeds its declared namespace.'}
            $attributes=[IO.File]::GetAttributes($entry)
            if($attributes -band [IO.FileAttributes]::ReparsePoint){throw 'ModelFF output reparse entry refused before descent.'}
            $relative=[IO.Path]::GetRelativePath($Namespace.RunRoot,$entry).Replace('\','/')
            if($attributes -band [IO.FileAttributes]::Directory){
                if(!$Namespace.Directories.ContainsKey($relative)){throw 'Unexpected ModelFF output directory.'}
                $dirCount++;$pending.Push($entry)
            }else{
                if(!$Namespace.Files.ContainsKey($relative)){throw 'Unexpected ModelFF output file.'}
                $length=([IO.FileInfo]$entry).Length
                if($length -lt 0 -or $length -gt $MaximumBytes-$bytes){throw 'Global ModelFF output byte allowance exceeded.'}
                $bytes+=$length;$fileCount++
            }
        }
    }
    [pscustomobject]@{Bytes=$bytes;Entries=$count;Files=$fileCount;Directories=$dirCount;EntryLimit=$Namespace.EntryLimit}
}

function New-ModelFFOutputNamespaceCounter($Namespace) {
    if($Namespace -isnot [Collections.ObjectModel.ReadOnlyDictionary[string,object]] -or
       $Namespace.Schema -cne 'iw7.model-ff-output-namespace/1'){throw 'Pre-run sealed ModelFF namespace required for counter closure.'}
    $sealedModelFFNamespace=$Namespace
    $modelFFMeasureImplementation=(Get-Command Measure-ModelFFOutputNamespace).ScriptBlock
    {param([string]$Root,[long]$MaximumBytes=268435456)
        (& $modelFFMeasureImplementation $sealedModelFFNamespace $Root $MaximumBytes).Bytes
    }.GetNewClosure()
}
