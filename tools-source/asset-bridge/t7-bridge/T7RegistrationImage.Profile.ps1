# Finite sibling for the actual closed registration CPP39 cohort. H1 owns lifecycle.
function Get-T7RegistrationImageCohort {
    [ordered]@{
        Source='b38a5d9cacc39f1e150a7ad0de21000c6e2f52d4';NativeSource='fab935826c898806855376662a8a03317b3ad8f1'
        EXEBytes=22024704;EXESHA256='eeeca36f26ff2c76b98a608fe17a6b47259401b1cd800f73fe886bd099ac6dbc'
        Plan=@(396872,'dd85b86f508439ee45ff9a23543f8b7e16e852b8dab39bf2215ebb1c53f6f4e4')
        Receipt=@(46047,'24380749ad1407e71587c57cfe35aea770cfa75510247749a8c165f7cdb8c0b1')
        SourceManifest=@(362970,'f13f0a2d319f500603d7b07bbb96a195b06fe2b2c34115c542252e74c0830b83')
        HostWitness=@(2313,'011864cfc3f0e61a54b4ea3ed0a2bd94761ba8d4b82a0c70857e140cc559020b')
        ClosureWitness=@(1287,'68408f6d089a7a7870073f612030136466a961e312186990405c1f298526407d')
        FixtureStdout=@(38,'3aa779ecccb3f318c1a61b34b0fc1b267077231c7ecaa9646c34ea999e483f3f')
    }
}
function Assert-T7RegistrationImagePlan($Plan) {
    if(!(Test-T7RegistrationImagePlan $Plan)){throw 'Exact registration operation/profile/schema required.'}
    $c=Get-T7RegistrationImageCohort
    $marker=$Plan.SelectedRegistrationImageHeaderV1
    Assert-T7CatalogueFields $marker @('Schema','SourceManifest','HostWitness','ClosureWitness','FixtureStdout')
    if($marker.Schema -cne 'iw7.t7-registration-image-cpp39/1' -or $Plan.BootstrapPolicy -cne 'QualifiedCollectionV3' -or
       $Plan.Bootstraps -isnot [array] -or $Plan.Bootstraps.Count -ne 23 -or !$Plan.PSObject.Properties['SharedQualification'] -or
       !(Test-T7CatalogueInteger $Plan.CandidateBytes 64MB) -or $Plan.CandidateBytes -ne $c.EXEBytes -or $Plan.CandidateSHA256 -cne $c.EXESHA256 -or
       $Plan.ExpectedBuildPlanSHA256 -cne $c.Plan[1] -or $Plan.ExpectedBuildReceiptSHA256 -cne $c.Receipt[1] -or
       $Plan.OutputKey -cne 't7_iw7_registration_image_metadata_v1' -or $Plan.TraceStderrLimitBytes -ne 16384){throw 'Exact CPP39 collection/tuple/bounds required.'}
    foreach($name in 'SelectedImageProvenanceV1','SelectedMaterialPartsV1','SelectedXpakProvider','ExportRequest','ExportRequestFile','SelectedStreamedRenderOnlyV2',
        'SelectedMeshMaterialObservation','ResidentMultiSurfaceV2','ResidentSurfaceCountDiagnostic','SelectedStreamedStaticV1','ZombiesObservationC','ZombiesAddObservationC2'){
        if($Plan.PSObject.Properties[$name]){throw 'Registration metadata cannot select another operation/provider.'}
    }
    $expected=@('-t7-iw7-image-registration-metadata-v1','mp_freerun_04','p7_fre_platform_cap_02','0')
    if($Plan.Arguments -isnot [array] -or $Plan.Arguments.Count -ne 4){throw 'Exact four registration arguments required.'}
    for($i=0;$i -lt 4;$i++){if($Plan.Arguments[$i] -isnot [string] -or $Plan.Arguments[$i] -cne $expected[$i]){throw 'Exact registration selector required.'}}
    foreach($name in 'SourceManifest','HostWitness','ClosureWitness','FixtureStdout'){
        $pin=$marker.$name;Assert-T7CatalogueFields $pin @('Path','Bytes','SHA256')
        if($pin.Bytes -ne $c[$name][0] -or $pin.SHA256 -cne $c[$name][1]){throw 'Exact closed CPP39 text pin required.'}
        Assert-T7CatalogueTextPin $pin $Plan.Bindings
    }
    foreach($name in 'Plan','Receipt'){
        $path=if($name -ceq 'Plan'){$Plan.BuildPlan}else{$Plan.BuildReceipt}
        Assert-T7CatalogueTextPin ([pscustomobject]@{Path=$path;Bytes=$c[$name][0];SHA256=$c[$name][1]}) $Plan.Bindings
    }
}
function Assert-T7RegistrationImageBuild($Plan,$Receipt) {
    Assert-T7RegistrationImagePlan $Plan
    $c=Get-T7RegistrationImageCohort;$m=$Plan.SelectedRegistrationImageHeaderV1
    $build=Read-H1SmallJson $Plan.BuildPlan 1MB
    $source=Read-H1SmallJson $m.SourceManifest.Path 1MB
    $hostProof=Read-H1SmallJson $m.HostWitness.Path 8KB;$closure=Read-H1SmallJson $m.ClosureWitness.Path 8KB
    Assert-T7RegistrationImageCpp39 $Plan $build $Receipt $source $hostProof $closure
    foreach($name in 'Wiring','PreparedMain','PreparedCLI','BaseBuildPlan','BaseBuildReceipt','LinkResponse',
        'RegistrationWiring','RegistrationContract','RegistrationCapture','RegistrationEntry','RegistrationFixture','RegistrationObserver','RegistrationResponse'){
        Assert-T7CatalogueTextPin $build.BuildProfile.$name $Plan.Bindings
    }
    $dependencies=@($Receipt.Stages[2].Artifacts|Where-Object {[IO.Path]::GetFileName($_.Path) -ceq 'dependencies.json'})
    if($dependencies.Count -ne 1){throw 'One original CPP39 main dependency text required.'}
    Assert-T7CatalogueTextPin $dependencies[0] $Plan.Bindings
}
function Assert-T7RegistrationImageCpp39($Plan,$Build,$Receipt,$Manifest,$HostWitness,$Closure) {
    $c=Get-T7RegistrationImageCohort;$p=$Build.BuildProfile
    if($Plan.CandidateBytes -ne $c.EXEBytes -or $Plan.CandidateSHA256 -cne $c.EXESHA256 -or
       $Plan.ExpectedBuildPlanSHA256 -cne $c.Plan[1] -or $Plan.ExpectedBuildReceiptSHA256 -cne $c.Receipt[1] -or
       $Build.SourceCommit -cne $c.NativeSource -or $Manifest.revisions.'x64-zt-extensions' -cne $c.Source -or
       $p.Name -cne 't7-registration-image-header-metadata-v1' -or $p.Option -cne '-t7-iw7-image-registration-metadata-v1' -or !(Test-T7CatalogueInteger $p.ArgumentCount 5) -or $p.ArgumentCount -ne 5 -or
       $p.ObservationSchema -cne 'iw7.t7-registration-image-header-metadata/1' -or $p.RegistrationSchema -cne $p.ObservationSchema -or
       $p.RegistrationFixtureChecks -ne 39 -or $p.SourceOnlyPending -isnot [bool] -or $p.SourceOnlyPending -or
       $p.RegistrationCPPQualified -isnot [bool] -or $p.RegistrationCPPQualified -or
       $Receipt.Schema -cne 'iw7.t7-minimal-build/1' -or $Receipt.Status -cne 'Passed' -or $Receipt.PlanSHA256 -cne $c.Plan[1]){throw 'Exact measured CPP39 recipe/source/receipt required.'}
    foreach($name in 'InputsReverified','TreeClosureConfirmed','LeaseReleased','RegistrationFixturePassed','RegistrationCPPQualified'){
        if($Receipt.$name -isnot [bool] -or !$Receipt.$name){throw 'CPP39 actual receipt qualification missing.'}
    }
    foreach($name in 'Quarantined','CandidateExecuted'){if($Receipt.$name -isnot [bool] -or $Receipt.$name){throw 'CPP39 must remain closed/unexecuted.'}}
    if($Receipt.Stages -isnot [array] -or ($Receipt.Stages.Name -join '|') -cne 'registration-fixture-compile|registration-fixture-test|main|zonetool11|link' -or
       ($Receipt.Stages.Stage -join '|') -cne 'Compile|Probe|Compile|Compile|Link'){throw 'Exact five CPP39 stages required.'}
    foreach($stage in $Receipt.Stages){
        if(!(Test-T7CatalogueInteger $stage.ExitCode 0) -or $stage.TreeClosureConfirmed -isnot [bool] -or !$stage.TreeClosureConfirmed){throw 'CPP39 stage failed/unclosed.'}
        if($stage.Stage -cin @('Compile','Link')){
            $t=$stage.CompilerTelemetry
            if($t.Completed -isnot [bool] -or !$t.Completed -or $t.AfterStop.RootExited -isnot [bool] -or !$t.AfterStop.RootExited -or
               !(Test-T7CatalogueInteger $t.AfterStop.RootExitCode 0) -or !(Test-T7CatalogueInteger $t.AfterStop.ActiveProcesses 0) -or
               $t.AfterStopMembers.Members -isnot [array] -or $t.AfterStopMembers.Members.Count){throw 'CPP39 original compiler/job not empty.'}
        }
    }
    if($Receipt.Stages[1].Checks -ne 39 -or $Receipt.Stages[1].EngineInvoked -isnot [bool] -or $Receipt.Stages[1].EngineInvoked){throw 'Actual authored39 fixture required.'}
    foreach($name in 'SameOriginalAppDomain','ContextVariableSame','GuardsVariableSame','StateVariableSame','ContextSame','CanExit','Closed','OwnerClosed','LeaseIsNull',
        'TreeClosureConfirmed','LeaseReleased','InputsReverified','RegistrationFixturePassed','RegistrationCPPQualified','CPPExecuted'){
        if($HostWitness.$name -isnot [bool] -or !$HostWitness.$name){throw 'CPP39 original context proof missing.'}
    }
    foreach($name in 'Quarantined','CandidateExecuted','Ready'){if($HostWitness.$name -isnot [bool] -or $HostWitness.$name){throw 'CPP39 host overclaims runtime.'}}
    foreach($name in 'NoExitVerified','VerifiedBeforeImportsAndAdmission'){if($HostWitness.Host.$name -isnot [bool] -or !$HostWitness.Host.$name){throw 'CPP39 original fresh NoExit host required.'}}
    if($HostWitness.Host.Invocation -cne '.' -or $HostWitness.Host.EntryAssembly -cne [IO.Path]::ChangeExtension($HostWitness.Host.Image,'.dll') -or
       $HostWitness.Parent.Image -cne $HostWitness.Host.Image -or $HostWitness.Host.Arguments -isnot [array] -or $HostWitness.Host.Arguments.Count -ne 6 -or
       $HostWitness.Host.Arguments[0] -cne $HostWitness.Host.EntryAssembly -or ($HostWitness.Host.Arguments[1..4] -join '|') -cne '-NoLogo|-NoProfile|-NoExit|-Command'){
        throw 'CPP39 exact physical/managed dot invocation required.'
    }
    foreach($name in 'MatchesLastStage','JobHandleClosed','ProcessHandleClosed'){
        if($HostWitness.OriginalOwner.$name -isnot [bool] -or !$HostWitness.OriginalOwner.$name){throw 'CPP39 original last owner not closed.'}
    }
    if($HostWitness.OriginalOwner.PID -ne 28908 -or !(Test-T7CatalogueInteger $HostWitness.OriginalOwner.ExitCode 0)){throw 'CPP39 original link identity/exit required.'}
    if($HostWitness.Schema -cne 'iw7.t7-image-registration-cpp-preexit/1' -or $HostWitness.Host.PID -ne 788 -or $HostWitness.Parent.PID -ne 8584 -or
       $HostWitness.Host.CreationFileTime -ne 134364942263246878 -or $HostWitness.Parent.CreationFileTime -ne 134364942260845785 -or
       $HostWitness.Guards -ne 0 -or $HostWitness.CallerSourceGuards -ne 0 -or $HostWitness.PlanSHA256 -cne $c.Plan[1] -or
       $Closure.Schema -cne 'iw7.t7-image-registration-cpp-closure/1' -or $Closure.Passed -isnot [bool] -or !$Closure.Passed -or
       $Closure.ActualPTYSession -ne 82491 -or !(Test-T7CatalogueInteger $Closure.ActualPTYExit 0) -or $Closure.PlanSHA256 -cne $c.Plan[1] -or
       $Closure.Receipt.SHA256 -cne $c.Receipt[1] -or $Closure.Preexit.SHA256 -cne $c.HostWitness[1] -or
       ($Closure.ExpectedIDs -join '|') -cne '788|3176|7536|8584|10528|19112|24732|24976|27288|28244|28908'){throw 'CPP39 exact original host/PTY/closure required.'}
    foreach($name in 'RemainingOwn','HeavyOrGames','Leases'){if($Closure.$name -isnot [array] -or $Closure.$name.Count){throw 'CPP39 independent closure is not empty.'}}
    foreach($name in 'CPPExecuted','RegistrationCPPQualified'){if($Closure.$name -isnot [bool] -or !$Closure.$name){throw 'CPP39 closure qualification missing.'}}
    foreach($name in 'CandidateExecuted','Ready'){if($Closure.$name -isnot [bool] -or $Closure.$name){throw 'CPP39 closure overclaims runtime.'}}
    $exe=@($Receipt.Stages[-1].Artifacts|Where-Object {$_.Path -ceq $Plan.CandidateSource})
    if($exe.Count -ne 1 -or $exe[0].Bytes -ne $c.EXEBytes -or $exe[0].SHA256 -cne $c.EXESHA256 -or
       $Plan.CandidateSource -cne (Join-Path $Build.RunRoot 'link/zonetool-t7.exe') -or $Plan.BuildReceipt -cne (Join-Path $Build.RunRoot 'receipt.json')){throw 'Original admitted CPP39 link artifact required.'}
}
function ConvertFrom-T7RegistrationImageRecord([string]$Text,[int]$ExitCode) {
    $records=[regex]::Matches($Text,'(?m)^.*?T7_REGISTRATION_IMAGE_METADATA (\{[^\r\n]*\})\r?$')
    if(!$records.Count){return 'RegistrationNoReport'}
    if($records.Count -ne 1 -or [Text.Encoding]::UTF8.GetByteCount($records[0].Groups[1].Value) -gt 64KB){throw 'One bounded registration metadata record required.'}
    $r=$records[0].Groups[1].Value|ConvertFrom-Json -Depth 25
    foreach($name in 'schema','source_profile','native_source_commit','zone','model','capture_phase','recheck_phase'){
        if($r.$name -isnot [string]){throw 'Typed registration metadata text scalars required.'}
    }
    Assert-T7CatalogueFields $r @('allocation_retained','association_rechecked_at_registration','atomic_snapshot_proven','binding_hash_u32','binding_index','capture_ordinal',
        'capture_phase','failure_stage','header_copies','header_rechecked_at_registration','image','image_header_bytes','lifetime_proven','lod','model','model_default',
        'name_rechecked_at_registration','native_source_commit','payload_bytes_read','pixels_copied','provenance','ready','reason','recheck_phase','refused',
        'registration_header_bytes_copied','registration_header_observed','runtime_abi_proven','same_object_proven','schema','slot','source_profile','zone')
    if($r -isnot [pscustomobject] -or $r.schema -cne 'iw7.t7-registration-image-header-metadata/1' -or
       $r.source_profile -cne 't7-registration-image-header-metadata-v1' -or $r.capture_phase -cne 'after_original_model_add' -or $r.recheck_phase -cne $r.capture_phase){throw 'Registration metadata object/schema/phases required.'}
    if($r.native_source_commit -cne 'fab935826c898806855376662a8a03317b3ad8f1' -or $r.zone -cne 'mp_freerun_04' -or $r.model -cne 'p7_fre_platform_cap_02'){
        throw 'Registration metadata source/zone/model differs.'
    }
    foreach($name in 'same_object_proven','allocation_retained','atomic_snapshot_proven','pixels_copied','runtime_abi_proven','lifetime_proven','ready'){
        if($r.$name -isnot [bool] -or $r.$name){throw 'Registration record promotes object/pixel/runtime proof.'}
    }
    if($r.refused -isnot [bool] -or !(Test-T7CatalogueInteger $r.payload_bytes_read 0)){throw 'Typed registration refusal and zero payload required.'}
    if($r.refused){if($ExitCode -eq 0){throw 'Registration refusal contradicts exit zero.'};return 'RegistrationRecordRefused'}
    if($r.model_default -isnot [bool] -or $r.model_default){throw 'Default model cannot qualify registration capture.'}
    foreach($pair in @(@('lod',0),@('slot',0),@('binding_index',4),@('binding_hash_u32',2695565377))){
        if(!(Test-T7CatalogueInteger $r.($pair[0]) $pair[1]) -or $r.($pair[0]) -ne $pair[1]){throw 'Exact typed registration selection required.'}
    }
    foreach($name in 'registration_header_observed','association_rechecked_at_registration','header_rechecked_at_registration','name_rechecked_at_registration'){
        if($r.$name -isnot [bool] -or !$r.$name){throw 'Registration capture/rechecks incomplete.'}
    }
    foreach($pair in @(@('image_header_bytes',264),@('header_copies',2),@('registration_header_bytes_copied',528))){
        if(!(Test-T7CatalogueInteger $r.($pair[0]) $pair[1]) -or $r.($pair[0]) -ne $pair[1]){throw 'Two complete typed registration copies required.'}
    }
    if(!(Test-T7CatalogueInteger $r.capture_ordinal ([long]::MaxValue)) -or $r.capture_ordinal -le 0 -or
       $r.capture_ordinal -ne $r.provenance.registration.ordinal){throw 'Same-pass registration ordinal required.'}
    if($ExitCode -ne 0){return 'RegistrationRecordFromFailedProcess'}
    'RegistrationRecordCaptured'
}
function Read-T7RegistrationImageRecord($Plan,$State,$Context) {
    $text=Read-T7ImageMetadataStdout $Plan $State $Context
    $State.SelectedRegistrationHeader=[ordered]@{Schema='iw7.t7-registration-image-header-metadata/1';InterpretationPending=$true;PixelsCopied=$false;Ready=$false}
    ConvertFrom-T7RegistrationImageRecord $text $State.ExitCode
}
