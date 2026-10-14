# Execute the actual source gates on authored plans/output text, never native code.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$null=. (Join-Path $PSScriptRoot 'Test-ImageMetadataBuild.ps1')
foreach($function in 'Assert-T7RegistrationMetadataTransition','Assert-T7RegistrationFixtureOutput'){
    $node=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $function},$true)
    if(!$node){throw "Actual registration gate missing: $function"}
    . ([scriptblock]::Create($node.Extent.Text))
}
$checks=0;$ownedRuntime=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../runtime'))
$tempRoot=Join-Path $ownedRuntime ('registration-source-check-'+[Guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($tempRoot)|Out-Null
try{
    $p=$plan|ConvertTo-Json -Depth 25|ConvertFrom-Json
    $p.RunRoot=Join-Path $tempRoot 'run';$p.PreparedRoot=Join-Path $tempRoot 'prepared'
    $native=Join-Path $tempRoot 'native';[IO.Directory]::CreateDirectory($native)|Out-Null
    $p.Inputs=@([pscustomobject]@{Path=(Join-Path $native 'src/zonetool/zonetool/t7/structs.hpp');Bytes=1;SHA256=('0'*64)})
    $profile=$p.BuildProfile;$profile.Name='t7-registration-image-header-metadata-v1'
    $profile.Option='-t7-iw7-image-registration-metadata-v1';$profile.ObservationSchema='iw7.t7-registration-image-header-metadata/1'
    $profile.MetadataFixtureNativeRoot=$native
    $profile|Add-Member NoteProperty RegistrationSchema $profile.ObservationSchema
    $profile|Add-Member NoteProperty RegistrationFixtureChecks 39
    $profile|Add-Member NoteProperty RegistrationCPPQualified $false
    $contractPath=Join-Path $PSScriptRoot 'registration-image-metadata-source-contract.json'
    $c=Get-Content -LiteralPath $contractPath -Raw|ConvertFrom-Json
    $m=[pscustomobject]@{Schema='iw7.t7-registration-image-metadata-build/1';SourceProfile=$profile.Name;
        SourceOnlyPending=$true;CPPQualified=$false;Ready=$false;
        BaseMainBytes=$p.ReuseCompile.ImageMetadata.MainBytes;BaseMainSHA256=$p.ReuseCompile.ImageMetadata.MainSHA256;
        BaseCLIBytes=$p.ReuseCompile.ImageMetadata.CLIBytes;BaseCLISHA256=$p.ReuseCompile.ImageMetadata.CLISHA256;
        MainBytes=$c.main.bytes;MainSHA256=$c.main.sha256;CLIBytes=$c.cli.bytes;CLISHA256=$c.cli.sha256}
    $p.ReuseCompile|Add-Member NoteProperty RegistrationMetadata $m
    foreach($row in @(@('PreparedMain','main','main.cpp'),@('PreparedCLI','cli','zonetool.cpp'))){
        $profile.($row[0]).Path=Join-Path $p.PreparedRoot $row[2]
        $profile.($row[0]).Bytes=$c.($row[1]).bytes;$profile.($row[0]).SHA256=$c.($row[1]).sha256
    }
    foreach($row in @(@('MainResponse','main.obj.rsp'),@('CLIResponse','zonetool11.obj.rsp'),@('LinkResponse','link.rsp'),@('MetadataFixtureResponse','metadata-fixture.rsp'))){
        $profile.($row[0]).Path=Join-Path $tempRoot $row[1]
    }
    $profile.MetadataGuardedObserver.Path=Join-Path $p.PreparedRoot 'selected_material_metadata_guarded.hpp'
    foreach($row in @(@('RegistrationWiring','prepare_image_registration_metadata.py'),@('RegistrationContract','registration-image-metadata-source-contract.json'),
        @('RegistrationCapture','registration_image_header_capture.hpp'),@('RegistrationEntry','native_image_registration_metadata.inc'),@('RegistrationFixture','registration_image_header_fixture.cpp'))){
        $path=Join-Path $PSScriptRoot $row[1]
        $profile|Add-Member NoteProperty $row[0] ([pscustomobject]@{Path=$path;Bytes=(Get-Item -LiteralPath $path).Length;SHA256=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()})
    }
    $profile|Add-Member NoteProperty RegistrationObserver ([pscustomobject]@{Path=(Join-Path $p.PreparedRoot 'selected_image_registration_observer.hpp');Bytes=$c.derived_observer.bytes;SHA256=$c.derived_observer.sha256})
    $fixtureRoot=Join-Path $p.RunRoot 'registration-fixture-compile'
    $fixtureArgs=@('/nologo','/std:c++20','/EHsc','/W4','/WX','/MT','/Od','/Z7','/external:W0',
        ('/external:I'+(Join-Path $native 'src/zonetool')),('/external:I'+(Join-Path $native 'deps/json/single_include/nlohmann')),
        ('/I'+$PSScriptRoot),('/I'+$p.PreparedRoot),'/sourceDependencies',(Join-Path $fixtureRoot 'dependencies.json'),
        ('/Fo'+(Join-Path $fixtureRoot 'registration-fixture.obj')),('/Fe'+(Join-Path $fixtureRoot 'registration-fixture.exe')),
        (Join-Path $PSScriptRoot 'registration_image_header_fixture.cpp'),'/link','/INCREMENTAL:NO','/DEBUG',('/PDB:'+(Join-Path $fixtureRoot 'registration-fixture.pdb')))
    $response=Join-Path $tempRoot 'registration-fixture.rsp'
    [IO.File]::WriteAllText($response,(@($fixtureArgs|ForEach-Object {'"'+$_+'"'})-join ' '))
    $profile|Add-Member NoteProperty RegistrationResponse ([pscustomobject]@{Path=$response;Bytes=(Get-Item $response).Length;SHA256=(Get-FileHash $response).Hash.ToLowerInvariant()})
    $p.Stages=@([pscustomobject]@{Name='registration-fixture-compile';Stage='Compile';Image=$p.Compiler;Arguments=@('@'+$response);DeadlineSeconds=120;
        Artifacts=@('registration-fixture.obj','registration-fixture.exe','registration-fixture.pdb','dependencies.json')},
        [pscustomobject]@{Name='registration-fixture-test';Stage='Probe';Image=(Join-Path $fixtureRoot 'registration-fixture.exe');Arguments=@();DeadlineSeconds=15;Artifacts=@()})+@($p.Stages|Where-Object Name -CNotLike 'metadata-fixture-*')
    foreach($row in @(@('main','MainResponse'),@('zonetool11','CLIResponse'),@('link','LinkResponse'))){
        @($p.Stages|Where-Object Name -CEQ $row[0])[0].Arguments=@('@'+$profile.($row[1]).Path)
    }
    foreach($pin in @($profile.PSObject.Properties|Where-Object {$_.Value -is [pscustomobject] -and $_.Value.PSObject.Properties['Path']}|ForEach-Object Value)){
        $p.Bindings=@($p.Bindings|Where-Object Path -CNE $pin.Path)+@([pscustomobject]@{Path=$pin.Path;Bytes=$pin.Bytes;SHA256=$pin.SHA256;IsText=$true})
    }
    if(!(Assert-T7BuildProfile $p $PSScriptRoot)){throw 'New authored full registration profile refused'};$checks++
    foreach($case in 'missing-marker','wrong-base','wrong-output','wrong-profile','old-native-option','premature-cpp','wrong-check-count','missing-header','duplicate-header','missing-test','test-before-compile','old-fixture-order','wrong-argv','wrong-deadline','wrong-artifact','wrong-observer'){
        $bad=$p|ConvertTo-Json -Depth 25|ConvertFrom-Json
        switch($case){
            missing-marker {$bad.ReuseCompile.PSObject.Properties.Remove('RegistrationMetadata')}
            wrong-base {$bad.ReuseCompile.RegistrationMetadata.BaseCLISHA256='0'*64}
            wrong-output {$bad.BuildProfile.PreparedCLI.SHA256='0'*64}
            wrong-profile {$bad.BuildProfile.Name='t7-image-provenance-v1'}
            old-native-option {$bad.BuildProfile.Option='-t7-iw7-image-metadata-v1'}
            premature-cpp {$bad.BuildProfile.RegistrationCPPQualified=$true}
            wrong-check-count {$bad.BuildProfile.RegistrationFixtureChecks=53}
            missing-header {$bad.Inputs=@()}
            duplicate-header {$bad.Inputs+=@($bad.Inputs[0])}
            missing-test {$bad.Stages=@($bad.Stages|Where-Object Name -CNE 'registration-fixture-test')}
            test-before-compile {$bad.Stages=@($bad.Stages[1],$bad.Stages[0])+$bad.Stages[2..4]}
            old-fixture-order {$bad.Stages[0].Name='metadata-fixture-compile';$bad.Stages[1].Name='metadata-fixture-test'}
            wrong-argv {$bad.Stages[0].Arguments=@('/unsupported')}
            wrong-deadline {$bad.Stages[1].DeadlineSeconds=120}
            wrong-artifact {$bad.Stages[0].Artifacts=@('old.exe')}
            wrong-observer {$bad.BuildProfile.RegistrationObserver.SHA256='0'*64}
        }
        $refused=$false;try{$null=Assert-T7BuildProfile $bad $PSScriptRoot}catch{$refused=$true}
        if(!$refused){throw "Altered registration profile accepted: $case"};$checks++
    }
    # Actual early DEFAULT/-Run gate is before imports, native hashes and admission.
    $buildProfile=$profile;$Run=$false;$result=. $body|ConvertFrom-Json
    if(!$result.SourceOnlyPending -or $result.RegistrationCPPQualified -or !$result.FixtureFirstEnforced -or
       $result.RegistrationFixtureRequired -ne 39 -or $null -ne $result.CandidateSHA256 -or $null -ne $result.CandidateBytes){throw 'DEFAULT relabelled qualification'};$checks++
    foreach($flag in 'NativeTypesLoaded','BinaryInputsHashed','ZoneHashObserved','LeaseAcquired','FilesCreated','Ready'){
        if($result.$flag -isnot [bool] -or $result.$flag){throw 'DEFAULT reached side effects'}
    };$checks++
    $Run=$true;$refused=$false;try{. $body}catch{$refused=$_.Exception.Message -like 'Image-provenance producer is source-pending:*'}
    if(!$refused){throw 'Base-unqualified Run admitted'};$checks++
    $probeRoot=Join-Path $tempRoot 'authored-probe';[IO.Directory]::CreateDirectory($probeRoot)|Out-Null
    $stdout=Join-Path $probeRoot 'stdout.log';$stderr=Join-Path $probeRoot 'stderr.log'
    foreach($newline in "`n","`r`n"){
        [IO.File]::WriteAllText($stdout,"IW7_T7_REGISTRATION_HEADER_CHECKS=39"+$newline);[IO.File]::WriteAllText($stderr,'')
        $stageState=[ordered]@{};Assert-T7RegistrationFixtureOutput $probeRoot $stageState
        if($stageState.Checks -ne 39 -or $stageState.EngineInvoked){throw 'Actual output gate marker differs'};$checks++
    }
    foreach($case in 'old53','wrong38','extra-line','stderr'){
        [IO.File]::WriteAllText($stdout,"IW7_T7_REGISTRATION_HEADER_CHECKS=39`n");[IO.File]::WriteAllText($stderr,'')
        switch($case){old53 {[IO.File]::WriteAllText($stdout,"T7_IMAGE_PROVENANCE_CHECKS=53`n")};wrong38 {[IO.File]::WriteAllText($stdout,"IW7_T7_REGISTRATION_HEADER_CHECKS=38`n")};extra-line {[IO.File]::AppendAllText($stdout,"extra`n")};stderr {[IO.File]::WriteAllText($stderr,'fault')}}
        $refused=$false;try{Assert-T7RegistrationFixtureOutput $probeRoot ([ordered]@{})}catch{$refused=$true}
        if(!$refused){throw "Incorrect authored fixture output accepted: $case"};$checks++
    }
    [ordered]@{SourceOnly=$true;Checks=$checks;CPPExecuted=$false;NativeHeaderObserved=$false;SDKOrToolBytesRead=$false;LeaseAcquired=$false;Ready=$false}|ConvertTo-Json -Compress
}finally{
    if([IO.Path]::GetFullPath($tempRoot) -cne $tempRoot -or [IO.Path]::GetDirectoryName($tempRoot) -cne $ownedRuntime){throw 'Test cleanup target changed'}
    Remove-Item -LiteralPath $tempRoot -Recurse -Force
}
