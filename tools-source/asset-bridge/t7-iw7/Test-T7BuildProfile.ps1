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
function New-MessageFixture {
    $fixture=New-CallersFixture
    $fixture.BuildProfile.Name='t7-catalog-message'
    $fixture.BuildProfile|Add-Member -NotePropertyName MessageSchema -NotePropertyValue 'iw7.t7-catalog-message/1'
    return $fixture
}
if(!(Assert-T7BuildProfile (New-MessageFixture) $PSScriptRoot)){throw 'Qualified message profile refused.'};$checks++
$fixture=New-MessageFixture;$fixture.BuildProfile.MessageSchema='iw7.t7-catalog-message/2';Must-Refuse $fixture
$fixture=New-MessageFixture;$fixture.BuildProfile.CallerSchema='iw7.t7-catalog-callers/2';Must-Refuse $fixture
$fixture=New-MessageFixture;$fixture.BuildProfile.PSObject.Properties.Remove('MessageSchema');Must-Refuse $fixture
$fixture=New-MessageFixture;$fixture.BuildProfile.Name='t7-catalog-callers';Must-Refuse $fixture
$fixture=New-MessageFixture;$fixture.BuildProfile.PreparedMain.SHA256=('b'*64);Must-Refuse $fixture
$fixture=New-MessageFixture;$fixture.ReuseCompile.RecompiledMain=$false;Must-Refuse $fixture
$fixture=New-MessageFixture;$fixture.BuildProfile|Add-Member -NotePropertyName MessageBytes -NotePropertyValue 4096;Must-Refuse $fixture
function New-PublicationFixture {
    $fixture=New-MessageFixture
    $fixture.BuildProfile.Name='t7-catalog-message-publication'
    $fixture.BuildProfile|Add-Member NoteProperty PublicationSchema 'iw7.t7-message-publication-build/1'
    $fixture.ReuseCompile|Add-Member NoteProperty RecompiledZonetool $true
    $fixture.ReuseCompile|Add-Member NoteProperty StageRoots @('C:\old\xpak')
    $fixture|Add-Member NoteProperty RunRoot 'C:\fresh'
    $fixture|Add-Member NoteProperty Compiler 'C:\compiler\cl.exe'
    $responseRoot=Split-Path $fixture.PreparedRoot -Parent
    foreach($row in @(@('PublicationWiring',(Join-Path $PSScriptRoot 'prepare_message_publication.py')),
        @('PublicationSource',(Join-Path $PSScriptRoot 'native_message_publication.inc')),
        @('PreparedCLI',(Join-Path $fixture.PreparedRoot 'zonetool.cpp')),
        @('MainResponse',(Join-Path $responseRoot 'main.obj.rsp')),
        @('CLIResponse',(Join-Path $responseRoot 'zonetool11.obj.rsp')),@('LinkResponse',(Join-Path $responseRoot 'link.rsp')))) {
        $pin=[pscustomobject]@{Path=$row[1];Bytes=1024;SHA256=('a'*64)}
        $fixture.BuildProfile|Add-Member NoteProperty $row[0] $pin
        $fixture.Bindings+=@([pscustomobject]@{Path=$pin.Path;Bytes=$pin.Bytes;SHA256=$pin.SHA256;IsText=$true})
    }
    $stages=@(foreach($row in @(@('main','MainResponse'),@('zonetool11','CLIResponse'),@('link','LinkResponse'))) {
        [pscustomobject]@{Name=$row[0];Arguments=@('@'+$fixture.BuildProfile.($row[1]).Path);
            Image=$(if($row[0] -ceq 'link'){'C:\compiler\link.exe'}else{$fixture.Compiler});
            Artifacts=@(if($row[0] -ceq 'link'){'zonetool-t7.exe','zonetool-t7.pdb','zonetool-t7.lib','zonetool-t7.exp'}
                else{($row[0]+'.obj'),'compile.pdb','dependencies.json'})}
    })
    $fixture|Add-Member NoteProperty Stages $stages
    return $fixture
}
if(!(Assert-T7BuildProfile (New-PublicationFixture) $PSScriptRoot)){throw 'Qualified two-TU publication fixture refused.'};$checks++
$fixture=New-PublicationFixture;$fixture.ReuseCompile.RecompiledZonetool=$false;Must-Refuse $fixture
$fixture=New-PublicationFixture;$fixture.ReuseCompile.RecompiledZonetool='true';Must-Refuse $fixture
$fixture=New-PublicationFixture;$fixture.ReuseCompile.PSObject.Properties.Remove('RecompiledZonetool');Must-Refuse $fixture
$fixture=New-PublicationFixture;$fixture.ReuseCompile.RecompiledMain=$false;Must-Refuse $fixture
$fixture=New-PublicationFixture;$fixture.BuildProfile.Name='t7-catalog-message';Must-Refuse $fixture
$fixture=New-PublicationFixture;$fixture.BuildProfile=$null;Must-Refuse $fixture
$fixture=New-PublicationFixture;$fixture.BuildProfile.PublicationSchema='other';Must-Refuse $fixture
$fixture=New-PublicationFixture;$fixture.Stages=@($fixture.Stages[0],$fixture.Stages[2]);Must-Refuse $fixture
$fixture=New-PublicationFixture;$fixture.Stages=@($fixture.Stages[1],$fixture.Stages[0],$fixture.Stages[2]);Must-Refuse $fixture
$fixture=New-PublicationFixture;$fixture.Stages[1].Arguments=@('@C:\old\zonetool11.obj.rsp');Must-Refuse $fixture
$fixture=New-PublicationFixture;$fixture.Stages[1].Arguments+=@('/FoC:\old\zonetool11.obj');Must-Refuse $fixture
$fixture=New-PublicationFixture;$fixture.Stages[1].Image='C:\other\cl.exe';Must-Refuse $fixture
$fixture=New-PublicationFixture;$fixture.Stages[1].Artifacts=@('compile.pdb','dependencies.json');Must-Refuse $fixture
$fixture=New-PublicationFixture;$fixture.Stages[0].Artifacts=@('main.obj','compile.pdb','dependencies.json','other.obj');Must-Refuse $fixture
$fixture=New-PublicationFixture;$fixture.Stages[2].Artifacts=@('zonetool-t7.exe');Must-Refuse $fixture
foreach($name in 'PublicationWiring','PublicationSource','PreparedCLI','MainResponse','CLIResponse','LinkResponse') {
    $fixture=New-PublicationFixture;$fixture.BuildProfile.$name.SHA256=('b'*64);Must-Refuse $fixture
    $fixture=New-PublicationFixture;$fixture.BuildProfile.PSObject.Properties.Remove($name);Must-Refuse $fixture
}
$fixture=New-PublicationFixture;$fixture.BuildProfile.PublicationSource.Bytes=16385;Must-Refuse $fixture
$fixture=New-PublicationFixture;$fixture.BuildProfile.LinkResponse.Bytes=262145;Must-Refuse $fixture
$fixture=New-MessageFixture;$fixture.ReuseCompile|Add-Member NoteProperty RecompiledZonetool $false;Must-Refuse $fixture

