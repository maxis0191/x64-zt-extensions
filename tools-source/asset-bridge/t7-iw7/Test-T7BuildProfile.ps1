# Exercise the runner's actual profile validator without loading any provider.
[CmdletBinding()]
param()
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$errors=$null;$tokens=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Run-T7Build.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Runner syntax errors.'}
$function=$ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq 'Assert-T7BuildProfile'},$true)
if(!$function){throw 'Actual profile validator missing.'}
. ([scriptblock]::Create($function.Extent.Text))
function New-Fixture {
    $prepared='C:\invented-t7-prepared'
    $profile=[ordered]@{Name='t7-prepatch-probe';Option='-t7-prepatch-probe';ArgumentCount=2;Report='t7-prepatch-probe.local.json'}
    $bindings=@()
    foreach($row in @(@('Helper',(Join-Path $prepared 'native_prepatch_probe.inc')),
        @('Wiring',(Join-Path $PSScriptRoot 'prepare_prepatch.py')),@('PreparedMain',(Join-Path $prepared 'main.cpp')))) {
        $pin=[ordered]@{Path=$row[1];Bytes=1024;SHA256=('a'*64)}
        $profile[$row[0]]=$pin
        $bindings+=[ordered]@{Path=$pin.Path;Bytes=$pin.Bytes;SHA256=$pin.SHA256;IsText=$true}
    }
    return ([ordered]@{BuildProfile=$profile;PreparedRoot=$prepared;Bindings=$bindings;ReuseCompile=@{RecompiledMain=$true}}|ConvertTo-Json -Depth 10|ConvertFrom-Json)
}
$checks=0
function Must-Refuse($Fixture) {
    $refused=$false
    try{$null=Assert-T7BuildProfile $Fixture $PSScriptRoot}catch{$refused=$true}
    if(!$refused){throw 'Unqualified diagnostic profile accepted.'}
    $script:checks++
}
if(!(Assert-T7BuildProfile (New-Fixture) $PSScriptRoot)){throw 'Qualified fixture refused.'};$checks++
if(Assert-T7BuildProfile ([pscustomobject]@{ReuseCompile=$null}) $PSScriptRoot){throw 'Legacy build classified as diagnostic.'};$checks++
$fixture=New-Fixture;$fixture.BuildProfile=$null;Must-Refuse $fixture
$fixture=New-Fixture;$fixture.ReuseCompile.RecompiledMain=$false;Must-Refuse $fixture
$fixture=New-Fixture;$fixture.BuildProfile.Option='-dumpzone';Must-Refuse $fixture
$fixture=New-Fixture;$fixture.BuildProfile.ArgumentCount=3;Must-Refuse $fixture
$fixture=New-Fixture;$fixture.BuildProfile.Report='other.json';Must-Refuse $fixture
$fixture=New-Fixture;$fixture.BuildProfile.Helper.Path='C:\unbound.inc';Must-Refuse $fixture
$fixture=New-Fixture;$fixture.BuildProfile.PreparedMain.SHA256=('b'*64);Must-Refuse $fixture
$fixture=New-Fixture;$fixture.Bindings[1].IsText=$false;Must-Refuse $fixture
$fixture=New-Fixture;$fixture.Bindings=@($fixture.Bindings)+@($fixture.Bindings[0]);Must-Refuse $fixture
function New-TraceFixture {
    $fixture=New-Fixture
    $profile=[ordered]@{Name='t7-catalog-trace';Option='-t7-iw7-catalog';ArgumentCount=3;TraceSchema='iw7.t7-catalog-trace/1'}
    $bindings=@()
    foreach($row in @(
        @('Wiring',(Join-Path $PSScriptRoot 'prepare_catalog_trace.py'),('a'*64)),
        @('PreparedMain',(Join-Path $fixture.PreparedRoot 'main.cpp'),('a'*64)),
        @('BaseBuildPlan','C:\ordinary-d2\build-plan.local.json','daa7097f872b83a5762b2cb56bf6dd5a235ed2beee8e0ff077276c61622d53fa'),
        @('BaseBuildReceipt','C:\ordinary-d2\receipt.json','c609bc56523654d8bca4b855024a463393185aab8e19ed4eae94c1ff8f6a09c2'))) {
        $pin=[ordered]@{Path=$row[1];Bytes=1024;SHA256=$row[2]}
        $profile[$row[0]]=$pin
        $bindings+=[ordered]@{Path=$pin.Path;Bytes=$pin.Bytes;SHA256=$pin.SHA256;IsText=$true}
    }
    $fixture.BuildProfile=([pscustomobject]$profile);$fixture.Bindings=$bindings
    return ($fixture|ConvertTo-Json -Depth 10|ConvertFrom-Json)
}
if(!(Assert-T7BuildProfile (New-TraceFixture) $PSScriptRoot)){throw 'Qualified catalogue trace refused.'};$checks++
$fixture=New-TraceFixture;$fixture.BuildProfile.Name='unknown-trace';Must-Refuse $fixture
$fixture=New-TraceFixture;$fixture.BuildProfile.Option='-t7-prepatch-probe';Must-Refuse $fixture
$fixture=New-TraceFixture;$fixture.BuildProfile.ArgumentCount=4;Must-Refuse $fixture
$fixture=New-TraceFixture;$fixture.BuildProfile.TraceSchema='iw7.t7-catalog-trace/2';Must-Refuse $fixture
$fixture=New-TraceFixture;$fixture.BuildProfile.BaseBuildPlan.SHA256=('b'*64);Must-Refuse $fixture
$fixture=New-TraceFixture;$fixture.BuildProfile.BaseBuildReceipt.SHA256=('b'*64);Must-Refuse $fixture
$fixture=New-TraceFixture;$fixture.BuildProfile.Wiring.Path='C:\other.py';Must-Refuse $fixture
$fixture=New-TraceFixture;$fixture.BuildProfile.PreparedMain.Bytes=65537;Must-Refuse $fixture
$fixture=New-TraceFixture;$fixture.BuildProfile|Add-Member -NotePropertyName Helper -NotePropertyValue @{};Must-Refuse $fixture
$fixture=New-TraceFixture;$fixture.Bindings[2].IsText=$false;Must-Refuse $fixture
$fixture=New-TraceFixture;$fixture.ReuseCompile.RecompiledMain=$false;Must-Refuse $fixture
$fixture=New-TraceFixture;$fixture.ReuseCompile.RecompiledMain='true';Must-Refuse $fixture
function New-ExitContextFixture {
    $fixture=New-TraceFixture
    $fixture.BuildProfile.Name='t7-catalog-exit-context'
    $fixture.BuildProfile|Add-Member -NotePropertyName ContextSchema -NotePropertyValue 'iw7.t7-catalog-exit-context/1'
    return $fixture
}
if(!(Assert-T7BuildProfile (New-ExitContextFixture) $PSScriptRoot)){throw 'Qualified exit context refused.'};$checks++
$fixture=New-ExitContextFixture;$fixture.BuildProfile.ContextSchema='iw7.t7-catalog-exit-context/2';Must-Refuse $fixture
$fixture=New-ExitContextFixture;$fixture.BuildProfile.TraceSchema='iw7.t7-catalog-trace/2';Must-Refuse $fixture
$fixture=New-ExitContextFixture;$fixture.BuildProfile.PSObject.Properties.Remove('ContextSchema');Must-Refuse $fixture
$fixture=New-ExitContextFixture;$fixture.BuildProfile.Name='t7-catalog-trace';Must-Refuse $fixture
$fixture=New-ExitContextFixture;$fixture.BuildProfile.PreparedMain.SHA256=('b'*64);Must-Refuse $fixture
$fixture=New-ExitContextFixture;$fixture.ReuseCompile.RecompiledMain=$false;Must-Refuse $fixture
$fixture=New-ExitContextFixture;$fixture.BuildProfile|Add-Member -NotePropertyName UnboundedStack -NotePropertyValue $true;Must-Refuse $fixture
function New-CallersFixture {
    $fixture=New-ExitContextFixture
    $fixture.BuildProfile.Name='t7-catalog-callers'
    $fixture.BuildProfile|Add-Member -NotePropertyName CallerSchema -NotePropertyValue 'iw7.t7-catalog-callers/1'
    return $fixture
}
if(!(Assert-T7BuildProfile (New-CallersFixture) $PSScriptRoot)){throw 'Qualified callers profile refused.'};$checks++
$fixture=New-CallersFixture;$fixture.BuildProfile.CallerSchema='iw7.t7-catalog-callers/2';Must-Refuse $fixture
$fixture=New-CallersFixture;$fixture.BuildProfile.ContextSchema='iw7.t7-catalog-exit-context/2';Must-Refuse $fixture
$fixture=New-CallersFixture;$fixture.BuildProfile.PSObject.Properties.Remove('CallerSchema');Must-Refuse $fixture
$fixture=New-CallersFixture;$fixture.BuildProfile.Name='t7-catalog-exit-context';Must-Refuse $fixture
$fixture=New-CallersFixture;$fixture.BuildProfile.PreparedMain.SHA256=('b'*64);Must-Refuse $fixture
$fixture=New-CallersFixture;$fixture.ReuseCompile.RecompiledMain=$false;Must-Refuse $fixture
$fixture=New-CallersFixture;$fixture.BuildProfile|Add-Member -NotePropertyName TargetAddresses -NotePropertyValue @('0x140584FD8');Must-Refuse $fixture
"T7_BUILD_PROFILE_CHECKS=$checks"
