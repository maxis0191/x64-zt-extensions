# Default checks source/metadata only. Native execution needs a reviewed exact
# plan and separate coordinator GO; no ZoneTool/game launch exists in this runner.
[CmdletBinding()]
param([Parameter(Mandatory)][string]$PlanPath,[Parameter(Mandatory)][string]$PlanSHA256,[switch]$Run)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
if(!$IsWindows -or [IntPtr]::Size -ne 8 -or $PSVersionTable.PSVersion.Major -lt 7){throw 'Windows x64 PowerShell 7 required.'}
if($PlanSHA256 -cnotmatch '^[0-9a-f]{64}$'){throw 'Exact reviewed plan SHA256 required.'}
$guards=[Collections.Generic.List[object]]::new()
$context=[pscustomobject]@{Owner=$null;Closed=$true;Lease=$null;Guards=$guards}
$state=$null;$failure=$null;$created=$false;$launcher=$null;$priority=$null
function Open-T7Bootstrap($Path,[long]$Bytes,[string]$SHA256) {
    if(![IO.Path]::IsPathFullyQualified($Path) -or [IO.Path]::GetFullPath($Path) -cne $Path){throw 'Canonical bootstrap path required.'}
    for($part=$Path;$part;$part=[IO.Path]::GetDirectoryName($part)) {
        if(([IO.File]::GetAttributes($part) -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Bootstrap reparse path refused.'}
    }
    if($Bytes -le 0 -or $Bytes -gt 32MB -or $SHA256 -cnotmatch '^[0-9a-f]{64}$'){throw 'Invalid source binding.'}
    $stream=[IO.FileStream]::new($Path,'Open','Read','Read');$guards.Add($stream)
    if($stream.Length -ne $Bytes){throw 'Bootstrap length differs.'}
    $hash=[Security.Cryptography.SHA256]::Create()
    try{$actual=[Convert]::ToHexString($hash.ComputeHash($stream)).ToLowerInvariant()}finally{$hash.Dispose()}
    if($actual -cne $SHA256){throw 'Bootstrap source differs.'}
    $stream.Position=0;return $stream
}
function Assert-T7BuildProfile($Plan,[string]$SourceRoot) {
    $profile=if($Plan.PSObject.Properties.Name -contains 'BuildProfile'){$Plan.BuildProfile}else{$null}
    $recompiled=$Plan.PSObject.Properties.Name -contains 'ReuseCompile' -and $null -ne $Plan.ReuseCompile -and
        $Plan.ReuseCompile.PSObject.Properties.Name -contains 'RecompiledMain' -and
        $Plan.ReuseCompile.RecompiledMain -is [bool] -and $Plan.ReuseCompile.RecompiledMain
    $cliMarker=$Plan.PSObject.Properties.Name -contains 'ReuseCompile' -and $null -ne $Plan.ReuseCompile -and
        $Plan.ReuseCompile.PSObject.Properties.Name -contains 'RecompiledZonetool'
    $zombies=$null -ne $profile -and $profile.Name -ceq 't7-zombies-catalogue-observation-c'
    $add=$null -ne $profile -and $profile.Name -ceq 't7-zombies-catalogue-observation-c2'
    $publication=$null -ne $profile -and $profile.Name -cin @('t7-catalog-message-publication','t7-zombies-catalogue-observation-c','t7-zombies-catalogue-observation-c2')
    if($cliMarker -and !$publication){throw 'CLI rebuild marker requires the publication profile.'}
    if($publication -and (!$cliMarker -or $Plan.ReuseCompile.RecompiledZonetool -isnot [bool] -or
        !$Plan.ReuseCompile.RecompiledZonetool)){throw 'Publication requires both fresh translation units.'}
    if($null -eq $profile) {
        if($recompiled){throw 'Recompiled main requires the explicit diagnostic profile.'}
        return $false
    }
    if(!$recompiled){throw 'Explicit profile requires a main rebuild.'}
    if($profile.Name -ceq 't7-prepatch-probe') {
        if($profile.Option -cne '-t7-prepatch-probe' -or $profile.ArgumentCount -ne 2 -or
           $profile.Report -cne 't7-prepatch-probe.local.json'){throw 'Exact pre-patch profile required.'}
        $paths=@{
            Helper=(Join-Path $Plan.PreparedRoot 'native_prepatch_probe.inc')
            Wiring=(Join-Path $SourceRoot 'prepare_prepatch.py')
            PreparedMain=(Join-Path $Plan.PreparedRoot 'main.cpp')
        }
    } elseif($profile.Name -cin @('t7-catalog-trace','t7-catalog-exit-context','t7-catalog-callers','t7-catalog-message','t7-catalog-message-publication','t7-zombies-catalogue-observation-c','t7-zombies-catalogue-observation-c2')) {
        $fields='ArgumentCount,BaseBuildPlan,BaseBuildReceipt,Name,Option,PreparedMain,TraceSchema,Wiring'
        if($profile.Name -cin @('t7-catalog-exit-context','t7-catalog-callers','t7-catalog-message','t7-catalog-message-publication','t7-zombies-catalogue-observation-c','t7-zombies-catalogue-observation-c2')) {
            if($profile.ContextSchema -cne 'iw7.t7-catalog-exit-context/1'){throw 'Exact exit-context schema required.'}
            $fields='ArgumentCount,BaseBuildPlan,BaseBuildReceipt,ContextSchema,Name,Option,PreparedMain,TraceSchema,Wiring'
        }
        if($profile.Name -cin @('t7-catalog-callers','t7-catalog-message','t7-catalog-message-publication','t7-zombies-catalogue-observation-c','t7-zombies-catalogue-observation-c2')) {
            if($profile.CallerSchema -cne 'iw7.t7-catalog-callers/1'){throw 'Exact caller schema required.'}
            $fields='ArgumentCount,BaseBuildPlan,BaseBuildReceipt,CallerSchema,ContextSchema,Name,Option,PreparedMain,TraceSchema,Wiring'
        }
        if($profile.Name -cin @('t7-catalog-message','t7-catalog-message-publication','t7-zombies-catalogue-observation-c','t7-zombies-catalogue-observation-c2')) {
            if($profile.MessageSchema -cne 'iw7.t7-catalog-message/1'){throw 'Exact message schema required.'}
            $fields='ArgumentCount,BaseBuildPlan,BaseBuildReceipt,CallerSchema,ContextSchema,MessageSchema,Name,Option,PreparedMain,TraceSchema,Wiring'
        }
        if($publication) {
            if($profile.PublicationSchema -cne 'iw7.t7-message-publication-build/1') {throw 'Exact publication build schema required.'}
            $fields=(@($fields.Split(','))+@('PublicationSchema','PublicationWiring','PublicationSource','PreparedCLI',
                'MainResponse','CLIResponse','LinkResponse')|Sort-Object)-join ','
            if((@($Plan.Stages.Name)-join ',') -cne 'main,zonetool11,link') {throw 'Publication requires main,zonetool11,link in order.'}
        }
        if($zombies) {
            if($profile.ObservationSchema -cne 'iw7.t7-zm-observation/1' -or
               !$Plan.ReuseCompile.PSObject.Properties['ZombiesObservationC']){throw 'Explicit Zombies observation source marker required.'}
            $fields=(@($fields.Split(','))+@('ObservationSchema','ObserverSource','ObserverAdapter')|Sort-Object)-join ','
        }
        if($add) {
            if($profile.ObservationSchema -cne 'iw7.t7-zm-add-observation/1' -or
               !$Plan.ReuseCompile.PSObject.Properties['ZombiesAddObservationC2']){throw 'Explicit C2 source marker required.'}
            $fields=(@($fields.Split(','))+@('ObservationSchema','ObserverSource','ObserverAdapter')|Sort-Object)-join ','
        }
        if($profile.Option -cne '-t7-iw7-catalog' -or $profile.ArgumentCount -ne 3 -or
           $profile.TraceSchema -cne 'iw7.t7-catalog-trace/1' -or
           (@($profile.PSObject.Properties.Name|Sort-Object)-join ',') -cne $fields -or
           $profile.BaseBuildPlan.SHA256 -cne 'daa7097f872b83a5762b2cb56bf6dd5a235ed2beee8e0ff077276c61622d53fa' -or
           $profile.BaseBuildReceipt.SHA256 -cne 'c609bc56523654d8bca4b855024a463393185aab8e19ed4eae94c1ff8f6a09c2'){
            throw 'Exact catalogue trace profile and ordinary D2 proof required.'
        }
        $paths=@{
            Wiring=(Join-Path $SourceRoot 'prepare_catalog_trace.py')
            PreparedMain=(Join-Path $Plan.PreparedRoot 'main.cpp')
            BaseBuildPlan=$profile.BaseBuildPlan.Path
            BaseBuildReceipt=$profile.BaseBuildReceipt.Path
        }
        if($publication) {
            $responseRoot=Split-Path $Plan.PreparedRoot -Parent
            $paths.PublicationWiring=Join-Path $SourceRoot 'prepare_message_publication.py'
            $paths.PublicationSource=Join-Path $SourceRoot 'native_message_publication.inc'
            $paths.PreparedCLI=Join-Path $Plan.PreparedRoot 'zonetool.cpp'
            $paths.MainResponse=Join-Path $responseRoot 'main.obj.rsp'
            $paths.CLIResponse=Join-Path $responseRoot 'zonetool11.obj.rsp'
            $paths.LinkResponse=Join-Path $responseRoot 'link.rsp'
            foreach($row in @(@('main','MainResponse'),@('zonetool11','CLIResponse'),@('link','LinkResponse'))) {
                $stage=@($Plan.Stages|Where-Object Name -CEQ $row[0])[0]
                if(@($stage.Arguments).Count -ne 1 -or $stage.Arguments[0] -cne ('@'+$paths[$row[1]])) {
                    throw 'Publication stage must use its pinned response file.'
                }
                $image=if($row[0] -ceq 'link'){Join-Path (Split-Path $Plan.Compiler -Parent) 'link.exe'}else{$Plan.Compiler}
                if($stage.Image -cne $image){throw 'Publication stage image differs.'}
                $artifacts=@(if($row[0] -ceq 'link'){'zonetool-t7.exe','zonetool-t7.pdb','zonetool-t7.lib','zonetool-t7.exp'}
                    else{($row[0]+'.obj'),'compile.pdb','dependencies.json'})
                if((@($stage.Artifacts)-join ',') -cne ($artifacts-join ',')) {throw 'Publication stage artifact guards differ.'}
            }
        }
        if($zombies) {
            $paths.ObserverSource=Join-Path $SourceRoot 'native_catalog_zombies_observation.inc'
            $paths.ObserverAdapter=Join-Path $SourceRoot 'prepare_catalog_zombies_observation.py'
        }
        if($add) {
            $paths.ObserverSource=Join-Path $SourceRoot 'native_catalog_add_observation.inc'
            $paths.ObserverAdapter=Join-Path $SourceRoot 'prepare_catalog_add_observation.py'
        }
    } else {
        throw 'Unknown T7 build profile.'
    }
    foreach($name in $paths.Keys) {
        $pin=$profile.$name
        $limit=if($name -ceq 'BaseBuildPlan'){2MB}elseif($name -ceq 'BaseBuildReceipt'){128KB}
               elseif($name -ceq 'LinkResponse'){256KB}elseif($name -ceq 'PublicationSource'){16KB}
               elseif($name -ceq 'PreparedCLI' -and $Plan.ReuseCompile.PSObject.Properties.Name -contains 'SelectedStreamedRenderOnlyV2' -and
                   $Plan.ReuseCompile.SelectedStreamedRenderOnlyV2.Schema -ceq 'iw7.t7-selected-streamed-render-only-build/2' -and
                   $Plan.ReuseCompile.SelectedStreamedRenderOnlyV2.GeometryProfile -ceq 't7-iw7-selected-streamed-render-only-v2' -and
                   $Plan.ReuseCompile.SelectedStreamedRenderOnlyV2.CollisionPolicy -ceq 'omit-source-rigid-collision-trees'){128KB}
               elseif($name -ceq 'PreparedCLI' -and $Plan.ReuseCompile.PSObject.Properties.Name -contains 'SelectedStreamedStaticV1' -and
                   $Plan.ReuseCompile.SelectedStreamedStaticV1.Schema -ceq 'iw7.t7-selected-streamed-static-build/1' -and
                   $Plan.ReuseCompile.SelectedStreamedStaticV1.GeometryProfile -ceq 't7-iw7-selected-streamed-static-v1'){128KB}else{64KB}
        if($pin.Path -cne $paths[$name] -or $pin.Bytes -le 0 -or $pin.Bytes -gt $limit -or
           $pin.SHA256 -cnotmatch '^[0-9a-f]{64}$'){throw 'Diagnostic source pin differs.'}
        $match=@($Plan.Bindings|Where-Object {$_.Path -ceq $pin.Path -and $_.IsText -is [bool] -and $_.IsText -and
            $_.Bytes -eq $pin.Bytes -and $_.SHA256 -ceq $pin.SHA256})
        if($match.Count -ne 1){throw 'Diagnostic source pin is not guarded by the build.'}
    }
    return $true
}
function Assert-T7InputBindings($Plan) {
    # This runs before any binding is opened, binary metadata is queried or
    # provider is loaded. Legacy128 and sealed E2/v2144 remain unchanged;
    # the explicit selected-streamed marker adds five exact source bindings.
    $bindings=@($Plan.Bindings);$inputs=@($Plan.Inputs)
    $reuse=if($Plan.PSObject.Properties.Name -contains 'ReuseCompile'){$Plan.ReuseCompile}else{$null}
    $zombies=$null -ne $reuse -and $reuse.PSObject.Properties.Name -contains 'ZombiesObservationC'
    $add=$null -ne $reuse -and $reuse.PSObject.Properties.Name -contains 'ZombiesAddObservationC2'
    if($zombies -and $add){throw 'C and C2 observation markers are exclusive.'}
    $observed=$zombies -or $add
    if($bindings.Count -gt $(if($observed){151}else{149}) -or $inputs.Count -gt 2048 -or
        @($bindings.Path|Sort-Object -Unique).Count -ne $bindings.Count -or
        @($inputs.Path|Sort-Object -Unique).Count -ne $inputs.Count){throw 'Input set bound/uniqueness differs.'}
    if(@($bindings|Where-Object {$_.IsText -isnot [bool]}).Count){throw 'Binding text/binary classification required.'}
    $v2=$null -ne $reuse -and $reuse.PSObject.Properties.Name -contains 'ResidentMultiSurfaceV2'
    $streamedV1=$null -ne $reuse -and $reuse.PSObject.Properties.Name -contains 'SelectedStreamedStaticV1'
    $renderOnly=$null -ne $reuse -and $reuse.PSObject.Properties.Name -contains 'SelectedStreamedRenderOnlyV2'
    if($renderOnly -and ($streamedV1 -or $zombies)){throw 'Render-only and frozen V1/C markers are exclusive.'}
    if($add -and (!$renderOnly -or $streamedV1)){throw 'C2 requires the explicit render-only V2 marker.'}
    $streamed=$streamedV1 -or $renderOnly
    if(!$v2) {
        if($observed){throw 'Observation requires the current selected-streamed publication proof.'}
        if($streamed){throw 'Selected-streamed marker requires the exact common geometry proof.'}
        if($bindings.Count -gt 128){throw 'Legacy input binding limit is 128.'}
        return
    }
    if($Plan.SourceCommit -cne 'fab935826c898806855376662a8a03317b3ad8f1' -or
        $Plan.BuildProfile.Name -cne $(if($add){'t7-zombies-catalogue-observation-c2'}elseif($zombies){'t7-zombies-catalogue-observation-c'}else{'t7-catalog-message-publication'}) -or
        $Plan.BuildProfile.PublicationSchema -cne 'iw7.t7-message-publication-build/1' -or
        $reuse.RecompiledMain -isnot [bool] -or !$reuse.RecompiledMain -or
        $reuse.RecompiledZonetool -isnot [bool] -or !$reuse.RecompiledZonetool -or
        $reuse.PSObject.Properties.Name -contains 'ResidentSurfaceCountDiagnostic' -or
        $bindings.Count -ne $(if($observed){151}elseif($streamed){149}else{144}) -or $inputs.Count -ne 1146 -or
        @($bindings|Where-Object IsText).Count -ne $(if($observed){145}elseif($streamed){143}else{138})){throw 'Exact multisurface publication input profile required.'}
    $observerRoot=[IO.Path]::GetDirectoryName($Plan.Runner)
    if($zombies) {
        $observation=$reuse.ZombiesObservationC
        if(!$streamed -or $Plan.BuildProfile.ObservationSchema -cne 'iw7.t7-zm-observation/1' -or
           (@($observation.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'BaseCLIBytes,BaseCLISHA256,CLIBytes,CLISHA256,Schema,SourceProfile' -or
           $observation.Schema -cne 'iw7.t7-zm-observation-build/1' -or
           $observation.SourceProfile -cne 't7-zombies-catalogue-observation-c' -or
           $observation.BaseCLIBytes -ne 107785 -or $observation.BaseCLISHA256 -cne 'c480fbd39525df09bd5677026678743c73fa66eb3ca0752e78729eee2f4dcc50' -or
           $observation.CLIBytes -ne 118485 -or $observation.CLISHA256 -cne '917c2f9025185d23a8b2b683157144c2da62fe747f17f11e0f8c1abcf66be987'){
            throw 'Exact reviewed Zombies observation transition required.'
        }
        foreach($source in @(
            @('ObserverSource','native_catalog_zombies_observation.inc',9668,'50361fbd5deb38b7410e31b995b1dcd7cdf6e43f04dc81835ed213f74155d181'),
            @('ObserverAdapter','prepare_catalog_zombies_observation.py',7613,'1bf133356025893ff59c4d3de7e3614ac60f00a098f16b4b707e0eaa012da445'))) {
            $path=Join-Path $observerRoot $source[1];$pin=$Plan.BuildProfile.($source[0])
            if((@($pin.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'Bytes,Path,SHA256' -or
               $pin.Path -cne $path -or $pin.Bytes -ne $source[2] -or $pin.SHA256 -cne $source[3] -or
               @($bindings|Where-Object {$_.Path -ceq $path -and $_.IsText -and
                   $_.Bytes -eq $source[2] -and $_.SHA256 -ceq $source[3]}).Count -ne 1){throw 'Approved Zombies observation source binding required.'}
        }
    }
    if($add) {
        $observation=$reuse.ZombiesAddObservationC2
        if($Plan.BuildProfile.ObservationSchema -cne 'iw7.t7-zm-add-observation/1' -or
           (@($observation.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'BaseCLIBytes,BaseCLISHA256,CLIBytes,CLISHA256,Schema,SourceProfile' -or
           $observation.Schema -cne 'iw7.t7-zm-add-observation-build/1' -or
           $observation.SourceProfile -cne 't7-zombies-catalogue-observation-c2' -or
           $observation.BaseCLIBytes -ne 112377 -or $observation.BaseCLISHA256 -cne 'c63d9552464da674d3b03c35f7edc16385fb9370b113a3925fd7bc4835fb005a' -or
           $observation.CLIBytes -ne 119139 -or $observation.CLISHA256 -cne '19af683d0c609d43cefc7c93dd3d7fa6f7ae1a6f5b90d2945d37b1830bda1111'){
            throw 'Exact reviewed C2 source transition required.'
        }
        foreach($source in @(
            @('ObserverSource','native_catalog_add_observation.inc',6397,'fe37357ad1f3162f24ae79af51f325763b81e05851eb263f8681b5558835f11d'),
            @('ObserverAdapter','prepare_catalog_add_observation.py',6156,'cf6551b918e21d0046136ea3e328494960b70a62334bc3f2727e0a52fee5ec6f'))) {
            $path=Join-Path $observerRoot $source[1];$pin=$Plan.BuildProfile.($source[0])
            if((@($pin.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'Bytes,Path,SHA256' -or
               $pin.Path -cne $path -or $pin.Bytes -ne $source[2] -or $pin.SHA256 -cne $source[3] -or
               @($bindings|Where-Object {$_.Path -ceq $path -and $_.IsText -and
                   $_.Bytes -eq $source[2] -and $_.SHA256 -ceq $source[3]}).Count -ne 1){throw 'Approved C2 source binding required.'}
        }
    }
    if($streamed) {
        if($renderOnly) {
            $marker=$reuse.SelectedStreamedRenderOnlyV2
            if(!$marker -or (@($marker.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'CollisionPolicy,GeometryProfile,Schema' -or
                $marker.Schema -cne 'iw7.t7-selected-streamed-render-only-build/2' -or
                $marker.GeometryProfile -cne 't7-iw7-selected-streamed-render-only-v2' -or
                $marker.CollisionPolicy -cne 'omit-source-rigid-collision-trees'){throw 'Exact render-only source marker required.'}
            $sourcePins=@(
                @('streamed_mesh_payload.hpp',18512,'53265601cec86ba6e0b731e54d9c706f41d390756f4e4566ace70bd5fbd25adf'),
                @('t7_iw7_streamed_model.hpp',11951,'04007fa53fc6a3cc0307a589e7f28cebfa1c2a37c6071e0a2cb9ded412782453'),
                @('native_streamed_export.inc',10919,'f4fdc95d6a29bbe36c9140beff11567ab3ecc4d87f3c28e1e4e7fa4a25ec92c7'),
                @('streamed_contract.py',10366,'cc584cf6d2ff82be77b9ef0e926cda75ac7768f85e906d6eef22c2f8c2572df4'),
                @('test_streamed_contract.py',13768,'86392ae7934213692ae4c9453579d4b006d2665d6a80aaf52e39a41edc18bb3c') )
        } else {
            $marker=$reuse.SelectedStreamedStaticV1
            if(!$marker -or (@($marker.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'GeometryProfile,Schema' -or
                $marker.Schema -cne 'iw7.t7-selected-streamed-static-build/1' -or
                $marker.GeometryProfile -cne 't7-iw7-selected-streamed-static-v1'){throw 'Exact selected-streamed source marker required.'}
        $sourcePins=@(
            @('streamed_mesh_payload.hpp',18512,'53265601cec86ba6e0b731e54d9c706f41d390756f4e4566ace70bd5fbd25adf'),
            @('t7_iw7_streamed_model.hpp',11289,'5eeaa89565bcfb2c5a1d899f78a47787584a1472caae9e84f04af1b8c886e5a0'),
            @('native_streamed_export.inc',9823,'60916d49cb4490f0cc508b699d9adaa02a780229fa5e69e3c66297f50c3b0123'),
            @('streamed_contract.py',7996,'b7d68593b93975832cfa6362c2f782187772c2255cd59c78ab5aae66d759518f'),
            @('test_streamed_contract.py',8796,'fe25379d80cc1ec328836a0e75652046c01b9ddadba3dba73c8e7a550bed1d16'))
        }
        foreach($source in $sourcePins) {
            $path=Join-Path $observerRoot $source[0]
            if(@($bindings|Where-Object {$_.Path -ceq $path -and $_.IsText -and
                $_.Bytes -eq $source[1] -and $_.SHA256 -ceq $source[2]}).Count -ne 1){throw 'Exact selected-streamed source binding required.'}
        }
    }
    $materialHeader=if($renderOnly){@('selected_material_observation.hpp',18583,'a8848a92b8d7918fbe91ec4b68df123b1eaab89edde9d8a7c24d5a0cfb576ffc')}elseif($streamed){@('selected_material_observation.hpp',16489,'0ea84735fca2502033cc48a4eede6a19e1bd1283ba1975829f763c16e5ef343a')}
        else{@('selected_material_observation.hpp',12765,'a935803571f04b3a2cad7346824bf3194f5d44aeada15b224a3faa75ea292d7f')}
    $materialFixture=if($renderOnly){@('selected_material_observation_fixture.cpp',20260,'b3de68880b6f8c717c2e70ed44497ae2f95f37db7e73bbf34ef014d8e5b6fc6f')}elseif($streamed){@('selected_material_observation_fixture.cpp',13721,'cb27d4df66f3a186de3e0f5faedf7bf713610a2da0fc599861e5a4838ea2dfed')}
        else{@('selected_material_observation_fixture.cpp',8146,'f011131feeb5495b3bfb0a1e86ad34aad20fc7869ec775c861290df6e3e1a05b')}
    foreach($observer in @(
        @('resident_image_copy.hpp',6366,'96291c23f132e09285d4ea3171c9107ac525d8628403014eae85a895f99c324e'),
        $materialHeader,$materialFixture)) {
        $path=Join-Path $observerRoot $observer[0]
        if(@($bindings|Where-Object {$_.Path -ceq $path -and $_.IsText -and
            $_.Bytes -eq $observer[1] -and $_.SHA256 -ceq $observer[2]}).Count -ne 1){
            throw 'Exact read-only selected-metadata source binding required.'
        }
    }
    # Check classification by the retained six-tool metadata inventory too.
    # Counts alone must not permit an EXE to become a pre-admission text read.
    $binaryRows=[Collections.Generic.List[string]]::new()
    foreach($pin in $bindings) {
        if($pin.IsText) {
            if([IO.Path]::GetExtension($pin.Path) -in @('.exe','.dll','.obj','.pdb','.lib','.res','.pch')){
                throw 'Opaque build input cannot be a text binding.'
            }
        } else {$binaryRows.Add([IO.Path]::GetFileName($pin.Path).ToLowerInvariant()+'|'+$pin.Bytes+'|'+$pin.SHA256+"`n")}
    }
    $binaryRows.Sort([StringComparer]::Ordinal);$binaryBytes=[Text.Encoding]::UTF8.GetBytes(($binaryRows -join ''))
    if($binaryBytes.Length -ne 494 -or [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($binaryBytes)).ToLowerInvariant() -cne
        '3d5bcf2d88a865efba3e9fea62c90949a7b44330631689946f733de3497cb89d'){throw 'Exact six binary metadata bindings required.'}
    $proof=$reuse.ResidentMultiSurfaceV2;$headers=$proof.AdditionalHeaderInputs
    $readSHA='d9cdd533796a9fe14e0d5140d8adcbf5cbc932fafd4c06e18a615d15199a2185'
    $compileSHA='a7083ce5b9ba2fe1421c4f8733cf1d1e0b286549dbc55a44f3ef30ceb3c05333'
    $linkSHA='70455d2f32a9b034dda20fbaf48443ee68a02e552381edbf88b19d219f1f66b2'
    if($proof.Schema -cne 'iw7.t7-resident-multi-surface-build/2' -or
        $proof.Header -cne 'prepared/t7_iw7_resident_model.hpp' -or
        $proof.PreviousSHA256 -cne '6d2da3d4f7c3d0686909dc488f3d176ee2dd250e8d43d9a3cd9bcfa701482777' -or
        $proof.SHA256 -cne '857d57b5f3c1c970f45e513e357215f3506e9c48b2daea4b4f62cb33e0d9bce4' -or
        $proof.E7ReadSHA256 -cne $readSHA -or $proof.E7CompileSHA256 -cne $compileSHA -or
        $proof.E7LinkSHA256 -cne $linkSHA -or $proof.E7TranslationUnits -ne 413 -or $proof.E7Objects -ne 413 -or
        $headers.Count -ne 66 -or $headers.Bytes -ne 87204 -or @($headers.Inputs).Count -ne 66 -or
        $headers.E7ReadSHA256 -cne $readSHA -or $headers.E7CompileSHA256 -cne $compileSHA -or
        $headers.CompilerContextMatchesCLI -isnot [bool] -or !$headers.CompilerContextMatchesCLI){
        throw 'Complete pinned multisurface dependency proof required.'
    }
    $suffix='\src\zonetool\zonetool\iw7\assets\xsurface.cpp'
    $tu=$headers.E7TranslationUnit
    if(![IO.Path]::IsPathFullyQualified($tu) -or [IO.Path]::GetFullPath($tu) -cne $tu -or
        !$tu.EndsWith($suffix,[StringComparison]::Ordinal)){throw 'Exact IW7 writer source context required.'}
    $native=$tu.Substring(0,$tu.Length-$suffix.Length)
    $rows=[Collections.Generic.List[string]]::new();$seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($pin in $headers.Inputs) {
        if(![IO.Path]::IsPathFullyQualified($pin.Path) -or [IO.Path]::GetFullPath($pin.Path) -cne $pin.Path -or
            !$seen.Add($pin.Path) -or $pin.Bytes -le 0 -or $pin.Bytes -gt 16KB -or
            $pin.SHA256 -cnotmatch '^[0-9a-f]{64}$'){throw 'Canonical unique bounded header pin required.'}
        $relative=[IO.Path]::GetRelativePath($native,$pin.Path).Replace('\','/').ToLowerInvariant()
        $rows.Add($relative+'|'+$pin.Bytes+'|'+$pin.SHA256+"`n")
        $input=@($inputs|Where-Object {$_.Path -ceq $pin.Path -and $_.Bytes -eq $pin.Bytes -and $_.SHA256 -ceq $pin.SHA256})
        $binding=@($bindings|Where-Object {$_.Path -ceq $pin.Path -and $_.Bytes -eq $pin.Bytes -and
            $_.SHA256 -ceq $pin.SHA256 -and $_.IsText})
        if($input.Count -ne 1 -or $binding.Count -ne 1){throw 'Header proof/Inputs/text Bindings bijection differs.'}
    }
    # Canonical sorted relative-path|raw-bytes|SHA256 LF rows from the reviewed
    # MULTISURFACE_HEADER_PINS table. Do not duplicate or discover native files.
    $rows.Sort([StringComparer]::Ordinal);$bytes=[Text.Encoding]::UTF8.GetBytes(($rows -join ''))
    if($bytes.Length -ne 7676 -or [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant() -cne
        '5ee7ea0b46848bca9f4d365d0035cf070b2f57c6723019ab1288a54a93a7297b'){throw 'Reviewed 66-header pin inventory differs.'}
    $pch=$headers.PCHExcludedForPreparedYMinus
    if(![IO.Path]::IsPathFullyQualified($pch) -or [IO.Path]::GetFullPath($pch) -cne $pch -or
        !$pch.EndsWith('\obj\community.pch',[StringComparison]::Ordinal)){throw 'Exact excluded E7 PCH required.'}
    $obj=Split-Path $pch -Parent
    foreach($row in @(@('CL.read.1.tlog',$readSHA,15206288,15206288),
        @('CL.command.1.tlog',$compileSHA,1,4MB),@('link.command.1.tlog',$linkSHA,1,256KB))) {
        $path=Join-Path $obj ('tlog/'+$row[0])
        if(@($bindings|Where-Object {$_.Path -ieq $path -and $_.IsText -and $_.SHA256 -ceq $row[1] -and
            $_.Bytes -ge $row[2] -and $_.Bytes -le $row[3]}).Count -ne 1){throw 'Sealed E7 journal text binding absent.'}
    }
    if(@($proof.DependencyJSON).Count -ne 3 -or @($reuse.StageRoots).Count -ne 1){throw 'Exact retained dependency proof required.'}
    $oldRun=Split-Path $reuse.StageRoots[0] -Parent
    $depPins=@(@('helper',16296,'6897d27e8fe0754509e52258082d6178c8cb74fe21a8ef4b006006e97ab9dd12'),
        @('zonetool11',76744,'cfe62be9ce9bf87abd8e6713f1e1f334d76f69472500d2cb260696de26ee8273'),
        @('xpak',64444,'3d742923def4fb049d82853ac0e776ffd071228deaf1da1a624603d10dfd3908'))
    foreach($row in $depPins) {
        $path=Join-Path $oldRun ($row[0]+'/dependencies.json')
        foreach($set in @(@($proof.DependencyJSON),$bindings)) {
            if(@($set|Where-Object {$_.Path -ceq $path -and $_.Bytes -eq $row[1] -and $_.SHA256 -ceq $row[2]}).Count -ne 1){
                throw 'Pinned C dependency JSON or binding differs.'
            }
        }
        if(@($bindings|Where-Object {$_.Path -ceq $path -and $_.IsText}).Count -ne 1){throw 'C dependency JSON must be text.'}
    }
    if(@($proof.SourceTransitions).Count -ne 3){throw 'Exact three source transitions required.'}
    $rows.Clear()
    foreach($row in $proof.SourceTransitions) {
        $rows.Add((@($row.Path,$row.PreviousBytes,$row.PreviousSHA256,$row.Bytes,$row.SHA256,$row.WiredBytes,$row.WiredSHA256)-join '|')+"`n")
        $path=Join-Path (Split-Path $Plan.PreparedRoot -Parent) $row.Path
        $wiredBytes=$row.WiredBytes;$wiredSHA=$row.WiredSHA256
        if($observed -and $row.Path -ceq 'prepared/zonetool.cpp') {
            if($wiredBytes -ne $observation.BaseCLIBytes -or $wiredSHA -cne $observation.BaseCLISHA256){throw 'Zombies observation base transition differs.'}
            $wiredBytes=$observation.CLIBytes;$wiredSHA=$observation.CLISHA256
        }
        if(@($bindings|Where-Object {$_.Path -ceq $path -and $_.IsText -and $_.Bytes -eq $wiredBytes -and
            $_.SHA256 -ceq $wiredSHA}).Count -ne 1){throw 'Wired v2 transition binding differs.'}
    }
    $rows.Sort([StringComparer]::Ordinal);$bytes=[Text.Encoding]::UTF8.GetBytes(($rows -join ''))
    $transitionBytes=if($streamed){716}else{714}
    $transitionSHA=if($renderOnly){'09f477a869eabe0794118dff29a8412773b30ab4602ea7c18190ea748768a395'}elseif($streamed){'76570ca356d90c45c04b7cd4c8e46ff8126fc1cdb9c0919562dbb265955bee6b'}else{
        'e1b572bfacbce89260ffce52d21c26e15f2ae2aa5172256cd063797b9a0f1b1c'}
    if($bytes.Length -ne $transitionBytes -or [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant() -cne
        $transitionSHA){throw 'Reviewed versioned source transitions differ.'}
}
function Split-T7ResponseArguments([string]$Text) {
    # Deliberately bounded MSVC response syntax: space/tab separators and quoted
    # segments within arguments. Escaped/doubled or unclosed quotes are refused,
    # not guessed; the generator never needs them for these file destinations.
    if($Text -match '[\x00-\x08\x0a-\x1f\x7f]|\\+"|""' -or $Text.Contains('@')) {
        throw 'Unsupported or indirect publication response syntax.'
    }
    $arguments=[Collections.Generic.List[string]]::new()
    $token=[Text.StringBuilder]::new();$quoted=$false
    foreach($character in $Text.ToCharArray()) {
        if($character -eq '"') {$quoted=!$quoted;continue}
        if(!$quoted -and ($character -eq ' ' -or $character -eq "`t")) {
            if($token.Length){$arguments.Add($token.ToString());$null=$token.Clear()}
        } else {$null=$token.Append($character)}
    }
    if($quoted){throw 'Unclosed publication response quote.'}
    if($token.Length){$arguments.Add($token.ToString())}
    return ,$arguments.ToArray()
}
function Assert-T7ResponseOutputs([string[]]$Arguments,[System.Collections.IDictionary]$Outputs) {
    $seen=@{}
    for($index=0;$index -lt $Arguments.Count;$index++) {
        $argument=$Arguments[$index]
        if($argument -notmatch '^[-/]'){continue}
        $option=$argument.Substring(1)
        # This existing linker flag shares PDB's prefix but takes no filename.
        if($option -ieq 'PDBCompress'){continue}
        foreach($name in $Outputs.Keys) {
            if(!$option.StartsWith($name,[StringComparison]::OrdinalIgnoreCase)){continue}
            if($seen.ContainsKey($name)){throw 'Duplicate publication output option.'}
            $seen[$name]=$true
            $value=$option.Substring($name.Length)
            if($value.StartsWith(':')){$value=$value.Substring(1)}
            if(!$value) {
                $index++
                if($index -ge $Arguments.Count){throw 'Missing publication output value.'}
                $value=$Arguments[$index]
            }
            if($value -cne $Outputs[$name]){throw 'Publication output must belong to its exact fresh stage.'}
            break
        }
    }
    if($seen.Count -ne $Outputs.Count){throw 'Missing publication output option.'}
}
function Assert-T7PublicationResponses($Plan,[string]$MainResponse,[string]$CLIResponse,[string]$LinkResponse) {
    # Pure text validation, only for the new profile. The caller already guards
    # these exact response files by length/hash; no binary input is read here.
    foreach($row in @(@('main','main.cpp',$MainResponse),@('zonetool11','zonetool.cpp',$CLIResponse))) {
        $name=$row[0];$text=$row[2];$stageRoot=Join-Path $Plan.RunRoot $name
        $arguments=Split-T7ResponseArguments $text.TrimEnd("`r","`n")
        Assert-T7ResponseOutputs $arguments ([ordered]@{
            Fo=(Join-Path $stageRoot ($name+'.obj'));Fd=(Join-Path $stageRoot 'compile.pdb')
            sourceDependencies=(Join-Path $stageRoot 'dependencies.json')
        })
        if(!$arguments.Count -or $arguments[-1] -cne (Join-Path $Plan.PreparedRoot $row[1])) {throw 'Exact prepared compile source required.'}
    }
    $lines=@($LinkResponse.TrimEnd("`r","`n") -split "`r?`n")
    if($lines.Count -ne 414 -or $lines[0] -match '(?i)\.obj\b|@') {throw 'Exact direct 413-object link required.'}
    $linkRoot=Join-Path $Plan.RunRoot 'link'
    Assert-T7ResponseOutputs (Split-T7ResponseArguments $lines[0]) ([ordered]@{
        OUT=(Join-Path $linkRoot 'zonetool-t7.exe');PDB=(Join-Path $linkRoot 'zonetool-t7.pdb')
        IMPLIB=(Join-Path $linkRoot 'zonetool-t7.lib')
    })
    $objects=@();$unique=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($line in $lines[1..413]) {
        if($line -notmatch '^"([^"\r\n]+\.obj)"$') {throw 'Direct quoted link object required.'}
        $path=$Matches[1]
        if(!$unique.Add($path)){throw 'Duplicate publication link object.'}
        $objects+=$path
    }
    foreach($name in 'main','zonetool11') {
        $objectMatches=@($objects|Where-Object {[IO.Path]::GetFileName($_) -ieq ($name+'.obj')})
        $expected=Join-Path (Join-Path $Plan.RunRoot $name) ($name+'.obj')
        if($objectMatches.Count -ne 1 -or $objectMatches[0] -cne $expected) {throw 'Publication link refuses a retained main or CLI object.'}
    }
    if(@($Plan.ReuseCompile.StageRoots).Count -ne 1){throw 'Publication retains only xpak dependencies.'}
    $objectMatches=@($objects|Where-Object {[IO.Path]::GetFileName($_) -ieq 'xpak.obj'})
    if($objectMatches.Count -ne 1 -or $objectMatches[0] -cne (Join-Path $Plan.ReuseCompile.StageRoots[0] 'xpak.obj')) {
        throw 'Exact retained xpak object required.'
    }
}
try {
    $planSize=(Get-Item -LiteralPath $PlanPath).Length
    if($planSize -gt 2MB){throw 'Plan exceeds 2 MiB.'}
    $planStream=Open-T7Bootstrap $PlanPath $planSize $PlanSHA256
    $reader=[IO.StreamReader]::new($planStream,[Text.Encoding]::UTF8,$true,4096,$true)
    try{$plan=$reader.ReadToEnd()|ConvertFrom-Json -Depth 25}finally{$reader.Dispose()}
    if($plan.Schema -cne 'iw7.t7-minimal-build-plan/1' -or $plan.Runner -cne $PSCommandPath -or
       $plan.Profile -cne (Join-Path $PSScriptRoot 'T7Build.Profile.ps1')){throw 'Exact T7 runner/profile required.'}
    if($plan.PhysicalBytes -ne 4GB -or $plan.CommitBytes -ne 6GB -or $plan.GroupDeadlineSeconds -ne 600 -or
       $plan.OutputLimitBytes -ne 256MB -or $plan.MetadataReserveBytes -ne 1MB -or $plan.CleanupSeconds -ne 5 -or
       $plan.ReusedObjects -ne 410 -or $plan.ReusedProjectLibraries -ne 18 -or $plan.ReusedResources -ne 1){throw 'Fixed minimal build limits differ.'}
    $reuse=$plan.PSObject.Properties.Name -contains 'ReuseCompile' -and $null -ne $plan.ReuseCompile
    $recompiled=Assert-T7BuildProfile $plan $PSScriptRoot
    $buildProfile=if($recompiled){$plan.BuildProfile}else{$null}
    $publication=$null -ne $buildProfile -and $buildProfile.Name -cin @('t7-catalog-message-publication','t7-zombies-catalogue-observation-c','t7-zombies-catalogue-observation-c2')
    $names=@(if($publication){'main','zonetool11','link'}elseif($recompiled){'main','link'}elseif($reuse){'link'}else{'helper','probe','main','zonetool11','xpak','link'})
    if(@($plan.Stages).Count -ne $names.Count -or (@($plan.Stages.Name)-join ',') -cne ($names-join ',')){throw 'Exact full, retained-link or diagnostic main/link stages required.'}
    Assert-T7InputBindings $plan
    foreach($pin in $plan.Bindings) {
        if($pin.IsText -isnot [bool]){throw 'Binding text/binary classification required.'}
        if($pin.IsText){$null=Open-T7Bootstrap $pin.Path $pin.Bytes $pin.SHA256}
        elseif((Get-Item -LiteralPath $pin.Path).Length -ne $pin.Bytes){throw 'Binary metadata changed.'}
    }
    foreach($required in @($plan.Runner,$plan.Profile,$plan.Core,$plan.CompilerCore,$plan.ObserverSource,$plan.CompilerPolicySource,$plan.Scheduler)) {
        if(@($plan.Bindings|Where-Object {$_.Path -ceq $required -and $_.IsText}).Count -ne 1){throw 'Exact source provider pin missing.'}
    }
    if($publication) {
        Assert-T7PublicationResponses $plan ([IO.File]::ReadAllText($plan.BuildProfile.MainResponse.Path)) `
            ([IO.File]::ReadAllText($plan.BuildProfile.CLIResponse.Path)) ([IO.File]::ReadAllText($plan.BuildProfile.LinkResponse.Path))
    }
    . $plan.Core
    $runtime=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../runtime'))
    Assert-H1Path $plan.RunRoot
    if([IO.Path]::GetDirectoryName($plan.RunRoot) -cne $runtime -or (Test-Path -LiteralPath $plan.RunRoot)){throw 'Fresh output directly under owned runtime required.'}
    foreach($stage in $plan.Stages) {
        $expectedType=if($stage.Name -ceq 'probe'){'Probe'}elseif($stage.Name -ceq 'link'){'Link'}else{'Compile'}
        $expectedSeconds=if($expectedType -ceq 'Probe'){15}else{120}
        if($stage.Stage -cne $expectedType -or $stage.DeadlineSeconds -ne $expectedSeconds){throw 'Fixed stage profile differs.'}
        Assert-H1Path $stage.Image
    }
    foreach($pin in $plan.Inputs) {
        Assert-H1Path $pin.Path
        if((Get-Item -LiteralPath $pin.Path).Length -ne $pin.Bytes){throw 'Recorded input metadata differs.'}
    }
    if($reuse) {
        $prior=Read-H1SmallJson $plan.ReuseCompile.Receipt
        if($prior.Schema -cne 'iw7.t7-minimal-build/1' -or $prior.Status -cne 'Failed' -or
           $prior.TreeClosureConfirmed -isnot [bool] -or !$prior.TreeClosureConfirmed -or
           $prior.LeaseReleased -isnot [bool] -or !$prior.LeaseReleased -or
           $prior.Quarantined -isnot [bool] -or $prior.Quarantined -or
           $prior.PlanSHA256 -cne $plan.ReuseCompile.SourcePlanSHA256 -or $plan.ReuseCompile.Checks -ne 51){throw 'Retained compile proof differs.'}
        foreach($name in 'helper','probe','main','zonetool11','xpak') {
            $row=@($prior.Stages|Where-Object Name -CEQ $name)
            if($row.Count -ne 1 -or $row[0].ExitCode -ne 0 -or !$row[0].TreeClosureConfirmed){throw 'Retained sub-stage was not successful and closed.'}
        }
        if(@($prior.Stages|Where-Object Name -CEQ 'probe')[0].Checks -ne 51){throw 'Retained name probe differs.'}
        foreach($required in @($plan.ReuseCompile.Receipt,$plan.ReuseCompile.SourcePlan)) {
            if(@($plan.Bindings|Where-Object {$_.Path -ceq $required -and $_.IsText}).Count -ne 1){throw 'Retained receipt/plan binding absent.'}
        }
        $priorPlan=Read-H1SmallJson $plan.ReuseCompile.SourcePlan 2MB
        $retainedNames=@(if($publication){'xpak'}elseif($recompiled){'zonetool11','xpak'}else{'main','zonetool11','xpak'})
        $retainedRoots=@($retainedNames|ForEach-Object {Join-Path $priorPlan.RunRoot $_})
        if((@($plan.ReuseCompile.StageRoots)-join '|') -cne ($retainedRoots-join '|')){throw 'Exact retained dependency roots required.'}
    }
    if(!$Run) {
        [ordered]@{Schema='iw7.t7-minimal-build-check/1';PlanSHA256=$PlanSHA256;Stages=@($plan.Stages).Count;ReusedCompilation=$reuse;BuildProfile=$buildProfile;
            ExpectedInputs=@($plan.Inputs).Count;MissingExpectedPins=@($plan.MissingExpectedPins).Count;
            NativeTypesLoaded=$false;BinaryInputsHashed=$false;LeaseAcquired=$false;RunRootCreated=$false;Ready=$false}|ConvertTo-Json
        return
    }
    if($plan.InputPinsComplete -isnot [bool] -or !$plan.InputPinsComplete -or @($plan.MissingExpectedPins).Count){throw 'Complete reviewed expected input pins required before native GO.'}
    if(('IW7.AnimationProbe.NativeJob' -as [type]) -or ('IW7.H1Diagnostics.JobMembers' -as [type]) -or ('IW7ResourceMemoryV1' -as [type])){throw 'Fresh PowerShell host required.'}
    . $plan.Scheduler
    $state=[ordered]@{Schema='iw7.t7-minimal-build/1';PlanSHA256=$PlanSHA256;Status='Pending';Ready=$false;BuildProfile=$buildProfile;
        EstimatesAreMeasured=$false;TreeClosureConfirmed=$true;LeaseReleased=$false;Quarantined=$false;
        MaxObservedOutputBytes=0L;CompilerTelemetry=[ordered]@{Completed=$false};Stages=[Collections.Generic.List[object]]::new()}
    $context.Lease=Enter-IW7ResourceLease -Scope $plan.RunRoot -Kind Build -PhysicalBytes $plan.PhysicalBytes -CommitBytes $plan.CommitBytes -Owner 'T7 three TU build and name helper'
    $state.LeaseToken=$context.Lease.Token;$script:T7GroupStarted=Get-H1Clock
    if(Test-Path -LiteralPath $plan.RunRoot){throw 'Output appeared during admission.'}
    [IO.Directory]::CreateDirectory($plan.RunRoot)|Out-Null;$created=$true
    . $plan.CompilerPolicySource
    . $plan.CompilerCore
    . $plan.Profile
    $launcher=Get-Process -Id $PID;$priority=$launcher.PriorityClass;$launcher.PriorityClass='BelowNormal'
    # No binary contents are read until the one account-wide reservation exists.
    foreach($pin in @($plan.Inputs)+@($plan.Bindings|Where-Object {!$_.IsText})){Open-T7Pin $pin $context}
    if($reuse){foreach($root in $plan.ReuseCompile.StageRoots){Assert-T7Dependencies $plan $root}}
    $null=[Reflection.Assembly]::LoadFrom($plan.JobAssembly)
    Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
    Add-Type -LiteralPath $plan.ObserverSource
    Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
    foreach($stage in $plan.Stages) {
        Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
        if(!$context.Closed){throw 'Previous original job not closed.'}
        $script:T7CurrentStage=$stage
        $stageRoot=Join-Path $plan.RunRoot $stage.Name
        [IO.Directory]::CreateDirectory($stageRoot)|Out-Null
        $stageState=[ordered]@{Stage=$stage.Stage;Name=$stage.Name;PlanSHA256=$PlanSHA256;DeadlineSeconds=$stage.DeadlineSeconds;
            MaxObservedOutputBytes=$state.MaxObservedOutputBytes;TreeClosureConfirmed=$false;
            CompilerTelemetry=[ordered]@{Completed=$false;Action=$null}}
        $state.Stages.Add($stageState)
        $stageStarted=Get-H1Clock
        $image=if($stage.Stage -ceq 'Probe'){@($state.Stages[0].Artifacts|Where-Object Path -CEQ $stage.Image)[0]}
               else{@($plan.Bindings|Where-Object Path -CEQ $stage.Image)[0]}
        $start=New-T7Start $plan $stage $stageRoot
        Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
        Invoke-T7OwnedStage $plan $stageState $context $start $image.SHA256 $stageRoot $stageStarted
        $stageState.Artifacts=@(Get-H1CompilerArtifacts $plan $context)
        if($stageState.CompilerTelemetry.Completed) {
            foreach($prior in $stageState.CompilerTelemetry.Artifacts) {
                $now=@($stageState.Artifacts|Where-Object Path -CEQ $prior.Path)
                if($now.Count -ne 1 -or $now[0].SHA256 -cne $prior.SHA256 -or $now[0].Bytes -ne $prior.Bytes){throw 'Artifact changed across compiler cleanup.'}
            }
        }
        if($stage.Stage -ceq 'Compile'){Assert-T7Dependencies $plan $stageRoot}
        if($stage.Stage -ceq 'Probe') {
            $stdout=Join-Path $stageRoot 'stdout.log';$stderr=Join-Path $stageRoot 'stderr.log'
            if((Get-Item -LiteralPath $stdout).Length -gt 128 -or (Get-Item -LiteralPath $stderr).Length -ne 0){throw 'Name helper output differs.'}
            $observed=[IO.File]::ReadAllText($stdout)
            if($observed -cne "T7_ASSET_NAME_CHECKS=51`n" -and $observed -cne "T7_ASSET_NAME_CHECKS=51`r`n"){throw 'Exactly 51 native name checks required.'}
            $stageState.Checks=51
        }
        Test-H1Budget $plan $stageState
        Assert-H1Deadline $stageStarted $stage.DeadlineSeconds
        $state.MaxObservedOutputBytes=[math]::Max($state.MaxObservedOutputBytes,$stageState.MaxObservedOutputBytes)
    }
    foreach($pin in $plan.Inputs){Open-T7Pin $pin $context}
    foreach($pin in $plan.Bindings){$guard=Open-H1Pin $pin;try{}finally{$guard.Dispose()};Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds}
    Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
    $state.ElapsedMs=(Get-H1Clock)-$script:T7GroupStarted
    $state.InputsReverified=$true;$state.CandidateExecuted=$false
}catch{
    $failure=$_
    if($state){$state.Status='Failed';$state.Error=$_.Exception.Message}
}finally{
    if($state){Complete-H1Stage $context $state}
    if($launcher -and $null -ne $priority){try{$launcher.PriorityClass=$priority}catch{if(!$failure){$failure=$_};$state.Status='Failed'}}
    if($context.Closed -and !$context.Lease){foreach($guard in $guards){$guard.Dispose()};$guards.Clear()}
    if($state -and $created) {
        try {
            Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
            if(!$failure -and $context.Closed -and !$context.Lease){$state.Status='Passed'}
        }catch{
            if(!$failure){$failure=$_}
            if($state.Status -cne 'Quarantined'){$state.Status='Failed'}
            $state.GroupDeadlineError=$_.Exception.Message
        }
        $state.ElapsedMs=(Get-H1Clock)-$script:T7GroupStarted
        $state.FinishedUtc=[datetime]::UtcNow.ToString('o')
        try{Write-H1Receipt $plan $state $plan.RunRoot}catch{if(!$failure){$failure=$_};Write-Warning $_.Exception.Message}
        if(!$failure) {
            try{Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds}
            catch {
                $failure=$_;$state.Status='Failed';$state.GroupDeadlineError=$_.Exception.Message
                $state.ElapsedMs=(Get-H1Clock)-$script:T7GroupStarted
                # A slow publication must not leave a canonical Passed receipt.
                # Preserve the late attempt, then publish failure diagnostics.
                try {
                    $receipt=Join-Path $plan.RunRoot 'receipt.json'
                    $late=Join-Path $plan.RunRoot 'receipt.deadline-exceeded.json'
                    Assert-H1Path $receipt;Assert-H1Path $late
                    [IO.File]::Move($receipt,$late)
                    Write-H1Receipt $plan $state $plan.RunRoot
                }catch{Write-Warning ('Late receipt failure: '+$_.Exception.Message)}
            }
        }
    }
}
if($failure){throw $failure}
if(!$state.LeaseReleased -or $state.Status -cne 'Passed'){throw 'Build did not close and release successfully.'}
[ordered]@{Status=$state.Status;Receipt=(Join-Path $plan.RunRoot 'receipt.json');CandidateExecuted=$false;Ready=$false}|ConvertTo-Json
