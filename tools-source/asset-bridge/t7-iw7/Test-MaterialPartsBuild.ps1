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
    "PASS actual material-parts finite guard: $checks checks; authored JSON only, no binaries or engine."
}finally{
    $full=[IO.Path]::GetFullPath($root);$temporary=[IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    if(!$full.StartsWith($temporary,[StringComparison]::OrdinalIgnoreCase)){throw 'Authored cleanup target outside temporary root'}
    Remove-Item -LiteralPath $full -Recurse -Force
}
