# Authored metadata bodies only. No CPP tuple, SDK, file artifact, native job or lease.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
$source=Join-Path (Split-Path $PSScriptRoot -Parent) 't7-iw7'
$contractPath=Join-Path $source 'registration-bindings-build-source-contract.json'
$contract=Get-Content -LiteralPath $contractPath -Raw|ConvertFrom-Json
$producer=Get-Content -LiteralPath (Join-Path $source 'registration-material-bindings-source-contract.json') -Raw|ConvertFrom-Json
$contractSHA=(Get-FileHash -LiteralPath $contractPath).Hash.ToLowerInvariant()
$checks=0;$hash='a'*64;$stdout=$contract.fixture_stdout;$stderr=''
function Check([bool]$Value,[string]$Why){if(!$Value){throw $Why};$script:checks++}
function Refuses([scriptblock]$Action){$caught=$false;try{& $Action}catch{$caught=$true};Check $caught 'Altered CPP80 declaration accepted.'}
function New-DeclaredFixture {
    $prepared='C:\authored\prepared';$run='C:\authored\run';$src='C:\authored\source'
    $profile=[pscustomobject]@{Name='t7-registration-material-bindings-v1';Option='-t7-iw7-registration-material-bindings-v1';
        ObservationSchema='iw7.t7-registration-material-bindings/1';BindingsSchema='iw7.t7-registration-material-bindings/1';
        RegistrationSchema='iw7.t7-registration-image-header-metadata/1';ArgumentCount=5;RegistrationFixtureChecks=39;
        BindingsLegacyChecks=39;BindingsFixtureChecks=41;BindingsTotalChecks=80;
        SourceOnlyPending=$false;RegistrationCPPQualified=$false;BindingsCPPQualified=$false}
    foreach($row in @(@('BindingsBuildContract','registration-bindings-build-source-contract.json',3052,$contractSHA),
        @('BindingsBuildValidator','RegistrationBindingsBuild.Source.ps1',$contract.validator.bytes,$contract.validator.sha256),
        @('BindingsContract','registration-material-bindings-source-contract.json',5391,'d60f0e33d9dddb69656744f6481ba32ced1a7a040d75ff913908192297e3c9a6'),
        @('PreparedMain','main.cpp',$contract.producer.main.bytes,$contract.producer.main.sha256),
        @('PreparedCLI','zonetool.cpp',$contract.producer.cli.bytes,$contract.producer.cli.sha256))){
        $base=if($row[0] -cin @('PreparedMain','PreparedCLI')){$prepared}else{$src}
        $profile|Add-Member $row[0] ([pscustomobject]@{Path=(Join-Path $base $row[1]);Bytes=$row[2];SHA256=$row[3]})
    }
    $marker=[ordered]@{Schema='iw7.t7-registration-bindings-build/1';SourceProfile=$profile.Name;SourceOnlyPending=$true;
        CPPQualified=$false;NativeObserved=$false;Ready=$false;LegacyFixtureChecks=39;BindingsFixtureChecks=41;TotalFixtureChecks=80;ExpectedFixtureStdout=$stdout}
    foreach($row in @(@('BaseMain',$producer.base_main),@('BaseCLI',$producer.base_cli),@('Main',$contract.producer.main),@('CLI',$contract.producer.cli))){
        $marker[$row[0]+'Bytes']=$row[1].bytes;$marker[$row[0]+'SHA256']=$row[1].sha256
    }
    $names=@('registration-fixture-compile','registration-fixture-test','main','zonetool11','link');$kinds=@('Compile','Probe','Compile','Compile','Link')
    $sets=@('registration-fixture.obj|registration-fixture.exe|registration-fixture.pdb|dependencies.json','','main.obj|compile.pdb|dependencies.json',
        'zonetool11.obj|compile.pdb|dependencies.json','zonetool-t7.exe|zonetool-t7.pdb|zonetool-t7.lib|zonetool-t7.exp')
    $declared=@();$stages=@()
    for($i=0;$i -lt 5;$i++){
        $artifacts=@($sets[$i].Split('|')|Where-Object {$_})
        $seconds=if($i -eq 1){15}else{120}
        $declared+=,[pscustomobject]@{Name=$names[$i];Stage=$kinds[$i];DeadlineSeconds=$seconds;Artifacts=$artifacts;Arguments=@()}
        $pins=@(foreach($name in $artifacts){[pscustomobject]@{Path=(Join-Path (Join-Path $run $names[$i]) $name);Bytes=1;SHA256=('b'*64)}})
        $stage=[pscustomobject]@{Name=$names[$i];Stage=$kinds[$i];DeadlineSeconds=$seconds;PlanSHA256=$hash;ExitCode=0;TreeClosureConfirmed=$true;
            Artifacts=$pins;CompilerTelemetry=[pscustomobject]@{Completed=($i -ne 1);AfterStop=[pscustomobject]@{RootExited=$true;RootExitCode=0;ActiveProcesses=0};AfterStopMembers=[pscustomobject]@{Members=@()}}}
        if($i -eq 1){$stage|Add-Member LegacyRegistrationChecks 39;$stage|Add-Member BindingsChecks 41;$stage|Add-Member EngineInvoked $false}
        $stages+=,$stage
    }
    $build=[pscustomobject]@{Schema='iw7.t7-minimal-build-plan/1';SourceCommit='fab935826c898806855376662a8a03317b3ad8f1';
        RunRoot=$run;PreparedRoot=$prepared;GroupDeadlineSeconds=600;OutputLimitBytes=268435456;MetadataReserveBytes=1048576;
        BuildProfile=$profile;ReuseCompile=[pscustomobject]@{RegistrationBindingsObservation=[pscustomobject]$marker};Stages=$declared}
    $receipt=[pscustomobject]@{Schema='iw7.t7-minimal-build/1';Status='Passed';PlanSHA256=$hash;BuildProfile=($profile|ConvertTo-Json -Depth 12|ConvertFrom-Json);
        InputsReverified=$true;TreeClosureConfirmed=$true;LeaseReleased=$true;RegistrationFixturePassed=$true;RegistrationCPPQualified=$true;
        RegistrationBindingsFixturePassed=$true;Quarantined=$false;CandidateExecuted=$false;Ready=$false;
        CompilerTelemetry=[pscustomobject]@{Completed=$false};Stages=$stages}
    [pscustomobject]@{Build=$build;Receipt=$receipt}
}
# Any filesystem/process/admission helper reached by the shape check is a defect.
function Get-Item {throw 'Shape queried the filesystem.'}
function Get-FileHash {throw 'Shape hashed a file.'}
function Get-Content {throw 'Shape read a file.'}
function Assert-H1Path {throw 'Shape inspected path ancestry.'}
function New-T7PrepatchStart {throw 'Shape reached process setup.'}
function Enter-IW7ResourceLease {throw 'Shape attempted admission.'}
$f=New-DeclaredFixture;$before=$f|ConvertTo-Json -Depth 24 -Compress
$out=@(Assert-T7RegistrationBindingsCpp80Shape $f.Build $f.Receipt $hash $stdout $stderr)
Check ($out.Count -eq 0) 'Shape emitted a qualification result.'
Check (($f|ConvertTo-Json -Depth 24 -Compress) -ceq $before) 'Shape changed its input bodies.'
Assert-T7RegistrationBindingsCpp80Shape $f.Build $f.Receipt $hash ($stdout.Replace("`n","`r`n")) $stderr;Check $true 'CRLF marker refused.'
foreach($side in 'Build','Receipt'){
    $f=New-DeclaredFixture;$f.$side.BuildProfile=@($f.$side.BuildProfile)
    Refuses {Assert-T7RegistrationBindingsCpp80Shape $f.Build $f.Receipt $hash $stdout $stderr}
}
$f=New-DeclaredFixture # Later argument refusals must start from a valid body.
foreach($bad in @($null,@($hash),'old')){Refuses {Assert-T7RegistrationBindingsCpp80Shape $f.Build $f.Receipt $bad $stdout $stderr}}
foreach($bad in @($null,@($stdout),($stdout+'extra'),"IW7_T7_REGISTRATION_HEADER_CHECKS=39`nIW7_T7_INCOMING_IMAGE_CHECKS=48`n")){
    Refuses {Assert-T7RegistrationBindingsCpp80Shape $f.Build $f.Receipt $hash $bad $stderr}
}
foreach($bad in @($null,@(''),'error')){Refuses {Assert-T7RegistrationBindingsCpp80Shape $f.Build $f.Receipt $hash $stdout $bad}}
foreach($name in 'GroupDeadlineSeconds','OutputLimitBytes','MetadataReserveBytes'){
    $f=New-DeclaredFixture;$f.Build.$name=[string]$f.Build.$name
    Refuses {Assert-T7RegistrationBindingsCpp80Shape $f.Build $f.Receipt $hash $stdout $stderr}
}
foreach($field in 'InputsReverified','TreeClosureConfirmed','LeaseReleased','RegistrationFixturePassed','RegistrationCPPQualified','RegistrationBindingsFixturePassed'){
    foreach($bad in @($false,'true')){$f=New-DeclaredFixture;$f.Receipt.$field=$bad;Refuses {Assert-T7RegistrationBindingsCpp80Shape $f.Build $f.Receipt $hash $stdout $stderr}}
}
foreach($field in 'Quarantined','CandidateExecuted','Ready'){
    $f=New-DeclaredFixture;$f.Receipt.$field=$true;Refuses {Assert-T7RegistrationBindingsCpp80Shape $f.Build $f.Receipt $hash $stdout $stderr}
}
foreach($field in 'SourceOnlyPending','RegistrationCPPQualified','BindingsCPPQualified'){
    $f=New-DeclaredFixture;$f.Build.BuildProfile.$field=$true;Refuses {Assert-T7RegistrationBindingsCpp80Shape $f.Build $f.Receipt $hash $stdout $stderr}
}
foreach($role in 'BindingsBuildContract','BindingsBuildValidator','BindingsContract','PreparedMain','PreparedCLI'){
    foreach($kind in 'null','hash','bytes-array','path'){
        $f=New-DeclaredFixture;$pin=$f.Build.BuildProfile.$role
        switch($kind){null {$f.Build.BuildProfile.$role=$null};hash {$pin.SHA256='0'*64};bytes-array {$pin.Bytes=@($pin.Bytes)};path {$pin.Path+=':other'}}
        Refuses {Assert-T7RegistrationBindingsCpp80Shape $f.Build $f.Receipt $hash $stdout $stderr}
    }
}
foreach($case in 'old-mode','failed','mismatch-hash','receipt-source-path','fake-qualification','placeholder','incoming','marker-null','marker-extra','marker-promoted'){
    $f=New-DeclaredFixture
    switch($case){
        old-mode {$f.Build.BuildProfile.Name='t7-incoming-image-header-observation-v1'}
        failed {$f.Receipt.Status='Failed'}
        mismatch-hash {$f.Receipt.PlanSHA256='0'*64}
        receipt-source-path {$f.Receipt.BuildProfile.PreparedMain.Path='C:\foreign\main.cpp'}
        fake-qualification {$f.Receipt|Add-Member RegistrationBindingsCPPQualified $true}
        placeholder {$f.Receipt.CompilerTelemetry.Completed=$true}
        incoming {$f.Build.ReuseCompile|Add-Member IncomingObservation $false}
        marker-null {$f.Build.ReuseCompile.RegistrationBindingsObservation=$null}
        marker-extra {$f.Build.ReuseCompile.RegistrationBindingsObservation|Add-Member Extra $false}
        marker-promoted {$f.Build.ReuseCompile.RegistrationBindingsObservation.CPPQualified=$true}
    }
    Refuses {Assert-T7RegistrationBindingsCpp80Shape $f.Build $f.Receipt $hash $stdout $stderr}
}
for($i=0;$i -lt 5;$i++){
    foreach($case in 'exit','closure','deadline','telemetry','artifact'){
        $f=New-DeclaredFixture;$stage=$f.Receipt.Stages[$i]
        switch($case){exit {$stage.ExitCode=1};closure {$stage.TreeClosureConfirmed=$false};deadline {$stage.DeadlineSeconds=1};
            telemetry {$stage.CompilerTelemetry.Completed=!$stage.CompilerTelemetry.Completed};artifact {$stage.Artifacts+=,[pscustomobject]@{Path='C:\foreign\extra.bin';Bytes=1;SHA256=('b'*64)}}}
        Refuses {Assert-T7RegistrationBindingsCpp80Shape $f.Build $f.Receipt $hash $stdout $stderr}
    }
    if($i -ne 1){
        foreach($case in 'root-live','active-member','members-array'){
            $f=New-DeclaredFixture;$t=$f.Receipt.Stages[$i].CompilerTelemetry
            switch($case){root-live {$t.AfterStop.RootExited=$false};active-member {$t.AfterStop.ActiveProcesses=1};members-array {$t.AfterStopMembers.Members=@(123)}}
            Refuses {Assert-T7RegistrationBindingsCpp80Shape $f.Build $f.Receipt $hash $stdout $stderr}
        }
    }
}
foreach($case in 'legacy','new','new-text','engine','probe-args','source-artifacts','artifact-hash','artifact-empty','phase-order'){
    $f=New-DeclaredFixture
    switch($case){legacy {$f.Receipt.Stages[1].LegacyRegistrationChecks=38};new {$f.Receipt.Stages[1].BindingsChecks=48};
        new-text {$f.Receipt.Stages[1].BindingsChecks='41'};engine {$f.Receipt.Stages[1].EngineInvoked=$true};probe-args {$f.Build.Stages[1].Arguments=@('extra')};
        source-artifacts {$f.Build.Stages[4].Artifacts=@()};artifact-hash {$f.Receipt.Stages[4].Artifacts[0].SHA256='old'};
        artifact-empty {$f.Receipt.Stages[4].Artifacts[0].Bytes=0};phase-order {$f.Receipt.Stages=@($f.Receipt.Stages[1],$f.Receipt.Stages[0])+$f.Receipt.Stages[2..4]}}
    Refuses {Assert-T7RegistrationBindingsCpp80Shape $f.Build $f.Receipt $hash $stdout $stderr}
}
$f=New-DeclaredFixture;Assert-T7RegistrationBindingsCpp80Shape $f.Build $f.Receipt $hash $stdout $stderr
$intent=[pscustomobject]@{Operation='RegistrationMaterialBindingsV1'}
Refuses {Assert-T7CatalogueBuild $intent $f.Receipt};Refuses {New-T7CatalogueStart $intent}
Check (!('IW7.AnimationProbe.NativeJob' -as [type])) 'Source controls loaded a native type.'
[ordered]@{SourceOnly=$true;Checks=$checks;CPPExecuted=$false;FileArtifactsRead=$false;LeaseAcquired=$false;QualifiedCohortSelected=$false;Ready=$false}|ConvertTo-Json -Compress
