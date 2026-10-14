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
function Get-T7ResidentExportVersion($Plan) {
    # The plan selects the contract before a manifest is opened. Historical v1
    # plans retain their exact selection; a producer cannot promote itself to v2.
    if(!$Plan.PSObject.Properties['ResidentMultiSurfaceV2']){return 1}
    if($Plan.PSObject.Properties['ResidentSurfaceCountDiagnostic']){throw 'Resident v2 and surface-count diagnostic contracts cannot be mixed.'}
    $contract=$Plan.ResidentMultiSurfaceV2
    Assert-T7CatalogueFields $contract @('Schema')
    if((Get-T7CatalogueOperation $Plan) -cne 'ResidentExportV1' -or
       $contract.Schema -isnot [string] -or $contract.Schema -cne 'iw7.t7-resident-multi-surface/2'){
        throw 'Explicit resident multi-surface v2 contract required.'
    }
    2
}
function Get-T7ResidentExportReportLimit($Plan) {
    if((Get-T7ResidentExportVersion $Plan) -eq 2){256KB}else{4KB}
}
function Get-T7SelectedObservationProbe($Plan) {
    if(!$Plan.PSObject.Properties['SelectedMeshMaterialObservation']){return $null}
    $probe=$Plan.SelectedMeshMaterialObservation
    Assert-T7CatalogueFields $probe @('Schema')
    if((Get-T7ResidentExportVersion $Plan) -ne 2 -or $probe.Schema -isnot [string] -or
       $probe.Schema -cne 'iw7.t7-selected-mesh-material-probe/1'){
        throw 'Explicit selected mesh/material v2 probe contract required.'
    }
    $probe
}
function Get-T7SelectedObservationBuildPins($Plan) {
    if(!(Get-T7SelectedObservationProbe $Plan)){throw 'Selected observation probe required.'}
    $prepared=Join-Path (Split-Path $Plan.BuildPlan -Parent) 'prepared'
    $source=Split-Path (Split-Path (Split-Path $Plan.BuildPlan -Parent) -Parent) -Parent
    $closure=Join-Path (Split-Path $Plan.BuildReceipt -Parent) 'closure-evidence'
    $pins=[ordered]@{}
    foreach($row in @(
        @('BuildPlan',$Plan.BuildPlan,366065,'13318cc0cdd91621c47edaf838a81357f774649a2940fc9df2e85f1351b7223f'),
        @('BuildReceipt',$Plan.BuildReceipt,22239,'1d54bdceca45ae97ef0875ad745eac79a9214d02927b6f444eb526bdc589a511'),
        @('Header',(Join-Path $prepared 't7_iw7_resident_model.hpp'),21290,'857d57b5f3c1c970f45e513e357215f3506e9c48b2daea4b4f62cb33e0d9bce4'),
        @('Completion',(Join-Path $closure 'completion.local.json'),3577,'53daaddcbab90f9ed817646b47a33b02a95a83d67d189f065d17a044ffec6f29'),
        @('HostClosure',(Join-Path $closure 'original-host-closure.local.json'),1344,'b8a33531d763145c6efac1d8e3b5f3548c66c249debd70eba1fe7e209813b714'),
        @('ToolEvidence',(Join-Path $closure 'original-tool-evidence.local.json'),11223,'3a36fa07a5c3f6bff3904d963e278c819bf25e1c95284450b8e53e48ebe73b5d'),
        @('Bundle',(Join-Path $closure 'bundle-manifest.local.json'),941,'196e136c58a6cbd11cb173890f9f36dcdc4903e5b3885ad6d3993fa8067a21c7'),
        @('SourceReceipt',(Join-Path $source 'source-workspace.json'),305152,'be37410f9ab395bb9d08131ce4a40f7e2ce8e3bdd31a15ea03142b2a897153ea'),
        @('NativeExport',(Join-Path $source 'tools-source/asset-bridge/t7-iw7/native_export.inc'),17096,'7ad6c120adb021c7097080f71cae566fcaf2436ad5a1907b6ef57d020459d343'),
        @('MaterialHeader',(Join-Path $source 'tools-source/asset-bridge/t7-iw7/selected_material_observation.hpp'),12765,'a935803571f04b3a2cad7346824bf3194f5d44aeada15b224a3faa75ea292d7f'),
        @('MaterialFixture',(Join-Path $source 'tools-source/asset-bridge/t7-iw7/selected_material_observation_fixture.cpp'),8146,'f011131feeb5495b3bfb0a1e86ad34aad20fc7869ec775c861290df6e3e1a05b'))){
        $pin=[pscustomobject]@{Path=$row[1];Bytes=$row[2];SHA256=$row[3]}
        Assert-T7CatalogueTextPin $pin $Plan.Bindings;$pins[$row[0]]=$pin
    }
    if($Plan.ExpectedBuildPlanSHA256 -cne $pins.BuildPlan.SHA256 -or $Plan.ExpectedBuildReceiptSHA256 -cne $pins.BuildReceipt.SHA256 -or
       $Plan.CandidateBytes -ne 21849600 -or $Plan.CandidateSHA256 -cne '7c7ad775b201dea60ec050a28e5943cbf1eeeaa8e6386eba675c7ffc001f5e7f'){
        throw 'Exact E2 observation build/candidate required.'
    }
    $pins
}
function Get-T7ResidentExportDiagnostic($Plan) {
    if(!$Plan.PSObject.Properties['ResidentSurfaceCountDiagnostic']){return $null}
    if($Plan.PSObject.Properties['ResidentMultiSurfaceV2']){throw 'Resident v2 and surface-count diagnostic contracts cannot be mixed.'}
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
function Get-T7ResidentMultiSurfaceBuildPins($Plan) {
    if((Get-T7CatalogueCandidateProfile $Plan) -ceq 't7-zombies-catalogue-observation-c2'){return (Get-T7CatalogueZombiesAddBuildPins $Plan)}
    if((Get-T7CatalogueCandidateProfile $Plan) -ceq 't7-zombies-catalogue-observation-c'){return (Get-T7CatalogueZombiesBuildPins $Plan)}
    if(Get-T7SelectedStreamedExport $Plan){return (Get-T7SelectedStreamedBuildPins $Plan)}
    if(Get-T7SelectedObservationProbe $Plan){return (Get-T7SelectedObservationBuildPins $Plan)}
    # These are the reviewed D texts, not a caller-supplied qualification flag.
    # The caller retains all text bindings before reading any of them.
    if((Get-T7ResidentExportVersion $Plan) -ne 2){throw 'Explicit resident v2 build contract required.'}
    $witness=@($Plan.Bindings|Where-Object SHA256 -CEQ '29fc704e3c173b4ae1c72fe4a3e4f6627c4d6768209a5a685905ab63d039dd19')
    if($witness.Count -ne 1){throw 'Exact independent D witness binding required.'}
    $prepared=Join-Path (Split-Path $Plan.BuildPlan -Parent) 'prepared'
    $prefix=Join-Path (Split-Path (Split-Path $Plan.BuildPlan -Parent) -Parent) 't7-multisurface-build-d-'
    $pins=[ordered]@{}
    foreach($row in @(
        @('BuildPlan',$Plan.BuildPlan,365638,'551a4017b334d573e5873dfda3e6134968549db08e0aabacbc269ad4a398488a'),
        @('BuildReceipt',$Plan.BuildReceipt,22380,'25d2593dbb412ac676f5e11f1b4d8ae34f26623217159ddb36dfc3f42d96ce0b'),
        @('Header',(Join-Path $prepared 't7_iw7_resident_model.hpp'),21290,'857d57b5f3c1c970f45e513e357215f3506e9c48b2daea4b4f62cb33e0d9bce4'),
        @('Completion',($prefix+'completion.local.json'),16438,'962e795e474f8fd5a86a41eff3f4bd31879ba07d77c510053b0442a98c8ae199'),
        @('ActualHostExit',($prefix+'host-exit.local.json'),1290,'b776e7cce3ad68c0e994fb12a29aa7dcfc769663985260125c2a6308c8c2bbfe'),
        @('OriginalHostClosure',($prefix+'original-host-closure.local.json'),368,'690e509cd2363e4937b22a915164a03bceb8b167ec6cb5c5098fda32242ff1f0'),
        @('HostIdentity',($prefix+'host-identity.local.json'),835,'8b2726f6bcc3c27a548c9b3e3aa1e6fce97be56aaec44211de9f004c8751d217'),
        @('Witness',$witness[0].Path,8167,'29fc704e3c173b4ae1c72fe4a3e4f6627c4d6768209a5a685905ab63d039dd19'))){
        $pin=[pscustomobject]@{Path=$row[1];Bytes=$row[2];SHA256=$row[3]}
        Assert-T7CatalogueTextPin $pin $Plan.Bindings;$pins[$row[0]]=$pin
    }
    if($Plan.ExpectedBuildPlanSHA256 -cne $pins.BuildPlan.SHA256 -or $Plan.ExpectedBuildReceiptSHA256 -cne $pins.BuildReceipt.SHA256 -or
       $Plan.CandidateBytes -ne 21805568 -or $Plan.CandidateSHA256 -cne '3c9271a0ef0e96cce26f44c30e6b04aa4c2338c86057ac52da489a7bc0e28e7f'){
        throw 'Exact approved D build and candidate tuple required.'
    }
    $pins
}
function Assert-T7ResidentMultiSurfaceBuild($Plan,$Receipt,$Build) {
    # Called after the ordinary publication qualifier, including three closed
    # stages and 413 direct link objects. Never opens a binary or a job handle.
    $pins=Get-T7ResidentMultiSurfaceBuildPins $Plan
    $observation=[bool](Get-T7SelectedObservationProbe $Plan)
    $streamed=[bool](Get-T7SelectedStreamedExport $Plan)
    $zombies=(Get-T7CatalogueCandidateProfile $Plan) -ceq 't7-zombies-catalogue-observation-c'
    $zombiesAdd=(Get-T7CatalogueCandidateProfile $Plan) -ceq 't7-zombies-catalogue-observation-c2'
    $bindingCount=if($zombies -or $zombiesAdd){151}elseif($streamed){149}elseif($observation){144}else{141}
    $transitionSHA=if($zombiesAdd -or ($streamed -and (Get-T7SelectedStreamedRenderOnly $Plan))){'09f477a869eabe0794118dff29a8412773b30ab4602ea7c18190ea748768a395'}elseif($zombies -or ($streamed -and (Test-T7SelectedStreamedE4Build $Plan))){'76570ca356d90c45c04b7cd4c8e46ff8126fc1cdb9c0919562dbb265955bee6b'}elseif($streamed){'50e4bbe0d8bfb0df9a091dbc2034a8730071a9011c9825cf49ef9583120694ed'}elseif($observation){'e1b572bfacbce89260ffce52d21c26e15f2ae2aa5172256cd063797b9a0f1b1c'}else{'fcedb13a3e4b16bd2b4af0957780b755e235d99a91ffe1dc4b8f9bc7a3ed5a46'}
    if(!$Build.ReuseCompile.PSObject.Properties['ResidentMultiSurfaceV2'] -or
       $Build.ReuseCompile.PSObject.Properties['ResidentSurfaceCountDiagnostic']){throw 'Exact resident v2 reuse marker required.'}
    $proof=$Build.ReuseCompile.ResidentMultiSurfaceV2
    Assert-T7CatalogueFields $proof @('Schema','Header','PreviousSHA256','SHA256','DependencyJSON','E7ReadSHA256','E7CompileSHA256','E7LinkSHA256','E7TranslationUnits','E7Objects','SourceTransitions','AdditionalHeaderInputs')
    $readSHA='d9cdd533796a9fe14e0d5140d8adcbf5cbc932fafd4c06e18a615d15199a2185'
    $compileSHA='a7083ce5b9ba2fe1421c4f8733cf1d1e0b286549dbc55a44f3ef30ceb3c05333'
    if($proof.Schema -cne 'iw7.t7-resident-multi-surface-build/2' -or $proof.Header -cne 'prepared/t7_iw7_resident_model.hpp' -or
       $proof.PreviousSHA256 -cne '6d2da3d4f7c3d0686909dc488f3d176ee2dd250e8d43d9a3cd9bcfa701482777' -or $proof.SHA256 -cne $pins.Header.SHA256 -or
       $proof.E7ReadSHA256 -cne $readSHA -or $proof.E7CompileSHA256 -cne $compileSHA -or
       $proof.E7LinkSHA256 -cne '70455d2f32a9b034dda20fbaf48443ee68a02e552381edbf88b19d219f1f66b2' -or
       !(Test-T7CatalogueInteger $proof.E7TranslationUnits 413) -or $proof.E7TranslationUnits -ne 413 -or
       !(Test-T7CatalogueInteger $proof.E7Objects 413) -or $proof.E7Objects -ne 413 -or
       $pins.Header.Path -cne (Join-Path $Build.PreparedRoot 't7_iw7_resident_model.hpp') -or
       @($Build.Bindings).Count -ne $bindingCount -or @($Build.Bindings.Path|Sort-Object -Unique).Count -ne $bindingCount -or
       @($Build.Bindings|Where-Object {$_.IsText -is [bool] -and $_.IsText}).Count -ne ($bindingCount-6) -or
       @($Build.Bindings|Where-Object {$_.IsText -is [bool] -and !$_.IsText}).Count -ne 6 -or
       @($Build.Inputs).Count -ne 1146 -or @($Build.Inputs.Path|Sort-Object -Unique).Count -ne 1146){throw 'Exact resident v2 source and input closure required.'}
    Assert-T7CatalogueTextPin $pins.Header $Build.Bindings
    $headers=$proof.AdditionalHeaderInputs
    Assert-T7CatalogueFields $headers @('Count','Bytes','E7TranslationUnit','E7ReadSHA256','E7CompileSHA256','CompilerContextMatchesCLI','PCHExcludedForPreparedYMinus','Inputs')
    if(!(Test-T7CatalogueInteger $headers.Count 66) -or $headers.Count -ne 66 -or $headers.Bytes -ne 87204 -or
       @($headers.Inputs).Count -ne 66 -or $headers.E7ReadSHA256 -cne $readSHA -or $headers.E7CompileSHA256 -cne $compileSHA -or
       $headers.CompilerContextMatchesCLI -isnot [bool] -or !$headers.CompilerContextMatchesCLI){throw 'Exact resident v2 header closure required.'}
    $suffix='\src\zonetool\zonetool\iw7\assets\xsurface.cpp';$tu=$headers.E7TranslationUnit
    Assert-H1Path $tu;Assert-H1Path $headers.PCHExcludedForPreparedYMinus
    if(!$tu.EndsWith($suffix,[StringComparison]::Ordinal) -or
       !$headers.PCHExcludedForPreparedYMinus.EndsWith('\obj\community.pch',[StringComparison]::Ordinal)){throw 'Exact resident v2 compiler context required.'}
    $native=$tu.Substring(0,$tu.Length-$suffix.Length)
    $rows=[Collections.Generic.List[string]]::new();$seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($pin in $headers.Inputs){
        Assert-T7CatalogueTextPin $pin $Build.Bindings
        if(!$seen.Add($pin.Path) -or $pin.Bytes -gt 16KB -or
           @($Build.Inputs|Where-Object {$_.Path -ceq $pin.Path -and $_.Bytes -eq $pin.Bytes -and $_.SHA256 -ceq $pin.SHA256}).Count -ne 1){throw 'Resident v2 header Inputs/Bindings bijection differs.'}
        $rows.Add([IO.Path]::GetRelativePath($native,$pin.Path).Replace('\','/').ToLowerInvariant()+'|'+$pin.Bytes+'|'+$pin.SHA256+"`n")
    }
    $rows.Sort([StringComparer]::Ordinal);$bytes=[Text.Encoding]::UTF8.GetBytes(($rows -join ''))
    if($bytes.Length -ne 7676 -or [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant() -cne
       '5ee7ea0b46848bca9f4d365d0035cf070b2f57c6723019ab1288a54a93a7297b'){throw 'Reviewed resident v2 66-header inventory differs.'}
    $rows.Clear()
    if(@($proof.SourceTransitions).Count -ne 3){throw 'Exact resident v2 three source transitions required.'}
    foreach($row in $proof.SourceTransitions){
        Assert-T7CatalogueFields $row @('Path','PreviousBytes','PreviousSHA256','Bytes','SHA256','WiredBytes','WiredSHA256')
        $rows.Add((@($row.Path,$row.PreviousBytes,$row.PreviousSHA256,$row.Bytes,$row.SHA256,$row.WiredBytes,$row.WiredSHA256)-join '|')+"`n")
        $wired=[pscustomobject]@{Path=(Join-Path (Split-Path $Build.PreparedRoot -Parent) $row.Path);Bytes=$row.WiredBytes;SHA256=$row.WiredSHA256}
        if(($zombies -or $zombiesAdd) -and $row.Path -ceq 'prepared/zonetool.cpp'){
            # The common three-row proof seals the reviewed pre-overlay TU.
            # C's independent finite marker seals its final compiler input.
            if($zombiesAdd){Assert-T7CatalogueZombiesAddSourceTransition $Build;$cProof=$Build.ReuseCompile.ZombiesAddObservationC2}
            else{Assert-T7CatalogueZombiesSourceTransition $Build;$cProof=$Build.ReuseCompile.ZombiesObservationC}
            if($row.WiredBytes -ne $cProof.BaseCLIBytes -or $row.WiredSHA256 -cne $cProof.BaseCLISHA256){throw 'C base CLI differs from the common source transition.'}
            $wired.Bytes=$cProof.CLIBytes;$wired.SHA256=$cProof.CLISHA256
        }
        Assert-T7CatalogueTextPin $wired $Build.Bindings
    }
    $rows.Sort([StringComparer]::Ordinal);$bytes=[Text.Encoding]::UTF8.GetBytes(($rows -join ''))
    if($bytes.Length -ne $(if($streamed -or $zombies -or $zombiesAdd){716}else{714}) -or [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant() -cne
       $transitionSHA){throw 'Reviewed resident v2 source transitions differ.'}
    $specs=@(@('helper',16296,'6897d27e8fe0754509e52258082d6178c8cb74fe21a8ef4b006006e97ab9dd12'),
        @('zonetool11',76744,'cfe62be9ce9bf87abd8e6713f1e1f334d76f69472500d2cb260696de26ee8273'),
        @('xpak',64444,'3d742923def4fb049d82853ac0e776ffd071228deaf1da1a624603d10dfd3908'))
    if(@($proof.DependencyJSON).Count -ne 3){throw 'Exact resident v2 retained dependencies required.'}
    for($i=0;$i -lt 3;$i++){
        $pin=$proof.DependencyJSON[$i];Assert-T7CatalogueTextPin $pin $Build.Bindings
        if($pin.Path -cne (Join-Path (Split-Path $Build.ReuseCompile.Receipt -Parent) ($specs[$i][0]+'/dependencies.json')) -or
           $pin.Bytes -ne $specs[$i][1] -or $pin.SHA256 -cne $specs[$i][2]){throw 'Resident v2 retained dependency differs.'}
    }
    $depPath=Join-Path $Build.RunRoot 'zonetool11/dependencies.json';$doc=Read-H1SmallJson $depPath 1MB
    $includes=$doc.Data.Includes;$included=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    if($includes -isnot [array] -or $includes.Count -gt 4096){throw 'Bounded resident v2 includes required.'}
    # MSVC legitimately repeats Windows packing headers; only the prepared
    # adapter and the 66 newly bound writer headers must occur exactly once.
    foreach($path in $includes){Assert-H1Path $path;$null=$included.Add($path)}
    $adapter=@($includes|Where-Object {[IO.Path]::GetFileName($_) -ieq 't7_iw7_resident_model.hpp'})
    if($adapter.Count -ne 1 -or $adapter[0] -ine $pins.Header.Path -or $included.Contains($headers.PCHExcludedForPreparedYMinus)){
        throw 'Resident v2 CLI must include the exact adapter once without the excluded PCH.'
    }
    foreach($pin in $headers.Inputs){if(@($includes|Where-Object {$_ -ieq $pin.Path}).Count -ne 1){throw 'Resident v2 CLI must include each reviewed header exactly once.'}}
    if($zombiesAdd){Assert-T7CatalogueZombiesAddBuildClosure $Plan $Receipt $Build $pins}
    elseif($zombies){Assert-T7CatalogueZombiesBuildClosure $Plan $Receipt $Build $pins}
    elseif($streamed){Assert-T7SelectedStreamedClosure $Plan $Receipt $Build $pins}
    elseif($observation){Assert-T7SelectedObservationClosure $Plan $Receipt $pins}
    else{Assert-T7ResidentMultiSurfaceClosure $Plan $Receipt $pins}
}
function Assert-T7SelectedObservationClosure($Plan,$Receipt,$Pins) {
    $completion=Read-H1SmallJson $Pins.Completion.Path 8KB
    $hostProof=Read-H1SmallJson $Pins.HostClosure.Path 4KB
    $tools=Read-H1SmallJson $Pins.ToolEvidence.Path 16KB
    $bundle=Read-H1SmallJson $Pins.Bundle.Path 4KB
    $source=Read-H1SmallJson $Pins.SourceReceipt.Path 1MB
    if($completion.Schema -cne 'iw7.t7-build-e2-completion/1' -or $hostProof.Schema -cne 'iw7.t7-build-e2-host-closure/1' -or
       $bundle.Schema -cne 'iw7.t7-build-e2-closure-bundle/1' -or $tools.Schema -cne 'iw7.t7-build-e2-original-tool-evidence/1' -or
       $completion.CompiledAssetCommit -cne 'afdd8062732499698a6a810918b8aae082ba3668' -or
       $completion.NativeDependencyCommit -cne '2f9462db806bbd3ab51f9ecb2f3b25ae54ae10f1' -or
       $completion.UpstreamSourceCommit -cne 'fab935826c898806855376662a8a03317b3ad8f1' -or
       $source.product -cne 'x64-zt-extensions' -or $source.revisions.'x64-zt-extensions' -cne $completion.CompiledAssetCommit -or
       $source.revisions.'iw7-mod-components' -cne $completion.NativeDependencyCommit -or $completion.Status -cne 'Passed' -or
       $completion.LeaseToken -cne $Receipt.LeaseToken){throw 'Exact E2 source/closure provenance required.'}
    foreach($field in 'Path','SHA256'){
        if($completion.BuildPlan.$field -cne $Pins.BuildPlan.$field){throw 'E2 build plan closure pin differs.'}
    }
    foreach($field in 'Path','Bytes','SHA256'){
        if($completion.BuildReceipt.$field -cne $Pins.BuildReceipt.$field){throw 'E2 build receipt closure pin differs.'}
    }
    foreach($field in 'InputsReverified','TreeClosureConfirmed','LeaseReleased'){
        if($completion.$field -isnot [bool] -or !$completion.$field){throw 'E2 build closure incomplete.'}
    }
    foreach($field in 'Quarantined','CandidateExecuted','ArtifactBytesReadOrHashedAfterRelease','FixturePassed','StockSondeExecuted'){
        if($completion.$field -isnot [bool] -or $completion.$field){throw 'E2 build-only scope differs.'}
    }
    if(@($bundle.Files).Count -ne 3){throw 'Three original E2 closure evidence files required.'}
    foreach($role in 'Completion','HostClosure','ToolEvidence'){
        $rows=@($bundle.Files|Where-Object Path -CEQ $Pins[$role].Path)
        if($rows.Count -ne 1 -or $rows[0].Bytes -ne $Pins[$role].Bytes -or $rows[0].SHA256 -cne $Pins[$role].SHA256){throw 'E2 closure bundle member differs.'}
    }
    if($completion.OriginalSessionId -ne 75422 -or $hostProof.OriginalSessionId -ne 75422 -or
       !(Test-T7CatalogueInteger $completion.OriginalPTYExitCode 0) -or !(Test-T7CatalogueInteger $hostProof.ActualPTYExit.ExitCode 0) -or
       $hostProof.ActualPTYExit.ChunkId -cne '96d4f3' -or $hostProof.HostState.Closed -isnot [bool] -or !$hostProof.HostState.Closed -or
       $null -ne $hostProof.HostState.Lease -or !(Test-T7CatalogueInteger $hostProof.HostState.Guards 0) -or $hostProof.HostState.Status -cne 'Passed' -or
       !(Test-T7CatalogueInteger $hostProof.FreshClosureInventory.LeaseCount 0) -or
       $hostProof.FreshClosureInventory.OriginalHostsAndStagesAbsent -isnot [bool] -or !$hostProof.FreshClosureInventory.OriginalHostsAndStagesAbsent -or
       $hostProof.FreshClosureInventory.HeavyAndGameProcessesAbsent -isnot [bool] -or !$hostProof.FreshClosureInventory.HeavyAndGameProcessesAbsent){throw 'Original E2 host exit and closure required.'}
    foreach($chunk in '041444','1656ef','96d4f3','8e6728','d1f504'){
        $rows=@($tools.Records|Where-Object {$_.ToolResult.chunk_id -ceq $chunk})
        if($rows.Count -ne 1 -or ($chunk -cne '1656ef' -and !(Test-T7CatalogueInteger $rows[0].ToolResult.exit_code 0))){throw 'Original E2 tool completion differs.'}
    }
    if(@($completion.Stages).Count -ne 3){throw 'Three E2 stage identities required.'}
    foreach($stage in $Receipt.Stages){
        $rows=@($completion.Stages|Where-Object Name -CEQ $stage.Name)
        if($rows.Count -ne 1 -or !(Test-T7CatalogueInteger $rows[0].ExitCode 0) -or !$rows[0].TreeClosureConfirmed){throw 'E2 stage completion differs.'}
        foreach($field in 'PID','Image'){
            if($rows[0].Identity.$field -cne $stage.Identity.$field){throw 'E2 original stage identity differs.'}
        }
        if(([datetimeoffset]$rows[0].Identity.CreatedUtc).UtcTicks -ne ([datetimeoffset]$stage.Identity.CreatedUtc).UtcTicks){throw 'E2 original stage creation differs.'}
        if($stage.CompilerTelemetry.Completed -isnot [bool] -or !$stage.CompilerTelemetry.Completed -or
           $stage.CompilerTelemetry.CompilerResult.BoundInputsVerified -ne 144 -or
           !(Test-T7CatalogueInteger $stage.LastOriginalSnapshot.ActiveProcesses 0)){throw 'E2 owned-stage telemetry closure required.'}
    }
}
function Assert-T7ResidentMultiSurfaceClosure($Plan,$Receipt,$Pins) {
    $completion=Read-H1SmallJson $Pins.Completion.Path 32KB
    $actual=Read-H1SmallJson $Pins.ActualHostExit.Path 4KB
    $closure=Read-H1SmallJson $Pins.OriginalHostClosure.Path 4KB
    $identity=Read-H1SmallJson $Pins.HostIdentity.Path 4KB
    $witness=Read-H1SmallJson $Pins.Witness.Path 16KB
    # Private compilation checkout, deliberately distinct from upstream fab935.
    $source='0bc0b16aafb2ceb3863f9c20b5f50fb5c8a5f777'
    if($completion.Schema -cne 'iw7.t7-multisurface-build-completion/1' -or $completion.SourceCommit -cne $source -or
       $completion.Status -cne 'PassedOriginalHostExitedIndependentPending' -or $completion.NativeInvocationCount -ne 1 -or
       $actual.Schema -cne 'iw7.t7-build-d-host-exit/1' -or $closure.Schema -cne 'iw7.t7-build-d-original-host-closure/1' -or
       $identity.Schema -cne 'iw7.t7-build-d-host-identity/1' -or $identity.PlanSHA256 -cne $Pins.BuildPlan.SHA256 -or
       $witness.Schema -cne 'iw7.t7-build-independent-absence/1' -or $witness.WitnessStatus -cne 'Passed' -or
       $witness.BuildStatus -cne 'Passed' -or $witness.SourceCommit -cne $source -or $witness.PlanSHA256 -cne $Pins.BuildPlan.SHA256){throw 'Exact D closure source/status required.'}
    foreach($pair in @(@($completion.Plan,$Pins.BuildPlan),@($completion.Receipt,$Pins.BuildReceipt),
        @($actual.HostIdentity,$Pins.HostIdentity),@($actual.OriginalHostClosure,$Pins.OriginalHostClosure))){
        foreach($field in 'Path','Bytes','SHA256'){if($pair[0].$field -cne $pair[1].$field){throw 'D closure evidence pin differs.'}}
    }
    foreach($role in 'BuildReceipt','HostIdentity','OriginalHostClosure','ActualHostExit'){
        $matches=@($witness.EvidencePins|Where-Object Role -CEQ $role)
        if($matches.Count -ne 1){throw 'D witness evidence role differs.'}
        foreach($field in 'Path','Bytes','SHA256'){if($matches[0].$field -cne $Pins[$role].$field){throw 'D witness evidence pin differs.'}}
    }
    foreach($spec in @(@($completion,@('SourceTrackedClean','InputsReverified','TreeClosureConfirmed','LeaseReleased','OriginalHostClosureConfirmed')),
        @($closure,@('Closed','OwnerClosed','LeaseIsNull','InputsReverified','CanExit')),
        @($identity,@('ExactPlanCommandMatched')),@($witness,@('SourceCleanAndStable','SchedulerAndIndependentCimAgree')))){
        foreach($field in $spec[1]){if($spec[0].$field -isnot [bool] -or !$spec[0].$field){throw 'D closure positive proof missing.'}}
    }
    foreach($field in 'Quarantined','CandidateExecuted','ExportExecuted','FastfileBuilt','RuntimeVerified','OwnerAccepted','Ready'){
        if($completion.$field -isnot [bool] -or $completion.$field){throw 'D build-only closure claim differs.'}
    }
    foreach($value in @($completion.ExitCode,$closure.NativeOwnerExitCode,$closure.GuardCount,$closure.RegistryLeaseCount,
        $witness.ObservedDescendantCount,$witness.RootProcessCount,$witness.OtherCommandLineRootProcessCount,$witness.LeaseCount,$witness.HeavyIncludingVctipCount)){
        if(!(Test-T7CatalogueInteger $value 0)){throw 'D closure retains live work or a failed owner.'}
    }
    if($closure.ReceiptStatus -cne 'Passed' -or $completion.LeaseToken -cne $Receipt.LeaseToken -or
       $identity.SessionId -ne $actual.SessionId -or $closure.SessionId -ne $identity.SessionId -or $closure.HostPID -ne $identity.Host.PID -or
       $witness.ActualExit.PTYSessionId -ne $actual.SessionId -or $witness.ActualExit.ToolChunkId -cne $actual.ActualCompletion.ToolChunkId -or
       $witness.ActualExit.OwnerThreadCommandStatus -cne 'completed' -or $witness.ActualExit.ExitInferredFromAbsence -isnot [bool] -or
       $witness.ActualExit.ExitInferredFromAbsence -or !(Test-T7CatalogueInteger $witness.ActualExit.Code 0) -or
       !(Test-T7CatalogueInteger $witness.ActualExit.OwnerThreadCommandExitCode 0)){throw 'Actual original D host exit required.'}
    foreach($exitProof in @($actual.ActualCompletion,$completion.ActualPTYCompletion)){
        if($exitProof.SessionCompleted -isnot [bool] -or !$exitProof.SessionCompleted -or !(Test-T7CatalogueInteger $exitProof.ExitCode 0) -or
           $exitProof.ToolChunkId -cne 'd29829'){throw 'Completed original D PTY proof required.'}
    }
    $expected=[ordered]@{Host=$identity.Host;Parent=$identity.Parent}
    foreach($stage in $Receipt.Stages){
        $telemetry=$stage.CompilerTelemetry
        if($telemetry.Completed -isnot [bool] -or !$telemetry.Completed -or $telemetry.CompilerResult.BoundInputsVerified -ne 141 -or
           !(Test-T7CatalogueInteger $telemetry.CompilerResult.ExitCode 0) -or !(Test-T7CatalogueInteger $stage.LastOriginalSnapshot.ActiveProcesses 0) -or
           @($telemetry.BeforeStopFirst.Members).Count -ne 1 -or !(Test-T7CatalogueInteger $telemetry.AfterStopMembers.ListedCount 0)){
            throw 'D original compiler and telemetry closure required.'
        }
        $expected[$stage.Name+'Root']=$stage.Identity;$expected[$stage.Name+'Telemetry']=$telemetry.BeforeStopFirst.Members[0]
    }
    if(@($witness.AbsentExactIdentities).Count -ne 8){throw 'Eight exact D absence identities required.'}
    foreach($role in $expected.Keys){
        $matches=@($witness.AbsentExactIdentities|Where-Object Role -CEQ $role);$original=$expected[$role]
        if($matches.Count -ne 1 -or $matches[0].PID -ne $original.PID -or $matches[0].Image -cne $original.Image -or
           ([DateTimeOffset]$matches[0].CreatedUtc).UtcTicks -ne ([DateTimeOffset]$original.CreatedUtc).UtcTicks){throw 'D witness process identity differs.'}
    }
}
function Assert-T7ResidentExportDiagnosticMetadata($Plan,$Base) {
    $old=@($Base.InputMetadata);$current=@($Plan.InputMetadata)
    if(Get-T7SelectedStreamedExport $Plan){$current=@($current|Where-Object {$_.Path -cnotin @($Plan.SelectedXpakProvider.Metadata.Path,$Plan.ExportRequestFile.Path)})}
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
    $version=Get-T7ResidentExportVersion $Plan
    $null=Get-T7SelectedObservationProbe $Plan
    $streamed=[bool](Get-T7SelectedStreamedExport $Plan)
    $command=if($streamed -and (Get-T7SelectedStreamedRenderOnly $Plan)){'-t7-iw7-model-streamed-v2'}elseif($streamed){'-t7-iw7-model-streamed-v1'}elseif($version -eq 2){'-t7-iw7-model-v2'}else{'-t7-iw7-model'}
    $arguments=@($command,'mp_freerun_04','p7_fre_platform_cap_02','0');if($streamed){$arguments+=@('streamed-request.json');Assert-T7SelectedStreamedProvider $Plan}
    $diagnostic=Get-T7ResidentExportDiagnostic $Plan
    if((Get-T7CatalogueBootstrapPolicy $Plan) -cne 'QualifiedCollectionV3' -or
       $Plan.EngineOutputProfile -cne 'ObservedStartupManifestA' -or
       $Plan.CandidateProfile -cne 't7-catalog-message-publication' -or
       ($version -eq 1 -and !$diagnostic -and ($Plan.CandidateBytes -ne 21751296 -or $Plan.CandidateSHA256 -cne '31b9d908d15fb5f0bf17a7b27309dc7183458d5e586dfc6e427cc8ec2b3fa647')) -or
       @(Get-T7CatalogueBootstraps $Plan).Count -ne 23 -or
       $Plan.OutputKey -cne (Get-T7ResidentExportOutputKey $Plan) -or
       @($Plan.Arguments).Count -ne $arguments.Count -or
       (@($Plan.Arguments) -join '|') -cne ($arguments -join '|') -or
       $Plan.ExportModelLimitBytes -ne 1MB -or $Plan.ExportMeshLimitBytes -ne 16MB -or
       $Plan.ReportLimitBytes -ne (Get-T7ResidentExportReportLimit $Plan)){
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
    if($streamed){$expected+=@(Join-Path $Repo 'tools-source/asset-bridge/t7-iw7/streamed_contract.py')}
    if(@($Plan.ReadbackSources).Count -ne $expected.Count -or @($Plan.ReadbackSources.Path|Sort-Object -Unique).Count -ne $expected.Count){
        if($streamed){throw 'Five independent reader source pins required.'}else{throw 'Four independent reader source pins required.'}
    }
    foreach($pin in $Plan.ReadbackSources){
        if($pin.Path -cnotin $expected){throw 'Unexpected independent reader source.'}
        Assert-T7CatalogueTextPin $pin $Plan.Bindings
    }
    if($version -eq 2){$null=Get-T7ResidentMultiSurfaceBuildPins $Plan}
    if(Get-T7SelectedStreamedRenderOnly $Plan){$null=Get-T7SelectedStreamedOutputPathProof $Plan}
}
function Assert-T7ResidentExportCatalogue($Plan) {
    # Caller retains every text binding before these reads. No stock read or new qualification.
    $base=Read-H1SmallJson $Plan.SourceCataloguePlan.Path 128KB
    $receipt=Read-H1SmallJson $Plan.SourceCatalogueReceipt.Path 128KB
    $catalogue=Read-H1SmallJson $Plan.SourceCatalogue.Path 512KB
    $request=Read-H1SmallJson $Plan.ExportRequestFile.Path 4KB
    if(Get-T7SelectedStreamedExport $Plan){Assert-T7SelectedStreamedRequest $request -RenderOnly:(Get-T7SelectedStreamedRenderOnly $Plan)}
    else{Assert-T7ResidentExportRequest $request;if(($request|ConvertTo-Json -Compress) -cne ($Plan.ExportRequest|ConvertTo-Json -Compress)){throw 'Standalone export request differs.'}}
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
    if((Get-T7ResidentExportDiagnostic $Plan) -or (Get-T7ResidentExportVersion $Plan) -eq 2){
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
function Assert-T7ResidentExportGeometryV2($Manifest) {
    # Metadata only, before artifact hashing or any downstream geometry scan.
    # Every ordered occurrence counts in full, including repeated materials or
    # native pointer aliases. This bounds logical geometry bytes, not total RAM.
    $counts=$Manifest.selected_counts
    Assert-T7CatalogueFields $counts @('bones','roots','surfaces','vertices','triangles')
    foreach($spec in @(@('bones',1,1),@('roots',1,1),@('surfaces',1,255),
        @('vertices',3,16711425),@('triangles',1,16711425))){
        $value=$counts.($spec[0])
        if(!(Test-T7CatalogueInteger $value $spec[2]) -or $value -lt $spec[1]){throw 'Export v2 geometry count outside bounded contract.'}
    }
    $n=[long]$counts.surfaces
    if($Manifest.surface_records -isnot [array] -or $Manifest.surface_records.Count -ne $n){throw 'One ordered v2 surface record per surface required.'}
    if($Manifest.material_dependencies -isnot [array] -or $Manifest.material_dependencies.Count -ne $n){throw 'One ordered v2 material occurrence per surface required.'}
    $vertices=0L;$triangles=0L
    for($i=0;$i -lt $n;$i++){
        $row=$Manifest.surface_records[$i]
        Assert-T7CatalogueFields $row @('index','material_slot','vertices','triangles')
        foreach($field in 'index','material_slot'){
            if(!(Test-T7CatalogueInteger $row.$field 254) -or $row.$field -ne $i){throw 'Sequential v2 surface and material indices required.'}
        }
        if(!(Test-T7CatalogueInteger $row.vertices 65535) -or $row.vertices -lt 3 -or
           !(Test-T7CatalogueInteger $row.triangles 65535) -or $row.triangles -lt 1){throw 'Export v2 surface count outside bounded contract.'}
        Assert-T7ResidentExportName $Manifest.material_dependencies[$i]
        $vertices+=[long]$row.vertices;$triangles+=[long]$row.triangles
    }
    if($vertices -ne $counts.vertices -or $triangles -ne $counts.triangles){throw 'Exact v2 vertex and triangle sums required.'}
    # T7XSurface is 96 bytes: source bookkeeping adds 16 per occurrence.
    # The validated upper bounds make every intermediate exact in Int64.
    $source=200L+112L*$n+28L*$vertices+6L*$triangles
    $destination=56L+272L*$n+32L*$vertices+6L*$triangles
    $work=256L+384L*$n+60L*$vertices+12L*$triangles
    if($source+$destination -ne $work -or $work -gt 16MB -or
       !(Test-T7CatalogueInteger $Manifest.geometry_work_bytes_upper_bound 16MB) -or
       $Manifest.geometry_work_bytes_upper_bound -ne $work){throw 'Exact v2 geometry work bytes within 16 MiB required.'}
}
function Assert-T7ResidentExportManifest($Manifest,$Plan) {
    Assert-T7ResidentExportRequest $Plan.ExportRequest
    $version=Get-T7ResidentExportVersion $Plan
    $streamed=[bool](Get-T7SelectedStreamedExport $Plan)
    $falseFields=@('zonetool_xpak_helper_reads_allowed','engine_io_verified','dependency_payloads_verified',
        'asset_zone_ownership_verified','serialized_parse_verified','runtime_verified','ready')
    $fields=@('schema','requested_zone','source_model','selected_source_lod','output_model_name',
        'output_mesh_name','output_root_key','target','profile','geometry_profile','root_bone_name','selected_counts','material_dependencies','model','mesh')+$falseFields
    if($version -eq 2){$fields+=@('surface_records','geometry_work_bytes_upper_bound')}
    if($streamed){$fields+=@('selected_mesh_payload')}
    if(Get-T7SelectedStreamedRenderOnly $Plan){$fields+=@('selected_collision_policy')}
    Assert-T7CatalogueFields $Manifest $fields
    foreach($field in 'schema','requested_zone','source_model','output_model_name','output_root_key','target','profile','geometry_profile'){
        if($Manifest.$field -isnot [string]){throw 'Export manifest scalar string required.'}
    }
    $renderOnly=$streamed -and (Get-T7SelectedStreamedRenderOnly $Plan)
    $schema=if($renderOnly){'iw7.t7-iw7-selected-streamed-export/2'}elseif($streamed){'iw7.t7-iw7-selected-streamed-export/1'}else{'iw7.t7-iw7-resident-export/'+$version}
    $profile=if($renderOnly){'selected-streamed-render-only-rigid-one-lod'}elseif($streamed){'selected-streamed-rigid-one-lod'}else{'resident-rigid-one-lod'}
    $geometry=if($renderOnly){'t7-iw7-selected-streamed-render-only-v2'}elseif($streamed){'t7-iw7-selected-streamed-static-v1'}else{'t7-iw7-resident-static-v'+$version}
    if($Manifest.schema -cne $schema -or $Manifest.target -cne 'iw7' -or
       $Manifest.profile -cne $profile -or $Manifest.geometry_profile -cne $geometry -or
       $Manifest.requested_zone -cne $Plan.ExportRequest.zone -or $Manifest.source_model -cne $Plan.ExportRequest.model -or
       $Manifest.output_model_name -cne $Plan.ExportRequest.model -or !(Test-T7CatalogueInteger $Manifest.selected_source_lod 0) -or
       $Manifest.output_root_key -cne (Get-T7ResidentExportOutputKey $Plan)){throw 'Export manifest request or profile differs.'}
    foreach($flag in $falseFields){if($Manifest.$flag -isnot [bool] -or $Manifest.$flag){throw 'Export manifest overclaims its scope.'}}
    Assert-T7ResidentExportName $Manifest.output_mesh_name
    if($version -eq 1){
        if($Manifest.material_dependencies -isnot [array] -or $Manifest.material_dependencies.Count -ne 1){throw 'Exactly one unresolved material name required.'}
        Assert-T7ResidentExportName $Manifest.material_dependencies[0]
    }
    if($Manifest.root_bone_name -isnot [string] -or $Manifest.root_bone_name -cnotmatch '\A[\x20-\x7e]{1,255}\z'){throw 'Exact bounded root bone name required.'}
    if($version -eq 2){Assert-T7ResidentExportGeometryV2 $Manifest}
    else{
        Assert-T7CatalogueFields $Manifest.selected_counts @('bones','roots','surfaces','vertices','triangles')
        foreach($spec in @(@('bones',1,1),@('roots',1,1),@('surfaces',1,1),@('vertices',3,65535),@('triangles',1,65535))){
            $v=$Manifest.selected_counts.($spec[0])
            if(!(Test-T7CatalogueInteger $v $spec[2]) -or $v -lt $spec[1]){throw 'Export geometry count outside resident pilot.'}
        }
    }
    if($streamed){Assert-T7SelectedStreamedPayload $Manifest.selected_mesh_payload $Plan $Manifest.selected_counts.surfaces}
    if($renderOnly){Assert-T7SelectedStreamedCollisionPolicy $Manifest.selected_collision_policy $Manifest.selected_counts.surfaces}
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
    $reportLimit=Get-T7ResidentExportReportLimit $Plan
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
            if($relative -ceq 'manifest.json'){$limit=$reportLimit;if(++$manifests -gt 1){throw 'Duplicate export manifest.'}}
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
    $reportLimit=Get-T7ResidentExportReportLimit $Plan
    $files=@(Get-T7ResidentExportFiles $Plan)
    $manifest=@($files|Where-Object RelativePath -CEQ 'manifest.json')
    if(!$manifest.Count){return 'NoExport'}
    $State.ExportOutcome='ExportPresentUnqualified'
    if($manifest.Count -ne 1 -or $manifest[0].Bytes -le 0){throw 'One nonempty export manifest required.'}
    # Freeze the bounded manifest before hashing; metadata from enumeration alone
    # must not authorize an unbounded hash if another writer replaced the file.
    $guard=[IO.FileStream]::new($manifest[0].Path,'Open','Read','Read')
    try{
        if($guard.Length -le 0 -or $guard.Length -gt $reportLimit -or $guard.Length -ne $manifest[0].Bytes){throw 'Export manifest size changed.'}
        $sha=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($guard)).ToLowerInvariant()
        $pin=[pscustomobject]@{Path=$manifest[0].Path;Bytes=$guard.Length;SHA256=$sha}
        Assert-H1Path $pin.Path;$guard.Position=0;$Context.Guards.Add($guard);$guard=$null;$State.Report=$pin
    }finally{if($guard){$guard.Dispose()}}
    $report=Read-H1SmallJson $pin.Path $reportLimit
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
    if((Get-T7ResidentExportVersion $Plan) -eq 2){
        $State.SurfaceRecords=$report.surface_records;$State.GeometryWorkBytesUpperBound=$report.geometry_work_bytes_upper_bound
    }
    $State.SerializedParseVerified=$false;$State.DependencyPayloadsVerified=$false
    if($State.ExitCode -ne 0){return 'ValidExportFromFailedProcess'}
    'ExportFilesObserved'
}

# E3 is an explicit new epoch; the D/E2 selectors and their retained pins stay exact.
function Get-T7SelectedStreamedExport($Plan) {
    if(Get-T7SelectedStreamedRenderOnly $Plan){return $Plan.SelectedStreamedRenderOnlyV2}
    if(!$Plan.PSObject.Properties['SelectedStreamedStaticV1']){return $null}
    $marker=$Plan.SelectedStreamedStaticV1
    Assert-T7CatalogueFields $marker @('Schema')
    if($marker.Schema -cne 'iw7.t7-selected-streamed-export-plan/1' -or
       (Get-T7ResidentExportVersion $Plan) -ne 2 -or
       $Plan.PSObject.Properties['SelectedMeshMaterialObservation'] -or
       $Plan.PSObject.Properties['ResidentSurfaceCountDiagnostic']){throw 'Distinct selected-streamed E3 contract required.'}
    $marker
}
function Get-T7SelectedStreamedRenderOnly($Plan) {
    if(!$Plan.PSObject.Properties['SelectedStreamedRenderOnlyV2']){return $false}
    $marker=$Plan.SelectedStreamedRenderOnlyV2;Assert-T7CatalogueFields $marker @('Schema')
    if($marker.Schema -cne 'iw7.t7-selected-streamed-render-only-plan/2' -or
       (Get-T7ResidentExportVersion $Plan) -ne 2 -or
       $Plan.PSObject.Properties['SelectedStreamedStaticV1'] -or $Plan.PSObject.Properties['SelectedMeshMaterialObservation'] -or
       $Plan.PSObject.Properties['ResidentSurfaceCountDiagnostic']){throw 'Distinct E5 render-only v2 plan required.'}
    $true
}
function Get-T7SelectedStreamedBuildPins($Plan) {
    if(!(Get-T7SelectedStreamedExport $Plan)){throw 'Explicit E3 selector required.'}
    if(Get-T7SelectedStreamedRenderOnly $Plan){return (Get-T7SelectedStreamedE5BuildPins $Plan)}
    if(Test-T7SelectedStreamedE4Build $Plan){return (Get-T7SelectedStreamedE4BuildPins $Plan)}
    $prepared=Join-Path (Split-Path $Plan.BuildPlan -Parent) 'prepared'
    $source=Split-Path (Split-Path (Split-Path $Plan.BuildPlan -Parent) -Parent) -Parent
    $root=Split-Path $Plan.BuildReceipt -Parent
    $pins=[ordered]@{}
    foreach($row in @(
        @('BuildPlan',$Plan.BuildPlan,367632,'6df0db3f13852df5b70e660de915e376f5339f44ad04327166f82304b71ce4e8'),
        @('BuildReceipt',$Plan.BuildReceipt,12189,'bc44d8e228197c8ba8f0d70b1b7f4b239a0d4e5d556b5380349b549bd31a5b7d'),
        @('Header',(Join-Path $prepared 't7_iw7_resident_model.hpp'),21290,'857d57b5f3c1c970f45e513e357215f3506e9c48b2daea4b4f62cb33e0d9bce4'),
        @('HostClosure',(Join-Path $root 'original-host-closure.local.json'),241,'fc4f46de56b8eb3c0961634fde0afac7c7ec00e24272238754dff33df5e63bb9'),
        @('HostExit',(Join-Path $root 'original-host-exit-request.local.json'),285,'7eb29dbb7f23e77a608c634bf246b908f76219850c57928997936d63ab90efa5'),
        @('Inventory',(Join-Path $root 'post-host-inventory.local.json'),627,'6ec892385767476d7c1de73fcaef5ac73fd224068882a51a63d2aad51cfdbd9f'),
        @('Bundle',(Join-Path $root 'closure-bundle-manifest.local.json'),1245,'7cbe2043ec64d24776e2b67d653f6eafbe533f8c0c308827ce6348471ab30b89'),
        @('SourceReceipt',(Join-Path $source 'source-workspace.json'),308357,'a97b32ff7a2022dd038142c75b0fa5973f61f9f8bfe05d76e9c97572d8a4fcec'),
        @('NativeExport',(Join-Path $source 'tools-source/asset-bridge/t7-iw7/native_export.inc'),18268,'c6a197911d7adfef96273e29367e090666b130580356658478859f007165fa3d'),
        @('MaterialHeader',(Join-Path $source 'tools-source/asset-bridge/t7-iw7/selected_material_observation.hpp'),15261,'699796230fb3b626c9faf8ebb3e06c75eb376048c5f9928f341636235683d4da'),
        @('MaterialFixture',(Join-Path $source 'tools-source/asset-bridge/t7-iw7/selected_material_observation_fixture.cpp'),10869,'d5e30aba27684ef68b60c269d1afa22c9b0e8eedad697b40412d45fce3ce8029'),
        @('PayloadHeader',(Join-Path $source 'tools-source/asset-bridge/t7-iw7/streamed_mesh_payload.hpp'),17917,'4572066e2a3692bfdec563dac87e8610506836c5bd7334f85672fe574d82208f'),
        @('StreamedHeader',(Join-Path $source 'tools-source/asset-bridge/t7-iw7/t7_iw7_streamed_model.hpp'),10708,'baacda879ad058bbcba115362d8b86d10efd40c70040efd6bd036047b387f139'),
        @('NativeStreamed',(Join-Path $source 'tools-source/asset-bridge/t7-iw7/native_streamed_export.inc'),9823,'60916d49cb4490f0cc508b699d9adaa02a780229fa5e69e3c66297f50c3b0123'),
        @('StreamedContract',(Join-Path $source 'tools-source/asset-bridge/t7-iw7/streamed_contract.py'),7996,'b7d68593b93975832cfa6362c2f782187772c2255cd59c78ab5aae66d759518f'),
        @('StreamedTest',(Join-Path $source 'tools-source/asset-bridge/t7-iw7/test_streamed_contract.py'),8796,'fe25379d80cc1ec328836a0e75652046c01b9ddadba3dba73c8e7a550bed1d16'))){
        $pin=[pscustomobject]@{Path=$row[1];Bytes=$row[2];SHA256=$row[3]}
        Assert-T7CatalogueTextPin $pin $Plan.Bindings;$pins[$row[0]]=$pin
    }
    if($Plan.ExpectedBuildPlanSHA256 -cne $pins.BuildPlan.SHA256 -or
       $Plan.ExpectedBuildReceiptSHA256 -cne $pins.BuildReceipt.SHA256 -or
       $Plan.CandidateBytes -ne 21916160 -or
       $Plan.CandidateSHA256 -cne '2de24e4a715d92cebe767073f212241319c85bd7a5863201f1eaf9da39f9ff7d'){
        throw 'Exact compiled E3 build and candidate required.'
    }
    $pins
}
function Assert-T7SelectedStreamedClosure($Plan,$Receipt,$Build,$Pins) {
    if(Get-T7SelectedStreamedRenderOnly $Plan){Assert-T7SelectedStreamedE5Closure $Plan $Receipt $Build $Pins;return}
    if(Test-T7SelectedStreamedE4Build $Plan){Assert-T7SelectedStreamedE4Closure $Plan $Receipt $Build $Pins;return}
    Assert-T7CatalogueFields $Build.ReuseCompile.SelectedStreamedStaticV1 @('Schema','GeometryProfile')
    if($Build.ReuseCompile.SelectedStreamedStaticV1.Schema -cne 'iw7.t7-selected-streamed-static-build/1' -or
       $Build.ReuseCompile.SelectedStreamedStaticV1.GeometryProfile -cne 't7-iw7-selected-streamed-static-v1'){
        throw 'Actual compiled E3 reuse marker required.'
    }
    foreach($name in 'NativeExport','MaterialHeader','MaterialFixture','PayloadHeader','StreamedHeader','NativeStreamed','StreamedContract','StreamedTest'){
        Assert-T7CatalogueTextPin $Pins[$name] $Build.Bindings
    }
    $source=Read-H1SmallJson $Pins.SourceReceipt.Path 512KB
    if($source.schema -cne 'iw7.source-workspace/1' -or
       $source.revisions.'x64-zt-extensions' -cne 'e3451959dba1dafe11095f1434a614c8ddff3fbe' -or
       $source.revisions.'iw7-mod-components' -cne '2f9462db806bbd3ab51f9ecb2f3b25ae54ae10f1'){
        throw 'Exact E3 compilation source provenance required.'
    }
    $hostProof=Read-H1SmallJson $Pins.HostClosure.Path 2KB
    $exitProof=Read-H1SmallJson $Pins.HostExit.Path 2KB
    $inventory=Read-H1SmallJson $Pins.Inventory.Path 2KB
    $bundle=Read-H1SmallJson $Pins.Bundle.Path 4KB
    if($hostProof.Schema -cne 'iw7.t7-build-e3-original-host-closure/1' -or
       $hostProof.Status -cne 'Passed' -or !$hostProof.Closed -or !$hostProof.LeaseIsNull -or $hostProof.GuardCount -ne 0 -or
       $hostProof.HostPID -ne 19096 -or $hostProof.SessionId -ne 99797 -or
       $exitProof.Schema -cne 'iw7.t7-build-e3-original-host-exit-request/1' -or
       $exitProof.Status -cne 'Passed' -or !$exitProof.OriginalJobsClosed -or !$exitProof.LeaseIsNull -or
       $exitProof.GuardCount -ne 0 -or $exitProof.RequestedExitCode -ne 0 -or
       $exitProof.HostPID -ne $hostProof.HostPID -or $exitProof.SessionId -ne $hostProof.SessionId -or
       $bundle.Schema -cne 'iw7.t7-build-e3-closure-bundle/1' -or $bundle.OriginalSessionId -ne 99797 -or
       $bundle.ActualExitCode -ne 0 -or $bundle.ActualExitChunk -cne '0fe3ec' -or
       $inventory.Schema -cne 'iw7.t7-build-e3-post-host-inventory/1' -or !$inventory.OriginalIDsAbsent -or
       @($inventory.Leases).Count -ne 0 -or (@($inventory.OriginalIDs) -join '|') -cne '24496|19096|3880|24600|14616'){
        throw 'Actual E3 original host/job/PTY closure required.'
    }
    $expected=@($Pins.BuildReceipt,$Pins.HostClosure,$Pins.HostExit,$Pins.Inventory)
    if(@($bundle.Files).Count -ne 4){throw 'Exact original E3 closure bundle required.'}
    foreach($pin in $expected){
        $rows=@($bundle.Files|Where-Object {$_.Path -ceq $pin.Path -and $_.Bytes -eq $pin.Bytes -and $_.SHA256 -ceq $pin.SHA256})
        if($rows.Count -ne 1){throw 'Original E3 bundle pin differs.'}
    }
    for($i=0;$i -lt 3;$i++){
        $stage=$Receipt.Stages[$i];$snap=$stage.LastOriginalSnapshot
        if($stage.Identity.PID -ne @(3880,24600,14616)[$i] -or !$snap.RootExited -or
           $snap.RootExitCode -ne 0 -or $snap.ActiveProcesses -ne 0 -or $snap.PID -ne $stage.Identity.PID -or
           $snap.Image -cne $stage.Identity.Image -or
           ([datetimeoffset]$snap.CreatedUtc).UtcTicks -ne ([datetimeoffset]$stage.Identity.CreatedUtc).UtcTicks){
            throw 'Original E3 compiler/link snapshots must refer to the exact closed jobs.'
        }
    }
    if(([datetimeoffset]$inventory.CapturedUtc).UtcTicks -le ([datetimeoffset]$exitProof.CapturedUtc).UtcTicks -or
       ([datetimeoffset]$exitProof.CapturedUtc).UtcTicks -le ([datetimeoffset]$hostProof.CapturedUtc).UtcTicks){
        throw 'E3 host/exit/absence ordering differs.'
    }
}
# E4 changes only the finite compiled-build projection. Request, provider sealing,
# argv, geometry guards and the historical E3 projection retain their contracts.
function Test-T7SelectedStreamedE4Build($Plan) {
    [bool]($Plan.PSObject.Properties['ExpectedBuildPlanSHA256'] -and
        $Plan.ExpectedBuildPlanSHA256 -ceq '26b46072a089c4ae67f601b134791c829a6223ce7a6c82b576f7bfce592c1c4d')
}
function Get-T7SelectedStreamedE4BuildPins($Plan) {
    if(!(Get-T7SelectedStreamedExport $Plan) -or !(Test-T7SelectedStreamedE4Build $Plan)){throw 'Exact E4 build selector required.'}
    $prepared=Join-Path (Split-Path $Plan.BuildPlan -Parent) 'prepared'
    $source=Split-Path (Split-Path (Split-Path $Plan.BuildPlan -Parent) -Parent) -Parent
    $root=Split-Path $Plan.BuildReceipt -Parent;$pins=[ordered]@{}
    foreach($row in @(
        @('BuildPlan',$Plan.BuildPlan,367367,'26b46072a089c4ae67f601b134791c829a6223ce7a6c82b576f7bfce592c1c4d'),
        @('BuildReceipt',$Plan.BuildReceipt,23683,'7f26c634aec1062440e68d0bcb50c0360d58196404ddf829d99422bf9b5e61f5'),
        @('Header',(Join-Path $prepared 't7_iw7_resident_model.hpp'),21290,'857d57b5f3c1c970f45e513e357215f3506e9c48b2daea4b4f62cb33e0d9bce4'),
        @('HostClosure',(Join-Path $root 'original-host-closure.local.json'),247,'a700e7ab1a0eac91943ca9b32827f8913778570aec44057b27c36df7b074d563'),
        @('HostExit',(Join-Path $root 'original-host-exit-request.local.json'),371,'d1e2eb794d5814de8cf91886059b7d9742f963f285e9dde351b686749a086e25'),
        @('Inventory',(Join-Path $root 'post-host-inventory.local.json'),1022,'1dddec32ce20a1321176d78608e08df85914516d334bce0a0d69ad80173f48e9'),
        @('Bundle',(Join-Path $root 'closure-bundle-final.local.json'),1438,'f91e4574d8e72d259b7794ff8a80e605bdb6f3b40c43f54edb70122f891a8cae'),
        @('ToolReturn',(Join-Path $root 'original-host-tool-return.local.json'),395,'e9497a0a36542134397577817ed5585681f98e26ba82093ff4239cf16a6ae6be'),
        @('Completion',(Join-Path $root 'completion.local.json'),8829,'2a08b8f0c139a29346d4733b6c02ad981713bc461adff809a35392b282cc9955'),
        @('SourceReceipt',(Join-Path $source 'source-workspace.json'),311246,'85f3b846aa0391a4b29cde9dff9aac6a24addbed86cfed22ab993379683c52d8'),
        @('NativeExport',(Join-Path $source 'tools-source/asset-bridge/t7-iw7/native_export.inc'),18268,'c6a197911d7adfef96273e29367e090666b130580356658478859f007165fa3d'),
        @('MaterialHeader',(Join-Path $source 'tools-source/asset-bridge/t7-iw7/selected_material_observation.hpp'),16489,'0ea84735fca2502033cc48a4eede6a19e1bd1283ba1975829f763c16e5ef343a'),
        @('MaterialFixture',(Join-Path $source 'tools-source/asset-bridge/t7-iw7/selected_material_observation_fixture.cpp'),13721,'cb27d4df66f3a186de3e0f5faedf7bf713610a2da0fc599861e5a4838ea2dfed'),
        @('PayloadHeader',(Join-Path $source 'tools-source/asset-bridge/t7-iw7/streamed_mesh_payload.hpp'),18512,'53265601cec86ba6e0b731e54d9c706f41d390756f4e4566ace70bd5fbd25adf'),
        @('StreamedHeader',(Join-Path $source 'tools-source/asset-bridge/t7-iw7/t7_iw7_streamed_model.hpp'),11289,'5eeaa89565bcfb2c5a1d899f78a47787584a1472caae9e84f04af1b8c886e5a0'),
        @('NativeStreamed',(Join-Path $source 'tools-source/asset-bridge/t7-iw7/native_streamed_export.inc'),9823,'60916d49cb4490f0cc508b699d9adaa02a780229fa5e69e3c66297f50c3b0123'),
        @('StreamedContract',(Join-Path $source 'tools-source/asset-bridge/t7-iw7/streamed_contract.py'),7996,'b7d68593b93975832cfa6362c2f782187772c2255cd59c78ab5aae66d759518f'),
        @('StreamedTest',(Join-Path $source 'tools-source/asset-bridge/t7-iw7/test_streamed_contract.py'),8796,'fe25379d80cc1ec328836a0e75652046c01b9ddadba3dba73c8e7a550bed1d16'))){
        $pin=[pscustomobject]@{Path=$row[1];Bytes=$row[2];SHA256=$row[3]}
        Assert-T7CatalogueTextPin $pin $Plan.Bindings;$pins[$row[0]]=$pin
    }
    if($Plan.ExpectedBuildReceiptSHA256 -cne $pins.BuildReceipt.SHA256 -or $Plan.CandidateBytes -ne 21919232 -or
       $Plan.CandidateSHA256 -cne '3dfa1b7851b7532526c38c295b1ed7014613dfbf3fd4db0225afd26b0457be71'){
        throw 'Exact compiled E4 receipt and candidate required.'
    }
    $pins
}
function Assert-T7SelectedStreamedE4Closure($Plan,$Receipt,$Build,$Pins) {
    Assert-T7CatalogueFields $Build.ReuseCompile.SelectedStreamedStaticV1 @('Schema','GeometryProfile')
    if($Build.ReuseCompile.SelectedStreamedStaticV1.Schema -cne 'iw7.t7-selected-streamed-static-build/1' -or
       $Build.ReuseCompile.SelectedStreamedStaticV1.GeometryProfile -cne 't7-iw7-selected-streamed-static-v1' -or
       $Build.ReuseCompile.PSObject.Properties['ZombiesObservationC'] -or
       $Build.BuildProfile.PreparedCLI.Bytes -ne 107785 -or
       $Build.BuildProfile.PreparedCLI.SHA256 -cne 'c480fbd39525df09bd5677026678743c73fa66eb3ca0752e78729eee2f4dcc50'){
        throw 'Exact E4 selected-streamed source profile required.'
    }
    foreach($name in 'NativeExport','MaterialHeader','MaterialFixture','PayloadHeader','StreamedHeader','NativeStreamed','StreamedContract','StreamedTest'){
        Assert-T7CatalogueTextPin $Pins[$name] $Build.Bindings
    }
    $source=Read-H1SmallJson $Pins.SourceReceipt.Path 512KB
    if($source.schema -cne 'iw7.source-workspace/1' -or
       $source.revisions.'x64-zt-extensions' -cne '8ff96b53ca4cc374b31f09182bd334770603e3fb' -or
       $source.revisions.'iw7-mod-components' -cne '2f9462db806bbd3ab51f9ecb2f3b25ae54ae10f1'){
        throw 'Exact E4 compilation source provenance required.'
    }
    $hostProof=Read-H1SmallJson $Pins.HostClosure.Path 2KB;$exitProof=Read-H1SmallJson $Pins.HostExit.Path 2KB
    $inventory=Read-H1SmallJson $Pins.Inventory.Path 2KB;$bundle=Read-H1SmallJson $Pins.Bundle.Path 4KB
    $tool=Read-H1SmallJson $Pins.ToolReturn.Path 2KB;$completion=Read-H1SmallJson $Pins.Completion.Path 16KB
    Assert-T7CatalogueFields $hostProof @('Schema','Host','HostCreationUtc','Session','Closed','LeaseNull','Guards','Status','CanExit')
    Assert-T7CatalogueFields $exitProof @('Schema','Host','HostCreationUtc','Session','PlanSHA256','CapturedUtc','Closed','LeaseNull','Guards','RequestedExitCode')
    foreach($proof in @($hostProof,$exitProof)){
        foreach($name in 'Closed','LeaseNull'){if($proof.$name -isnot [bool] -or !$proof.$name){throw 'E4 original host is not closed.'}}
        if($proof.Host -ne 400 -or $proof.Session -ne 19852 -or $proof.Guards -ne 0 -or
           ([datetimeoffset]$proof.HostCreationUtc).UtcTicks -ne ([datetimeoffset]'2026-10-13T23:23:48.5108279Z').UtcTicks){throw 'Exact E4 original host identity required.'}
    }
    if($hostProof.Schema -cne 'iw7.t7-original-build-host-closure/1' -or $hostProof.Status -cne 'Passed' -or
       $hostProof.CanExit -isnot [bool] -or !$hostProof.CanExit -or
       $exitProof.Schema -cne 'iw7.t7-original-build-host-exit-request/1' -or $exitProof.RequestedExitCode -ne 0 -or
       $exitProof.PlanSHA256 -cne $Plan.ExpectedBuildPlanSHA256 -or
       $inventory.Schema -cne 'iw7.t7-e4-post-host-inventory/1' -or $inventory.OriginalPTY -ne 19852 -or
       $inventory.ActualExitCode -ne 0 -or $inventory.OriginalExitChunk -cne 'b5624c' -or
       (@($inventory.OwnPIDSet) -join '|') -cne '25300|400|25580|20080|15196|21056|492|12008' -or
       @($inventory.OwnPresent).Count -ne 0 -or @($inventory.Heavy).Count -ne 0 -or @($inventory.ResourceStatus.Leases).Count -ne 0 -or
       $bundle.Schema -cne 'iw7.t7-e4-build-closure-bundle/2' -or $bundle.SourceMain -cne $source.revisions.'x64-zt-extensions' -or
       $bundle.PlanSHA256 -cne $Plan.ExpectedBuildPlanSHA256 -or $bundle.OriginalPTY -ne 19852 -or
       $bundle.ActualExitCode -ne 0 -or $bundle.ActualExitChunk -cne 'b5624c' -or @($bundle.Files).Count -ne 6){throw 'Exact original E4 closure evidence required.'}
    if($tool.Schema -cne 'iw7.t7-e4-original-host-tool-return/1' -or $tool.Session -ne 19852 -or
       $tool.ChunkId -cne 'b5624c' -or $tool.ExitCode -ne 0 -or $tool.OriginalInnerPID -ne 400 -or $tool.OriginalOuterPID -ne 25300 -or
       $completion.Schema -cne 'iw7.t7-e4-native-build-completion/1' -or $completion.SourceMain -cne $source.revisions.'x64-zt-extensions' -or
       $completion.PlanPath -cne $Pins.BuildPlan.Path -or $completion.PlanSHA256 -cne $Pins.BuildPlan.SHA256 -or
       $completion.ReceiptPath -cne $Pins.BuildReceipt.Path -or $completion.PostflightPath -cne $Pins.Inventory.Path -or
       $completion.Status -cne 'Passed' -or $completion.LeaseToken -cne $Receipt.LeaseToken){throw 'Exact E4 actual tool return and completion required.'}
    foreach($name in 'TreeClosureConfirmed','InputsReverified','LeaseReleased'){
        if($completion.$name -isnot [bool] -or !$completion.$name){throw 'E4 completion is not closed.'}
    }
    foreach($name in 'CandidateExecuted','Quarantined','Ready','StockExecuted','GeometryVerified','RuntimeVerified'){
        if($completion.$name -isnot [bool] -or $completion.$name){throw 'E4 build completion overclaims its scope.'}
    }
    foreach($name in 'Path','Bytes','SHA256'){
        if($completion.OriginalToolReturn.$name -cne $Pins.ToolReturn.$name){throw 'E4 completion tool pin differs.'}
    }
    foreach($pin in @($Pins.BuildReceipt,$Pins.HostClosure,$Pins.HostExit,$Pins.Inventory,$Pins.ToolReturn,$Pins.Completion)){
        if(@($bundle.Files|Where-Object {$_.Name -ceq [IO.Path]::GetFileName($pin.Path) -and $_.Bytes -eq $pin.Bytes -and $_.SHA256 -ceq $pin.SHA256}).Count -ne 1){throw 'E4 bundle pin differs.'}
    }
    for($i=0;$i -lt 3;$i++){
        $stage=$Receipt.Stages[$i];$snap=$stage.LastOriginalSnapshot
        if($stage.Identity.PID -ne @(25580,20080,15196)[$i] -or $snap.RootExited -isnot [bool] -or !$snap.RootExited -or
           $snap.RootExitCode -ne 0 -or $snap.ActiveProcesses -ne 0 -or $snap.PID -ne $stage.Identity.PID -or
           $snap.Image -cne $stage.Identity.Image -or ([datetimeoffset]$snap.CreatedUtc).UtcTicks -ne ([datetimeoffset]$stage.Identity.CreatedUtc).UtcTicks){throw 'Exact closed original E4 compiler/link jobs required.'}
    }
    if(([datetimeoffset]$inventory.CapturedUtc).UtcTicks -le ([datetimeoffset]$exitProof.CapturedUtc).UtcTicks -or
       ([datetimeoffset]$exitProof.CapturedUtc).UtcTicks -le ([datetimeoffset]$hostProof.HostCreationUtc).UtcTicks){throw 'E4 host/exit/absence ordering differs.'}
}
function Get-T7SelectedStreamedE5BuildPins($Plan) {
    if(!(Get-T7SelectedStreamedRenderOnly $Plan)){throw 'Explicit E5 render-only selector required.'}
    $prepared=Join-Path (Split-Path $Plan.BuildPlan -Parent) 'prepared'
    $source=Split-Path (Split-Path (Split-Path $Plan.BuildPlan -Parent) -Parent) -Parent
    $root=Split-Path $Plan.BuildReceipt -Parent;$pins=[ordered]@{}
    foreach($row in @(
        @('BuildPlan',$Plan.BuildPlan,368157,'b702de6b61403a2abd3be6a01a2504058d58bdfb082dc67d9b07e6cd6a911063'),
        @('BuildReceipt',$Plan.BuildReceipt,24288,'942c4963e40ee18e10a9bcafdd8fc38b8140582e6fcea479f6c95ebce68b61b8'),
        @('Header',(Join-Path $prepared 't7_iw7_resident_model.hpp'),21290,'857d57b5f3c1c970f45e513e357215f3506e9c48b2daea4b4f62cb33e0d9bce4'),
        @('HostClosure',(Join-Path $root 'original-host-closure.local.json'),339,'5cec4f0db38b6b0546df2aaeda046e122c0f3f16cc5e2dad2c2a9d4ca0594c0e'),
        @('HostExit',(Join-Path $root 'original-host-exit-request.local.json'),372,'b2101fc68afdeab89cfa66db64355e02a619918924b4ce940732e459ee7a674b'),
        @('Inventory',(Join-Path $root 'post-host-inventory.local.json'),964,'20d2a0cfec5759e6917d5f6e874e60efacc5f5151d68e943329ba08aaa137aaf'),
        @('Bundle',(Join-Path $root 'closure-bundle-final.local.json'),1341,'6ba7950c10bd925711ac284f8077f2ed140ac6f1b24f5a36622547ce9e16dd13'),
        @('ToolReturn',(Join-Path $root 'original-host-tool-return.local.json'),373,'670bdf6ac2935440505b1a211dc8b7892c2165aa50ecbd965443503f60dcc0b0'),
        @('Completion',(Join-Path $root 'completion.local.json'),14273,'e5a2d25bdccc482dfd00b94379eb74683af2edcfa3b1ac72e479e5160130f0fe'),
        @('SourceReceipt',(Join-Path $source 'source-workspace.json'),311609,'973e77d41e8300ec3330987ada8bdca4a2bb0e7a3c4d625381511cd4d6117051'),
        @('NativeExport',(Join-Path $source 'tools-source/asset-bridge/t7-iw7/native_export.inc'),18796,'ea2904c37beeaa652c9a56b66775f3a45df0de4250095059dc0769b79f7d7fdd'),
        @('MaterialHeader',(Join-Path $source 'tools-source/asset-bridge/t7-iw7/selected_material_observation.hpp'),18583,'a8848a92b8d7918fbe91ec4b68df123b1eaab89edde9d8a7c24d5a0cfb576ffc'),
        @('MaterialFixture',(Join-Path $source 'tools-source/asset-bridge/t7-iw7/selected_material_observation_fixture.cpp'),20260,'b3de68880b6f8c717c2e70ed44497ae2f95f37db7e73bbf34ef014d8e5b6fc6f'),
        @('PayloadHeader',(Join-Path $source 'tools-source/asset-bridge/t7-iw7/streamed_mesh_payload.hpp'),18512,'53265601cec86ba6e0b731e54d9c706f41d390756f4e4566ace70bd5fbd25adf'),
        @('StreamedHeader',(Join-Path $source 'tools-source/asset-bridge/t7-iw7/t7_iw7_streamed_model.hpp'),11951,'04007fa53fc6a3cc0307a589e7f28cebfa1c2a37c6071e0a2cb9ded412782453'),
        @('NativeStreamed',(Join-Path $source 'tools-source/asset-bridge/t7-iw7/native_streamed_export.inc'),10919,'f4fdc95d6a29bbe36c9140beff11567ab3ecc4d87f3c28e1e4e7fa4a25ec92c7'),
        @('StreamedContract',(Join-Path $source 'tools-source/asset-bridge/t7-iw7/streamed_contract.py'),10366,'cc584cf6d2ff82be77b9ef0e926cda75ac7768f85e906d6eef22c2f8c2572df4'),
        @('StreamedTest',(Join-Path $source 'tools-source/asset-bridge/t7-iw7/test_streamed_contract.py'),13768,'86392ae7934213692ae4c9453579d4b006d2665d6a80aaf52e39a41edc18bb3c'))){
        $pin=[pscustomobject]@{Path=$row[1];Bytes=$row[2];SHA256=$row[3]};Assert-T7CatalogueTextPin $pin $Plan.Bindings;$pins[$row[0]]=$pin
    }
    if($Plan.ExpectedBuildPlanSHA256 -cne $pins.BuildPlan.SHA256 -or $Plan.ExpectedBuildReceiptSHA256 -cne $pins.BuildReceipt.SHA256 -or
       $Plan.CandidateBytes -ne 21924864 -or $Plan.CandidateSHA256 -cne 'aa322cac65d61d2ed8fa544f79a117201a3fcde8408b6b6cb59ea745f20f5d2f'){throw 'Exact compiled E5 v2 build and candidate required.'}
    $pins
}
function Assert-T7SelectedStreamedE5Closure($Plan,$Receipt,$Build,$Pins) {
    $marker=$Build.ReuseCompile.SelectedStreamedRenderOnlyV2
    Assert-T7CatalogueFields $marker @('Schema','GeometryProfile','CollisionPolicy')
    if($marker.Schema -cne 'iw7.t7-selected-streamed-render-only-build/2' -or $marker.GeometryProfile -cne 't7-iw7-selected-streamed-render-only-v2' -or
       $marker.CollisionPolicy -cne 'omit-source-rigid-collision-trees' -or $Build.ReuseCompile.PSObject.Properties['SelectedStreamedStaticV1'] -or
       $Build.ReuseCompile.PSObject.Properties['ZombiesObservationC'] -or $Build.BuildProfile.PreparedCLI.Bytes -ne 112377 -or
       $Build.BuildProfile.PreparedCLI.SHA256 -cne 'c63d9552464da674d3b03c35f7edc16385fb9370b113a3925fd7bc4835fb005a'){throw 'Exact E5 v2 compiler profile required.'}
    foreach($name in 'NativeExport','MaterialHeader','MaterialFixture','PayloadHeader','StreamedHeader','NativeStreamed','StreamedContract','StreamedTest'){Assert-T7CatalogueTextPin $Pins[$name] $Build.Bindings}
    $source=Read-H1SmallJson $Pins.SourceReceipt.Path 512KB
    if($source.schema -cne 'iw7.source-workspace/1' -or $source.revisions.'x64-zt-extensions' -cne 'af41e7680da51ac67d4a52bc4fad978b9ccf44e8' -or
       $source.revisions.'iw7-mod-components' -cne '2f9462db806bbd3ab51f9ecb2f3b25ae54ae10f1'){throw 'Exact E5 compilation source provenance required.'}
    $hostProof=Read-H1SmallJson $Pins.HostClosure.Path 2KB;$exitProof=Read-H1SmallJson $Pins.HostExit.Path 2KB
    $tool=Read-H1SmallJson $Pins.ToolReturn.Path 2KB;$inventory=Read-H1SmallJson $Pins.Inventory.Path 2KB
    $completion=Read-H1SmallJson $Pins.Completion.Path 16KB;$bundle=Read-H1SmallJson $Pins.Bundle.Path 4KB
    Assert-T7CatalogueFields $completion.SourceMarker @('Schema','GeometryProfile','CollisionPolicy')
    foreach($name in 'Schema','GeometryProfile','CollisionPolicy'){
        if($completion.SourceMarker.$name -cne $marker.$name){throw 'E5 completion source marker differs.'}
    }
    if($hostProof.Schema -cne 'iw7.t7-e5-original-build-host-closure/1' -or $exitProof.Schema -cne 'iw7.t7-e5-original-host-exit-request/1' -or
       $tool.Schema -cne 'iw7.t7-e5-original-host-tool-return/1' -or $inventory.Schema -cne 'iw7.t7-e5-post-host-inventory/1' -or
       $completion.Schema -cne 'iw7.t7-e5-native-build-completion/1' -or $bundle.Schema -cne 'iw7.t7-e5-build-closure-bundle/1'){throw 'Exact original E5 closure schemas required.'}
    foreach($proof in @($hostProof,$exitProof)){
        foreach($name in 'Closed','LeaseNull'){if($proof.$name -isnot [bool] -or !$proof.$name){throw 'E5 original host is not closed.'}}
        if($proof.Host -ne 14904 -or $proof.Session -ne 83868 -or $proof.Guards -ne 0 -or $proof.PlanSHA256 -cne $Pins.BuildPlan.SHA256 -or
           ([datetimeoffset]$proof.HostCreationUtc).UtcTicks -ne ([datetimeoffset]'2026-10-14T00:28:39.6665468Z').UtcTicks){throw 'Exact E5 original host identity required.'}
    }
    if($hostProof.Status -cne 'Passed' -or $hostProof.CanExit -isnot [bool] -or !$hostProof.CanExit -or $exitProof.RequestedExitCode -ne 0 -or
       $tool.Session -ne 83868 -or $tool.ChunkId -cne 'dfb099' -or $tool.ExitCode -ne 0 -or $tool.OriginalInnerPID -ne 14904 -or $tool.OriginalOuterPID -ne 25564 -or
       ([datetimeoffset]$tool.OriginalInnerCreationUtc).UtcTicks -ne ([datetimeoffset]$hostProof.HostCreationUtc).UtcTicks -or
       $inventory.OriginalPTY -ne 83868 -or (@($inventory.OwnPIDSet)-join '|') -cne '25564|14904|22580|5220|2560|2888|8452|15080' -or
       @($inventory.OwnPresent).Count -ne 0 -or @($inventory.Heavy).Count -ne 0 -or @($inventory.ResourceStatus.Leases).Count -ne 0 -or
       $completion.SourceHead -cne $source.revisions.'x64-zt-extensions' -or $completion.PlanPath -cne $Pins.BuildPlan.Path -or
       $completion.PlanSHA256 -cne $Pins.BuildPlan.SHA256 -or $completion.ReceiptPath -cne $Pins.BuildReceipt.Path -or $completion.PostflightPath -cne $Pins.Inventory.Path -or
       $completion.Status -cne 'Passed' -or $completion.LeaseToken -cne $Receipt.LeaseToken -or
       $bundle.SourceHead -cne $source.revisions.'x64-zt-extensions' -or $bundle.PlanSHA256 -cne $Pins.BuildPlan.SHA256 -or
       $bundle.OriginalPTY -ne 83868 -or $bundle.ActualExitCode -ne 0 -or $bundle.ActualExitChunk -cne 'dfb099' -or @($bundle.Files).Count -ne 6){throw 'Exact E5 actual tool/build completion required.'}
    foreach($name in 'InputsReverified','TreeClosureConfirmed','LeaseReleased'){if($completion.$name -isnot [bool] -or !$completion.$name){throw 'E5 completion is not closed.'}}
    foreach($name in 'Path','Bytes','SHA256'){
        if($completion.OriginalToolReturn.$name -cne $Pins.ToolReturn.$name){throw 'E5 completion tool pin differs.'}
    }
    foreach($proof in @(@{Object=$completion;Names=@('CandidateExecuted','Quarantined','StockExecuted','GeometryVerified','RuntimeVerified','Ready')},@{Object=$bundle;Names=@('OpaqueArtifactsReread')})){
        foreach($name in $proof.Names){if($proof.Object.$name -isnot [bool] -or $proof.Object.$name){throw 'E5 build evidence overclaims its scope.'}}
    }
    foreach($pin in @($Pins.BuildReceipt,$Pins.HostClosure,$Pins.HostExit,$Pins.ToolReturn,$Pins.Inventory,$Pins.Completion)){
        if(@($bundle.Files|Where-Object {$_.Name -ceq [IO.Path]::GetFileName($pin.Path) -and $_.Bytes -eq $pin.Bytes -and $_.SHA256 -ceq $pin.SHA256}).Count -ne 1){throw 'E5 bundle pin differs.'}
    }
    for($i=0;$i -lt 3;$i++){$stage=$Receipt.Stages[$i];$snap=$stage.LastOriginalSnapshot
        if($stage.Identity.PID -ne @(22580,5220,2560)[$i] -or $snap.RootExited -isnot [bool] -or !$snap.RootExited -or $snap.RootExitCode -ne 0 -or $snap.ActiveProcesses -ne 0 -or
           $snap.PID -ne $stage.Identity.PID -or $snap.Image -cne $stage.Identity.Image -or ([datetimeoffset]$snap.CreatedUtc).UtcTicks -ne ([datetimeoffset]$stage.Identity.CreatedUtc).UtcTicks){throw 'Exact closed original E5 compiler/link jobs required.'}
    }
    if(([datetimeoffset]$inventory.CapturedUtc).UtcTicks -le ([datetimeoffset]$exitProof.CapturedUtc).UtcTicks -or
       ([datetimeoffset]$exitProof.CapturedUtc).UtcTicks -le ([datetimeoffset]$hostProof.HostCreationUtc).UtcTicks){throw 'E5 original lifecycle ordering differs.'}
}
function Assert-T7SelectedStreamedCollisionPolicy($Policy,[int]$Surfaces) {
    Assert-T7CatalogueFields $Policy @('policy','scope','source_tree_present','cpu_tree_present','collision_dropped','collision_tree_payload_bytes_read','collision_conversion_attempted','collision_compatibility_verified','ready')
    if($Policy.policy -isnot [string] -or $Policy.scope -isnot [string] -or
       $Policy.policy -cne 'omit-source-rigid-collision-trees' -or $Policy.scope -cne 'render-only' -or
       !(Test-T7CatalogueInteger $Policy.collision_tree_payload_bytes_read 0)){throw 'Exact render-only collision scope and zero payload read required.'}
    foreach($name in 'source_tree_present','cpu_tree_present','collision_dropped'){
        if($Policy.$name -isnot [array] -or $Policy.$name.Count -ne $Surfaces){throw 'Exactly N ordered collision booleans required.'}
        foreach($value in $Policy.$name){if($value -isnot [bool]){throw 'Exact collision booleans required.'}}
    }
    for($i=0;$i -lt $Surfaces;$i++){if($Policy.cpu_tree_present[$i] -or $Policy.collision_dropped[$i] -ne $Policy.source_tree_present[$i]){throw 'Foreign trees must be omitted only in the CPU view.'}}
    foreach($name in 'collision_conversion_attempted','collision_compatibility_verified','ready'){if($Policy.$name -isnot [bool] -or $Policy.$name){throw 'Collision conversion and compatibility remain unproved.'}}
}
function Assert-T7SelectedStreamedRequest($Request,[switch]$RenderOnly) {
    $fields=@('schema','target','profile','zone','model','lod','xpak_key','packages')
    if($RenderOnly){$fields+=@('collision_policy')}
    Assert-T7CatalogueFields $Request $fields
    $schema=if($RenderOnly){'iw7.t7-iw7-selected-streamed-request/2'}else{'iw7.t7-iw7-selected-streamed-request/1'}
    $profile=if($RenderOnly){'selected-streamed-render-only-rigid-one-lod'}else{'selected-streamed-rigid-one-lod'}
    if($Request.schema -cne $schema -or $Request.target -cne 'iw7' -or
       $Request.profile -cne $profile -or $Request.zone -cne 'mp_freerun_04' -or
       $Request.model -cne 'p7_fre_platform_cap_02' -or !(Test-T7CatalogueInteger $Request.lod 0) -or
       $Request.xpak_key -cne 'f58d58f1fc9b6b01' -or $Request.packages -isnot [array] -or $Request.packages.Count -ne 1){
        throw 'Only the observed E3 donor/key and single qualified provider are admitted.'
    }
    $package=$Request.packages[0];Assert-T7CatalogueFields $package @('path','identity','bytes')
    if($package.path -cne 'zone/mp_initial.xpak' -or $package.identity -cne 'D088B64A:000C0000001EB2FD' -or
       !(Test-T7CatalogueInteger $package.bytes 654311424) -or $package.bytes -ne 654311424){throw 'Exact observed E3 provider required.'}
    if($RenderOnly -and ($Request.collision_policy -isnot [string] -or $Request.collision_policy -cne 'omit-source-rigid-collision-trees')){throw 'Exact E5 render-only collision policy required.'}
}
function Get-T7ResidentExportOutputKey($Plan) {
    if(!(Get-T7SelectedStreamedExport $Plan)){return (Get-T7ResidentExportKey $Plan.ExportRequest)}
    $request=Read-T7SelectedStreamedRequestFile $Plan
    $geometry=if(Get-T7SelectedStreamedRenderOnly $Plan){'t7-iw7-selected-streamed-render-only-v2'}else{'t7-iw7-selected-streamed-static-v1'}
    $rows=@($geometry,$request.zone,$request.model,'0',$request.xpak_key,
        $request.packages[0].path,$request.packages[0].identity,[string]$request.packages[0].bytes)
    't7_iw7_streamed_'+[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::ASCII.GetBytes(($rows -join "`n")))).ToLowerInvariant()
}
function Get-T7SelectedStreamedOutputPathProof($Plan) {
    if(!(Get-T7SelectedStreamedRenderOnly $Plan)){throw 'Output path guard requires the explicit E5 donor route.'}
    $request=Read-T7SelectedStreamedRequestFile $Plan
    Assert-T7SelectedStreamedRequest $request -RenderOnly
    $root=Join-Path (Join-Path $Plan.WorkingDirectory 'dump') (Get-T7ResidentExportOutputKey $Plan)
    # This route admits only the qualified platform donor and its observed mesh name.
    $paths=@(foreach($relative in @('manifest.json','xmodel/p7_fre_platform_cap_02.xmb','xsurface/p7_fre_platform_cap_02_lod0ca80354f.xsb')){
        $path=[IO.Path]::GetFullPath((Join-Path $root $relative));Assert-H1Path $path
        $characters=$path.Length+1 # MAX_PATH includes the terminating NUL.
        if($characters -ge 260){throw 'E5 CRT output paths including NUL must be shorter than 260 characters; use a fresh short RunRoot.'}
        [pscustomobject]@{RelativePath=$relative;Path=$path;CharactersIncludingNul=$characters}
    })
    [pscustomobject]@{Schema='iw7.t7-e5-output-path-proof/1';Paths=$paths;CRTPathLimitIncludingNul=260;OpaqueOutputRead=$false;NativeStarted=$false}
}
function Assert-T7SelectedStreamedProvider($Plan) {
    if(!(Get-T7SelectedStreamedExport $Plan)){return}
    Assert-T7CatalogueFields $Plan.SelectedXpakProvider @('Metadata','RelativePath','FileId','HeaderSHA256','IndexOffset','IndexBytes','IndexSHA256','EntryOffset','PayloadOffset','PayloadBytes')
    $p=$Plan.SelectedXpakProvider;$m=$p.Metadata
    Assert-T7CatalogueFields $m @('Path','Bytes','Attributes','LastWriteUtc','CreationUtc')
    Assert-H1Path $m.Path
    if([IO.Path]::GetFileName($m.Path) -cne 'mp_initial.xpak' -or $m.Bytes -ne 654311424 -or $m.Attributes -cne 'Archive' -or
       $p.RelativePath -cne 'zone/mp_initial.xpak' -or $p.FileId -cne 'D088B64A:000C0000001EB2FD' -or
       $p.HeaderSHA256 -cne 'cdba1da8159369941de080768c536852a71af332a02f41e946916337fbb4ea88' -or
       $p.IndexOffset -ne 653787136 -or $p.IndexBytes -ne 31152 -or
       $p.IndexSHA256 -cne 'f1c5a39dd5372081b06aa391899888806e78979c22649a043d7bf85548b13257' -or
       $p.EntryOffset -ne 653815768 -or $p.PayloadOffset -ne 146723456 -or $p.PayloadBytes -ne 7680){throw 'Exact admitted provider/header/index/target extent required.'}
    # This large package must never enter the ordinary whole-file SHA pin path.
    if(@($Plan.Bindings|Where-Object Path -CEQ $m.Path).Count){throw 'Selected XPAK cannot be a whole-file H1 binding.'}
    $renderOnly=Get-T7SelectedStreamedRenderOnly $Plan
    $requestBytes=if($renderOnly){463}else{377};$requestSHA=if($renderOnly){'66e9d49388dfe18bd5c088ef0c945ede544b4410c0dc31ae8e1b95efaf21db8d'}else{'2f79f63fdf6378ee420b0f63ef5e1d19dedcb55909a77f759ac071247839502c'}
    if($Plan.ExportRequestFile.Bytes -ne $requestBytes -or $Plan.ExportRequestFile.SHA256 -cne $requestSHA){
        throw 'Exact independently validated request bytes required.'
    }
    $request=Read-T7SelectedStreamedRequestFile $Plan
    foreach($metadata in @($m,$Plan.SelectedStreamedRequestMetadata)){
        Assert-T7CatalogueMetadata $metadata
        $rows=@($Plan.InputMetadata|Where-Object Path -CEQ $metadata.Path)
        if($rows.Count -ne 1 -or ($rows[0]|ConvertTo-Json -Compress) -cne ($metadata|ConvertTo-Json -Compress)){throw 'Selected provider/request metadata not retained in exact input rows.'}
    }
    if($Plan.SelectedStreamedRequestMetadata.Path -cne $Plan.ExportRequestFile.Path -or
       $Plan.SelectedStreamedRequestMetadata.Bytes -ne $requestBytes){throw 'Request alias source metadata differs.'}
    if(([datetimeoffset]$m.LastWriteUtc).UtcDateTime.ToFileTimeUtc() -ne 134362733249245718L -or
       ([datetimeoffset]$m.CreationUtc).UtcDateTime.ToFileTimeUtc() -ne 134362732743239258L){throw 'Selected provider dates differ from discovery.'}
}
function Get-T7SelectedStreamedLinks($Plan) {
    if(!(Get-T7SelectedStreamedExport $Plan)){return}
    ,@($Plan.ExportRequestFile.Path,'streamed-request.json')
    ,@($Plan.SelectedXpakProvider.Metadata.Path,$Plan.SelectedXpakProvider.RelativePath)
}
function Read-T7SelectedStreamedDigest($Stream,[long]$Offset,[int]$Bytes) {
    if($Bytes -le 0 -or $Bytes -gt 8MB -or $Offset -lt 0 -or $Offset -gt $Stream.Length-$Bytes){throw 'Bounded selected metadata range required.'}
    $buffer=[byte[]]::new($Bytes);$Stream.Position=$Offset;$read=0
    while($read -lt $Bytes){$n=$Stream.Read($buffer,$read,$Bytes-$read);if(!$n){throw 'Truncated selected metadata range.'};$read+=$n}
    [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($buffer)).ToLowerInvariant()
}
function Open-T7SelectedStreamedProvider($Plan,[string]$Path,$Context) {
    Assert-T7SelectedStreamedProvider $Plan;$p=$Plan.SelectedXpakProvider
    $alias=Join-Path $Plan.WorkingDirectory $p.RelativePath
    if($Path -cne $p.Metadata.Path -and $Path -cne $alias){throw 'Only the admitted original or its exact selected alias allowed.'}
    Assert-H1Path $Path
    $guard=[IO.FileStream]::new($Path,'Open','Read','Read')
    try {
        $f=Get-Item -LiteralPath $Path
        if($guard.Length -ne $p.Metadata.Bytes -or (Get-T7CatalogueFileId $Path) -cne $p.FileId -or
           $f.Attributes.ToString() -cne $p.Metadata.Attributes -or
           $f.LastWriteTimeUtc.Ticks -ne ([datetimeoffset]$p.Metadata.LastWriteUtc).UtcTicks -or
           $f.CreationTimeUtc.Ticks -ne ([datetimeoffset]$p.Metadata.CreationUtc).UtcTicks){throw 'Retained selected XPAK identity/metadata changed.'}
        if((Read-T7SelectedStreamedDigest $guard 0 120) -cne $p.HeaderSHA256 -or
           (Read-T7SelectedStreamedDigest $guard $p.IndexOffset $p.IndexBytes) -cne $p.IndexSHA256){throw 'Selected header/index differs from qualified discovery.'}
        if((Get-T7CatalogueFileId $Path) -cne $p.FileId -or $guard.Length -ne $p.Metadata.Bytes){throw 'Selected XPAK changed while observed.'}
        $guard.Position=0;$Context.Guards.Add($guard);$guard=$null
        [pscustomobject]@{Path=$Path;Source=$p.Metadata.Path;Bytes=$p.Metadata.Bytes;FileId=$p.FileId;GuardScope='SelectedXpakHeaderIndex';HeaderSHA256=$p.HeaderSHA256;IndexSHA256=$p.IndexSHA256}
    }finally{if($guard){$guard.Dispose()}}
}
function New-T7SelectedStreamedAliases($Plan,$Context) {
    if(!(Get-T7SelectedStreamedExport $Plan)){return}
    $null=Open-T7SelectedStreamedProvider $Plan $Plan.SelectedXpakProvider.Metadata.Path $Context
    New-T7CatalogueAlias $Plan.ExportRequestFile (Join-Path $Plan.WorkingDirectory 'streamed-request.json') $Context
    $destination=Join-Path $Plan.WorkingDirectory $Plan.SelectedXpakProvider.RelativePath
    Assert-H1Path $destination;if(Test-Path -LiteralPath $destination){throw 'Selected alias destination exists.'}
    New-Item -ItemType HardLink -Path $destination -Target $Plan.SelectedXpakProvider.Metadata.Path -ErrorAction Stop|Out-Null
    Open-T7SelectedStreamedProvider $Plan $destination $Context
}
function Assert-T7SelectedStreamedPayload($Payload,$Plan,[int]$Surfaces) {
    Assert-T7CatalogueFields $Payload @('key_hex','source_shared_flags','cpu_view_shared_flags','source_surface_flags','opaque_descriptor_words_hex','descriptor_field_semantics_verified',
        'package_path','package_identity','file_bytes','hash_table_offset','hash_entry_offset','payload_offset','compressed_bytes','packed_entry_size','indexed_bytes','opcodes','opaque_header_offsets',
        'payload_bytes','payload_sha256','headers_rechecked','atomic_snapshot_proven','engine_object_writes')
    $p=$Plan.SelectedXpakProvider
    foreach($name in 'source_shared_flags','cpu_view_shared_flags','file_bytes','hash_table_offset','hash_entry_offset','payload_offset','compressed_bytes','packed_entry_size','indexed_bytes','payload_bytes'){
        if(!(Test-T7CatalogueInteger $Payload.$name ([long]::MaxValue))){throw 'Exact integer payload scalars required.'}
    }
    if($Payload.key_hex -cne 'f58d58f1fc9b6b01' -or $Payload.source_shared_flags -ne 9 -or $Payload.cpu_view_shared_flags -ne 8 -or
       $Payload.package_path -cne $p.RelativePath -or $Payload.package_identity -cne $p.FileId -or $Payload.file_bytes -ne $p.Metadata.Bytes -or
       $Payload.hash_table_offset -ne $p.IndexOffset -or $Payload.hash_entry_offset -ne $p.EntryOffset -or $Payload.payload_offset -ne $p.PayloadOffset -or
       $Payload.compressed_bytes -ne $p.PayloadBytes -or $Payload.packed_entry_size -ne 7680 -or $Payload.indexed_bytes -ne $p.IndexBytes -or
       $Payload.payload_bytes -ne 18624 -or $Payload.payload_sha256 -cnotmatch '\A[0-9a-f]{64}\z' -or
       $Payload.headers_rechecked -isnot [bool] -or !$Payload.headers_rechecked){throw 'Native selected payload differs from admitted exact key/provider/extent.'}
    foreach($name in 'descriptor_field_semantics_verified','atomic_snapshot_proven','engine_object_writes'){
        if($Payload.$name -isnot [bool] -or $Payload.$name){throw 'Selected payload overclaims descriptor/atomic/engine state.'}
    }
    if($Payload.source_surface_flags -isnot [array] -or $Payload.source_surface_flags.Count -ne $Surfaces -or
       $Payload.opaque_descriptor_words_hex -isnot [array] -or $Payload.opaque_descriptor_words_hex.Count -ne 3){throw 'Exact selected surface and opaque-word arrays required.'}
    foreach($word in $Payload.opaque_descriptor_words_hex){if($word -isnot [string] -or $word -cnotmatch '\A[0-9a-f]{16}\z'){throw 'Exact uint64 hex strings required.'}}
    foreach($flag in $Payload.source_surface_flags){if(!(Test-T7CatalogueInteger $flag 65535) -or ($flag -band 2)){throw 'Only bounded raw rigid surface flags admitted.'}}
    if($Payload.opaque_header_offsets -isnot [array] -or $Payload.opaque_header_offsets.Count -lt 1 -or $Payload.opaque_header_offsets.Count -gt 128 -or
       $Payload.opcodes -isnot [array] -or $Payload.opcodes.Count -lt $Payload.opaque_header_offsets.Count -or
       $Payload.opcodes.Count -gt 30*$Payload.opaque_header_offsets.Count){throw 'Bounded observed packet commands required.'}
    foreach($v in $Payload.opaque_header_offsets){if(!(Test-T7CatalogueInteger $v ([uint32]::MaxValue))){throw 'Bounded opaque header offsets required.'}}
    foreach($v in $Payload.opcodes){if(!(Test-T7CatalogueInteger $v 3) -or $v -cnotin @(0,3)){throw 'Only observed raw/LZ4 opcodes admitted.'}}
}
function Read-T7SelectedStreamedRequestFile($Plan) {
    Assert-T7CatalogueTextPin $Plan.ExportRequestFile $Plan.Bindings
    if($Plan.ExportRequestFile.Bytes -gt 4KB){throw 'Bounded flat request required.'}
    $guard=Open-H1Pin $Plan.ExportRequestFile
    try{$request=Read-H1SmallJson $Plan.ExportRequestFile.Path 4KB;Assert-T7SelectedStreamedRequest $request -RenderOnly:(Get-T7SelectedStreamedRenderOnly $Plan);return $request}
    finally{$guard.Dispose()}
}
