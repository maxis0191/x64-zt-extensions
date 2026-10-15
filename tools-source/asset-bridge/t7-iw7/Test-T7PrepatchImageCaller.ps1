# Actual Source validators on authored declarations/RSP text; no opaque/native/lease IO.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Run-T7Build.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Runner parse failed.'}
foreach($name in 'Open-T7Bootstrap','Split-T7ResponseArguments','Assert-T7ImageCallerFixtureResponse','Assert-T7BuildProfile','Assert-T7OSResourceContext','Assert-T7InputBindings'){
    $fn=$ast.Find({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$true)
    . ([scriptblock]::Create($fn.Extent.Text))
}
$guards=[Collections.Generic.List[object]]::new()
$script:callerSourceTestRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot ('../../../runtime/caller Source-response-test-'+[guid]::NewGuid().ToString('N'))))
[IO.Directory]::CreateDirectory($script:callerSourceTestRoot)|Out-Null
function Clear-CallerSourceGuards {
    foreach($guard in $script:guards){$guard.Dispose()};$script:guards.Clear()
}
function New-CallerFixture {
    Clear-CallerSourceGuards
    $prepared=Join-Path $script:callerSourceTestRoot 'prepared';$oldRoot='C:\authored-v3'
    $runRoot=Join-Path $script:callerSourceTestRoot 'run'
    $fixtureRoot=Join-Path $runRoot 'caller-fixture-compile'
    $response=Join-Path $script:callerSourceTestRoot 'caller-fixture.rsp'
    $fixtureArguments=@('/nologo','/std:c++20','/EHsc','/W4','/WX','/MT','/Od','/Z7',('/I'+$PSScriptRoot),
        '/sourceDependencies',(Join-Path $fixtureRoot 'dependencies.json'),('/Fo'+(Join-Path $fixtureRoot 'caller-fixture.obj')),
        ('/Fe'+(Join-Path $fixtureRoot 'caller-fixture.exe')),(Join-Path $PSScriptRoot 'prepatch_image_caller_fixture.cpp'),
        '/link','/INCREMENTAL:NO','/DEBUG',('/PDB:'+(Join-Path $fixtureRoot 'caller-fixture.pdb')))
    [IO.File]::WriteAllText($response,(@($fixtureArguments|ForEach-Object {'"'+$_+'"'}) -join ' '),[Text.UTF8Encoding]::new($false))
    $profile=[ordered]@{Name='t7-prepatch-image-caller-v1';Option='-t7-prepatch-image-caller-v1';ArgumentCount=2;
        Report='t7-prepatch-image-caller-v1.local.json';ObservationSchema='iw7.t7-prepatch-image-caller-observation/1'}
    $bindings=@()
    foreach($row in @(
        @('Helper',(Join-Path $prepared 'native_prepatch_image_caller_v1.inc'),16778,'39fd69039d16285ca574f73a768130e294c618a089ba365bacdf84fd2cfa0019'),
        @('Wiring',(Join-Path $PSScriptRoot 'prepare_prepatch_image_caller.py'),2749,'8e6edee60d06dda0c77f8f2cf73bd39677523f0ba046ced2046218cc7eb7d7a2'),
        @('RangeGuard',(Join-Path $prepared 'prepatch_image_caller_range.hpp'),3117,'0a633964ed558de91bae621b51b28d5e8e0eab20ab790fc000b1b3c6978aa38a'),
        @('RangeGuardSource',(Join-Path $PSScriptRoot 'prepatch_image_caller_range.hpp'),3117,'0a633964ed558de91bae621b51b28d5e8e0eab20ab790fc000b1b3c6978aa38a'),
        @('BoundaryFixture',(Join-Path $PSScriptRoot 'prepatch_image_caller_fixture.cpp'),3828,'a2471c937e91191fca49820a50ac15091832eaa54bb993c639671e490dd9ade4'),
        @('FixtureResponse',$response,(Get-Item -LiteralPath $response).Length,(Get-FileHash -LiteralPath $response).Hash.ToLowerInvariant()),
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
    [ordered]@{BuildProfile=$profile;PreparedRoot=$prepared;RunRoot=$runRoot;Compiler='C:\authored-compiler\cl.exe';Runner=(Join-Path $PSScriptRoot 'Run-T7Build.ps1');SourceCommit='fab935826c898806855376662a8a03317b3ad8f1';
        Bindings=$bindings;Inputs=@(@{Path='C:\retained-C\input.obj';Bytes=1024;SHA256=('1'*64)});
        Stages=@(
            @{Name='caller-fixture-compile';Stage='Compile';Image='C:\authored-compiler\cl.exe';DeadlineSeconds=120;Arguments=@('@'+$response);Artifacts=@('caller-fixture.obj','caller-fixture.exe','caller-fixture.pdb','dependencies.json')},
            @{Name='caller-fixture-test';Stage='Probe';Image=(Join-Path $fixtureRoot 'caller-fixture.exe');DeadlineSeconds=15;Arguments=@();Artifacts=@()},
            @{Name='main';Stage='Compile';Image='C:\authored-compiler\cl.exe';DeadlineSeconds=120;Arguments=@('@'+(Join-Path $script:callerSourceTestRoot 'main.obj.rsp'));Artifacts=@('main.obj','compile.pdb','dependencies.json')},
            @{Name='link';Stage='Link';Image='C:\authored-compiler\link.exe';DeadlineSeconds=120;Arguments=@('@'+(Join-Path $script:callerSourceTestRoot 'link.rsp'));Artifacts=@('zonetool-t7.exe','zonetool-t7.pdb','zonetool-t7.lib','zonetool-t7.exp')});
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
    {param($f)$f.ReuseCompile.OriginalStatus='Passed'},
    {param($f)$f.ReuseCompile.Checks='51'},
    {param($f)$f.ReuseCompile.StageRoots='C:\retained-C'},
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
    {param($f)$f.Stages[1].Arguments=@('extra')},
    {param($f)$f.Stages[1].Image='C:\other.exe'},
    {param($f)$f.Stages[0].DeadlineSeconds=121},
    {param($f)$f.Stages[0].Artifacts=@('other.exe')},
    {param($f)$f.Stages[0].Arguments=@('@C:\other.rsp')},
    {param($f)$f.Stages=@($f.Stages[2],$f.Stages[3])}
)){
    foreach($validator in 'profile','bindings'){
        $fixture=New-CallerFixture;& $change $fixture;$refused=$false
        try{if($validator -ceq 'profile'){$null=Assert-T7BuildProfile $fixture $PSScriptRoot}else{Assert-T7InputBindings $fixture}}catch{$refused=$true}
        if(!$refused){throw "Image-caller invalid $validator accepted: $change"};$checks++
    }
}
# Reproduce P2 with every path/source pin/stage still valid, including a real
# repinned RSP. Then require the actual held Source/parser/argv refusal.
$profileFunction=$ast.Find({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq 'Assert-T7BuildProfile'},$true).Extent.Text
$responseCall='if($caller){Assert-T7ImageCallerFixtureResponse $Plan $SourceRoot}'
if(($profileFunction.Split($responseCall,[StringSplitOptions]::None)).Count -ne 2){throw 'One actual caller response guard required.'}
. ([scriptblock]::Create($profileFunction.Replace('function Assert-T7BuildProfile(', 'function Assert-T7CallerBeforeRspFix(').Replace($responseCall,'')))
$rspCases=@('source','runtime','optimization','warnings','warnings-as-errors','include','object','executable','symbols','dependencies','extra','nested','extra-source','unclosed-quote','size')
foreach($rspCase in $rspCases){
    foreach($validator in 'profile','bindings'){
        $fixture=New-CallerFixture;$response=$fixture.BuildProfile.FixtureResponse.Path
        $rsp=[IO.File]::ReadAllText($response)
        switch($rspCase){
            source {$rsp=$rsp.Replace('prepatch_image_caller_fixture.cpp','other.cpp')}
            runtime {$rsp=$rsp.Replace('"/MT"','"/MD"')}
            optimization {$rsp=$rsp.Replace('"/Od"','"/O2"')}
            warnings {$rsp=$rsp.Replace('"/W4"','"/W3"')}
            warnings-as-errors {$rsp=$rsp.Replace('"/WX"','"/WX-"')}
            include {$rsp=$rsp.Replace(('"/I'+$PSScriptRoot+'"'),'"/IC:\other includes"')}
            object {$rsp=$rsp.Replace('caller-fixture.obj','other.obj')}
            executable {$rsp=$rsp.Replace('caller-fixture.exe','other.exe')}
            symbols {$rsp=$rsp.Replace('caller-fixture.pdb','other.pdb')}
            dependencies {$rsp=$rsp.Replace('dependencies.json','other.json')}
            extra {$rsp+=' "/DFAKE"'}
            nested {$rsp+=' "@C:\extra.rsp"'}
            extra-source {$rsp+=' "C:\other.cpp"'}
            unclosed-quote {$rsp+=' "'}
            size {$rsp+=(' '*16KB)}
        }
        [IO.File]::WriteAllText($response,$rsp,[Text.UTF8Encoding]::new($false))
        $fixture.BuildProfile.FixtureResponse.Bytes=(Get-Item -LiteralPath $response).Length
        $fixture.BuildProfile.FixtureResponse.SHA256=(Get-FileHash -LiteralPath $response).Hash.ToLowerInvariant()
        $fixture.Bindings[5].Bytes=$fixture.BuildProfile.FixtureResponse.Bytes
        $fixture.Bindings[5].SHA256=$fixture.BuildProfile.FixtureResponse.SHA256
        if(!(Assert-T7CallerBeforeRspFix $fixture $PSScriptRoot)){throw "Original P2 acceptance not reproduced: $rspCase"};$checks++
        $reason='';try{if($validator -ceq 'profile'){$null=Assert-T7BuildProfile $fixture $PSScriptRoot}else{Assert-T7InputBindings $fixture}}catch{$reason=$_.Exception.Message}
        $expectedReason=switch($rspCase){nested {'Unsupported or indirect publication response syntax.'};unclosed-quote {'Unclosed publication response quote.'};size {'Pinned finite image-caller fixture response required.'};default {'Exact image-caller fixture compile arguments required.'}}
        if($reason -cne $expectedReason -or ($rspCase -cne 'size' -and $guards.Count -ne 1)){
            throw "Repinned caller RSP refusal masked/missing ($rspCase/$validator): $reason"
        };$checks++
        Clear-CallerSourceGuards
    }
}
$probe=$ast.Find({param($n)$n -is [Management.Automation.Language.IfStatementAst] -and $n.Extent.Text.StartsWith("if(`$stage.Name -ceq 'caller-fixture-test')")},$true)
if(!$probe){throw 'Actual image-caller fixture gate missing.'}
$probeText=$probe.Clauses[0].Item2.Extent.Text
$probeBody=[scriptblock]::Create($probeText.Substring(1,$probeText.Length-2))
foreach($probeCase in 'lf','crlf','wrong-count','prefix','suffix','empty'){
    $observed="IW7_T7_PREPATCH_IMAGE_CALLER_CHECKS=25`n"
    switch($probeCase){crlf {$observed=$observed.Replace("`n","`r`n")};wrong-count {$observed=$observed.Replace('25','24')};prefix {$observed='extra'+$observed};suffix {$observed+='extra'};empty {$observed=''}}
    $stageState=[ordered]@{};$state=[ordered]@{ImageCallerFixturePassed=$false};$probeRefused=$false
    try{. $probeBody}catch{$probeRefused=$true}
    if($probeCase -cin @('lf','crlf')){
        if($probeRefused -or !$state.ImageCallerFixturePassed -or $stageState.Checks -ne 25 -or $stageState.EngineInvoked){throw 'Actual valid caller fixture output refused.'}
    }elseif(!$probeRefused -or $state.ImageCallerFixturePassed){throw 'Actual caller fixture gate accepted wrong marker.'}
    $checks++
}
if('IW7.AnimationProbe.NativeJob' -as [type]){throw 'Source tests imported a native job type.'}
Clear-CallerSourceGuards
[ordered]@{Schema='iw7.t7-prepatch-image-caller-source-tests/1';Checks=$checks;Status='Passed';NativeExecuted=$false;CPPFixtureExecuted=$false;
    RepinnedResponseMutationCases=$rspCases.Count;OriginalP2AcceptanceReproduced=$true;HeldSourceStreamValidated=$true;
    SourceResponseFixtureRoot=$script:callerSourceTestRoot;OpaqueInputsRead=$false;LeaseAcquired=$false;Ready=$false}|ConvertTo-Json -Compress
