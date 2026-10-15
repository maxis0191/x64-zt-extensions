# Actual Source validators against authored plans/output text; no SDK/native/H1 import.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$null=. (Join-Path $PSScriptRoot 'Test-IncomingImageBuild.ps1')
foreach($name in 'Open-T7Bootstrap','Import-T7BindingsBuildSource'){
    $fn=$ast.Find({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$true)
    if(!$fn){throw "Missing actual Source function: $name"}
    . ([scriptblock]::Create($fn.Extent.Text))
}
$guards=[Collections.Generic.List[object]]::new()
$ownedRuntime=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../runtime'))
$temp=Join-Path $ownedRuntime ('bindings-build-source-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($temp)|Out-Null
$checks=0
$caseContext='initial'
function Check([bool]$value,[string]$message){if(!$value){throw $message};$script:checks++}
function Refuses([scriptblock]$body){$refused=$false;try{&$body}catch{$refused=$true};Check $refused ('Authored inconsistent bindings Source accepted: '+$caseContext)}
try{
    $bp=$p|ConvertTo-Json -Depth 30|ConvertFrom-Json
    $bp.RunRoot=Join-Path $temp 'run';$bp.PreparedRoot=Join-Path $temp 'prepared'
    $native=Join-Path $temp 'native';[IO.Directory]::CreateDirectory($native)|Out-Null
    $bp.Inputs=@([pscustomobject]@{Path=(Join-Path $native 'src/zonetool/zonetool/t7/structs.hpp');Bytes=1;SHA256=('0'*64)})
    $profile=$bp.BuildProfile;$profile.Name='t7-registration-material-bindings-v1'
    $profile.Option='-t7-iw7-registration-material-bindings-v1';$profile.ObservationSchema='iw7.t7-registration-material-bindings/1'
    $profile.MetadataFixtureNativeRoot=$native
    foreach($row in @(@('BindingsSchema',$profile.ObservationSchema),@('BindingsCPPQualified',$false),
        @('BindingsLegacyChecks',39),@('BindingsFixtureChecks',41),@('BindingsTotalChecks',80))){$profile|Add-Member NoteProperty $row[0] $row[1]}
    $c=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'registration-bindings-build-source-contract.json') -Raw|ConvertFrom-Json
    $marker=[pscustomobject]@{Schema='iw7.t7-registration-bindings-build/1';SourceProfile=$profile.Name;SourceOnlyPending=$true;
        CPPQualified=$false;NativeObserved=$false;Ready=$false;LegacyFixtureChecks=39;BindingsFixtureChecks=41;TotalFixtureChecks=80;
        ExpectedFixtureStdout=$c.fixture_stdout;BaseMainBytes=$bp.ReuseCompile.RegistrationMetadata.MainBytes;
        BaseMainSHA256=$bp.ReuseCompile.RegistrationMetadata.MainSHA256;BaseCLIBytes=$bp.ReuseCompile.RegistrationMetadata.CLIBytes;
        BaseCLISHA256=$bp.ReuseCompile.RegistrationMetadata.CLISHA256;MainBytes=$c.producer.main.bytes;MainSHA256=$c.producer.main.sha256;
        CLIBytes=$c.producer.cli.bytes;CLISHA256=$c.producer.cli.sha256}
    $bp.ReuseCompile|Add-Member NoteProperty RegistrationBindingsObservation $marker
    foreach($row in @(@('PreparedMain','main','main.cpp'),@('PreparedCLI','cli','zonetool.cpp'))){
        $profile.($row[0]).Path=Join-Path $bp.PreparedRoot $row[2];$profile.($row[0]).Bytes=$c.producer.($row[1]).bytes;$profile.($row[0]).SHA256=$c.producer.($row[1]).sha256
    }
    foreach($row in @(@('MainResponse','main.obj.rsp'),@('CLIResponse','zonetool11.obj.rsp'),@('LinkResponse','link.rsp'),
        @('MetadataFixtureResponse','metadata-fixture.rsp'),@('RegistrationResponse','registration-fixture.rsp'))){$profile.($row[0]).Path=Join-Path $temp $row[1]}
    $profile.MetadataGuardedObserver.Path=Join-Path $bp.PreparedRoot 'selected_material_metadata_guarded.hpp'
    $profile.RegistrationObserver.Path=Join-Path $bp.PreparedRoot 'selected_image_registration_observer.hpp'
    foreach($row in @(@('BindingsBuildWiring','prepare_registration_bindings_build.py'),@('BindingsBuildValidator','RegistrationBindingsBuild.Source.ps1'),
        @('BindingsIncomingWiring','prepare_incoming_image_metadata.py'),
        @('BindingsBuildContract','registration-bindings-build-source-contract.json'),@('BindingsWiring','prepare_registration_material_bindings.py'),
        @('BindingsContract','registration-material-bindings-source-contract.json'),@('BindingsModule','registration_material_bindings.hpp'),
        @('BindingsEntry','native_registration_material_bindings.inc'),@('BindingsFixture','registration_material_bindings_fixture.cpp'),
        @('BindingsLegacyFixture','registration_image_header_fixture.cpp'))){
        $path=Join-Path $PSScriptRoot $row[1]
        $profile|Add-Member NoteProperty $row[0] ([pscustomobject]@{Path=$path;Bytes=(Get-Item $path).Length;SHA256=(Get-FileHash $path).Hash.ToLowerInvariant()})
    }
    foreach($row in @(@('BindingsCapture','selected_image_material_bindings_capture.hpp'),@('BindingsObserver','selected_image_material_bindings_observer.hpp'),
        @('BindingsBaselineFixture','bindings_registration_baseline_fixture.cpp'),@('BindingsCombinedFixture','registration_bindings_combined_fixture.cpp'))){
        $pin=$c.generated.('prepared/'+$row[1]);$profile|Add-Member NoteProperty $row[0] ([pscustomobject]@{Path=(Join-Path $bp.PreparedRoot $row[1]);Bytes=$pin.bytes;SHA256=$pin.sha256})
    }
    $root=Join-Path $bp.RunRoot 'registration-fixture-compile'
    $argsSource=@('/nologo','/std:c++20','/EHsc','/W4','/WX','/MT','/Od','/Z7','/external:W0',
        ('/external:I'+(Join-Path $native 'src/zonetool')),('/external:I'+(Join-Path $native 'deps/json/single_include/nlohmann')),
        ('/I'+$PSScriptRoot),('/I'+$bp.PreparedRoot),'/sourceDependencies',(Join-Path $root 'dependencies.json'),
        ('/Fo'+(Join-Path $root 'registration-fixture.obj')),('/Fe'+(Join-Path $root 'registration-fixture.exe')),
        (Join-Path $bp.PreparedRoot 'registration_bindings_combined_fixture.cpp'),'/link','/INCREMENTAL:NO','/DEBUG',('/PDB:'+(Join-Path $root 'registration-fixture.pdb')))
    [IO.File]::WriteAllText($profile.RegistrationResponse.Path,(@($argsSource|ForEach-Object {'"'+$_+'"'})-join ' '))
    $profile.RegistrationResponse.Bytes=(Get-Item $profile.RegistrationResponse.Path).Length
    $profile.RegistrationResponse.SHA256=(Get-FileHash $profile.RegistrationResponse.Path).Hash.ToLowerInvariant()
    $profile|Add-Member NoteProperty BindingsResponse $profile.RegistrationResponse
    foreach($row in @(@('registration-fixture-compile','RegistrationResponse'),@('main','MainResponse'),@('zonetool11','CLIResponse'),@('link','LinkResponse'))){
        @($bp.Stages|Where-Object Name -CEQ $row[0])[0].Arguments=@('@'+$profile.($row[1]).Path)
    }
    $bp.Stages[1].Image=Join-Path $root 'registration-fixture.exe'
    foreach($pin in @($profile.PSObject.Properties|Where-Object {$_.Value -is [pscustomobject] -and $_.Value.PSObject.Properties['Path']}|ForEach-Object Value)){
        $bp.Bindings=@($bp.Bindings|Where-Object Path -CNE $pin.Path)+@([pscustomobject]@{Path=$pin.Path;Bytes=$pin.Bytes;SHA256=$pin.SHA256;IsText=$true})
    }
    Check (Assert-T7BuildProfile $bp $PSScriptRoot) 'Actual bindings Source profile refused'
    # Execute the actual first bound expression; no full input/SDK walk is needed.
    $boundNode=$ast.Find({param($n)$n -is [Management.Automation.Language.IfStatementAst] -and
        $n.Extent.Text.Contains("throw 'Input set bound/uniqueness differs.'")},$true)
    $boundText=$boundNode.Clauses[0].Item1.Extent.Text
    $bound=[scriptblock]::Create($boundText)
    function Test-InputBound($Expression,[string]$Mode,[int]$Rows,[bool]$Duplicate=$false,[int]$InputRows=1146){
        $registrationBindings=$Mode -ceq 'bindings';$incoming=$Mode -ceq 'incoming';$registration=$true
        $metadata=$true;$provenance=$true;$parts=$false;$observed=$false
        $bindings=@(for($i=0;$i -lt $Rows;$i++){[pscustomobject]@{Path=('C:\authored\binding-'+$i)}})
        $inputs=@(for($i=0;$i -lt $InputRows;$i++){[pscustomobject]@{Path=('C:\authored\input-'+$i)}})
        if($Duplicate){$bindings[-1].Path=$bindings[0].Path}
        & $Expression
    }
    foreach($row in @(@('bindings',187,$false),@('bindings',188,$true),@('registration',173,$false),
        @('registration',174,$true),@('incoming',182,$false),@('incoming',183,$true))){
        Check ((Test-InputBound $bound $row[0] $row[1]) -eq $row[2]) 'Actual input bound mode differs'
    }
    Check (Test-InputBound $bound 'bindings' 187 $true) 'Duplicate Source binding passed first bound'
    Check (Test-InputBound $bound 'bindings' 187 $false 2049) 'Oversized input set passed first bound'
    $beforeText=$boundText.Replace('if($registrationBindings){187}elseif($incoming)','if($incoming)')
    Check ($beforeText -cne $boundText -and (Test-InputBound ([scriptblock]::Create($beforeText)) 'bindings' 187)) 'Original173-cap counterexample was not reproduced'
    foreach($role in @('BindingsBuildWiring','BindingsBuildValidator','BindingsBuildContract','BindingsWiring','BindingsContract','BindingsModule','BindingsEntry',
        'BindingsIncomingWiring','BindingsFixture','BindingsLegacyFixture','BindingsCapture','BindingsObserver','BindingsBaselineFixture','BindingsCombinedFixture','BindingsResponse')){
        foreach($kind in 'array','bytes-text','bytes-bool','path-array','hash-array','extra'){
            $caseContext=$role+'/'+$kind
            $bad=$bp|ConvertTo-Json -Depth 30|ConvertFrom-Json;$pin=$bad.BuildProfile.$role
            switch($kind){array {$bad.BuildProfile.$role=@($pin)};bytes-text {$pin.Bytes=[string]$pin.Bytes};bytes-bool {$pin.Bytes=$true};
                path-array {$pin.Path=@($pin.Path)};hash-array {$pin.SHA256=@($pin.SHA256)};extra {$pin|Add-Member NoteProperty Extra $true}}
            Refuses {Assert-T7BuildProfile $bad $PSScriptRoot}
        }
    }
    foreach($name in 'CPPQualified','NativeObserved','Ready'){
        $caseContext='proof/'+$name
        $bad=$bp|ConvertTo-Json -Depth 30|ConvertFrom-Json;$bad.ReuseCompile.RegistrationBindingsObservation.$name=$true
        Refuses {Assert-T7BuildProfile $bad $PSScriptRoot}
    }
    foreach($kind in 'missing','binary','hash','length-type'){
        $caseContext='before-import/'+$kind;$bad=$bp|ConvertTo-Json -Depth 30|ConvertFrom-Json
        $sourcePath=$bad.BuildProfile.BindingsBuildValidator.Path
        $sealed=@($bad.Bindings|Where-Object Path -CEQ $sourcePath)
        switch($kind){missing {$bad.Bindings=@($bad.Bindings|Where-Object Path -CNE $sourcePath)};
            binary {$sealed[0].IsText=$false};hash {$sealed[0].SHA256='0'*64};length-type {$sealed[0].Bytes=[string]$sealed[0].Bytes}}
        $beforeGuards=$guards.Count;Refuses {Assert-T7BuildProfile $bad $PSScriptRoot}
        Check ($guards.Count -eq $beforeGuards) 'Invalid Source binding reached bootstrap import'
    }
    # Real transition validator, synthetic contract file only; no fake asset/tool is opened.
    foreach($kind in 'baseline','wrong-hash','validator-null','source-null','generated-null'){
        $syntheticRoot=Join-Path $temp ('synthetic-source-'+$kind);[IO.Directory]::CreateDirectory($syntheticRoot)|Out-Null
        $caseContext='expected-subpin/'+$kind
        $synthetic=$bp|ConvertTo-Json -Depth 30|ConvertFrom-Json
        $contract=$c|ConvertTo-Json -Depth 30|ConvertFrom-Json
        switch($kind){wrong-hash {$contract.generated.'prepared/selected_image_material_bindings_capture.hpp'.sha256='0'*64};
            validator-null {$contract.validator=$null};source-null {$contract.source_pins.'registration_material_bindings.hpp'=$null};
            generated-null {$contract.generated.'prepared/selected_image_material_bindings_capture.hpp'=$null}}
        foreach($prop in $synthetic.BuildProfile.PSObject.Properties){
            if($prop.Name.StartsWith('Bindings',[StringComparison]::Ordinal) -and $prop.Value -is [pscustomobject] -and
               $prop.Value.PSObject.Properties['Path'] -and [IO.Path]::GetDirectoryName($prop.Value.Path) -ceq $PSScriptRoot){
                $oldPath=$prop.Value.Path;$prop.Value.Path=Join-Path $syntheticRoot ([IO.Path]::GetFileName($oldPath))
                $synthetic.Bindings=@($synthetic.Bindings|Where-Object Path -CNE $oldPath)
                $synthetic.Bindings+=@([pscustomobject]@{Path=$prop.Value.Path;Bytes=$prop.Value.Bytes;SHA256=$prop.Value.SHA256;IsText=$true})
            }
        }
        $contractPath=$synthetic.BuildProfile.BindingsBuildContract.Path
        [IO.File]::WriteAllText($contractPath,($contract|ConvertTo-Json -Depth 30),[Text.UTF8Encoding]::new($false))
        $contractPin=$synthetic.BuildProfile.BindingsBuildContract
        $contractPin.Bytes=(Get-Item $contractPath).Length;$contractPin.SHA256=(Get-FileHash $contractPath).Hash.ToLowerInvariant()
        @($synthetic.Bindings|Where-Object Path -CEQ $contractPath)[0].Bytes=$contractPin.Bytes
        @($synthetic.Bindings|Where-Object Path -CEQ $contractPath)[0].SHA256=$contractPin.SHA256
        [IO.File]::WriteAllBytes($synthetic.BuildProfile.BindingsBuildValidator.Path,[IO.File]::ReadAllBytes($bp.BuildProfile.BindingsBuildValidator.Path))
        if($kind -ceq 'baseline'){Import-T7BindingsBuildSource $synthetic $syntheticRoot;Assert-T7BindingsBuildTransition $synthetic $syntheticRoot;Check $true 'Synthetic baseline refused'}
        else{
            if($kind.EndsWith('-null',[StringComparison]::Ordinal)){
                $beforeGuards=$guards.Count;Refuses {Import-T7BindingsBuildSource $synthetic $syntheticRoot}
                Check ($guards.Count -eq $beforeGuards+1) 'NULL sub-pin reached helper bootstrap/import'
            }
            Refuses {Assert-T7BindingsBuildTransition $synthetic $syntheticRoot}
        }
    }
    foreach($case in 'counts','base','marker-missing','paired','stages','fixture-token'){
        $caseContext=$case
        $bad=$bp|ConvertTo-Json -Depth 30|ConvertFrom-Json
        switch($case){counts {$bad.BuildProfile.BindingsTotalChecks=87};base {$bad.ReuseCompile.RegistrationBindingsObservation.BaseCLISHA256='0'*64};
            marker-missing {$bad.ReuseCompile.PSObject.Properties.Remove('RegistrationBindingsObservation')};paired {$bad.BuildProfile.Name='t7-registration-image-header-metadata-v1'};
            stages {$bad.Stages=@($bad.Stages[1],$bad.Stages[0])+$bad.Stages[2..4]};fixture-token {[IO.File]::AppendAllText($bad.BuildProfile.RegistrationResponse.Path,' "other.cpp"')}}
        Refuses {Assert-T7BuildProfile $bad $PSScriptRoot}
    }
    $probe=Join-Path $temp 'authored-probe';[IO.Directory]::CreateDirectory($probe)|Out-Null
    foreach($nl in "`n","`r`n"){
        [IO.File]::WriteAllText((Join-Path $probe 'stdout.log'),$c.fixture_stdout.Replace("`n",$nl));[IO.File]::WriteAllText((Join-Path $probe 'stderr.log'),'')
        $state=[ordered]@{};Assert-T7BindingsFixtureOutput $probe $state
        Check ($state.LegacyRegistrationChecks -eq 39 -and $state.BindingsChecks -eq 41 -and !$state.EngineInvoked) 'Wrong actual fixture marker projection'
    }
    $caseContext='wrong-authored-output'
    foreach($text in @("IW7_T7_REGISTRATION_HEADER_CHECKS=39`n",($c.fixture_stdout+'extra'),"IW7_T7_REGISTRATION_HEADER_CHECKS=39`nIW7_T7_INCOMING_IMAGE_CHECKS=48`n")){
        [IO.File]::WriteAllText((Join-Path $probe 'stdout.log'),$text);Refuses {Assert-T7BindingsFixtureOutput $probe ([ordered]@{})}
    }
    [IO.File]::WriteAllText((Join-Path $probe 'stdout.log'),$c.fixture_stdout);[IO.File]::WriteAllText((Join-Path $probe 'stderr.log'),'authored error')
    Refuses {Assert-T7BindingsFixtureOutput $probe ([ordered]@{})}
    [ordered]@{SourceOnly=$true;Checks=$checks;CPPExecuted=$false;SDKOrToolBytesRead=$false;LeaseAcquired=$false;Ready=$false}|ConvertTo-Json -Compress
}finally{
    foreach($guard in $guards){$guard.Dispose()}
    if([IO.Path]::GetFullPath($temp) -cne $temp -or [IO.Path]::GetDirectoryName($temp) -cne $ownedRuntime){throw 'Source test cleanup target changed'}
    Remove-Item -LiteralPath $temp -Recurse -Force
}
