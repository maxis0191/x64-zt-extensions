# Actual Source validators on authored declarations only; no file/provider/lease IO.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Run-T7Build.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Runner parse failed.'}
foreach($name in 'Assert-T7BuildProfile','Assert-T7OSResourceContext','Assert-T7InputBindings'){
    $fn=$ast.Find({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$true)
    . ([scriptblock]::Create($fn.Extent.Text))
}
function New-CallerFixture {
    $prepared='C:\authored-caller\prepared';$oldRoot='C:\authored-v3'
    $profile=[ordered]@{Name='t7-prepatch-image-caller-v1';Option='-t7-prepatch-image-caller-v1';ArgumentCount=2;
        Report='t7-prepatch-image-caller-v1.local.json';ObservationSchema='iw7.t7-prepatch-image-caller-observation/1'}
    $bindings=@()
    foreach($row in @(
        @('Helper',(Join-Path $prepared 'native_prepatch_image_caller_v1.inc'),16778,'39fd69039d16285ca574f73a768130e294c618a089ba365bacdf84fd2cfa0019'),
        @('Wiring',(Join-Path $PSScriptRoot 'prepare_prepatch_image_caller.py'),2749,'8e6edee60d06dda0c77f8f2cf73bd39677523f0ba046ced2046218cc7eb7d7a2'),
        @('RangeGuard',(Join-Path $prepared 'prepatch_image_caller_range.hpp'),3117,'0a633964ed558de91bae621b51b28d5e8e0eab20ab790fc000b1b3c6978aa38a'),
        @('RangeGuardSource',(Join-Path $PSScriptRoot 'prepatch_image_caller_range.hpp'),3117,'0a633964ed558de91bae621b51b28d5e8e0eab20ab790fc000b1b3c6978aa38a'),
        @('BoundaryFixture',(Join-Path $PSScriptRoot 'prepatch_image_caller_fixture.cpp'),3828,'a2471c937e91191fca49820a50ac15091832eaa54bb993c639671e490dd9ade4'),
        @('FixtureResponse','C:\authored-caller\caller-fixture.rsp',128,('a'*64)),
        @('BaseHelper',(Join-Path $PSScriptRoot 'native_prepatch_link_v3.inc'),15827,'cf839e18a68adb4ed3aae82d683ef110ab595fa8c172584e47ca4d11bb8db48d'),
        @('BaseWiring',(Join-Path $PSScriptRoot 'prepare_prepatch_link_v3.py'),2236,'66f70ca5a979745288232d76496a339e08d639ddf34560aada6e6b63c5bcffa1'),
        @('BaseBuildPlan','C:\retained-C\plan.json',292575,'422e79898fa2b16defc8193182fe146e2db5d73aeb4516c2bd2aaf87c409c4de'),
        @('BaseBuildReceipt','C:\retained-C\receipt.json',26199,'af6beecf7a8892e16266a7641d2799f665f86fa8ad7c40c61561b782534f7897'),
        @('BaseV3BuildPlan',(Join-Path $oldRoot 'build-plan.local.json'),305621,'e484cef7415b2697c188b0202f3771af15377ecb56d98a0a85bfc1d2418fe530'),
        @('BaseV3Main',(Join-Path $oldRoot 'prepared/main.cpp'),14469,'84cde2924df0a0553dd2cddb0ca173aed54af43d6874b06718c01d1a6cec4989'),
        @('PreparedMain',(Join-Path $prepared 'main.cpp'),14557,'2ff1c104f8dfc99432179b289a0453aa1a81b8a99703803fcede1869fae61133'))){
        $pin=[ordered]@{Path=$row[1];Bytes=$row[2];SHA256=$row[3]};$profile[$row[0]]=$pin
        $bindings+=[ordered]@{Path=$pin.Path;Bytes=$pin.Bytes;SHA256=$pin.SHA256;IsText=$true}
    }
    $marker=[ordered]@{Schema='iw7.t7-prepatch-image-caller-build/1';SourceProfile='t7-prepatch-image-caller-v1';
        RetainedMainBytes=12854;RetainedMainSHA256='40de5fda829cec32a5d75359f58e69c84db7d8ee54f198cf6befa2a6ebe6f86e';
        BaseMainBytes=14469;BaseMainSHA256='84cde2924df0a0553dd2cddb0ca173aed54af43d6874b06718c01d1a6cec4989';
        MainBytes=14557;MainSHA256='2ff1c104f8dfc99432179b289a0453aa1a81b8a99703803fcede1869fae61133';
        HelperBytes=16778;HelperSHA256='39fd69039d16285ca574f73a768130e294c618a089ba365bacdf84fd2cfa0019'}
    [ordered]@{BuildProfile=$profile;PreparedRoot=$prepared;Runner=(Join-Path $PSScriptRoot 'Run-T7Build.ps1');SourceCommit='fab935826c898806855376662a8a03317b3ad8f1';
        Bindings=$bindings;Inputs=@(@{Path='C:\retained-C\input.obj';Bytes=1024;SHA256=('1'*64)});
        Stages=@(@{Name='caller-fixture-compile'},@{Name='caller-fixture-test'},@{Name='main'},@{Name='link'});
        ReuseCompile=@{RecompiledMain=$true;PrepatchImageCallerV1=$marker;SourcePlan=$profile.BaseBuildPlan.Path;Receipt=$profile.BaseBuildReceipt.Path;
            OriginalStatus='Failed';Checks=51;StageRoots=@('C:\retained-C\zonetool11','C:\retained-C\xpak');
            SourcePlanSHA256=$profile.BaseBuildPlan.SHA256;ReceiptSHA256=$profile.BaseBuildReceipt.SHA256}}|ConvertTo-Json -Depth 12|ConvertFrom-Json
}
$checks=0;$fixture=New-CallerFixture
if(!(Assert-T7BuildProfile $fixture $PSScriptRoot)){throw 'Valid caller profile refused.'};$checks++
Assert-T7InputBindings $fixture;$checks++
foreach($change in @(
    {param($f)$f.BuildProfile.Option='-t7-prepatch-link-v3'},
    {param($f)$f.BuildProfile.Option=@($f.BuildProfile.Option)},
    {param($f)$f.BuildProfile.ObservationSchema='iw7.t7-prepatch-link-observation/3'},
    {param($f)$f.BuildProfile.ArgumentCount='2'},
    {param($f)$f.BuildProfile|Add-Member NoteProperty Address '0x1B1E5D'},
    {param($f)$f.BuildProfile|Add-Member NoteProperty CodeLimit 8193},
    {param($f)$f.BuildProfile=@($f.BuildProfile)},
    {param($f)$f.ReuseCompile.PSObject.Properties.Remove('PrepatchImageCallerV1')},
    {param($f)$f.ReuseCompile|Add-Member NoteProperty PrepatchLinkV3 @{}},
    {param($f)$f.ReuseCompile|Add-Member NoteProperty PrepatchReferenceV2 @{}},
    {param($f)$f.ReuseCompile|Add-Member NoteProperty ImageProvenance @{}},
    {param($f)$f.ReuseCompile|Add-Member NoteProperty RecompiledZonetool $false},
    {param($f)$f.ReuseCompile.RecompiledMain=$false},
    {param($f)$f.ReuseCompile.PrepatchImageCallerV1.Schema=@($f.ReuseCompile.PrepatchImageCallerV1.Schema)},
    {param($f)$f.ReuseCompile.PrepatchImageCallerV1=@($f.ReuseCompile.PrepatchImageCallerV1)},
    {param($f)$f.ReuseCompile.PrepatchImageCallerV1|Add-Member NoteProperty Extra $true},
    {param($f)$f.ReuseCompile.PrepatchImageCallerV1.BaseMainBytes=14524},
    {param($f)$f.ReuseCompile.PrepatchImageCallerV1.MainSHA256=('0'*64)},
    {param($f)$f.BuildProfile.Helper.SHA256=@($f.BuildProfile.Helper.SHA256)},
    {param($f)$f.BuildProfile.Helper=$null},
    {param($f)$f.BuildProfile.RangeGuard=$null},
    {param($f)$f.BuildProfile.RangeGuardSource.SHA256=('0'*64);$f.Bindings[3].SHA256=('0'*64)},
    {param($f)$f.BuildProfile.BoundaryFixture.Bytes++;$f.Bindings[4].Bytes++},
    {param($f)$f.BuildProfile.FixtureResponse=$null},
    {param($f)$f.BuildProfile.FixtureResponse.Bytes=0;$f.Bindings[5].Bytes=0},
    {param($f)$f.BuildProfile.FixtureResponse.SHA256='wrong';$f.Bindings[5].SHA256='wrong'},
    {param($f)$f.BuildProfile.Wiring.Path='C:\other.py'},
    {param($f)$f.BuildProfile.BaseV3BuildPlan.Bytes++;$f.Bindings[10].Bytes++},
    {param($f)$f.BuildProfile.BaseV3Main.Path='C:\wrong\main.cpp';$f.Bindings[11].Path=$f.BuildProfile.BaseV3Main.Path},
    {param($f)$f.BuildProfile.BaseV3Main.PSObject.Properties.Remove('SHA256')},
    {param($f)$f.Bindings[0].IsText=$false},
    {param($f)$f.Bindings+=@($f.Bindings[0])},
    {param($f)$f.Stages=@($f.Stages[2],$f.Stages[3])}
)){
    foreach($validator in 'profile','bindings'){
        $fixture=New-CallerFixture;& $change $fixture;$refused=$false
        try{if($validator -ceq 'profile'){$null=Assert-T7BuildProfile $fixture $PSScriptRoot}else{Assert-T7InputBindings $fixture}}catch{$refused=$true}
        if(!$refused){throw "Image-caller invalid $validator accepted: $change"};$checks++
    }
}
if('IW7.AnimationProbe.NativeJob' -as [type]){throw 'Source tests imported a native job type.'}
[ordered]@{Schema='iw7.t7-prepatch-image-caller-source-tests/1';Checks=$checks;Status='Passed';NativeExecuted=$false;CPPFixtureExecuted=$false;
    OpaqueInputsRead=$false;LeaseAcquired=$false;Ready=$false}|ConvertTo-Json -Compress
