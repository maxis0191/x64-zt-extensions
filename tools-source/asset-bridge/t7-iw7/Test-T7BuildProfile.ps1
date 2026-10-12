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
"T7_BUILD_PROFILE_CHECKS=$checks"
