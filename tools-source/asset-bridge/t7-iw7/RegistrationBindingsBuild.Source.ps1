# Source/metadata validation only; original process/job ownership remains H1.
function script:Get-T7BindingsBuildFields {
    @('BindingsSchema','BindingsCPPQualified','BindingsLegacyChecks','BindingsFixtureChecks','BindingsTotalChecks',
      'BindingsBuildWiring','BindingsBuildValidator','BindingsBuildContract','BindingsIncomingWiring','BindingsWiring','BindingsContract','BindingsModule',
      'BindingsEntry','BindingsFixture','BindingsLegacyFixture','BindingsCapture','BindingsObserver',
      'BindingsBaselineFixture','BindingsCombinedFixture','BindingsResponse')
}
function script:Assert-T7BindingsBuildPin($Plan,$Pin,[string]$Path,$Expected,[long]$Cap=32768,[switch]$AllowUnspecified) {
    if($Pin -isnot [pscustomobject] -or (@($Pin.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'Bytes,Path,SHA256' -or
       $Pin.Path -isnot [string] -or $Pin.Path -cne $Path -or
       ($Pin.Bytes -isnot [int] -and $Pin.Bytes -isnot [long]) -or $Pin.Bytes -le 0 -or $Pin.Bytes -gt $Cap -or
       $Pin.SHA256 -isnot [string] -or $Pin.SHA256 -cnotmatch '^[0-9a-f]{64}$') {throw 'Closed typed bindings build Source pin required.'}
    if($null -eq $Expected -and !$AllowUnspecified){throw 'Required bindings expected Source pin cannot be NULL.'}
    if($null -ne $Expected){
        if($Expected -isnot [pscustomobject] -or (@($Expected.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'bytes,sha256' -or
           ($Expected.bytes -isnot [int] -and $Expected.bytes -isnot [long]) -or $Expected.bytes -le 0 -or $Expected.bytes -gt $Cap -or
           $Expected.sha256 -isnot [string] -or $Expected.sha256 -cnotmatch '^[0-9a-f]{64}$' -or
           $Pin.Bytes -ne $Expected.bytes -or $Pin.SHA256 -cne $Expected.sha256){throw 'Bindings build Source pin differs.'}
    }
    $sealed=@($Plan.Bindings|Where-Object {$_.Path -is [string] -and $_.Path -ceq $Path})
    if($sealed.Count -ne 1 -or ($sealed[0].Bytes -isnot [int] -and $sealed[0].Bytes -isnot [long]) -or
       $sealed[0].SHA256 -isnot [string] -or $sealed[0].Bytes -ne $Pin.Bytes -or $sealed[0].SHA256 -cne $Pin.SHA256 -or
       $sealed[0].IsText -isnot [bool] -or !$sealed[0].IsText){throw 'Bindings build Source must be sealed once as text.'}
}
function script:Assert-T7BindingsBuildTransition($Plan,[string]$SourceRoot) {
    $p=$Plan.BuildProfile;$m=$Plan.ReuseCompile.RegistrationBindingsObservation
    $keys='BaseCLIBytes,BaseCLISHA256,BaseMainBytes,BaseMainSHA256,BindingsFixtureChecks,CLIBytes,CLISHA256,CPPQualified,ExpectedFixtureStdout,LegacyFixtureChecks,MainBytes,MainSHA256,NativeObserved,Ready,Schema,SourceOnlyPending,SourceProfile,TotalFixtureChecks'
    if($m -isnot [pscustomobject] -or (@($m.PSObject.Properties.Name|Sort-Object)-join ',') -cne $keys){throw 'Closed bindings build marker required.'}
    foreach($row in @(@('Schema','iw7.t7-registration-bindings-build/1'),@('SourceProfile','t7-registration-material-bindings-v1'))){
        if($m.($row[0]) -isnot [string] -or $m.($row[0]) -cne $row[1]){throw 'Exact bindings build marker identity required.'}
    }
    foreach($name in 'CPPQualified','NativeObserved','Ready') {if($m.$name -isnot [bool] -or $m.$name){throw 'Bindings source cannot promote runtime proof.'}}
    if($m.SourceOnlyPending -isnot [bool] -or !$m.SourceOnlyPending -or $p.BindingsCPPQualified -isnot [bool] -or $p.BindingsCPPQualified){throw 'Bindings build remains Source pending.'}
    foreach($row in @(@('LegacyFixtureChecks',39),@('BindingsFixtureChecks',41),@('TotalFixtureChecks',80))){
        if(($m.($row[0]) -isnot [int] -and $m.($row[0]) -isnot [long]) -or $m.($row[0]) -ne $row[1]){throw 'Typed 39 plus 41 fixture counts required.'}
    }
    foreach($row in @(@('BindingsLegacyChecks',39),@('BindingsFixtureChecks',41),@('BindingsTotalChecks',80))){
        if(($p.($row[0]) -isnot [int] -and $p.($row[0]) -isnot [long]) -or $p.($row[0]) -ne $row[1]){throw 'Typed bindings profile fixture counts required.'}
    }
    if($p.BindingsSchema -isnot [string] -or $p.BindingsSchema -cne 'iw7.t7-registration-material-bindings/1'){throw 'Exact bindings observation schema required.'}
    foreach($name in 'BaseMainBytes','BaseCLIBytes','MainBytes','CLIBytes'){
        if(($m.$name -isnot [int] -and $m.$name -isnot [long]) -or $m.$name -le 0){throw 'Bindings integer source size required.'}
    }
    foreach($name in 'BaseMainSHA256','BaseCLISHA256','MainSHA256','CLISHA256'){
        if($m.$name -isnot [string] -or $m.$name -cnotmatch '^[0-9a-f]{64}$'){throw 'Bindings source hash scalar required.'}
    }
    $base=$Plan.ReuseCompile.RegistrationMetadata
    foreach($row in @(@('BaseMainBytes','MainBytes'),@('BaseMainSHA256','MainSHA256'),@('BaseCLIBytes','CLIBytes'),@('BaseCLISHA256','CLISHA256'))){
        if($m.($row[0]) -cne $base.($row[1])){throw 'Bindings must extend the exact CPP39 source pair.'}
    }
    $contractPath=Join-Path $SourceRoot 'registration-bindings-build-source-contract.json'
    Assert-T7BindingsBuildPin $Plan $p.BindingsBuildContract $contractPath $null 16384 -AllowUnspecified
    for($part=$contractPath;$part;$part=[IO.Path]::GetDirectoryName($part)){
        if(([IO.File]::GetAttributes($part) -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Bindings Source contract reparse refused.'}
    }
    if((Get-Item -LiteralPath $contractPath).Length -ne $p.BindingsBuildContract.Bytes -or
       (Get-FileHash -LiteralPath $contractPath).Hash -ine $p.BindingsBuildContract.SHA256){throw 'Bindings Source contract bytes differ.'}
    $c=Get-Content -LiteralPath $contractPath -Raw|ConvertFrom-Json
    if($c -isnot [pscustomobject] -or (@($c.PSObject.Properties.Name|Sort-Object)-join ',') -cne
       'cpp_qualified,fixture_stdout,generated,legacy_checks,native_observed,native_source_commit,new_checks,payload_limit_bytes,producer,ready,schema,source_only_pending,source_pins,source_profile,stage_names,total_checks,validator'){
        throw 'Closed bindings build Source contract required.'
    }
    if($c.schema -isnot [string] -or $c.schema -cne 'iw7.t7-registration-bindings-build-source/1' -or
       $c.source_profile -isnot [string] -or $c.source_profile -cne $m.SourceProfile -or
       $c.native_source_commit -isnot [string] -or $c.native_source_commit -cne 'fab935826c898806855376662a8a03317b3ad8f1' -or
       $c.source_only_pending -isnot [bool] -or !$c.source_only_pending){throw 'Exact pending bindings Source contract required.'}
    foreach($name in 'cpp_qualified','native_observed','ready'){if($c.$name -isnot [bool] -or $c.$name){throw 'Source contract cannot promote runtime proof.'}}
    foreach($row in @(@('legacy_checks',39),@('new_checks',41),@('total_checks',80),@('payload_limit_bytes',458752))){
        if(($c.($row[0]) -isnot [int] -and $c.($row[0]) -isnot [long]) -or $c.($row[0]) -ne $row[1]){throw 'Typed exact bindings contract scope required.'}
    }
    if($c.producer -isnot [pscustomobject] -or (@($c.producer.PSObject.Properties.Name|Sort-Object)-join ',') -cne 'cli,main' -or
       $c.generated -isnot [pscustomobject] -or (@($c.generated.PSObject.Properties.Name|Sort-Object)-join ',') -cne
       'prepared/bindings_registration_baseline_fixture.cpp,prepared/registration_bindings_combined_fixture.cpp,prepared/selected_image_material_bindings_capture.hpp,prepared/selected_image_material_bindings_observer.hpp' -or
       $c.source_pins -isnot [pscustomobject] -or (@($c.source_pins.PSObject.Properties.Name|Sort-Object)-join ',') -cne
       'native_registration_material_bindings.inc,prepare_incoming_image_metadata.py,prepare_registration_bindings_build.py,prepare_registration_material_bindings.py,registration_image_header_fixture.cpp,registration_material_bindings_fixture.cpp,registration_material_bindings.hpp,registration-material-bindings-source-contract.json'){
        throw 'Closed bindings source/derived inventories required.'
    }
    $expected="IW7_T7_REGISTRATION_HEADER_CHECKS=39`nIW7_T7_REGISTRATION_BINDINGS_CHECKS=41`n"
    if($m.ExpectedFixtureStdout -isnot [string] -or $m.ExpectedFixtureStdout -cne $expected -or
       $c.fixture_stdout -isnot [string] -or $c.fixture_stdout -cne $expected -or
       $c.stage_names -isnot [array] -or @($c.stage_names).Count -ne 5 -or @($c.stage_names|Where-Object {$_ -isnot [string]}).Count -or
       (@($c.stage_names)-join ',') -cne 'registration-fixture-compile,registration-fixture-test,main,zonetool11,link'){throw 'Exact bindings fixture output and five phases required.'}
    foreach($row in @(@('main','PreparedMain','MainBytes','MainSHA256'),@('cli','PreparedCLI','CLIBytes','CLISHA256'))){
        $pin=$p.($row[1]);$wanted=$c.producer.($row[0]);$cap=if($row[0] -ceq 'main'){65536}else{196608}
        Assert-T7BindingsBuildPin $Plan $pin (Join-Path $Plan.PreparedRoot $(if($row[0] -ceq 'main'){'main.cpp'}else{'zonetool.cpp'})) $wanted $cap
        if($m.($row[2]) -ne $wanted.bytes -or $m.($row[3]) -cne $wanted.sha256){throw 'Bindings main/CLI marker differs.'}
    }
    $roles=@{
        BindingsBuildWiring='prepare_registration_bindings_build.py';BindingsBuildValidator='RegistrationBindingsBuild.Source.ps1'
        BindingsIncomingWiring='prepare_incoming_image_metadata.py'
        BindingsWiring='prepare_registration_material_bindings.py';BindingsContract='registration-material-bindings-source-contract.json'
        BindingsModule='registration_material_bindings.hpp';BindingsEntry='native_registration_material_bindings.inc'
        BindingsFixture='registration_material_bindings_fixture.cpp';BindingsLegacyFixture='registration_image_header_fixture.cpp'
    }
    foreach($role in $roles.Keys){
        $wanted=if($role -ceq 'BindingsBuildValidator'){$c.validator}elseif($c.source_pins.PSObject.Properties[$roles[$role]]){$c.source_pins.($roles[$role])}else{$null}
        Assert-T7BindingsBuildPin $Plan $p.$role (Join-Path $SourceRoot $roles[$role]) $wanted
    }
    foreach($row in @(@('BindingsCapture','selected_image_material_bindings_capture.hpp'),@('BindingsObserver','selected_image_material_bindings_observer.hpp'),
        @('BindingsBaselineFixture','bindings_registration_baseline_fixture.cpp'),@('BindingsCombinedFixture','registration_bindings_combined_fixture.cpp'))){
        Assert-T7BindingsBuildPin $Plan $p.($row[0]) (Join-Path $Plan.PreparedRoot $row[1]) $c.generated.('prepared/'+$row[1])
    }
    Assert-T7BindingsBuildPin $Plan $p.BindingsResponse (Join-Path (Split-Path $Plan.PreparedRoot -Parent) 'registration-fixture.rsp') $null 16384 -AllowUnspecified
}
function script:Assert-T7BindingsFixtureOutput([string]$StageRoot,$StageState) {
    $stdout=Join-Path $StageRoot 'stdout.log';$stderr=Join-Path $StageRoot 'stderr.log'
    if((Get-Item -LiteralPath $stdout).Length -gt 128 -or (Get-Item -LiteralPath $stderr).Length -ne 0 -or
       ([IO.File]::ReadAllText($stdout)).Replace("`r`n","`n") -cne "IW7_T7_REGISTRATION_HEADER_CHECKS=39`nIW7_T7_REGISTRATION_BINDINGS_CHECKS=41`n"){
        throw 'Exactly 39 legacy and 41 bindings actual checks required before main/CLI compilation.'
    }
    $StageState.LegacyRegistrationChecks=39;$StageState.BindingsChecks=41;$StageState.EngineInvoked=$false
}
