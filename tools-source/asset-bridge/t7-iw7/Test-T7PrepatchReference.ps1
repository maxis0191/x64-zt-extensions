# Exercise the actual build validators without loading providers or binaries.
[CmdletBinding()]
param()
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Run-T7Build.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Runner syntax differs.'}
foreach($name in 'Assert-T7BuildProfile','Assert-T7InputBindings') {
    $function=$ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq $name},$true)
    if(!$function){throw 'Actual validator missing.'}
    . ([scriptblock]::Create($function.Extent.Text))
}
function New-ReferenceFixture {
    $prepared='C:\invented-prepatch-v2\prepared'
    $profile=[ordered]@{Name='t7-prepatch-reference-v2';Option='-t7-prepatch-reference-v2';ArgumentCount=2;
        Report='t7-prepatch-reference-v2.local.json';ObservationSchema='iw7.t7-prepatch-reference-observation/2'}
    $bindings=@()
    foreach($row in @(
        @('Helper',(Join-Path $prepared 'native_prepatch_reference_v2.inc'),15785,'0309b81376d3708cc8de43d297b43fbdfbdd535120e0ad054c157735c2c7457a'),
        @('Wiring',(Join-Path $PSScriptRoot 'prepare_prepatch_reference.py'),3665,'89f3f26699f1240400c4bd96f2987963374658e55a8501cab7dc2543a84ceace'),
        @('BaseHelper',(Join-Path $PSScriptRoot 'native_prepatch_probe.inc'),16281,'a9f458d2783c845af6958c896bda07fa4b92a5ea23a14c9e5d1201fe234a2018'),
        @('BaseWiring',(Join-Path $PSScriptRoot 'prepare_prepatch.py'),3078,'162763ab503a7971bc56753e3aba9fc1c76bf181881f9bddf45718456467e129'),
        @('BaseBuildPlan','C:\invented-retained\build-plan.json',292575,'422e79898fa2b16defc8193182fe146e2db5d73aeb4516c2bd2aaf87c409c4de'),
        @('BaseBuildReceipt','C:\invented-retained\receipt.json',26199,'af6beecf7a8892e16266a7641d2799f665f86fa8ad7c40c61561b782534f7897'),
        @('PreparedMain',(Join-Path $prepared 'main.cpp'),14524,'e719365c5a7f407218a7218bd9c7090421934042c34a9f163d9a8e3d42ee1e28'))) {
        $pin=[ordered]@{Path=$row[1];Bytes=$row[2];SHA256=$row[3]}
        $profile[$row[0]]=$pin
        $bindings+=[ordered]@{Path=$pin.Path;Bytes=$pin.Bytes;SHA256=$pin.SHA256;IsText=$true}
    }
    $marker=[ordered]@{Schema='iw7.t7-prepatch-reference-build/2';SourceProfile='t7-prepatch-reference-v2';
        RetainedMainBytes=12854;RetainedMainSHA256='40de5fda829cec32a5d75359f58e69c84db7d8ee54f198cf6befa2a6ebe6f86e';
        BaseMainBytes=13160;BaseMainSHA256='55081db20863f291f4f1fea8c1c995995e5e548b56acf043201fbb2e361f3934';
        MainBytes=14524;MainSHA256='e719365c5a7f407218a7218bd9c7090421934042c34a9f163d9a8e3d42ee1e28';
        HelperBytes=15785;HelperSHA256='0309b81376d3708cc8de43d297b43fbdfbdd535120e0ad054c157735c2c7457a'}
    return ([ordered]@{BuildProfile=$profile;PreparedRoot=$prepared;Runner=(Join-Path $PSScriptRoot 'Run-T7Build.ps1');
        SourceCommit='fab935826c898806855376662a8a03317b3ad8f1';Bindings=$bindings;Inputs=@(@{Path='C:\invented-prepatch-v2\retained.obj';Bytes=1024;SHA256=('1'*64)});
        Stages=@(@{Name='main'},@{Name='link'});ReuseCompile=@{RecompiledMain=$true;PrepatchReferenceV2=$marker;
            SourcePlan=$profile.BaseBuildPlan.Path;Receipt=$profile.BaseBuildReceipt.Path;
            SourcePlanSHA256=$profile.BaseBuildPlan.SHA256;ReceiptSHA256=$profile.BaseBuildReceipt.SHA256}}|
        ConvertTo-Json -Depth 10|ConvertFrom-Json)
}
$checks=0
$fixture=New-ReferenceFixture
if(!(Assert-T7BuildProfile $fixture $PSScriptRoot)){throw 'Qualified V2 fixture refused.'};$checks++
Assert-T7InputBindings $fixture;$checks++
foreach($change in @(
    {param($f) $f.BuildProfile.Option='-t7-prepatch-probe'},
    {param($f) $f.BuildProfile.Name='t7-prepatch-probe'},
    {param($f) $f.BuildProfile.ArgumentCount=3},
    {param($f) $f.BuildProfile.ArgumentCount='2'},
    {param($f) $f.BuildProfile.ObservationSchema='iw7.t7-prepatch-memory-observation/1'},
    {param($f) $f.BuildProfile.Report='t7-prepatch-probe.local.json'},
    {param($f) $f.BuildProfile|Add-Member NoteProperty Addresses @('0x1D4600')},
    {param($f) $f.ReuseCompile.PSObject.Properties.Remove('PrepatchReferenceV2')},
    {param($f) $f.ReuseCompile.RecompiledMain=$false},
    {param($f) $f.ReuseCompile.RecompiledMain='true'},
    {param($f) $f.ReuseCompile|Add-Member NoteProperty RecompiledZonetool $false},
    {param($f) $f.ReuseCompile|Add-Member NoteProperty ZombiesAddObservationC2 @{}},
    {param($f) $f.ReuseCompile|Add-Member NoteProperty SelectedStreamedRenderOnlyV2 @{}},
    {param($f) $f.ReuseCompile.PrepatchReferenceV2|Add-Member NoteProperty Extra $true},
    {param($f) $f.ReuseCompile.PrepatchReferenceV2.Schema='iw7.t7-prepatch-reference-build/1'},
    {param($f) $f.ReuseCompile.PrepatchReferenceV2.SourceProfile='t7-prepatch-probe'},
    {param($f) $f.ReuseCompile.PrepatchReferenceV2.BaseMainSHA256=('0'*64)},
    {param($f) $f.ReuseCompile.PrepatchReferenceV2.RetainedMainSHA256=('0'*64)},
    {param($f) $f.ReuseCompile.SourcePlanSHA256=('0'*64)},
    {param($f) $f.BuildProfile.BaseBuildReceipt.SHA256=('0'*64);$f.Bindings[5].SHA256=('0'*64)},
    {param($f) $f.ReuseCompile.PrepatchReferenceV2.MainBytes='14524'},
    {param($f) $f.ReuseCompile.PrepatchReferenceV2.HelperSHA256=('0'*64)},
    {param($f) $f.BuildProfile.Helper.Path='C:\elsewhere.inc'},
    {param($f) $f.BuildProfile.Helper.SHA256=('0'*64);$f.Bindings[0].SHA256=('0'*64)},
    {param($f) $f.BuildProfile.Wiring.Bytes=2106;$f.Bindings[1].Bytes=2106},
    {param($f) $f.BuildProfile.BaseHelper.SHA256=('0'*64);$f.Bindings[2].SHA256=('0'*64)},
    {param($f) $f.BuildProfile.PreparedMain|Add-Member NoteProperty Extra $true},
    {param($f) $f.Bindings[0].IsText=$false},
    {param($f) $f.Bindings+=@($f.Bindings[0])},
    {param($f) $f.SourceCommit=('0'*40)},
    {param($f) $f.Stages=@($f.Stages[1],$f.Stages[0])},
    {param($f) $f.Stages+=@([pscustomobject]@{Name='zonetool11'})}
)) {
    foreach($validator in 'profile','bindings') {
        $fixture=New-ReferenceFixture
        & $change $fixture
        $refused=$false
        try {
            if($validator -ceq 'profile'){$null=Assert-T7BuildProfile $fixture $PSScriptRoot}
            else {Assert-T7InputBindings $fixture}
        } catch {$refused=$true}
        if(!$refused){throw "Unqualified prepatch V2 accepted by $validator : $change"}
        $checks++
    }
}
[ordered]@{Schema='iw7.t7-prepatch-reference-source-tests/2';Checks=$checks;NativeExecuted=$false;Status='Passed'}|ConvertTo-Json -Compress
