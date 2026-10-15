# Actual build profile/output/DEFAULT guards on authored text only. No prepare()/SDK/native.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$null=. (Join-Path $PSScriptRoot 'Test-ImageRegistrationBuild.ps1')
foreach($name in 'Assert-T7IncomingMetadataTransition','Assert-T7IncomingFixtureOutput'){
    $fn=$ast.Find({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$true)
    . ([scriptblock]::Create($fn.Extent.Text))
}
$checks=0;$ownedRuntime=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../runtime'))
$temp=Join-Path $ownedRuntime ('incoming-build-source-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($temp)|Out-Null
try{
    $ip=$(if($env:IW7_T7_IMAGE_FIXTURE_PROOF){$baseQualified}else{$p})|ConvertTo-Json -Depth 25|ConvertFrom-Json
    $ip.RunRoot=Join-Path $temp 'run';$ip.PreparedRoot=Join-Path $temp 'prepared'
    $native=Join-Path $temp 'native';[IO.Directory]::CreateDirectory($native)|Out-Null
    $ip.Inputs=@([pscustomobject]@{Path=(Join-Path $native 'src/zonetool/zonetool/t7/structs.hpp');Bytes=1;SHA256=('0'*64)})
    $profile=$ip.BuildProfile;$profile.Name='t7-incoming-image-header-observation-v1'
    $profile.Option='-t7-iw7-incoming-image-header-v1';$profile.ObservationSchema='iw7.t7-incoming-image-header-observation/1'
    $profile.MetadataFixtureNativeRoot=$native
    $profile|Add-Member NoteProperty IncomingSchema $profile.ObservationSchema
    $profile|Add-Member NoteProperty IncomingFixtureChecks 48
    $profile|Add-Member NoteProperty IncomingCPPQualified $false
    $c=Get-Content (Join-Path $PSScriptRoot 'incoming-image-source-contract.json') -Raw|ConvertFrom-Json
    $m=[pscustomobject]@{Schema='iw7.t7-incoming-image-build/1';SourceProfile=$profile.Name;SourceOnlyPending=$true;CPPQualified=$false;Ready=$false;
        BaseMainBytes=$ip.ReuseCompile.RegistrationMetadata.MainBytes;BaseMainSHA256=$ip.ReuseCompile.RegistrationMetadata.MainSHA256;
        BaseCLIBytes=$ip.ReuseCompile.RegistrationMetadata.CLIBytes;BaseCLISHA256=$ip.ReuseCompile.RegistrationMetadata.CLISHA256;
        MainBytes=$c.main.bytes;MainSHA256=$c.main.sha256;CLIBytes=$c.cli.bytes;CLISHA256=$c.cli.sha256}
    $ip.ReuseCompile|Add-Member NoteProperty IncomingObservation $m
    foreach($row in @(@('PreparedMain','main','main.cpp'),@('PreparedCLI','cli','zonetool.cpp'))){
        $profile.($row[0]).Path=Join-Path $ip.PreparedRoot $row[2];$profile.($row[0]).Bytes=$c.($row[1]).bytes;$profile.($row[0]).SHA256=$c.($row[1]).sha256
    }
    foreach($row in @(@('MainResponse','main.obj.rsp'),@('CLIResponse','zonetool11.obj.rsp'),@('LinkResponse','link.rsp'),
        @('MetadataFixtureResponse','metadata-fixture.rsp'),@('RegistrationResponse','registration-fixture.rsp'))){$profile.($row[0]).Path=Join-Path $temp $row[1]}
    $profile.MetadataGuardedObserver.Path=Join-Path $ip.PreparedRoot 'selected_material_metadata_guarded.hpp'
    $profile.RegistrationObserver.Path=Join-Path $ip.PreparedRoot 'selected_image_registration_observer.hpp'
    foreach($row in @(@('IncomingWiring','prepare_incoming_image_metadata.py'),@('IncomingContract','incoming-image-source-contract.json'),
        @('IncomingMembers','incoming_image_capture_members.inc'),@('IncomingModule','incoming_image_event_observation.hpp'),
        @('IncomingEntry','native_incoming_image_metadata.inc'),@('IncomingFixture','incoming_image_event_fixture.cpp'))){
        $path=Join-Path $PSScriptRoot $row[1]
        $profile|Add-Member NoteProperty $row[0] ([pscustomobject]@{Path=$path;Bytes=(Get-Item $path).Length;SHA256=(Get-FileHash $path).Hash.ToLowerInvariant()})
    }
    foreach($row in @(@('IncomingCapture','derived_capture','selected_image_incoming_capture.hpp'),
        @('IncomingObserver','derived_observer','selected_image_incoming_observer.hpp'),
        @('IncomingBaselineFixture','derived_baseline_fixture','incoming_registration_baseline_fixture.cpp'))){
        $profile|Add-Member NoteProperty $row[0] ([pscustomobject]@{Path=(Join-Path $ip.PreparedRoot $row[2]);Bytes=$c.($row[1]).bytes;SHA256=$c.($row[1]).sha256})
    }
    $fixtureRoot=Join-Path $ip.RunRoot 'registration-fixture-compile'
    $fixtureArgs=@('/nologo','/std:c++20','/EHsc','/W4','/WX','/MT','/Od','/Z7','/external:W0',
        ('/external:I'+(Join-Path $native 'src/zonetool')),('/external:I'+(Join-Path $native 'deps/json/single_include/nlohmann')),
        ('/I'+$PSScriptRoot),('/I'+$ip.PreparedRoot),'/sourceDependencies',(Join-Path $fixtureRoot 'dependencies.json'),
        ('/Fo'+(Join-Path $fixtureRoot 'registration-fixture.obj')),('/Fe'+(Join-Path $fixtureRoot 'registration-fixture.exe')),
        (Join-Path $PSScriptRoot 'incoming_image_event_fixture.cpp'),'/link','/INCREMENTAL:NO','/DEBUG',('/PDB:'+(Join-Path $fixtureRoot 'registration-fixture.pdb')))
    $rsp=$profile.RegistrationResponse.Path
    [IO.File]::WriteAllText($rsp,(@($fixtureArgs|ForEach-Object {'"'+$_+'"'})-join ' '))
    $profile.RegistrationResponse.Bytes=(Get-Item $rsp).Length;$profile.RegistrationResponse.SHA256=(Get-FileHash $rsp).Hash.ToLowerInvariant()
    foreach($row in @(@('registration-fixture-compile','RegistrationResponse'),@('main','MainResponse'),@('zonetool11','CLIResponse'),@('link','LinkResponse'))){
        @($ip.Stages|Where-Object Name -CEQ $row[0])[0].Arguments=@('@'+$profile.($row[1]).Path)
    }
    $ip.Stages[1].Image=Join-Path $fixtureRoot 'registration-fixture.exe'
    foreach($pin in @($profile.PSObject.Properties|Where-Object {$_.Value -is [pscustomobject] -and $_.Value.PSObject.Properties['Path']}|ForEach-Object Value)){
        $ip.Bindings=@($ip.Bindings|Where-Object Path -CNE $pin.Path)+@([pscustomobject]@{Path=$pin.Path;Bytes=$pin.Bytes;SHA256=$pin.SHA256;IsText=$true})
    }
    if(!(Assert-T7BuildProfile $ip $PSScriptRoot)){throw 'Authored incoming build profile refused'};$checks++
    foreach($field in 'Schema','SourceProfile','IncomingSchema','Name','Option','ObservationSchema'){
        $bad=$ip|ConvertTo-Json -Depth 25|ConvertFrom-Json
        if($field -cin @('IncomingSchema','Name','Option','ObservationSchema')){$bad.BuildProfile.$field=@($bad.BuildProfile.$field)}else{$bad.ReuseCompile.IncomingObservation.$field=@($bad.ReuseCompile.IncomingObservation.$field)}
        $why='';try{Assert-T7IncomingMetadataTransition $bad $PSScriptRoot}catch{$why=$_.Exception.Message}
        if($why -cne 'Incoming schema/profile text scalars required.'){throw "Missing exact incoming type refusal: $field"};$checks++
    }
    foreach($case in 'missing-marker','wrong-base','wrong-cli','old-name','old-option','premature-cpp','wrong-count','wrong-derived','wrong-args','wrong-order'){
        $bad=$ip|ConvertTo-Json -Depth 25|ConvertFrom-Json
        switch($case){missing-marker {$bad.ReuseCompile.PSObject.Properties.Remove('IncomingObservation')};wrong-base {$bad.ReuseCompile.IncomingObservation.BaseCLISHA256='0'*64};
            wrong-cli {$bad.BuildProfile.PreparedCLI.SHA256='0'*64};old-name {$bad.BuildProfile.Name='t7-registration-image-header-metadata-v1'};
            old-option {$bad.BuildProfile.Option='-t7-iw7-image-registration-metadata-v1'};premature-cpp {$bad.BuildProfile.IncomingCPPQualified=$true};
            wrong-count {$bad.BuildProfile.IncomingFixtureChecks=39};wrong-derived {$bad.BuildProfile.IncomingCapture.SHA256='0'*64};
            wrong-args {$bad.Stages[0].Arguments=@('/unsupported')};wrong-order {$bad.Stages=@($bad.Stages[1],$bad.Stages[0])+$bad.Stages[2..4]}}
        $refused=$false;try{$null=Assert-T7BuildProfile $bad $PSScriptRoot}catch{$refused=$true}
        if(!$refused){throw "Altered incoming profile accepted: $case"};$checks++
    }
    $buildProfile=$profile;$Run=$false;$result=. $body|ConvertFrom-Json
    if($result.CPPEnabled -or !$result.SourceOnlyPending -or $result.IncomingCPPQualified -or !$result.CPPRecipeNeedsQualification -or
       $result.IncomingFixtureRequired -ne 48 -or $result.RegistrationFixtureRequired -ne 39 -or $null -ne $result.CandidateBytes -or $null -ne $result.CandidateSHA256){throw 'DEFAULT invented incoming CPP qualification'};$checks++
    foreach($flag in 'NativeTypesLoaded','BinaryInputsHashed','ZoneHashObserved','LeaseAcquired','FilesCreated','Ready'){
        if($result.$flag -isnot [bool] -or $result.$flag){throw 'Incoming DEFAULT crossed source boundary'}
    };$checks++
    $probeRoot=Join-Path $temp 'authored-output';[IO.Directory]::CreateDirectory($probeRoot)|Out-Null
    $stdout=Join-Path $probeRoot 'stdout.log';$stderr=Join-Path $probeRoot 'stderr.log'
    $good="IW7_T7_REGISTRATION_HEADER_CHECKS=39`nIW7_T7_INCOMING_IMAGE_CHECKS=48`n"
    foreach($newline in "`n","`r`n"){
        [IO.File]::WriteAllText($stdout,$good.Replace("`n",$newline));[IO.File]::WriteAllText($stderr,'')
        $stageState=[ordered]@{};Assert-T7IncomingFixtureOutput $probeRoot $stageState
        if($stageState.LegacyRegistrationChecks -ne 39 -or $stageState.IncomingChecks -ne 48 -or $stageState.EngineInvoked){throw 'Actual fixture gate counters differ'};$checks++
    }
    foreach($case in 'only39','only48','wrong47','extra','stderr'){
        [IO.File]::WriteAllText($stdout,$good);[IO.File]::WriteAllText($stderr,'')
        switch($case){only39 {[IO.File]::WriteAllText($stdout,"IW7_T7_REGISTRATION_HEADER_CHECKS=39`n")};
            only48 {[IO.File]::WriteAllText($stdout,"IW7_T7_INCOMING_IMAGE_CHECKS=48`n")};wrong47 {[IO.File]::WriteAllText($stdout,$good.Replace('CHECKS=48','CHECKS=47'))};
            extra {[IO.File]::AppendAllText($stdout,"extra`n")};stderr {[IO.File]::WriteAllText($stderr,'fault')}}
        $refused=$false;try{Assert-T7IncomingFixtureOutput $probeRoot ([ordered]@{})}catch{$refused=$true}
        if(!$refused){throw "Incorrect fixture output accepted: $case"};$checks++
    }
    [ordered]@{SourceOnly=$true;Checks=$checks;CPPExecuted=$false;NativeObserved=$false;SDKOrOpaqueRead=$false;LeaseAcquired=$false;Ready=$false}|ConvertTo-Json -Compress
}finally{
    if([IO.Path]::GetFullPath($temp) -cne $temp -or [IO.Path]::GetDirectoryName($temp) -cne $ownedRuntime){throw 'Source test cleanup target changed'}
    Remove-Item -LiteralPath $temp -Recurse -Force
}
