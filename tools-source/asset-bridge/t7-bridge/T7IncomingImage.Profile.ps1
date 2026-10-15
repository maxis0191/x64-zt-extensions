# Finite pending proposals and the separately qualified, closed CPP87 cohort.
function Assert-T7IncomingImageSourcePlan($Plan) {
    foreach($name in 'Schema','Operation','CandidateProfile'){
        if($Plan.$name -isnot [string]){throw 'Typed incoming Source selectors required.'}
    }
    if($Plan.Schema -cne 'iw7.t7-incoming-image-source-plan/1' -or $Plan.Operation -cne 'IncomingImageObservationV1' -or
       $Plan.CandidateProfile -cne 't7-incoming-image-header-observation-v1'){throw 'Exact incoming Source schema/operation/profile required.'}
    $marker=$Plan.SelectedIncomingImageObservationV1
    Assert-T7CatalogueFields $marker @('Schema','SourceRevision','Contract','NativeSchema','SlotOrder','SourceOnlyPending','CPPQualified','NativeObserved','QualifiedObjectMipCount','Ready')
    foreach($name in 'Schema','SourceRevision','NativeSchema'){
        if($marker.$name -isnot [string]){throw 'Typed incoming Source descriptor texts required.'}
    }
    if($marker.Schema -cne 'iw7.t7-incoming-image-proposal/1' -or
       $marker.NativeSchema -cne 'iw7.t7-incoming-image-header-observation/1'){throw 'Exact pending incoming Source basis required.'}
    # Keep the frozen proposal distinct from the corrected fixture prerequisite.
    $contractSHA=switch -CaseSensitive ($marker.SourceRevision){
        '4873ef4a4ce8478020d8533651f123f8feadfa95' {'1f672f51533f90ea10d396bd28a8298f6070d39df938b0bf4033c4754dc4659f'}
        '41e595f09dabdd6dff14439f09bd701bddd4a235' {'a2cdaf54b7387616bd56d9a78538e7a273ec35e9eb2f6f6ac1e130ecd3851323'}
        default {throw 'Exact pending incoming Source revision required.'}
    }
    $pin=$marker.Contract;Assert-T7CatalogueFields $pin @('Path','Bytes','SHA256')
    if($pin.Path -isnot [string] -or ![IO.Path]::IsPathFullyQualified($pin.Path) -or [IO.Path]::GetFullPath($pin.Path) -cne $pin.Path -or
       $pin.Path.StartsWith('\\') -or $pin.Path.Substring(2).Contains(':') -or $pin.Path -match '["\x00-\x1f]' -or
       [IO.Path]::GetFileName($pin.Path) -cne 'incoming-image-source-contract.json' -or
       !(Test-T7CatalogueInteger $pin.Bytes 8KB) -or $pin.Bytes -ne 4613 -or
       $pin.SHA256 -isnot [string] -or $pin.SHA256 -cne $contractSHA){
        throw 'Exact incoming Source contract text pin required.'
    }
    $slots=@('bootstrap/reference','bootstrap/ordinary','map_load/reference','map_load/ordinary')
    if($marker.SlotOrder -isnot [array] -or $marker.SlotOrder.Count -ne 4){throw 'Exact four incoming Source slots required.'}
    for($i=0;$i -lt 4;$i++){if($marker.SlotOrder[$i] -isnot [string] -or $marker.SlotOrder[$i] -cne $slots[$i]){throw 'Exact incoming Source slot order required.'}}
    if($marker.SourceOnlyPending -isnot [bool] -or !$marker.SourceOnlyPending){throw 'Incoming descriptor must remain Source pending.'}
    foreach($name in 'CPPQualified','NativeObserved','Ready'){
        if($marker.$name -isnot [bool] -or $marker.$name){throw 'Incoming Source cannot promote compiled/native/Ready proof.'}
    }
    if(![object]::ReferenceEquals($null,$marker.QualifiedObjectMipCount)){throw 'Incoming Source mip fact must remain NULL.'}
    foreach($name in 'CandidateSource','CandidateBytes','CandidateSHA256','BuildPlan','BuildReceipt','ExpectedBuildPlanSHA256','ExpectedBuildReceiptSHA256'){
        if(!$Plan.PSObject.Properties[$name] -or ![object]::ReferenceEquals($null,$Plan.$name)){throw 'Incoming unqualified candidate/build fields must remain NULL.'}
    }
    foreach($name in 'SelectedImageProvenanceV1','SelectedRegistrationImageHeaderV1','SelectedMaterialPartsV1','SelectedXpakProvider','ExportRequest','ExportRequestFile',
        'SelectedStreamedRenderOnlyV2','SelectedMeshMaterialObservation','ResidentMultiSurfaceV2','ResidentSurfaceCountDiagnostic','SelectedStreamedStaticV1','ZombiesObservationC','ZombiesAddObservationC2'){
        if($Plan.PSObject.Properties[$name]){throw 'Incoming Source cannot select another operation/provider.'}
    }
    $expected=@('-t7-iw7-incoming-image-header-v1','mp_freerun_04','p7_fre_platform_cap_02','0')
    if($Plan.Arguments -isnot [array] -or $Plan.Arguments.Count -ne 4){throw 'Exact incoming Source arguments required.'}
    for($i=0;$i -lt 4;$i++){if($Plan.Arguments[$i] -isnot [string] -or $Plan.Arguments[$i] -cne $expected[$i]){throw 'Exact incoming Source arguments required.'}}
}
function Assert-T7IncomingImageOperationalGate {
    throw 'Incoming Source proposal requires a qualified plan from the new actual closed CPP cohort; operational DEFAULT and Run are unavailable for Source proposals.'
}

