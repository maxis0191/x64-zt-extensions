# Actual metadata profile/stage guards with authored source paths; no SDK/CPP/engine.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$null=. (Join-Path $PSScriptRoot 'Test-ImageProvenanceBuild.ps1')
foreach($function in 'Assert-T7ImageMetadataTransition','Assert-T7ImageMetadataFixtureStages','Split-T7ResponseArguments'){
    $node=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $function},$true)
    if(!$node){throw "Actual metadata guard missing: $function"}
    . ([scriptblock]::Create($node.Extent.Text))
}
$checks=0;$tempRoot=Join-Path (Join-Path (Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent) 'runtime') ('metadata-source-check-'+[Guid]::NewGuid().ToString('N'))
$resolvedTemp=[IO.Path]::GetFullPath($tempRoot)
$expectedRuntime=[IO.Path]::GetFullPath((Split-Path $resolvedTemp -Parent))
[IO.Directory]::CreateDirectory($resolvedTemp)|Out-Null
try{
    $native=Join-Path $resolvedTemp 'native';[IO.Directory]::CreateDirectory($native)|Out-Null
    $prepared=Join-Path $resolvedTemp 'prepared';[IO.Directory]::CreateDirectory($prepared)|Out-Null
    $run=Join-Path $resolvedTemp 'run'
    $plan=$full|ConvertTo-Json -Depth 25|ConvertFrom-Json
    $plan|Add-Member NoteProperty RunRoot $run
    $plan|Add-Member NoteProperty Inputs @([pscustomobject]@{Path=(Join-Path $native 'src/zonetool/zonetool/t7/structs.hpp');Bytes=1;SHA256=('0'*64)})
    $plan.PreparedRoot=$prepared
    foreach($name in 'PreparedMain','PreparedCLI'){$plan.BuildProfile.$name.Path=Join-Path $prepared $(if($name -ceq 'PreparedMain'){'main.cpp'}else{'zonetool.cpp'})}
    foreach($name in 'MainResponse','CLIResponse','LinkResponse'){$plan.BuildProfile.$name.Path=Join-Path $resolvedTemp $(switch($name){MainResponse {'main.obj.rsp'};CLIResponse {'zonetool11.obj.rsp'};LinkResponse {'link.rsp'}})}
    foreach($row in @(@('main','MainResponse'),@('zonetool11','CLIResponse'),@('link','LinkResponse'))){
        $stage=@($plan.Stages|Where-Object Name -CEQ $row[0])[0];$stage.Arguments=@('@'+$plan.BuildProfile.($row[1]).Path)
    }
    $contractPath=Join-Path $PSScriptRoot 'image-metadata-source-contract.json'
    $contract=Get-Content -LiteralPath $contractPath -Raw|ConvertFrom-Json
    $profile=$plan.BuildProfile
    $profile|Add-Member NoteProperty MetadataSchema 'iw7.t7-selected-image-metadata/1'
    $profile|Add-Member NoteProperty MetadataOption '-t7-iw7-image-metadata-v1'
    $profile|Add-Member NoteProperty MetadataFixtureNativeRoot $native
    $profile|Add-Member NoteProperty MetadataMapperChecks 54
    $profile|Add-Member NoteProperty MetadataGuardChecks 13
    $extension=[ordered]@{Schema='iw7.t7-image-metadata-build/1';SourceProfile='t7-image-metadata-v1';
        BaseMainBytes=$marker.MainBytes;BaseMainSHA256=$marker.MainSHA256;BaseCLIBytes=$marker.CLIBytes;BaseCLISHA256=$marker.CLISHA256;
        MainBytes=$contract.main.bytes;MainSHA256=$contract.main.sha256;CLIBytes=$contract.cli.bytes;CLISHA256=$contract.cli.sha256}
    $plan.ReuseCompile|Add-Member NoteProperty ImageMetadata ([pscustomobject]$extension)
    $profile.PreparedMain.Bytes=$contract.main.bytes;$profile.PreparedMain.SHA256=$contract.main.sha256
    $profile.PreparedCLI.Bytes=$contract.cli.bytes;$profile.PreparedCLI.SHA256=$contract.cli.sha256
    $rows=@(@('MetadataWiring','prepare_image_metadata.py'),@('MetadataContract','image-metadata-source-contract.json'),
        @('MetadataPartsSource','selected_material_parts_observation.hpp'),@('MetadataBuilder','selected_image_header_metadata.hpp'),
        @('MetadataBuilderFixture','selected_image_header_metadata_fixture.cpp'),@('MetadataSource','selected_image_metadata.hpp'),
        @('MetadataEntry','native_image_metadata.inc'),@('MetadataReadGuard','selected_image_metadata_read_guard.hpp'),
        @('MetadataGuardFixture','selected_image_metadata_guard_fixture.cpp'))
    foreach($row in $rows){
        $path=Join-Path $PSScriptRoot $row[1]
        $pin=[pscustomobject]@{Path=$path;Bytes=(Get-Item -LiteralPath $path).Length;SHA256=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()}
        $profile|Add-Member NoteProperty $row[0] $pin
    }
    $profile|Add-Member NoteProperty MetadataGuardedObserver ([pscustomobject]@{Path=(Join-Path $prepared 'selected_material_metadata_guarded.hpp');
        Bytes=$contract.guarded_observer.bytes;SHA256=$contract.guarded_observer.sha256})
    $fixtureRoot=Join-Path $run 'metadata-fixture-compile'
    $fixtureArgs=@('/nologo','/std:c++20','/EHsc','/W4','/WX','/MT','/Od','/Z7','/external:W0',
        ('/external:I'+(Join-Path $native 'src/zonetool')),('/external:I'+(Join-Path $native 'deps/json/single_include/nlohmann')),
        ('/I'+$PSScriptRoot),('/I'+$prepared),'/sourceDependencies',(Join-Path $fixtureRoot 'dependencies.json'),
        ('/Fo'+(Join-Path $fixtureRoot 'metadata-fixture.obj')),('/Fe'+(Join-Path $fixtureRoot 'metadata-fixture.exe')),
        (Join-Path $PSScriptRoot 'selected_image_metadata_guard_fixture.cpp'),'/link','/INCREMENTAL:NO','/DEBUG',('/PDB:'+(Join-Path $fixtureRoot 'metadata-fixture.pdb')))
    $response=Join-Path $resolvedTemp 'metadata-fixture.rsp'
    [IO.File]::WriteAllText($response,(@($fixtureArgs|ForEach-Object {'"'+$_+'"'})-join ' '))
    $profile|Add-Member NoteProperty MetadataFixtureResponse ([pscustomobject]@{Path=$response;Bytes=(Get-Item $response).Length;SHA256=(Get-FileHash $response).Hash.ToLowerInvariant()})
    $plan.Stages=@([pscustomobject]@{Name='metadata-fixture-compile';Stage='Compile';Image=$plan.Compiler;Arguments=@('@'+$response);DeadlineSeconds=120;
        Artifacts=@('metadata-fixture.obj','metadata-fixture.exe','metadata-fixture.pdb','dependencies.json')},
        [pscustomobject]@{Name='metadata-fixture-test';Stage='Probe';Image=(Join-Path $fixtureRoot 'metadata-fixture.exe');Arguments=@();DeadlineSeconds=15;Artifacts=@()})+$plan.Stages
    # Rebuild the authored source binding references; none claims an actual recipe.
    $plan.Bindings=@($plan.Bindings|Where-Object {$_.Path -notin @($full.BuildProfile.PreparedMain.Path,$full.BuildProfile.PreparedCLI.Path,$full.BuildProfile.MainResponse.Path,$full.BuildProfile.CLIResponse.Path,$full.BuildProfile.LinkResponse.Path)})
    foreach($pin in @($profile.PSObject.Properties|Where-Object {$_.Value -is [pscustomobject] -and $_.Value.PSObject.Properties['Path']}|ForEach-Object Value)){
        $plan.Bindings=@($plan.Bindings|Where-Object Path -CNE $pin.Path)+@([pscustomobject]@{Path=$pin.Path;Bytes=$pin.Bytes;SHA256=$pin.SHA256;IsText=$true})
    }
    if(!(Assert-T7BuildProfile $plan $PSScriptRoot)){throw 'Authored metadata source profile refused'};$checks++
    foreach($case in 'missing-extension','wrong-base','wrong-new-output','wrong-option','wrong-native-root','wrong-check-count','missing-fixture-stage','altered-fixture-args'){
        $bad=$plan|ConvertTo-Json -Depth 25|ConvertFrom-Json
        switch($case){
            missing-extension {$bad.ReuseCompile.PSObject.Properties.Remove('ImageMetadata')}
            wrong-base {$bad.ReuseCompile.ImageMetadata.BaseCLISHA256='0'*64}
            wrong-new-output {$bad.BuildProfile.PreparedCLI.SHA256='0'*64}
            wrong-option {$bad.BuildProfile.MetadataOption='-t7-iw7-image-provenance-v1'}
            wrong-native-root {$bad.Inputs=@()}
            wrong-check-count {$bad.BuildProfile.MetadataGuardChecks=12}
            missing-fixture-stage {$bad.Stages=@($bad.Stages|Where-Object Name -CNE 'metadata-fixture-test')}
            altered-fixture-args {$bad.Stages[0].Arguments=@('/unsupported')}
        }
        $refused=$false;try{$null=Assert-T7BuildProfile $bad $PSScriptRoot}catch{$refused=$true}
        if(!$refused){throw "Invalid metadata source profile accepted: $case"};$checks++
    }
    [ordered]@{SourceOnly=$true;Checks=$checks;CPPExecuted=$false;NativeHeaderObserved=$false;SDKOrToolBytesRead=$false;Ready=$false}|ConvertTo-Json -Compress
}finally{
    if([IO.Path]::GetFullPath($resolvedTemp) -cne $resolvedTemp -or [IO.Path]::GetDirectoryName($resolvedTemp) -cne $expectedRuntime){throw 'Test cleanup target changed'}
    Remove-Item -LiteralPath $resolvedTemp -Recurse -Force
}
