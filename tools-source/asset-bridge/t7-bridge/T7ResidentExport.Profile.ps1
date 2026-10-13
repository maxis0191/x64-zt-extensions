# One observed donor, existing native resident-only exporter. No process/lease owner here.
function Assert-T7ResidentExportRequest($Request) {
    Assert-T7CatalogueFields $Request @('schema','target','profile','zone','model','lod')
    foreach($field in 'schema','target','profile','zone','model'){
        if($Request.$field -isnot [string]){throw 'Only the observed scalar string request is allowed.'}
    }
    if($Request.schema -cne 'iw7.t7-iw7-resident-model-request/1' -or $Request.target -cne 'iw7' -or
       $Request.profile -cne 'resident-rigid-one-lod' -or $Request.zone -cne 'mp_freerun_04' -or
       $Request.model -cne 'p7_fre_platform_cap_02' -or !(Test-T7CatalogueInteger $Request.lod 0)){
        throw 'Only the observed platform donor at LOD zero is allowed.'
    }
}
function Get-T7ResidentExportKey($Request) {
    Assert-T7ResidentExportRequest $Request
    $bytes=[Text.Encoding]::ASCII.GetBytes(($Request.zone+"`n"+$Request.model+"`n0"))
    't7_iw7_'+[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant()
}
function Assert-T7ResidentExportName($Name) {
    if($Name -isnot [string] -or $Name -cnotmatch '\A[\x20-\x7e]{1,255}\z' -or
       $Name.StartsWith(',') -or $Name -match '[:<>"|?*]'){throw 'Unsafe export asset name.'}
    foreach($part in ($Name -split '[/\\]')){
        if(!$part -or $part -in @('.','..') -or $part -match '[. ]$' -or
           $part.Split('.')[0].TrimEnd(' ') -match '^(CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|CLOCK\$|COM[0-9]|LPT[0-9])$'){
            throw 'Unsafe export path component.'
        }
    }
}
function Get-T7ResidentExportDiagnostic($Plan) {
    if(!$Plan.PSObject.Properties['ResidentSurfaceCountDiagnostic']){return $null}
    $diagnostic=$Plan.ResidentSurfaceCountDiagnostic
    Assert-T7CatalogueFields $diagnostic @('Schema','Header')
    if((Get-T7CatalogueOperation $Plan) -cne 'ResidentExportV1' -or
       $Plan.CandidateProfile -cne 't7-catalog-message-publication' -or
       $diagnostic.Schema -isnot [string] -or $diagnostic.Schema -cne 'iw7.t7-resident-surface-count-diagnostic/1'){
        throw 'Explicit resident surface-count diagnostic contract required.'
    }
    Assert-T7CatalogueTextPin $diagnostic.Header $Plan.Bindings
    if($diagnostic.Header.Bytes -ne 13545 -or
       $diagnostic.Header.SHA256 -cne '701e3d1eccb0e98ecccfd2012215aaf7eff8db7bd974b184e86648a138b6e3c3'){
        throw 'Exact surface-count diagnostic header required.'
    }
    $build=@($Plan.Bindings|Where-Object {$_.Path -ceq $Plan.BuildPlan -and $_.IsText -is [bool] -and $_.IsText})
    if($build.Count -ne 1 -or $build[0].Bytes -ne 303182 -or
       $Plan.ExpectedBuildPlanSHA256 -cne '4bfb8c9aa45352b0e99acc0a66eab8df93eec8bcac15b9443b766e01a8fcb9e6' -or
       $build[0].SHA256 -cne $Plan.ExpectedBuildPlanSHA256){throw 'Exact approved diagnostic build plan required.'}
    $receipt=@($Plan.Bindings|Where-Object {$_.Path -ceq $Plan.BuildReceipt -and $_.IsText -is [bool] -and $_.IsText})
    if($receipt.Count -ne 1 -or $receipt[0].Bytes -ne 22393 -or
       $Plan.ExpectedBuildReceiptSHA256 -cne '6cc2cab523115defa9ee0df2a9c5292a286236ce96d935fb374145a663510810' -or
       $receipt[0].SHA256 -cne $Plan.ExpectedBuildReceiptSHA256){throw 'Exact closed diagnostic build receipt required.'}
    $diagnostic
}
function Assert-T7ResidentExportDiagnosticBuild($Plan,$Receipt,$Build) {
    # Called after the existing publication build qualifier. All reads are guarded
    # source/dependency JSON; the real link artifact tuple is receipt metadata only.
    $diagnostic=Get-T7ResidentExportDiagnostic $Plan
    if(!$diagnostic -or !$Build.ReuseCompile.PSObject.Properties['ResidentSurfaceCountDiagnostic']){
        throw 'Explicit resident surface-count diagnostic contract and reuse proof required.'
    }
    $header=$diagnostic.Header
    if($header.Path -cne (Join-Path $Build.PreparedRoot 't7_iw7_resident_model.hpp')){throw 'Diagnostic prepared header path differs.'}
    Assert-T7CatalogueTextPin $header $Build.Bindings
    $old=[pscustomobject]@{Path=(Join-Path (Split-Path $Build.ReuseCompile.SourcePlan -Parent) 'prepared/t7_iw7_resident_model.hpp');
        Bytes=13444;SHA256='6d2da3d4f7c3d0686909dc488f3d176ee2dd250e8d43d9a3cd9bcfa701482777'}
    Assert-T7CatalogueTextPin $old $Build.Bindings
    $proof=$Build.ReuseCompile.ResidentSurfaceCountDiagnostic
    Assert-T7CatalogueFields $proof @('Header','PreviousSHA256','SHA256','DependencyJSON','E7ReadSHA256','E7CompileSHA256','E7LinkSHA256','E7TranslationUnits','E7Objects')
    if($proof.Header -cne 'prepared/t7_iw7_resident_model.hpp' -or $proof.PreviousSHA256 -cne $old.SHA256 -or
       $proof.SHA256 -cne $header.SHA256 -or
       $proof.E7ReadSHA256 -cne 'd9cdd533796a9fe14e0d5140d8adcbf5cbc932fafd4c06e18a615d15199a2185' -or
       $proof.E7CompileSHA256 -cne 'a7083ce5b9ba2fe1421c4f8733cf1d1e0b286549dbc55a44f3ef30ceb3c05333' -or
       $proof.E7LinkSHA256 -cne '70455d2f32a9b034dda20fbaf48443ee68a02e552381edbf88b19d219f1f66b2' -or
       !(Test-T7CatalogueInteger $proof.E7TranslationUnits 413) -or $proof.E7TranslationUnits -ne 413 -or
       !(Test-T7CatalogueInteger $proof.E7Objects 413) -or $proof.E7Objects -ne 413 -or
       $proof.DependencyJSON -isnot [array] -or $proof.DependencyJSON.Count -ne 3){throw 'Exact diagnostic reuse proof required.'}
    $specs=@(@('helper',16296,'6897d27e8fe0754509e52258082d6178c8cb74fe21a8ef4b006006e97ab9dd12'),
        @('zonetool11',76744,'cfe62be9ce9bf87abd8e6713f1e1f334d76f69472500d2cb260696de26ee8273'),
        @('xpak',64444,'3d742923def4fb049d82853ac0e776ffd071228deaf1da1a624603d10dfd3908'))
    for($i=0;$i -lt 3;$i++){
        $pin=$proof.DependencyJSON[$i];Assert-T7CatalogueTextPin $pin $Build.Bindings
        if($pin.Path -cne (Join-Path (Split-Path $Build.ReuseCompile.Receipt -Parent) ($specs[$i][0]+'/dependencies.json')) -or
           $pin.Bytes -ne $specs[$i][1] -or $pin.SHA256 -cne $specs[$i][2]){throw 'Diagnostic reuse dependency pin differs.'}
    }
    $depPath=Join-Path $Build.RunRoot 'zonetool11/dependencies.json'
    $dep=@($Receipt.Stages[1].Artifacts|Where-Object Path -CEQ $depPath)
    if($dep.Count -ne 1){throw 'Diagnostic CLI dependency artifact required.'}
    Assert-T7CatalogueTextPin $dep[0] $Plan.Bindings
    $doc=Read-H1SmallJson $depPath 1MB
    $includes=$doc.Data.Includes
    if($includes -isnot [array] -or $includes.Count -lt 1 -or $includes.Count -gt 4096){throw 'Bounded diagnostic CLI includes required.'}
    $matches=@(foreach($path in $includes){
        if($path -isnot [string] -or ![IO.Path]::IsPathFullyQualified($path) -or $path -match '[\x00\r\n]' -or
           '..' -cin ($path -split '[/\\]')){throw 'Absolute diagnostic CLI include required.'}
        if([IO.Path]::GetFileName($path) -ieq 't7_iw7_resident_model.hpp'){[IO.Path]::GetFullPath($path)}
    })
    if($matches.Count -ne 1 -or $matches[0] -ine $header.Path){throw 'CLI dependencies must include the exact diagnostic header once.'}
}
function Assert-T7ResidentExportDiagnosticMetadata($Plan,$Base) {
    $old=@($Base.InputMetadata);$current=@($Plan.InputMetadata)
    if($old.Count -ne 27 -or $current.Count -ne 27 -or
       @($old|Where-Object Path -CEQ $Base.CandidateSource).Count -ne 1 -or
       @($current|Where-Object Path -CEQ $Plan.CandidateSource).Count -ne 1){throw 'Exact diagnostic candidate metadata row required.'}
    for($i=0;$i -lt 27;$i++){
        if($old[$i].Path -ceq $Base.CandidateSource){
            Assert-T7CatalogueFields $current[$i] @($old[$i].PSObject.Properties.Name)
            if($old[$i].Bytes -ne $Base.CandidateBytes -or $current[$i].Path -cne $Plan.CandidateSource -or
               $current[$i].Bytes -ne $Plan.CandidateBytes){throw 'Diagnostic candidate metadata differs.'}
        }elseif(($old[$i]|ConvertTo-Json -Depth 20 -Compress) -cne ($current[$i]|ConvertTo-Json -Depth 20 -Compress)){
            throw 'Qualified source inputs changed: noncandidate InputMetadata'
        }
    }
}
function Assert-T7ResidentExportPlan($Plan,[string]$Repo) {
    Assert-T7ResidentExportRequest $Plan.ExportRequest
    $diagnostic=Get-T7ResidentExportDiagnostic $Plan
    if((Get-T7CatalogueBootstrapPolicy $Plan) -cne 'QualifiedCollectionV3' -or
       $Plan.EngineOutputProfile -cne 'ObservedStartupManifestA' -or
       $Plan.CandidateProfile -cne 't7-catalog-message-publication' -or
       (!$diagnostic -and ($Plan.CandidateBytes -ne 21751296 -or $Plan.CandidateSHA256 -cne '31b9d908d15fb5f0bf17a7b27309dc7183458d5e586dfc6e427cc8ec2b3fa647')) -or
       @(Get-T7CatalogueBootstraps $Plan).Count -ne 23 -or
       $Plan.OutputKey -cne (Get-T7ResidentExportKey $Plan.ExportRequest) -or
       @($Plan.Arguments).Count -ne 4 -or (@($Plan.Arguments) -join '|') -cne '-t7-iw7-model|mp_freerun_04|p7_fre_platform_cap_02|0' -or
       $Plan.ExportModelLimitBytes -ne 1MB -or $Plan.ExportMeshLimitBytes -ne 16MB -or $Plan.ReportLimitBytes -ne 4KB){
        throw 'Exact resident export candidate, request and output limits required.'
    }
    foreach($name in 'SourceCataloguePlan','SourceCatalogueReceipt','SourceCatalogue'){
        Assert-T7CatalogueTextPin $Plan.$name $Plan.Bindings
        $cap=if($name -ceq 'SourceCatalogue'){512KB}else{128KB}
        if($Plan.$name.Bytes -gt $cap){throw 'Source catalogue evidence exceeds bound.'}
    }
    foreach($spec in @(@('SourceCataloguePlan',59287,'718829c910020e96b94f59bf504a2ba318bcdd4f2baa80e0bc8a82526631a0d0'),
        @('SourceCatalogueReceipt',35780,'7347a78280abc12eedd8e5f02ff536e0c411cae2264bc7b50101136aac2a717e'),
        @('SourceCatalogue',1669,'d27e34f0f42ac8ccb2b675d4295b397e42636261213c149eaff942e7a7867e3f'))){
        if($Plan.($spec[0]).Bytes -ne $spec[1] -or $Plan.($spec[0]).SHA256 -cne $spec[2]){throw 'Exact observed catalogue F evidence required.'}
    }
    Assert-T7CatalogueTextPin $Plan.ExportRequestFile $Plan.Bindings
    if($Plan.ExportRequestFile.Bytes -gt 4KB){throw 'Export request exceeds bound.'}
    $expected=@((Join-Path $Repo 'tools-source/asset-bridge/t7-iw7/readback.py'),
        (Join-Path $Repo 'tools-source/asset-bridge/t7-iw7/boot_contract.py'),
        (Join-Path $Repo 'tools-source/asset-bridge/t7-iw7/export_contract.py'),
        (Join-Path $Repo 'tools-source/asset-bridge/h1-fixture/inspect_fixture.py'))
    if(@($Plan.ReadbackSources).Count -ne 4 -or @($Plan.ReadbackSources.Path|Sort-Object -Unique).Count -ne 4){throw 'Four independent reader source pins required.'}
    foreach($pin in $Plan.ReadbackSources){
        if($pin.Path -cnotin $expected){throw 'Unexpected independent reader source.'}
        Assert-T7CatalogueTextPin $pin $Plan.Bindings
    }
}
function Assert-T7ResidentExportCatalogue($Plan) {
    # Caller retains every text binding before these reads. No stock read or new qualification.
    $base=Read-H1SmallJson $Plan.SourceCataloguePlan.Path 128KB
    $receipt=Read-H1SmallJson $Plan.SourceCatalogueReceipt.Path 128KB
    $catalogue=Read-H1SmallJson $Plan.SourceCatalogue.Path 512KB
    $request=Read-H1SmallJson $Plan.ExportRequestFile.Path 4KB
    Assert-T7ResidentExportRequest $request
    if(($request|ConvertTo-Json -Compress) -cne ($Plan.ExportRequest|ConvertTo-Json -Compress)){throw 'Standalone export request differs.'}
    if($base.Schema -cne 'iw7.t7-catalogue-plan/1' -or $receipt.Schema -cne 'iw7.t7-catalogue-run/1' -or
       $receipt.PlanSHA256 -cne $Plan.SourceCataloguePlan.SHA256 -or $receipt.Status -cne 'CatalogueObservedPendingDonorReview' -or
       $receipt.ExitCode -ne 0 -or $receipt.CatalogueOutcome -cne 'CatalogueWithNames' -or
       $receipt.Quarantined -isnot [bool] -or $receipt.Quarantined){throw 'Closed successful source catalogue required.'}
    foreach($flag in 'TreeClosureConfirmed','LeaseReleased','InputsReverified','EngineOutputsValidated','OriginalInputMetadataUnchanged','AliasesRetained'){
        if($receipt.$flag -isnot [bool] -or !$receipt.$flag){throw 'Source catalogue closure proof missing.'}
    }
    foreach($field in 'Path','Bytes','SHA256'){
        if($receipt.Report.$field -cne $Plan.SourceCatalogue.$field){throw 'Catalogue report pin differs from source receipt.'}
    }
    $fields=@('CandidateSource','CandidateBytes','CandidateSHA256','EngineSource','SteamSource','Zone','Bootstraps','SharedQualification','InputMetadata')
    if(Get-T7ResidentExportDiagnostic $Plan){
        Assert-T7ResidentExportDiagnosticMetadata $Plan $base
        $fields=@('EngineSource','SteamSource','Zone','Bootstraps','SharedQualification')
    }
    foreach($field in $fields){
        if(($base.$field|ConvertTo-Json -Depth 20 -Compress) -cne ($Plan.$field|ConvertTo-Json -Depth 20 -Compress)){
            throw ('Qualified source inputs changed: '+$field)
        }
    }
    if((Get-T7CatalogueOutcome $catalogue 0) -cne 'CatalogueWithNames'){throw 'Source catalogue is not qualified.'}
    $rows=@($catalogue.models|Where-Object name -CEQ $Plan.ExportRequest.model)
    if($rows.Count -ne 1 -or $rows[0].reference -or !$rows[0].resolved_nondefault -or
       $rows[0].counts.bones -ne 1 -or $rows[0].counts.roots -ne 1 -or $rows[0].counts.cosmetic_bones -ne 0 -or $rows[0].counts.lods -ne 1){
        throw 'Exact observed nondefault one-root one-LOD donor required.'
    }
}
function Assert-T7ResidentExportManifest($Manifest,$Plan) {
    Assert-T7ResidentExportRequest $Plan.ExportRequest
    $falseFields=@('zonetool_xpak_helper_reads_allowed','engine_io_verified','dependency_payloads_verified',
        'asset_zone_ownership_verified','serialized_parse_verified','runtime_verified','ready')
    Assert-T7CatalogueFields $Manifest (@('schema','requested_zone','source_model','selected_source_lod','output_model_name',
        'output_mesh_name','output_root_key','target','profile','geometry_profile','root_bone_name','selected_counts','material_dependencies','model','mesh')+$falseFields)
    foreach($field in 'schema','requested_zone','source_model','output_model_name','output_root_key','target','profile','geometry_profile'){
        if($Manifest.$field -isnot [string]){throw 'Export manifest scalar string required.'}
    }
    if($Manifest.schema -cne 'iw7.t7-iw7-resident-export/1' -or $Manifest.target -cne 'iw7' -or
       $Manifest.profile -cne 'resident-rigid-one-lod' -or $Manifest.geometry_profile -cne 't7-iw7-resident-static-v1' -or
       $Manifest.requested_zone -cne $Plan.ExportRequest.zone -or $Manifest.source_model -cne $Plan.ExportRequest.model -or
       $Manifest.output_model_name -cne $Plan.ExportRequest.model -or !(Test-T7CatalogueInteger $Manifest.selected_source_lod 0) -or
       $Manifest.output_root_key -cne (Get-T7ResidentExportKey $Plan.ExportRequest)){throw 'Export manifest request or profile differs.'}
    foreach($flag in $falseFields){if($Manifest.$flag -isnot [bool] -or $Manifest.$flag){throw 'Export manifest overclaims its scope.'}}
    Assert-T7ResidentExportName $Manifest.output_mesh_name
    if($Manifest.material_dependencies -isnot [array] -or $Manifest.material_dependencies.Count -ne 1){throw 'Exactly one unresolved material name required.'}
    Assert-T7ResidentExportName $Manifest.material_dependencies[0]
    if($Manifest.root_bone_name -isnot [string] -or $Manifest.root_bone_name -cnotmatch '\A[\x20-\x7e]{1,255}\z'){throw 'Exact bounded root bone name required.'}
    Assert-T7CatalogueFields $Manifest.selected_counts @('bones','roots','surfaces','vertices','triangles')
    foreach($spec in @(@('bones',1,1),@('roots',1,1),@('surfaces',1,1),@('vertices',3,65535),@('triangles',1,65535))){
        $v=$Manifest.selected_counts.($spec[0])
        if(!(Test-T7CatalogueInteger $v $spec[2]) -or $v -lt $spec[1]){throw 'Export geometry count outside resident pilot.'}
    }
    foreach($spec in @(@('model',('xmodel/'+$Plan.ExportRequest.model+'.xmb'),1MB),
        @('mesh',('xsurface/'+$Manifest.output_mesh_name.Replace('\','/')+'.xsb'),16MB))){
        $artifact=$Manifest.($spec[0]);Assert-T7CatalogueFields $artifact @('relative_path','bytes','sha256')
        if($artifact.relative_path -isnot [string] -or $artifact.relative_path -cne $spec[1] -or !(Test-T7CatalogueInteger $artifact.bytes $spec[2]) -or $artifact.bytes -le 0 -or
           $artifact.sha256 -isnot [string] -or $artifact.sha256 -cnotmatch '\A[0-9a-fA-F]{64}\z'){throw 'Export artifact path, size or digest differs.'}
    }
}
function Assert-T7ResidentExportZone($Plan,$ObservedZone) {
    # Only compare the runner's admitted observation with the retained F JSON.
    $receipt=Read-H1SmallJson $Plan.SourceCatalogueReceipt.Path 128KB
    foreach($field in 'Path','Bytes','SHA256','FileId'){
        if($receipt.ObservedZone.$field -cne $ObservedZone.$field){throw 'Observed donor differs from catalogue F.'}
    }
}
function Get-T7ResidentExportFiles($Plan) {
    $dump=Join-Path $Plan.WorkingDirectory 'dump'
    if(!(Test-Path -LiteralPath $dump)){return}
    Assert-H1Path $dump
    if(![IO.Directory]::Exists($dump)){throw 'Export dump must be a directory.'}
    $root=Join-Path $dump $Plan.OutputKey
    foreach($child in [IO.Directory]::EnumerateFileSystemEntries($dump)){
        Assert-H1Path $child
        if($child -cne $root -or ![IO.Directory]::Exists($child)){throw 'Unexpected export root.'}
    }
    if(!(Test-Path -LiteralPath $root)){return}
    $pending=[Collections.Generic.Stack[string]]::new();$pending.Push($root)
    $count=0;$models=0;$meshes=0;$manifests=0
    while($pending.Count){
        foreach($path in [IO.Directory]::EnumerateFileSystemEntries($pending.Pop())){
            if(++$count -gt 32){throw 'Export subtree entry count exceeded.'}
            Assert-H1Path $path
            $relative=$path.Substring($root.Length+1).Replace('\','/')
            if([IO.Directory]::Exists($path)){
                if($relative -cne 'xmodel' -and $relative -cne 'xsurface' -and !$relative.StartsWith('xsurface/',[StringComparison]::Ordinal)){throw 'Unexpected export directory.'}
                if($relative.StartsWith('xsurface/',[StringComparison]::Ordinal)){Assert-T7ResidentExportName $relative.Substring(9)}
                $pending.Push($path);continue
            }
            $limit=0
            if($relative -ceq 'manifest.json'){$limit=4KB;if(++$manifests -gt 1){throw 'Duplicate export manifest.'}}
            elseif($relative -ceq ('xmodel/'+$Plan.ExportRequest.model+'.xmb')){$limit=1MB;if(++$models -gt 1){throw 'Duplicate export model.'}}
            elseif($relative.StartsWith('xsurface/',[StringComparison]::Ordinal) -and $relative.EndsWith('.xsb',[StringComparison]::Ordinal)){
                Assert-T7ResidentExportName $relative.Substring(9,$relative.Length-13)
                $limit=16MB;if(++$meshes -gt 1){throw 'Only one export mesh is allowed.'}
            }else{throw 'Unexpected export file.'}
            $file=Get-Item -LiteralPath $path
            if($file.Length -gt $limit){throw 'Export artifact byte cap exceeded.'}
            [pscustomobject]@{Path=$path;RelativePath=$relative;Bytes=$file.Length}
        }
    }
}
function Read-T7ResidentExportReport($Plan,$State,$Context) {
    if(!$Context.Closed -or !$Context.Lease){throw 'Original job must be closed with admission retained before export reads.'}
    $files=@(Get-T7ResidentExportFiles $Plan)
    $manifest=@($files|Where-Object RelativePath -CEQ 'manifest.json')
    if(!$manifest.Count){return 'NoExport'}
    $State.ExportOutcome='ExportPresentUnqualified'
    if($manifest.Count -ne 1 -or $manifest[0].Bytes -le 0){throw 'One nonempty export manifest required.'}
    # Freeze the bounded manifest before hashing; metadata from enumeration alone
    # must not authorize an unbounded hash if another writer replaced the file.
    $guard=[IO.FileStream]::new($manifest[0].Path,'Open','Read','Read')
    try{
        if($guard.Length -le 0 -or $guard.Length -gt 4KB -or $guard.Length -ne $manifest[0].Bytes){throw 'Export manifest size changed.'}
        $sha=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($guard)).ToLowerInvariant()
        $pin=[pscustomobject]@{Path=$manifest[0].Path;Bytes=$guard.Length;SHA256=$sha}
        Assert-H1Path $pin.Path;$guard.Position=0;$Context.Guards.Add($guard);$guard=$null;$State.Report=$pin
    }finally{if($guard){$guard.Dispose()}}
    $report=Read-H1SmallJson $pin.Path 4KB
    Assert-T7ResidentExportManifest $report $Plan
    if($files.Count -ne 3){throw 'Exactly manifest, model and mesh files required.'}
    $root=Join-Path (Join-Path $Plan.WorkingDirectory 'dump') $Plan.OutputKey
    $allowedDirectories=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach($file in $files){
        $parent=[IO.Path]::GetDirectoryName($file.Path)
        while($parent -cne $root){$null=$allowedDirectories.Add($parent);$parent=[IO.Path]::GetDirectoryName($parent)}
    }
    foreach($directory in [IO.Directory]::EnumerateDirectories($root,'*',[IO.SearchOption]::AllDirectories)){
        if(!$allowedDirectories.Contains($directory)){throw 'Unreferenced export directory.'}
    }
    $artifacts=@()
    foreach($name in 'model','mesh'){
        $declared=$report.$name;$rows=@($files|Where-Object RelativePath -CEQ $declared.relative_path)
        if($rows.Count -ne 1 -or $rows[0].Bytes -ne $declared.bytes){throw 'Export artifact differs from manifest.'}
        $artifact=[pscustomobject]@{Path=$rows[0].Path;Bytes=$declared.bytes;SHA256=$declared.sha256.ToLowerInvariant()}
        $Context.Guards.Add((Open-H1Pin $artifact));$artifacts+=@($artifact)
    }
    $State.ExportArtifacts=$artifacts;$State.SelectedCounts=$report.selected_counts
    $State.MaterialDependencies=$report.material_dependencies;$State.RootBoneName=$report.root_bone_name
    $State.SerializedParseVerified=$false;$State.DependencyPayloadsVerified=$false
    if($State.ExitCode -ne 0){return 'ValidExportFromFailedProcess'}
    'ExportFilesObserved'
}