function Get-T7IncomingImageCohort {
    [ordered]@{
        ReviewedPrerequisiteSource='41e595f09dabdd6dff14439f09bd701bddd4a235';Source='bde117b8dd40945033d00231b28738b345f09fdb'
        NativeSource='fab935826c898806855376662a8a03317b3ad8f1';EXEBytes=22059008;EXESHA256='4fcb0205e30979457784d1b883a153ecf5c20751543b68dfb184671d59e3ee4d'
        Plan=@(403533,'2becaab02373a248dbcf5797501680beeb4d80f1c5603cbe969540a35776c0f9')
        Receipt=@(49161,'481dfa424367320699ee368b7272fa17d64b29babef775efe63f4e1fcd81f9b4')
        Contract=@(4613,'a2cdaf54b7387616bd56d9a78538e7a273ec35e9eb2f6f6ac1e130ecd3851323')
        SourceManifest=@(372028,'d38eef9eb4be10c865cbed0bbc15ea12617321bc673cc8674ae514a997e31c59')
        HostWitness=@(10340,'9a895ee72e2d75909d006ee4bd8f0893cc172e992c9d016de7858dff71d2620b')
        ClosureWitness=@(6327,'5c33ec17caddb888a07d4f7697bba12bf97f9e54612549a3922fcbae144b7a66')
        FixtureStdout=@(71,'414c5d2a646e4a9d3671ae904a9d6d1f8109b559790ef2045fbbc7f8ffbbfdf2')
        FreshWitness=@(401,'98b8636504f3484b48cea365590a340c3bcad98c7a9369341997f0cca23786bf')
        OriginalIDs=@(23212,23336,21256,24680,22760,27180,7692,2840,29024,26324,19212)
    }
}
function Assert-T7IncomingImageCohortPin($Pin,[string]$Name,$Bindings) {
    $c=Get-T7IncomingImageCohort
    Assert-T7CatalogueFields $Pin @('Path','Bytes','SHA256')
    if($Pin.Path -isnot [string] -or !(Test-T7CatalogueInteger $Pin.Bytes 1MB) -or $Pin.Bytes -ne $c[$Name][0] -or
       $Pin.SHA256 -isnot [string] -or $Pin.SHA256 -cne $c[$Name][1]){throw 'Exact typed closed CPP87 text pin required.'}
    Assert-T7CatalogueTextPin $Pin $Bindings
}
function Assert-T7IncomingImagePlan($Plan) {
    if(!(Test-T7IncomingImageCompiledPlan $Plan)){throw 'Exact incoming compiled plan selectors required.'}
    $c=Get-T7IncomingImageCohort;$m=$Plan.SelectedIncomingImageObservationV1
    Assert-T7CatalogueFields $m @('Schema','ReviewedPrerequisiteSource','CompiledExtensionSource','Contract','SourceManifest','HostWitness','ClosureWitness','FixtureStdout','FreshWitness')
    foreach($name in 'Schema','ReviewedPrerequisiteSource','CompiledExtensionSource'){
        if($m.$name -isnot [string]){throw 'Typed CPP87 Source identities required.'}
    }
    if($m.Schema -cne 'iw7.t7-incoming-image-cpp87/1' -or $m.ReviewedPrerequisiteSource -cne $c.ReviewedPrerequisiteSource -or
       $m.CompiledExtensionSource -cne $c.Source -or $Plan.BootstrapPolicy -isnot [string] -or $Plan.BootstrapPolicy -cne 'QualifiedCollectionV3' -or
       $Plan.Bootstraps -isnot [array] -or $Plan.Bootstraps.Count -ne 23 -or !$Plan.PSObject.Properties['SharedQualification'] -or $null -eq $Plan.SharedQualification -or
       $Plan.CandidateSource -isnot [string] -or $Plan.BuildPlan -isnot [string] -or $Plan.BuildReceipt -isnot [string] -or
       !(Test-T7CatalogueInteger $Plan.CandidateBytes 64MB) -or $Plan.CandidateBytes -ne $c.EXEBytes -or
       $Plan.CandidateSHA256 -isnot [string] -or $Plan.CandidateSHA256 -cne $c.EXESHA256 -or
       $Plan.ExpectedBuildPlanSHA256 -isnot [string] -or $Plan.ExpectedBuildPlanSHA256 -cne $c.Plan[1] -or
       $Plan.ExpectedBuildReceiptSHA256 -isnot [string] -or $Plan.ExpectedBuildReceiptSHA256 -cne $c.Receipt[1] -or
       $Plan.OutputKey -isnot [string] -or $Plan.OutputKey -cne 't7_iw7_incoming_image_observation_v1' -or
       !(Test-T7CatalogueInteger $Plan.TraceStderrLimitBytes 16384) -or $Plan.TraceStderrLimitBytes -ne 16384){throw 'Exact closed CPP87 collection/tuple required.'}
    foreach($name in 'SelectedImageProvenanceV1','SelectedRegistrationImageHeaderV1','SelectedMaterialPartsV1','SelectedXpakProvider','ExportRequest','ExportRequestFile',
        'SelectedStreamedRenderOnlyV2','SelectedMeshMaterialObservation','ResidentMultiSurfaceV2','ResidentSurfaceCountDiagnostic','SelectedStreamedStaticV1','ZombiesObservationC','ZombiesAddObservationC2'){
        if($Plan.PSObject.Properties[$name]){throw 'Incoming compiled metadata cannot select another operation/provider.'}
    }
    $expected=@('-t7-iw7-incoming-image-header-v1','mp_freerun_04','p7_fre_platform_cap_02','0')
    if($Plan.Arguments -isnot [array] -or $Plan.Arguments.Count -ne 4){throw 'Exact incoming compiled arguments required.'}
    for($i=0;$i -lt 4;$i++){if($Plan.Arguments[$i] -isnot [string] -or $Plan.Arguments[$i] -cne $expected[$i]){throw 'Exact incoming compiled arguments required.'}}
    foreach($name in 'Contract','SourceManifest','HostWitness','ClosureWitness','FixtureStdout','FreshWitness'){
        Assert-T7IncomingImageCohortPin $m.$name $name $Plan.Bindings
    }
    foreach($name in 'Plan','Receipt'){
        $path=if($name -ceq 'Plan'){$Plan.BuildPlan}else{$Plan.BuildReceipt}
        Assert-T7IncomingImageCohortPin ([pscustomobject]@{Path=$path;Bytes=$c[$name][0];SHA256=$c[$name][1]}) $name $Plan.Bindings
    }
}
function Assert-T7IncomingImageBuild($Plan,$Receipt) {
    Assert-T7IncomingImagePlan $Plan;$m=$Plan.SelectedIncomingImageObservationV1
    $build=Read-H1SmallJson $Plan.BuildPlan 1MB
    Assert-T7IncomingImageCpp87 $Plan $build $Receipt (Read-H1SmallJson $m.SourceManifest.Path 1MB) `
        (Read-H1SmallJson $m.HostWitness.Path 16KB) (Read-H1SmallJson $m.ClosureWitness.Path 8KB) (Read-H1SmallJson $m.FreshWitness.Path 8KB)
    foreach($name in 'Wiring','PreparedMain','PreparedCLI','BaseBuildPlan','BaseBuildReceipt','LinkResponse',
        'RegistrationWiring','RegistrationContract','RegistrationCapture','RegistrationEntry','RegistrationFixture','RegistrationObserver','RegistrationResponse',
        'IncomingWiring','IncomingContract','IncomingMembers','IncomingModule','IncomingEntry','IncomingFixture','IncomingCapture','IncomingObserver','IncomingBaselineFixture'){
        Assert-T7CatalogueTextPin $build.BuildProfile.$name $Plan.Bindings
    }
    if($build.BuildProfile.IncomingContract.Path -cne $m.Contract.Path){throw 'Same corrected CPP87 contract pin required.'}
    $dependencies=@($Receipt.Stages[2].Artifacts|Where-Object {[IO.Path]::GetFileName($_.Path) -ceq 'dependencies.json'})
    if($dependencies.Count -ne 1){throw 'One original CPP87 main dependency text required.'}
    Assert-T7CatalogueTextPin $dependencies[0] $Plan.Bindings
    if(([IO.File]::ReadAllText($m.FixtureStdout.Path)).Replace("`r`n","`n") -cne "IW7_T7_REGISTRATION_HEADER_CHECKS=39`nIW7_T7_INCOMING_IMAGE_CHECKS=48`n"){
        throw 'Actual CPP87 two-marker fixture stdout required.'
    }
}
function Assert-T7IncomingImageCpp87($Plan,$Build,$Receipt,$Manifest,$HostWitness,$Closure,$Fresh) {
    $c=Get-T7IncomingImageCohort;$p=$Build.BuildProfile
    foreach($entry in @(@($Plan,@('CandidateSource','BuildReceipt','ExpectedBuildPlanSHA256','ExpectedBuildReceiptSHA256')),
        @($Build,@('SourceCommit','RunRoot')),@($p,@('Name','Option','ObservationSchema','IncomingSchema','RegistrationSchema')),
        @($Receipt,@('Schema','Status','PlanSHA256')),@($HostWitness,@('Schema','SourceCommit','Status')),
        @($Closure,@('Schema','SourceCommit','Status','ActualCompletionChunk')),@($Fresh,@('Schema')))){
        foreach($name in $entry[1]){if($entry[0].$name -isnot [string]){throw 'Typed CPP87 proof text scalars required.'}}
    }
    if($Manifest.revisions.'x64-zt-extensions' -isnot [string]){throw 'Typed compiled Source revision required.'}
    if(!(Test-T7CatalogueInteger $Plan.CandidateBytes 64MB) -or $Plan.CandidateBytes -ne $c.EXEBytes -or
       $Plan.CandidateSHA256 -isnot [string] -or $Plan.CandidateSHA256 -cne $c.EXESHA256 -or
       $Plan.ExpectedBuildPlanSHA256 -cne $c.Plan[1] -or $Plan.ExpectedBuildReceiptSHA256 -cne $c.Receipt[1] -or
       $Build.SourceCommit -cne $c.NativeSource -or $Manifest.revisions.'x64-zt-extensions' -cne $c.Source -or
       $p.Name -cne 't7-incoming-image-header-observation-v1' -or $p.Option -cne '-t7-iw7-incoming-image-header-v1' -or
       !(Test-T7CatalogueInteger $p.ArgumentCount 5) -or $p.ArgumentCount -ne 5 -or
       $p.ObservationSchema -cne 'iw7.t7-incoming-image-header-observation/1' -or $p.IncomingSchema -cne $p.ObservationSchema -or
       $p.RegistrationSchema -cne 'iw7.t7-registration-image-header-metadata/1' -or
       !(Test-T7CatalogueInteger $p.RegistrationFixtureChecks 39) -or $p.RegistrationFixtureChecks -ne 39 -or
       !(Test-T7CatalogueInteger $p.IncomingFixtureChecks 48) -or $p.IncomingFixtureChecks -ne 48 -or
       $Receipt.Schema -cne 'iw7.t7-minimal-build/1' -or $Receipt.Status -cne 'Passed' -or $Receipt.PlanSHA256 -cne $c.Plan[1]){throw 'Exact measured CPP87 recipe/source/receipt required.'}
    foreach($name in 'SourceOnlyPending','RegistrationCPPQualified','IncomingCPPQualified'){
        if($p.$name -isnot [bool] -or $p.$name){throw 'CPP87 recipe must preserve its unqualified input flags.'}
    }
    foreach($name in 'InputsReverified','TreeClosureConfirmed','LeaseReleased','RegistrationFixturePassed','IncomingFixturePassed','RegistrationCPPQualified','IncomingCPPQualified'){
        if($Receipt.$name -isnot [bool] -or !$Receipt.$name){throw 'CPP87 actual receipt qualification missing.'}
    }
    foreach($name in 'Quarantined','CandidateExecuted'){if($Receipt.$name -isnot [bool] -or $Receipt.$name){throw 'CPP87 must remain closed/unexecuted.'}}
    if($Receipt.Stages -isnot [array] -or $Receipt.Stages.Count -ne 5 -or ($Receipt.Stages.Name -join '|') -cne 'registration-fixture-compile|registration-fixture-test|main|zonetool11|link' -or
       ($Receipt.Stages.Stage -join '|') -cne 'Compile|Probe|Compile|Compile|Link'){throw 'Exact five CPP87 stages required.'}
    # Only the four actual compiler stages have completed compiler telemetry.
    # The inherited top-level placeholder and Probe telemetry remain false.
    foreach($stage in $Receipt.Stages){
        if($stage.Name -isnot [string] -or $stage.Stage -isnot [string] -or !(Test-T7CatalogueInteger $stage.ExitCode 0) -or
           $stage.TreeClosureConfirmed -isnot [bool] -or !$stage.TreeClosureConfirmed){throw 'CPP87 stage failed/unclosed.'}
        if($stage.Stage -cin @('Compile','Link')){
            $t=$stage.CompilerTelemetry
            if($t.Completed -isnot [bool] -or !$t.Completed -or $t.AfterStop.RootExited -isnot [bool] -or !$t.AfterStop.RootExited -or
               !(Test-T7CatalogueInteger $t.AfterStop.RootExitCode 0) -or !(Test-T7CatalogueInteger $t.AfterStop.ActiveProcesses 0) -or
               $t.AfterStopMembers.Members -isnot [array] -or $t.AfterStopMembers.Members.Count){throw 'CPP87 original compiler/job not empty.'}
        }
    }
    $probe=$Receipt.Stages[1]
    if(!(Test-T7CatalogueInteger $probe.LegacyRegistrationChecks 39) -or $probe.LegacyRegistrationChecks -ne 39 -or
       !(Test-T7CatalogueInteger $probe.IncomingChecks 48) -or $probe.IncomingChecks -ne 48 -or
       $probe.EngineInvoked -isnot [bool] -or $probe.EngineInvoked){throw 'Actual 39+48 authored fixture required.'}
    if($HostWitness.Schema -cne 'iw7.t7-incoming-image-cpp-preexit/1' -or $HostWitness.SourceCommit -cne $c.Source -or $HostWitness.Status -cne 'Passed'){
        throw 'Exact CPP87 original preexit required.'
    }
    foreach($name in 'SameActualCallerAppDomain','SameOriginalContextPSVariable','SameOriginalStatePSVariable','SameOriginalGuardsPSVariable','SameOriginalOwnerReference',
        'OriginalContextClosed','OriginalOwnerClosed','CallerSourcePinsReverified','LeaseNull','CanExit','InputsReverified','LeaseReleased','TreeClosureConfirmed',
        'RegistrationFixturePassed','IncomingFixturePassed','RegistrationCPPQualified','IncomingCPPQualified','ExactCreationFILETIMEsInt64','FourCompilerStageTelemetryCompleted','ProbeCompilerTelemetryNotApplicable'){
        if($HostWitness.$name -isnot [bool] -or !$HostWitness.$name){throw 'CPP87 original context proof missing.'}
    }
    foreach($name in 'CandidateExecuted','NativeCLIExecuted','StockRead','Ready','PhaseProjectionIncomplete'){
        if($HostWitness.$name -isnot [bool] -or $HostWitness.$name){throw 'CPP87 preexit overclaims or lacks full projection.'}
    }
    if(!(Test-T7CatalogueInteger $HostWitness.BuildGuards 0) -or !(Test-T7CatalogueInteger $HostWitness.CallerSourceGuards 0) -or
       $HostWitness.Host.PID -ne 19212 -or $HostWitness.Parent.PID -ne 26324 -or
       $HostWitness.Host.CreationFileTime -isnot [long] -or $HostWitness.Host.CreationFileTime -ne 134365054279170774L -or
       $HostWitness.Parent.CreationFileTime -isnot [long] -or $HostWitness.Parent.CreationFileTime -ne 134365054277439850L){throw 'CPP87 exact host generation/guards required.'}
    foreach($name in 'NoExitVerified','VerifiedBeforeImportsAndAdmission'){if($HostWitness.Host.$name -isnot [bool] -or !$HostWitness.Host.$name){throw 'Original fresh NoExit host required.'}}
    foreach($name in 'Invocation','EntryAssembly','Image'){if($HostWitness.Host.$name -isnot [string]){throw 'Typed CPP87 host texts required.'}}
    if($HostWitness.Parent.Image -isnot [string]){throw 'Typed CPP87 parent image required.'}
    if($HostWitness.Host.Invocation -cne '.' -or $HostWitness.Host.EntryAssembly -cne [IO.Path]::ChangeExtension($HostWitness.Host.Image,'.dll') -or
       $HostWitness.Parent.Image -cne $HostWitness.Host.Image -or $HostWitness.Host.Arguments -isnot [array] -or $HostWitness.Host.Arguments.Count -ne 6 -or
       $HostWitness.Host.Arguments[0] -cne $HostWitness.Host.EntryAssembly -or ($HostWitness.Host.Arguments[1..4] -join '|') -cne '-NoLogo|-NoProfile|-NoExit|-Command'){
        throw 'CPP87 exact physical/managed dot invocation required.'
    }
    foreach($argument in $HostWitness.Host.Arguments){if($argument -isnot [string]){throw 'Typed CPP87 host arguments required.'}}
    foreach($proof in $Closure.Receipt,$Closure.SameOriginalContextProof,$Closure.FreshObservation){
        if($proof.SHA256 -isnot [string]){throw 'Typed CPP87 closure text hashes required.'}
    }
    if($Closure.Schema -cne 'iw7.t7-incoming-image-cpp-closure/1' -or $Closure.SourceCommit -cne $c.Source -or $Closure.Status -cne 'Passed' -or
       !(Test-T7CatalogueInteger $Closure.ActualTruePTYSession 50444) -or $Closure.ActualTruePTYSession -ne 50444 -or
       !(Test-T7CatalogueInteger $Closure.ActualTruePTYExitCode 0) -or $Closure.ActualCompletionChunk -cne '1ae1c5' -or
       $Closure.Receipt.SHA256 -cne $c.Receipt[1] -or $Closure.SameOriginalContextProof.SHA256 -cne $c.HostWitness[1] -or
       $Closure.FreshObservation.SHA256 -cne $c.FreshWitness[1] -or !(Test-T7CatalogueInteger $Closure.LeaseRegistryCount 0)){
        throw 'CPP87 exact independent original closure required.'
    }
    foreach($name in 'AllElevenOriginalIdentitiesAbsent','InputsReverified','LeaseReleased','TreeClosureConfirmed','RegistrationCPPQualified','IncomingCPPQualified','NoOpaqueArtifactReopened'){
        if($Closure.$name -isnot [bool] -or !$Closure.$name){throw 'CPP87 independent closure proof missing.'}
    }
    foreach($name in 'CandidateExecuted','NativeCLIExecuted','StockRead','Ready','ContextReconstructed'){
        if($Closure.$name -isnot [bool] -or $Closure.$name){throw 'CPP87 closure overclaims runtime or reconstructed context.'}
    }
    if($HostWitness.KnownOriginalIdentities -isnot [array] -or $HostWitness.KnownOriginalIdentities.Count -ne 11 -or
       $Closure.OriginalIdentityObservations -isnot [array] -or $Closure.OriginalIdentityObservations.Count -ne 11){throw 'Eleven original CPP87 identities required.'}
    for($i=0;$i -lt 11;$i++){
        $known=$HostWitness.KnownOriginalIdentities[$i];$seen=$Closure.OriginalIdentityObservations[$i]
        if(!(Test-T7CatalogueInteger $known.PID ([int]::MaxValue)) -or $known.PID -ne $c.OriginalIDs[$i] -or $known.Image -isnot [string] -or
           $known.CreationFileTime -isnot [long] -or $known.CreationFileTime -le 0 -or $seen.Expected.PID -ne $known.PID -or
           !(Test-T7CatalogueInteger $seen.Expected.PID ([int]::MaxValue)) -or $seen.Expected.Image -isnot [string] -or
           $seen.Expected.Image -cne $known.Image -or $seen.Expected.CreationFileTime -isnot [long] -or $seen.Expected.CreationFileTime -ne $known.CreationFileTime -or
           $seen.OriginalIdentityPresent -isnot [bool] -or $seen.OriginalIdentityPresent -or $null -ne $seen.Live){throw 'Original CPP87 identity closure differs.'}
    }
    foreach($pair in @(@($HostWitness.Parent,9),@($HostWitness.Host,10))){
        $known=$HostWitness.KnownOriginalIdentities[$pair[1]]
        if($known.PID -ne $pair[0].PID -or $known.Image -cne $pair[0].Image -or $known.CreationFileTime -ne $pair[0].CreationFileTime){throw 'CPP87 host closure generation differs.'}
    }
    if($Fresh.Schema -cne 'iw7.t7-incoming-image-cpp-fresh-identities/1' -or $Fresh.OriginalPIDs -isnot [array] -or
       ($Fresh.OriginalPIDs -join '|') -cne ($c.OriginalIDs -join '|') -or !(Test-T7CatalogueInteger $Fresh.RegistryVersion 1) -or $Fresh.RegistryVersion -ne 1 -or
       !(Test-T7CatalogueInteger $Fresh.RegistryLeaseCount 0) -or $Fresh.NoProcessStopped -isnot [bool] -or !$Fresh.NoProcessStopped){throw 'CPP87 fresh independent observations required.'}
    foreach($name in 'LiveAtOriginalPIDs','CompilerOrVCTIP'){if($Fresh.$name -isnot [array] -or $Fresh.$name.Count){throw 'CPP87 fresh closure is not empty.'}}
    foreach($originalPID in $Fresh.OriginalPIDs){if(!(Test-T7CatalogueInteger $originalPID ([int]::MaxValue))){throw 'Typed CPP87 fresh PIDs required.'}}
    $exe=@($Receipt.Stages[-1].Artifacts|Where-Object {$_.Path -ceq $Plan.CandidateSource})
    if($exe.Count -ne 1 -or !(Test-T7CatalogueInteger $exe[0].Bytes 64MB) -or $exe[0].Bytes -ne $c.EXEBytes -or
       $exe[0].SHA256 -isnot [string] -or $exe[0].SHA256 -cne $c.EXESHA256 -or
       $Plan.CandidateSource -cne (Join-Path $Build.RunRoot 'link/zonetool-t7.exe') -or $Plan.BuildReceipt -cne (Join-Path $Build.RunRoot 'receipt.json')){
        throw 'Original admitted CPP87 link artifact metadata required.'
    }
}