foreach($functionName in 'Split-T7ResponseArguments','Assert-T7ResponseOutputs','Assert-T7PublicationResponses') {
    $responseFunction=$ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and
        $node.Name -ceq $functionName},$true)
    if(!$responseFunction){throw 'Actual response validator or helper missing.'}
    . ([scriptblock]::Create($responseFunction.Extent.Text))
}
function New-Responses($Fixture) {
    $texts=@(foreach($row in @(@('main','main.cpp'),@('zonetool11','zonetool.cpp'))) {
        $stage=Join-Path $Fixture.RunRoot $row[0]
        '/c /Fo"'+(Join-Path $stage ($row[0]+'.obj'))+'" /Fd"'+(Join-Path $stage 'compile.pdb')+
            '" /sourceDependencies "'+(Join-Path $stage 'dependencies.json')+'" "'+(Join-Path $Fixture.PreparedRoot $row[1])+"`"`n"
    })
    $objects=@('C:\fresh\main\main.obj','C:\fresh\zonetool11\zonetool11.obj','C:\old\xpak\xpak.obj')+
        @(0..409|ForEach-Object {'C:\e7\object'+$_+'.OBJ'})
    $linkRoot=Join-Path $Fixture.RunRoot 'link'
    $flags='/INCREMENTAL:NO /OUT:"'+(Join-Path $linkRoot 'zonetool-t7.exe')+
        '" /PDB:"'+(Join-Path $linkRoot 'zonetool-t7.pdb')+'" /IMPLIB:"'+(Join-Path $linkRoot 'zonetool-t7.lib')+'" /PDBCompress'
    $texts+=@($flags+"`n"+(($objects|ForEach-Object {'"'+$_+'"'}) -join "`n")+"`n")
    return ,$texts
}
function Must-RefuseResponses($Fixture,$Texts) {
    $refused=$false
    try{Assert-T7PublicationResponses $Fixture $Texts[0] $Texts[1] $Texts[2]}catch{$refused=$true}
    if(!$refused){throw 'Stale or redirected publication objects accepted.'}
    $script:checks++
}
$fixture=New-PublicationFixture;$texts=New-Responses $fixture
Assert-T7PublicationResponses $fixture $texts[0] $texts[1] $texts[2];$checks++
foreach($name in 'main','zonetool11') {
    $fixture=New-PublicationFixture;$texts=New-Responses $fixture
    $texts[2]=$texts[2].Replace(('C:\fresh\'+$name+'\'),('C:\old\'+$name+'\'));Must-RefuseResponses $fixture $texts
}
foreach($mode in 'duplicate','missing','extra-root','old-in-flags','nested-response','wrong-xpak') {
    $fixture=New-PublicationFixture;$texts=New-Responses $fixture
    switch($mode) {
        duplicate {$texts[2]=$texts[2].Replace('C:\e7\object0.OBJ','C:\old\zonetool11\zonetool11.obj')}
        missing {$texts[2]=$texts[2].Replace(('"C:\fresh\zonetool11\zonetool11.obj"'+"`n"),'')}
        extra-root {$fixture.ReuseCompile.StageRoots+=@('C:\old\zonetool11')}
        old-in-flags {$texts[2]=$texts[2].Replace('/INCREMENTAL:NO','/INCREMENTAL:NO "C:\old\zonetool11\zonetool11.obj"')}
        nested-response {$texts[2]=$texts[2].Replace('/INCREMENTAL:NO','@C:\old\link.rsp')}
        wrong-xpak {$texts[2]=$texts[2].Replace('C:\old\xpak\xpak.obj','C:\other\xpak.obj')}
    }
    Must-RefuseResponses $fixture $texts
}
foreach($index in 0,1) {
    foreach($mode in 'object','pdb','deps','source','duplicate-fo','nested','multiline') {
        $fixture=New-PublicationFixture;$texts=New-Responses $fixture
        switch($mode) {
            object {$texts[$index]=$texts[$index].Replace('/Fo"C:\fresh\','/Fo"C:\old\')}
            pdb {$texts[$index]=$texts[$index].Replace('/Fd"C:\fresh\','/Fd"C:\old\')}
            deps {$texts[$index]=$texts[$index].Replace('/sourceDependencies "C:\fresh\','/sourceDependencies "C:\old\')}
            source {$texts[$index]=$texts[$index].Replace('C:\invented-t7-prepared\','C:\old\')}
            duplicate-fo {$texts[$index]='/Fo"C:\old\bad.obj" '+$texts[$index]}
            nested {$texts[$index]='@C:\old\compile.rsp '+$texts[$index]}
            multiline {$texts[$index]="/c`n"+$texts[$index]}
        }
        Must-RefuseResponses $fixture $texts
    }
}
# Independent-review P2 reproductions: an extra unquoted compile output and a
# redirected link output with every one of the 413 required objects unchanged.
$fixture=New-PublicationFixture;$texts=New-Responses $fixture
$texts[0]=$texts[0].Replace('/Fd','/FoC:\outside\stolen.obj /Fd');Must-RefuseResponses $fixture $texts
$texts=New-Responses $fixture
$texts[2]=$texts[2].Replace('/OUT:"C:\fresh\link\zonetool-t7.exe"','/OUT:C:\outside\stolen.exe')
Must-RefuseResponses $fixture $texts

$outputCases=@(foreach($index in 0,1) {
    $stage=if($index -eq 0){'main'}else{'zonetool11'}
    foreach($entry in @(@('Fo',($stage+'.obj'),''),@('Fd','compile.pdb',''),@('sourceDependencies','dependencies.json',' '))) {
        $path='C:\fresh\'+$stage+'\'+$entry[1]
        ,@($index,$entry[0],('/'+$entry[0]+$entry[2]+'"'+$path+'"'),$path)
    }
})
$outputCases+=@(foreach($entry in @(@('OUT','exe'),@('PDB','pdb'),@('IMPLIB','lib'))) {
    $path='C:\fresh\link\zonetool-t7.'+$entry[1]
    ,@(2,$entry[0],('/'+$entry[0]+':"'+$path+'"'),$path)
})
foreach($entry in $outputCases) {
    $index=$entry[0];$name=$entry[1];$canonical=$entry[2];$path=$entry[3]
    # All output options are checked across quoting, separators, switch prefixes
    # and case. Duplicate identical destinations are also refused.
    foreach($variant in @(('/'+$name+$path),('/'+$name+':'+$path),('/'+$name+' "'+$path+'"'),
        ('/'+$name+': "'+$path+'"'),('"/'+$name+':'+$path+'"'),('-'+$name.ToUpperInvariant()+':'+$path),
        ('/'+$name.Substring(0,1)+'"'+$name.Substring(1)+'":'+$path))) {
        $fixture=New-PublicationFixture;$texts=New-Responses $fixture
        $texts[$index]=$texts[$index].Replace($canonical,$variant)
        Assert-T7PublicationResponses $fixture $texts[0] $texts[1] $texts[2];$checks++
        $texts=New-Responses $fixture
        $texts[$index]=$texts[$index].Replace($canonical,($canonical+' '+$variant))
        Must-RefuseResponses $fixture $texts
        $texts=New-Responses $fixture
        $texts[$index]=$texts[$index].Replace($canonical,$variant.Replace($path,'C:\outside\stolen.file'))
        Must-RefuseResponses $fixture $texts
    }
    foreach($replacement in @('',('/'+$name+':'),('/'+$name+':""'),('/'+$name+':"'+$path),
        ('/'+$name+':"'+$path+'\"'),('/'+$name+':"'+$path+'""'),('/'+$name+':'+"`r"+$path),
        ('/'+$name+':'+[char]0+$path))) {
        $fixture=New-PublicationFixture;$texts=New-Responses $fixture
        $texts[$index]=$texts[$index].Replace($canonical,$replacement)
        Must-RefuseResponses $fixture $texts
    }
}
# Spaces inside quoted paths and the existing manifest/PDBCompress flags must
# not be mistaken for output switches or separators.
$fixture=New-PublicationFixture;$fixture.RunRoot='C:\fresh space';$fixture.PreparedRoot='C:\prepared space'
$texts=New-Responses $fixture
$texts[2]=$texts[2].Replace('C:\fresh\','C:\fresh space\').Replace('/INCREMENTAL:NO',
    '/INCREMENTAL:NO /MANIFESTUAC:"level=''asInvoker'' uiAccess=''false''"')
Assert-T7PublicationResponses $fixture $texts[0] $texts[1] $texts[2];$checks++
$bindingResult=(& (Join-Path $PSScriptRoot 'Test-T7InputBindings.ps1'))|ConvertFrom-Json
if(!$bindingResult.Passed -or $bindingResult.NativeInvoked -or $bindingResult.OpaqueContentRead){throw 'Early input binding tests failed.'}
$checks+=$bindingResult.Checks
"T7_BUILD_PROFILE_CHECKS=$checks"
