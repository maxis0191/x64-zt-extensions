# Test actual V3 profile validators without opening providers or opaque files.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Run-T7Build.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Runner parse failed.'}
foreach($name in 'Assert-T7BuildProfile','Assert-T7OSResourceContext','Assert-T7InputBindings'){
    $fn=$ast.Find({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$true)
    . ([scriptblock]::Create($fn.Extent.Text))
}
function New-LinkFixture {
    $prepared='C:\invented-link-v3\prepared';$oldRoot='C:\invented-v2-plan'
    $profile=[ordered]@{Name='t7-prepatch-link-v3';Option='-t7-prepatch-link-v3';ArgumentCount=2;Report='t7-prepatch-link-v3.local.json';ObservationSchema='iw7.t7-prepatch-link-observation/3'}
    $bindings=@()
    foreach($row in @(
        @('Helper',(Join-Path $prepared 'native_prepatch_link_v3.inc'),15827,'cf839e18a68adb4ed3aae82d683ef110ab595fa8c172584e47ca4d11bb8db48d'),
        @('Wiring',(Join-Path $PSScriptRoot 'prepare_prepatch_link_v3.py'),2236,'66f70ca5a979745288232d76496a339e08d639ddf34560aada6e6b63c5bcffa1'),
        @('BaseHelper',(Join-Path $PSScriptRoot 'native_prepatch_reference_v2.inc'),15785,'0309b81376d3708cc8de43d297b43fbdfbdd535120e0ad054c157735c2c7457a'),
        @('BaseWiring',(Join-Path $PSScriptRoot 'prepare_prepatch_reference.py'),3665,'89f3f26699f1240400c4bd96f2987963374658e55a8501cab7dc2543a84ceace'),
        @('BaseBuildPlan','C:\retained-C\plan.json',292575,'422e79898fa2b16defc8193182fe146e2db5d73aeb4516c2bd2aaf87c409c4de'),
        @('BaseBuildReceipt','C:\retained-C\receipt.json',26199,'af6beecf7a8892e16266a7641d2799f665f86fa8ad7c40c61561b782534f7897'),
        @('BaseV2BuildPlan',(Join-Path $oldRoot 'build-plan.local.json'),303783,'0aca63cb09e8ecfc96dee34e1fdf94f8cb66e400f8a190ffdefd38bec3a2c549'),
        @('BaseV2Main',(Join-Path $oldRoot 'prepared/main.cpp'),14524,'e719365c5a7f407218a7218bd9c7090421934042c34a9f163d9a8e3d42ee1e28'),
        @('PreparedMain',(Join-Path $prepared 'main.cpp'),14469,'84cde2924df0a0553dd2cddb0ca173aed54af43d6874b06718c01d1a6cec4989'))){
        $pin=[ordered]@{Path=$row[1];Bytes=$row[2];SHA256=$row[3]};$profile[$row[0]]=$pin
        $bindings+=[ordered]@{Path=$pin.Path;Bytes=$pin.Bytes;SHA256=$pin.SHA256;IsText=$true}
    }
    $marker=[ordered]@{Schema='iw7.t7-prepatch-link-build/3';SourceProfile='t7-prepatch-link-v3';
        RetainedMainBytes=12854;RetainedMainSHA256='40de5fda829cec32a5d75359f58e69c84db7d8ee54f198cf6befa2a6ebe6f86e';
        BaseMainBytes=14524;BaseMainSHA256='e719365c5a7f407218a7218bd9c7090421934042c34a9f163d9a8e3d42ee1e28';
        MainBytes=14469;MainSHA256='84cde2924df0a0553dd2cddb0ca173aed54af43d6874b06718c01d1a6cec4989';
        HelperBytes=15827;HelperSHA256='cf839e18a68adb4ed3aae82d683ef110ab595fa8c172584e47ca4d11bb8db48d'}
    [ordered]@{BuildProfile=$profile;PreparedRoot=$prepared;Runner=(Join-Path $PSScriptRoot 'Run-T7Build.ps1');SourceCommit='fab935826c898806855376662a8a03317b3ad8f1';
        Bindings=$bindings;Inputs=@(@{Path='C:\retained-C\input.obj';Bytes=1024;SHA256=('1'*64)});Stages=@(@{Name='main'},@{Name='link'});
        ReuseCompile=@{RecompiledMain=$true;PrepatchLinkV3=$marker;SourcePlan=$profile.BaseBuildPlan.Path;Receipt=$profile.BaseBuildReceipt.Path;
            SourcePlanSHA256=$profile.BaseBuildPlan.SHA256;ReceiptSHA256=$profile.BaseBuildReceipt.SHA256}}|ConvertTo-Json -Depth 10|ConvertFrom-Json
}
$checks=0;$fixture=New-LinkFixture
if(!(Assert-T7BuildProfile $fixture $PSScriptRoot)){throw 'Valid V3 refused.'};$checks++
Assert-T7InputBindings $fixture;$checks++
foreach($change in @(
    {param($f)$f.BuildProfile.Option='-t7-prepatch-reference-v2'},
    {param($f)$f.BuildProfile.Option=@($f.BuildProfile.Option)},
    {param($f)$f.BuildProfile.ObservationSchema='iw7.t7-prepatch-reference-observation/2'},
    {param($f)$f.BuildProfile.ArgumentCount='2'},
    {param($f)$f.BuildProfile|Add-Member NoteProperty Addresses @('0x1D7960')},
    {param($f)$f.ReuseCompile.PSObject.Properties.Remove('PrepatchLinkV3')},
    {param($f)$f.ReuseCompile|Add-Member NoteProperty PrepatchReferenceV2 @{}},
    {param($f)$f.ReuseCompile|Add-Member NoteProperty MaterialParts @{}},
    {param($f)$f.ReuseCompile|Add-Member NoteProperty RecompiledZonetool $false},
    {param($f)$f.ReuseCompile.RecompiledMain=$false},
    {param($f)$f.ReuseCompile.PrepatchLinkV3.Schema=@($f.ReuseCompile.PrepatchLinkV3.Schema)},
    {param($f)$f.ReuseCompile.PrepatchLinkV3|Add-Member NoteProperty Extra $true},
    {param($f)$f.ReuseCompile.PrepatchLinkV3.BaseMainBytes=13160},
    {param($f)$f.ReuseCompile.PrepatchLinkV3.MainSHA256=('0'*64)},
    {param($f)$f.BuildProfile.Helper.SHA256=@($f.BuildProfile.Helper.SHA256);$f.Bindings[0].SHA256=@($f.Bindings[0].SHA256)},
    {param($f)$f.BuildProfile.Wiring.Path='C:\other.py'},
    {param($f)$f.BuildProfile.BaseV2BuildPlan.Bytes=303784;$f.Bindings[6].Bytes=303784},
    {param($f)$f.BuildProfile.BaseV2Main.Path='C:\wrong\main.cpp';$f.Bindings[7].Path=$f.BuildProfile.BaseV2Main.Path},
    {param($f)$f.BuildProfile.BaseV2Main.SHA256=('0'*64);$f.Bindings[7].SHA256=('0'*64)},
    {param($f)$f.BuildProfile.BaseV2Main.PSObject.Properties.Remove('SHA256')},
    {param($f)$f.Bindings[0].IsText=$false},
    {param($f)$f.Bindings+=@($f.Bindings[0])},
    {param($f)$f.Stages=@($f.Stages[1],$f.Stages[0])}
)){
    foreach($validator in 'profile','bindings'){
        $fixture=New-LinkFixture;& $change $fixture;$refused=$false
        try{if($validator -ceq 'profile'){$null=Assert-T7BuildProfile $fixture $PSScriptRoot}else{Assert-T7InputBindings $fixture}}catch{$refused=$true}
        if(!$refused){throw "V3 invalid $validator accepted: $change"};$checks++
    }
}
[ordered]@{Schema='iw7.t7-prepatch-link-v3-source-tests/3';Checks=$checks;Status='Passed';NativeExecuted=$false;OpaqueInputsRead=$false}|ConvertTo-Json -Compress