# Shell capture only. Consumer150 owns DTO/counter/copy semantics and deep outcomes.
function Assert-T7IncomingImageJsonNames($Element) {
    if($Element.ValueKind -eq [Text.Json.JsonValueKind]::Object){
        $names=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        foreach($property in $Element.EnumerateObject()){
            if(!$names.Add($property.Name)){throw 'Duplicate incoming JSON property refused.'}
            Assert-T7IncomingImageJsonNames $property.Value
        }
    }elseif($Element.ValueKind -eq [Text.Json.JsonValueKind]::Array){
        foreach($item in $Element.EnumerateArray()){Assert-T7IncomingImageJsonNames $item}
    }
}
function ConvertFrom-T7IncomingImageRecord($Text,$ExitCode) {
    if($Text -isnot [string] -or [Text.Encoding]::UTF8.GetByteCount($Text) -gt 1MB){throw 'Bounded incoming stdout text required.'}
    if(($ExitCode -isnot [int] -and $ExitCode -isnot [long]) -or $ExitCode -lt -2147483648L -or $ExitCode -gt 4294967295L){
        throw 'Typed original incoming native exit required.'
    }
    $markers=[regex]::Matches($Text,'T7_INCOMING_IMAGE_METADATA')
    if(!$markers.Count){return [pscustomobject]@{Outcome='IncomingNoReport';Record=$null}}
    $records=[regex]::Matches($Text,'(?m)^[^\r\n]*?T7_INCOMING_IMAGE_METADATA (\{[^\r\n]*\})\r?$')
    if($markers.Count -ne 1 -or $records.Count -ne 1 -or [Text.Encoding]::UTF8.GetByteCount($records[0].Groups[1].Value) -gt 32KB){
        throw 'One bounded incoming JSON object record required.'
    }
    $json=$records[0].Groups[1].Value
    $options=[Text.Json.JsonDocumentOptions]::new();$options.MaxDepth=25
    $document=[Text.Json.JsonDocument]::Parse($json,$options)
    try{Assert-T7IncomingImageJsonNames $document.RootElement}finally{$document.Dispose()}
    $r=ConvertFrom-Json -InputObject $json -Depth 25
    $falseFields=@('allocation_retained','atomic_snapshot_proven','descriptor_admissible','lifetime_proven','model_binding_correlated',
        'pixels_copied','ready','renderer_binding_proven','runtime_abi_proven','same_object_proven','same_pointer_proven','source_asset_name_association_proven')
    $boolFields=@('bootstrap_complete','cap_refused','exact_argv_validated_before_arm','map_complete','ordinary_name_observed','reference_name_observed','refused','window_complete')
    Assert-T7CatalogueFields $r ($falseFields+$boolFields+@('arm_generation','arm_phase','callback_limit','capture_phase','cases','image_callbacks',
        'name_comparison_rule','native_source_commit','non_target_callbacks','ordinary_absence_scope','ordinary_name_events','payload_bytes_read',
        'qualified_object_mip_count','read_bytes','read_limit','reason','reference_events','schema','source_profile','target_case_limit_per_phase','target_name','zone'))
    $texts=@{schema='iw7.t7-incoming-image-header-observation/1';source_profile='t7-incoming-image-header-observation-v1';
        native_source_commit='fab935826c898806855376662a8a03317b3ad8f1';zone='mp_freerun_04';target_name='$camo_base_normal';
        arm_phase='before_db_add_hook_create';capture_phase='before_image_bypass';name_comparison_rule='strip_one_leading_comma_then_exact_case_and_dollar'}
    foreach($name in $texts.Keys){if($r.$name -isnot [string] -or $r.$name -cne $texts[$name]){throw 'Exact typed incoming Source identity/phases required.'}}
    foreach($name in $falseFields){if($r.$name -isnot [bool] -or $r.$name){throw 'Incoming capture cannot promote descriptor/runtime/pixel proof.'}}
    foreach($name in $boolFields){if($r.$name -isnot [bool]){throw 'Typed incoming observation flags required.'}}
    if($null -ne $r.qualified_object_mip_count){throw 'Incoming capture mip fact must remain NULL.'}
    foreach($pair in @(@('arm_generation',1),@('callback_limit',65536),@('target_case_limit_per_phase',16),@('read_limit',2097152),@('payload_bytes_read',0))){
        if(!(Test-T7CatalogueInteger $r.($pair[0]) $pair[1]) -or $r.($pair[0]) -ne $pair[1]){throw 'Exact typed incoming scope and zero payload required.'}
    }
    foreach($pair in @(@('image_callbacks',65537),@('non_target_callbacks',65536),@('reference_events',34),@('ordinary_name_events',34),@('read_bytes',2097152))){
        if(!(Test-T7CatalogueInteger $r.($pair[0]) $pair[1])){throw 'Bounded typed incoming counters required.'}
    }
    if(!$r.exact_argv_validated_before_arm -or ($r.map_complete -and !$r.bootstrap_complete) -or
       $r.window_complete -eq $r.refused -or (!$r.refused -and !$r.map_complete) -or ($r.cap_refused -and !$r.refused)){
        throw 'Incoming arming/window/refusal flags contradict.'
    }
    if($r.refused){
        if($ExitCode -eq 0){throw 'Incoming refusal contradicts native exit zero.'}
        if($r.reason -isnot [string] -or [Text.Encoding]::UTF8.GetByteCount($r.reason) -gt 191){throw 'Bounded incoming refusal reason required.'}
    }elseif($null -ne $r.reason){throw 'Complete incoming window cannot carry a refusal reason.'}
    if($null -ne $r.ordinary_absence_scope -and ($r.ordinary_absence_scope -isnot [string] -or
       $r.ordinary_absence_scope -cnotin @('partial_or_refused_callback_window','not_observed_in_this_bounded_callback_window'))){throw 'Typed bounded incoming absence scope required.'}
    if($r.cases -isnot [array] -or $r.cases.Count -ne 4){throw 'Four ordered incoming capture slots required.'}
    for($i=0;$i -lt 4;$i++){
        $row=$r.cases[$i]
        Assert-T7CatalogueFields $row @('callback_ordinal','conflict_absence_proven','descriptor_admissible','effective_name','leading_comma_reference',
            'matching_events_in_phase','name_category','nonzero_descriptor_scalar_fields','phase','raw_name','repeated_headers_compared',
            'single_event_observed_in_phase','snapshot','state','unique_in_phase')
        $phase=if($i -lt 2){'bootstrap'}else{'map_load'};$category=if($i % 2 -eq 0){'reference'}else{'ordinary'}
        if($row.phase -isnot [string] -or $row.phase -cne $phase -or $row.name_category -isnot [string] -or $row.name_category -cne $category){throw 'Exact incoming capture slot order required.'}
        foreach($name in 'conflict_absence_proven','descriptor_admissible','repeated_headers_compared','single_event_observed_in_phase','unique_in_phase'){
            if($row.$name -isnot [bool]){throw 'Typed incoming case flags required.'}
        }
        if($row.conflict_absence_proven -or $row.descriptor_admissible -or $row.repeated_headers_compared){throw 'Incoming case cannot promote descriptor/conflict/comparison proof.'}
        foreach($name in 'raw_name','effective_name'){
            if($null -ne $row.$name -and ($row.$name -isnot [string] -or [Text.Encoding]::UTF8.GetByteCount($row.$name) -gt 129)){throw 'Typed bounded incoming names required.'}
        }
        if($null -ne $row.leading_comma_reference -and $row.leading_comma_reference -isnot [bool]){throw 'Typed nullable incoming reference flag required.'}
        foreach($pair in @(@('callback_ordinal',65537),@('nonzero_descriptor_scalar_fields',13))){
            if($null -ne $row.($pair[0]) -and !(Test-T7CatalogueInteger $row.($pair[0]) $pair[1])){throw 'Typed nullable incoming case counters required.'}
        }
        if(!(Test-T7CatalogueInteger $row.matching_events_in_phase 17) -or $row.state -isnot [string] -or
           $row.state -cnotin @('not_observed','target_matched_sample_refused','first_complete_sample','repeated_target_ambiguous')){throw 'Typed incoming case count/state required.'}
        if($null -ne $row.snapshot){
            $shot=$row.snapshot
            Assert-T7CatalogueFields $shot @('callback_header_name_rechecked','completed_header_bytes','copy_fault','header_copies','header_observed','header_rechecked','image','name_rechecked','reason','refused')
            foreach($name in 'callback_header_name_rechecked','copy_fault','header_observed','header_rechecked','name_rechecked','refused'){
                if($shot.$name -isnot [bool]){throw 'Typed incoming snapshot flags required.'}
            }
            if(!(Test-T7CatalogueInteger $shot.header_copies 2) -or ($null -ne $shot.completed_header_bytes -and !(Test-T7CatalogueInteger $shot.completed_header_bytes 528)) -or
               ($null -ne $shot.image -and $shot.image -isnot [pscustomobject]) -or
               ($null -ne $shot.reason -and ($shot.reason -isnot [string] -or [Text.Encoding]::UTF8.GetByteCount($shot.reason) -gt 255))){throw 'Typed bounded incoming snapshot fields required.'}
        }
    }
    $outcome=if($r.refused){'IncomingRecordRefused'}elseif($ExitCode -eq 0){'IncomingRecordCaptured'}else{'IncomingRecordFromFailedProcess'}
    [pscustomobject]@{Outcome=$outcome;Record=$r}
}
function Read-T7IncomingImageRecord($Plan,$State,$Context) {
    if($Context.Closed -isnot [bool] -or !$Context.Closed -or !$Context.Owner -or !$Context.Lease -or
       $State.TreeClosureConfirmed -isnot [bool] -or !$State.TreeClosureConfirmed -or
       $State.TerminationRequested -isnot [bool] -or $State.TerminationRequested -or $State.Quarantined -isnot [bool] -or $State.Quarantined){
        throw 'Original incoming job must close normally with admission retained.'
    }
    if(($State.ExitCode -isnot [int] -and $State.ExitCode -isnot [long]) -or $State.ExitCode -lt -2147483648L -or $State.ExitCode -gt 4294967295L){
        throw 'Typed original incoming native exit required before stdout read.'
    }
    $text=Read-T7ImageMetadataStdout $Plan $State $Context
    $result=ConvertFrom-T7IncomingImageRecord $text $State.ExitCode
    $State.SelectedIncomingObservation=[ordered]@{Schema='iw7.t7-incoming-image-header-observation/1';RecordPresent=($null -ne $result.Record);
        ConsumerSchema='iw7.t7-incoming-image-consumer/1';InterpretationPending=$true;DeepMetadataOutcome=$null;
        NativeExitCode=$State.ExitCode;DescriptorAdmissible=$false;QualifiedObjectMipCount=$null;PixelsCopied=$false;Ready=$false}
    $result.Outcome
}
