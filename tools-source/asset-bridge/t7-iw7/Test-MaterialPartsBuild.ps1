param([string]$Entry=(Join-Path $PSScriptRoot 'Run-T7Build.ps1'))
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($Entry,[ref]$tokens,[ref]$errors)
if($errors){throw 'Build runner parse failed'}
$function=@($ast.FindAll({param($n);$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq 'Assert-T7MaterialPartsTransition'},$true))
if($function.Count -ne 1){throw 'Unique actual transition guard required'}
. ([scriptblock]::Create($function[0].Extent.Text))
$root=Join-Path ([IO.Path]::GetTempPath()) ('parts-authored-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($root)|Out-Null
try{
    $contract=[ordered]@{schema='iw7.t7-material-parts-source/1';source_profile='t7-material-parts-v1';
        files=[ordered]@{
            'native_material_parts.inc'=@{lf_bytes=33;lf_sha256=('a'*64)}
            'selected_material_parts_observation.hpp'=@{lf_bytes=77;lf_sha256=('b'*64)}
            'selected_material_parts_observation_fixture.cpp'=@{lf_bytes=99;lf_sha256=('c'*64)}
        };main=@{bytes=43300;sha256=('d'*64)};cli=@{bytes=124000;sha256=('e'*64)}}
    $path=Join-Path $root 'material-parts-source-contract.json'
    $contract|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $path -Encoding utf8
    $plan=[ordered]@{BuildProfile=[ordered]@{
        PartsContract=@{Path=$path;Bytes=(Get-Item $path).Length;SHA256=(Get-FileHash $path).Hash.ToLowerInvariant()}
        PreparedMain=@{Bytes=43300;SHA256=('d'*64)};PreparedCLI=@{Bytes=124000;SHA256=('e'*64)}
        PartsSource=@{Bytes=77;SHA256=('b'*64)};PartsEntry=@{Bytes=33;SHA256=('a'*64)};PartsFixture=@{Bytes=99;SHA256=('c'*64)}
    };ReuseCompile=@{MaterialParts=[ordered]@{
        Schema='iw7.t7-material-parts-build/1';SourceProfile='t7-material-parts-v1';
        BaseMainBytes=43254;BaseMainSHA256='5aef1fad310071f5e680a9f5b4dbd6a303af6ea8605fccb5dc5705cb386b761d';
        BaseCLIBytes=112377;BaseCLISHA256='c63d9552464da674d3b03c35f7edc16385fb9370b113a3925fd7bc4835fb005a';
        MainBytes=43300;MainSHA256=('d'*64);CLIBytes=124000;CLISHA256=('e'*64)
    }};Bindings=@(@{Path=(Join-Path $root 'selected_material_observation.hpp');IsText=$true;Bytes=18583;
        SHA256='a8848a92b8d7918fbe91ec4b68df123b1eaab89edde9d8a7c24d5a0cfb576ffc'})}
    $raw=$plan|ConvertTo-Json -Depth 8
    $valid=$raw|ConvertFrom-Json
    Assert-T7MaterialPartsTransition $valid $root
    $checks=1
    foreach($case in 'wrongbase','array','bytesbool','shaarray','extrafield','unboundg2','maindelta','headerdelta','badcontractsha'){
        $p=$raw|ConvertFrom-Json
        switch($case){
            wrongbase {$p.ReuseCompile.MaterialParts.BaseMainSHA256='f'*64}
            array {$p.ReuseCompile.MaterialParts.SourceProfile=@($p.ReuseCompile.MaterialParts.SourceProfile)}
            bytesbool {$p.ReuseCompile.MaterialParts.MainBytes=$true}
            shaarray {$p.ReuseCompile.MaterialParts.CLISHA256=@($p.ReuseCompile.MaterialParts.CLISHA256)}
            extrafield {$p.ReuseCompile.MaterialParts|Add-Member NoteProperty Extra 'ignored'}
            unboundg2 {$p.Bindings=@()}
            maindelta {$p.BuildProfile.PreparedMain.Bytes++}
            headerdelta {$p.BuildProfile.PartsSource.SHA256='f'*64}
            badcontractsha {$p.BuildProfile.PartsContract.SHA256='f'*64}
        }
        $refused=$false;try{Assert-T7MaterialPartsTransition $p $root}catch{$refused=$true}
        if(!$refused){throw "Invalid actual guard case accepted: $case"};$checks++
    }
    # Exercise the actual selected-streamed source-pin block. This is metadata
    # selection only: no tlog, prepared payload or opaque input is opened.
    $pinBlock=@($ast.FindAll({param($node)
        $node -is [Management.Automation.Language.IfStatementAst] -and
        $node.Extent.Text.StartsWith('if($streamed) {') -and
        $node.Extent.Text.Contains('Exact selected-streamed source binding required.')},$true))
    if($pinBlock.Count -ne 1){throw 'Unique actual selected-streamed pin guard required'}
    $sourcePinGuard=[scriptblock]::Create($pinBlock[0].Extent.Text)
    function New-StreamedPins([bool]$RenderOnly,[bool]$ExtendedTest) {
        $rows=if($RenderOnly){@(
            @('streamed_mesh_payload.hpp',18512,'53265601cec86ba6e0b731e54d9c706f41d390756f4e4566ace70bd5fbd25adf'),
            @('t7_iw7_streamed_model.hpp',11951,'04007fa53fc6a3cc0307a589e7f28cebfa1c2a37c6071e0a2cb9ded412782453'),
            @('native_streamed_export.inc',10919,'f4fdc95d6a29bbe36c9140beff11567ab3ecc4d87f3c28e1e4e7fa4a25ec92c7'),
            @('streamed_contract.py',10366,'cc584cf6d2ff82be77b9ef0e926cda75ac7768f85e906d6eef22c2f8c2572df4'),
            @('test_streamed_contract.py',$(if($ExtendedTest){17443}else{13768}),
                $(if($ExtendedTest){'9146f69c84c4178341010f7b6d7c10c4226ce4c7ec524b5fcdf4da742a95ac30'}else{'86392ae7934213692ae4c9453579d4b006d2665d6a80aaf52e39a41edc18bb3c'}))
        )}else{@(
            @('streamed_mesh_payload.hpp',18512,'53265601cec86ba6e0b731e54d9c706f41d390756f4e4566ace70bd5fbd25adf'),
            @('t7_iw7_streamed_model.hpp',11289,'5eeaa89565bcfb2c5a1d899f78a47787584a1472caae9e84f04af1b8c886e5a0'),
            @('native_streamed_export.inc',9823,'60916d49cb4490f0cc508b699d9adaa02a780229fa5e69e3c66297f50c3b0123'),
            @('streamed_contract.py',7996,'b7d68593b93975832cfa6362c2f782187772c2255cd59c78ab5aae66d759518f'),
            @('test_streamed_contract.py',8796,'fe25379d80cc1ec328836a0e75652046c01b9ddadba3dba73c8e7a550bed1d16')
        )}
        foreach($row in $rows){[pscustomobject]@{Path=(Join-Path $observerRoot $row[0]);Bytes=$row[1];SHA256=$row[2];IsText=$true}}
    }
    $streamed=$true;$observerRoot='C:\authored'
    $reuse=[pscustomobject]@{
        SelectedStreamedRenderOnlyV2=[pscustomobject]@{Schema='iw7.t7-selected-streamed-render-only-build/2';
            GeometryProfile='t7-iw7-selected-streamed-render-only-v2';CollisionPolicy='omit-source-rigid-collision-trees'}
        SelectedStreamedStaticV1=[pscustomobject]@{Schema='iw7.t7-selected-streamed-static-build/1';GeometryProfile='t7-iw7-selected-streamed-static-v1'}
    }
    foreach($family in 'render-only','parts','c2','v1'){
        $renderOnly=$family -cne 'v1';$parts=$family -ceq 'parts';$add=$family -ceq 'c2'
        $bindings=@(New-StreamedPins $renderOnly ($parts -or $add))
        . $sourcePinGuard;$checks++
    }
    foreach($case in 'old-parts-test','new-legacy-test','duplicate','header-drift'){
        $renderOnly=$true;$parts=$case -cne 'new-legacy-test';$add=$false
        $bindings=@(New-StreamedPins $true ($case -cne 'old-parts-test'))
        if($case -ceq 'duplicate'){$bindings+=@($bindings[-1])}
        if($case -ceq 'header-drift'){$bindings[0].SHA256='f'*64}
        $refused=$false;try{. $sourcePinGuard}catch{$refused=$true}
        if(!$refused){throw "Invalid selected-streamed pin case accepted: $case"};$checks++
    }
    "PASS actual material-parts finite guard: $checks checks; authored JSON only, no binaries or engine."
}finally{
    $full=[IO.Path]::GetFullPath($root);$temporary=[IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    if(!$full.StartsWith($temporary,[StringComparison]::OrdinalIgnoreCase)){throw 'Authored cleanup target outside temporary root'}
    Remove-Item -LiteralPath $full -Recurse -Force
}
