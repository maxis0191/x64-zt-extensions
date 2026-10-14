# Source interface only. No actual full-CLI cohort has been qualified.
function Assert-T7ImageProvenanceSourceContract($Contract) {
    Assert-T7CatalogueFields $Contract @('schema','source_profile','files','main','cli')
    if($Contract.schema -isnot [string] -or $Contract.schema -cne 'iw7.t7-image-provenance-source/1' -or
       $Contract.source_profile -isnot [string] -or $Contract.source_profile -cne 't7-image-provenance-v1'){
        throw 'Exact image provenance source contract required.'
    }
    Assert-T7CatalogueFields $Contract.files @('selected_image_provenance.hpp','native_image_provenance.inc','selected_image_provenance_fixture.cpp')
    $sourcePins=@(
        @('selected_image_provenance.hpp',15069,'d8b3f07f787f03dbda7c0305e2aad685c131130fbe43a839145e869858925c16'),
        @('native_image_provenance.inc',1254,'360bcf806e2d69f3ecba2d2422b99c8c86a775397438117607115ed0d8b5573e'),
        @('selected_image_provenance_fixture.cpp',14892,'f123c92c219c6d133882cadda2c8f62967de9bb86f2de0f55d0b468384d5f574'))
    foreach($row in $sourcePins){
        $item=$Contract.files.($row[0]);Assert-T7CatalogueFields $item @('lf_bytes','lf_sha256')
        if(!(Test-T7CatalogueInteger $item.lf_bytes 16KB) -or $item.lf_bytes -ne $row[1] -or
           $item.lf_sha256 -isnot [string] -or $item.lf_sha256 -cne $row[2]){throw 'Exact image provenance source pin required.'}
    }
    foreach($row in @(
        @('main',43370,'13052a66ba89d5e66253c6931b81cb120aaa5acac37d6a4b15ab57cac4c10900'),
        @('cli',130246,'15d03375dcd65f428ed10522ed238fe24c8ab407716780188ce341b87e1cbcf1'))){
        $item=$Contract.($row[0]);Assert-T7CatalogueFields $item @('bytes','sha256')
        if(!(Test-T7CatalogueInteger $item.bytes 128KB) -or $item.bytes -ne $row[1] -or
           $item.sha256 -isnot [string] -or $item.sha256 -cne $row[2]){throw 'Exact image provenance rendered source pair required.'}
    }
}
function Assert-T7ImageProvenanceSourcePlan($Plan) {
    if($Plan.Operation -isnot [string] -or $Plan.Operation -cne 'ImageProvenanceV1' -or
       $Plan.CandidateProfile -isnot [string] -or $Plan.CandidateProfile -cne 't7-image-provenance-v1' -or
       $Plan.Schema -isnot [string] -or $Plan.Schema -cne 'iw7.t7-image-provenance-source-plan/1'){
        throw 'Image provenance operation/profile/source schema must be paired.'
    }
    $marker=$Plan.SelectedImageProvenanceV1
    Assert-T7CatalogueFields $marker @('Schema','SourceRevision','Contract','NativeSchema')
    if($marker.Schema -isnot [string] -or $marker.Schema -cne 'iw7.t7-image-provenance-proposal/1' -or
       $marker.SourceRevision -isnot [string] -or $marker.SourceRevision -cne '678bf7dde6a99207654256c1e53ebaaec286ffe1' -or
       $marker.NativeSchema -isnot [string] -or $marker.NativeSchema -cne 'iw7.t7-selected-image-provenance/1'){
        throw 'Exact pending image provenance source basis required.'
    }
    Assert-T7ImageProvenanceSourceContract $marker.Contract
    foreach($name in 'CandidateSource','CandidateBytes','CandidateSHA256','BuildPlan','BuildReceipt',
        'ExpectedBuildPlanSHA256','ExpectedBuildReceiptSHA256'){
        if(!$Plan.PSObject.Properties[$name] -or ![object]::ReferenceEquals($null,$Plan.$name)){
            throw 'Unqualified image provenance candidate and build fields must remain NULL.'
        }
    }
    foreach($name in 'SelectedMaterialPartsV1','ResidentSurfaceCountDiagnostic','ResidentMultiSurfaceV2',
        'SelectedMeshMaterialObservation','SelectedStreamedStaticV1','SelectedStreamedRenderOnlyV2',
        'SelectedXpakProvider','ExportRequest','ExportRequestFile','ZombiesObservationC','ZombiesAddObservationC2'){
        if($Plan.PSObject.Properties[$name]){throw 'Image provenance cannot select another operation or provider.'}
    }
    $expected=@('-t7-iw7-image-provenance-v1','mp_freerun_04','p7_fre_platform_cap_02','0')
    if($Plan.Arguments -isnot [array] -or $Plan.Arguments.Count -ne 4){throw 'Exact image provenance arguments required.'}
    for($i=0;$i -lt 4;$i++){
        if($Plan.Arguments[$i] -isnot [string] -or $Plan.Arguments[$i] -cne $expected[$i]){throw 'Exact image provenance arguments required.'}
    }
}
function Assert-T7ImageProvenanceOperationalGate {
    throw 'Image provenance awaits actual F53, merged source API and a qualified full-CLI CPP cohort; operational DEFAULT and Run are unavailable.'
}
function Assert-T7ImageProvenanceCompiledPlan($Plan) {
    if($Plan.Operation -isnot [string] -or $Plan.Operation -cne 'ImageProvenanceV1' -or
       $Plan.CandidateProfile -isnot [string] -or $Plan.CandidateProfile -cne 't7-image-provenance-v1' -or
       $Plan.Schema -isnot [string] -or $Plan.Schema -cne 'iw7.t7-image-provenance-plan/1'){
        throw 'Compiled provenance operation/profile must be paired.'
    }
    if($Plan.BootstrapPolicy -cne 'QualifiedCollectionV3' -or $Plan.Bootstraps -isnot [array] -or $Plan.Bootstraps.Count -ne 23 -or !$Plan.PSObject.Properties['SharedQualification']){
        throw 'Compiled provenance requires the 23-member V3 qualified collection.'
    }
    $marker=$Plan.SelectedImageProvenanceV1
    Assert-T7CatalogueFields $marker @('Schema','SourceManifest','HostWitness','ClosureWitness','FixtureStdout')
    if($marker.Schema -isnot [string] -or $marker.Schema -cne 'iw7.t7-image-provenance-cpp-d/1'){throw 'Exact compiled D provenance marker required.'}
    $d=Get-T7ImageProvenanceCppD
    if(!(Test-T7CatalogueInteger $Plan.CandidateBytes 64MB) -or $Plan.CandidateBytes -ne $d.EXEBytes -or
       $Plan.CandidateSHA256 -isnot [string] -or $Plan.CandidateSHA256 -cne $d.EXESHA256 -or
       $Plan.ExpectedBuildPlanSHA256 -isnot [string] -or $Plan.ExpectedBuildPlanSHA256 -cne $d.Plan[1] -or
       $Plan.ExpectedBuildReceiptSHA256 -isnot [string] -or $Plan.ExpectedBuildReceiptSHA256 -cne $d.Receipt[1] -or
       $Plan.OutputKey -isnot [string] -or $Plan.OutputKey -cne 't7_iw7_image_provenance_v1' -or
       !(Test-T7CatalogueInteger $Plan.TraceStderrLimitBytes 16384) -or $Plan.TraceStderrLimitBytes -ne 16384){throw 'Exact D tuple/provenance bounds required.'}
    foreach($name in 'SelectedMaterialPartsV1','SelectedXpakProvider','ExportRequest','ExportRequestFile','SelectedStreamedRenderOnlyV2',
        'SelectedMeshMaterialObservation','ResidentMultiSurfaceV2','ResidentSurfaceCountDiagnostic','SelectedStreamedStaticV1','ZombiesObservationC','ZombiesAddObservationC2'){
        if($Plan.PSObject.Properties[$name]){throw 'Provenance cannot select body/parts/export/provider routes.'}
    }
    $args=@('-t7-iw7-image-provenance-v1','mp_freerun_04','p7_fre_platform_cap_02','0')
    if($Plan.Arguments -isnot [array] -or $Plan.Arguments.Count -ne 4){throw 'Exact four F2 provenance arguments required.'}
    for($i=0;$i -lt 4;$i++){if($Plan.Arguments[$i] -isnot [string] -or $Plan.Arguments[$i] -cne $args[$i]){throw 'Exact four F2 provenance arguments required.'}}
    foreach($name in 'SourceManifest','HostWitness','ClosureWitness','FixtureStdout'){
        $pin=$marker.$name;Assert-T7CatalogueFields $pin @('Path','Bytes','SHA256')
        if(!(Test-T7CatalogueInteger $pin.Bytes 1MB) -or $pin.Bytes -ne $d[$name][0] -or
           $pin.SHA256 -isnot [string] -or $pin.SHA256 -cne $d[$name][1]){throw 'Exact D text witness pin required.'}
        Assert-T7CatalogueTextPin $pin $Plan.Bindings
    }
    foreach($row in @(@($Plan.BuildPlan,$d.Plan),@($Plan.BuildReceipt,$d.Receipt))){
        Assert-T7CatalogueTextPin ([pscustomobject]@{Path=$row[0];Bytes=$row[1][0];SHA256=$row[1][1]}) $Plan.Bindings
    }
}
function Assert-T7ImageProvenanceBuild($Plan,$Receipt) {
    Assert-T7ImageProvenanceCompiledPlan $Plan
    $marker=$Plan.SelectedImageProvenanceV1
    $build=Read-H1SmallJson $Plan.BuildPlan 1MB
    Assert-T7ImageProvenanceCppD $Plan $build $Receipt (Read-H1SmallJson $marker.SourceManifest.Path 1MB) `
        (Read-H1SmallJson $marker.HostWitness.Path 4KB) (Read-H1SmallJson $marker.ClosureWitness.Path 8KB)
    $d=Get-T7ImageProvenanceCppD
    foreach($name in 'PreparedMain','PreparedCLI'){
        $pin=$build.BuildProfile.$name
        if($pin.Bytes -ne $d[$name][0] -or $pin.SHA256 -cne $d[$name][1]){throw 'Compiled D source text identity differs.'}
    }
    foreach($name in 'Wiring','PreparedMain','PreparedCLI','BaseBuildPlan','BaseBuildReceipt','LinkResponse'){
        Assert-T7CatalogueTextPin $build.BuildProfile.$name $Plan.Bindings
    }
    $dependencies=@($Receipt.Stages[2].Artifacts|Where-Object {[IO.Path]::GetFileName($_.Path) -ceq 'dependencies.json'})
    if($dependencies.Count -ne 1){throw 'One original CPP D main dependency text required.'}
    Assert-T7CatalogueTextPin $dependencies[0] $Plan.Bindings
}
function Get-T7ImageProvenanceCppD {
    [ordered]@{
        Source='1ad68ee74a9775b5eefb150c9316dfee6fad5df9'
        NativeSource='fab935826c898806855376662a8a03317b3ad8f1'
        EXEBytes=21998592;EXESHA256='552a9805ff3fc66748b76bec2f93dda11924c68d371d809b7f3f04bb3438bdbd'
        Plan=@(384208,'9e735ab7cf6d557ee2ff3e474f179967ecb4fb7f3dbda517c63c82784c766a21')
        Receipt=@(39862,'73cebdc2857222a8a984e43d8aa37ceacaf2ffe08b9454b531ab93b112b7aff9')
        SourceManifest=@(358572,'48e1b9e66f1c81dfad39c889304b2604d2c2de15ce0cce4968c092cd4942cc53')
        HostWitness=@(1687,'d204e3d8045e5c55833a2cc9e9b2591cbe0354a1ef5521fb750905414c208da2')
        ClosureWitness=@(858,'d567af8bcc2a1385074e24d17b771a6979d3e08b51ba19cc0abd07c6cb38a871')
        FixtureStdout=@(129,'472f5784b87850a11d466ce8cbef3658e5bb7ba9a06436ad25c68201929010e5')
        PreparedMain=@(43482,'b786f2db40e4c70346846bccb336c86c957efbd76f1c9365994138119a4e4363')
        PreparedCLI=@(154456,'17c07359a55e23324239f9663a8d4ead3cb9d3343a8b7ff0d4baf01ca4dfae6b')
    }
}
function Assert-T7ImageProvenanceCppD($Plan,$Build,$Receipt,$Manifest,$HostWitness,$Closure) {
    $d=Get-T7ImageProvenanceCppD
    if($Plan.CandidateBytes -ne $d.EXEBytes -or $Plan.CandidateSHA256 -cne $d.EXESHA256 -or
       $Plan.ExpectedBuildPlanSHA256 -cne $d.Plan[1] -or $Plan.ExpectedBuildReceiptSHA256 -cne $d.Receipt[1]){
        throw 'Exact measured CPP D candidate and recipe/receipt required.'
    }
    if($Build.SourceCommit -cne $d.NativeSource -or $Manifest.revisions.'x64-zt-extensions' -cne $d.Source -or
       $Build.BuildProfile.Name -cne 't7-image-provenance-v1' -or $Build.BuildProfile.Option -cne '-t7-iw7-image-provenance-v1' -or
       $Build.BuildProfile.ObservationSchema -cne 'iw7.t7-selected-image-provenance/1' -or
       !(Test-T7CatalogueInteger $Build.BuildProfile.ArgumentCount 5) -or $Build.BuildProfile.ArgumentCount -ne 5 -or
       $Build.BuildProfile.SourceOnlyPending -isnot [bool] -or $Build.BuildProfile.SourceOnlyPending -or
       $Build.BuildProfile.MetadataMapperChecks -ne 54 -or $Build.BuildProfile.MetadataGuardChecks -ne 13 -or
       $Receipt.Schema -cne 'iw7.t7-minimal-build/1' -or $Receipt.Status -cne 'Passed' -or $Receipt.PlanSHA256 -cne $d.Plan[1]){
        throw 'Exact compiled D source/profile/fixture receipt required.'
    }
    foreach($name in 'InputsReverified','TreeClosureConfirmed','LeaseReleased'){
        if($Receipt.$name -isnot [bool] -or !$Receipt.$name){throw 'CPP D original lifecycle proof required.'}
    }
    foreach($name in 'Quarantined','CandidateExecuted'){
        if($Receipt.$name -isnot [bool] -or $Receipt.$name){throw 'CPP D must remain closed and unexecuted.'}
    }
    if($Receipt.Stages -isnot [array] -or ($Receipt.Stages.Name -join '|') -cne 'metadata-fixture-compile|metadata-fixture-test|main|zonetool11|link'){
        throw 'Exact five CPP D stages required.'
    }
    if(($Receipt.Stages.Stage -join '|') -cne 'Compile|Probe|Compile|Compile|Link'){throw 'Exact CPP D stage kinds required.'}
    foreach($stage in $Receipt.Stages){
        if(!(Test-T7CatalogueInteger $stage.ExitCode 0) -or $stage.TreeClosureConfirmed -isnot [bool] -or !$stage.TreeClosureConfirmed){throw 'CPP D stage failed or unclosed.'}
        if($stage.Stage -cin @('Compile','Link')){
            $t=$stage.CompilerTelemetry
            if($t.Completed -isnot [bool] -or !$t.Completed -or $t.AfterStop.RootExited -isnot [bool] -or !$t.AfterStop.RootExited -or
               !(Test-T7CatalogueInteger $t.AfterStop.RootExitCode 0) -or !(Test-T7CatalogueInteger $t.AfterStop.ActiveProcesses 0) -or
               $t.AfterStopMembers.Members -isnot [array] -or $t.AfterStopMembers.Members.Count){throw 'CPP D original compiler/job members remain.'}
        }
    }
    foreach($name in 'SameOriginalAppDomain','ContextVariableSame','GuardsVariableSame','StateVariableSame','ContextSame','CanExit','Closed','OwnerClosed','LeaseIsNull','TreeClosureConfirmed','LeaseReleased','InputsReverified','CPPExecuted'){
        if($HostWitness.$name -isnot [bool] -or !$HostWitness.$name){throw 'CPP D original host context not closed.'}
    }
    foreach($name in 'Quarantined','CandidateExecuted','Ready'){
        if($HostWitness.$name -isnot [bool] -or $HostWitness.$name){throw 'CPP D host proof overclaims execution.'}
    }
    if($HostWitness.Schema -cne 'iw7.t7-image-metadata-cpp-preexit/1' -or $HostWitness.Status -cne 'Passed' -or
       $Closure.Schema -cne 'iw7.t7-image-metadata-cpp-closure/1' -or $Closure.Status -cne 'Passed' -or
       !(Test-T7CatalogueInteger $HostWitness.Host.PID 32768) -or $HostWitness.Host.PID -ne 7876 -or
       !(Test-T7CatalogueInteger $HostWitness.Parent.PID 32768) -or $HostWitness.Parent.PID -ne 27716 -or
       $HostWitness.Host.CreationFileTime -isnot [long] -or $HostWitness.Host.CreationFileTime -ne 134364856078036793 -or
       $HostWitness.Parent.CreationFileTime -isnot [long] -or $HostWitness.Parent.CreationFileTime -ne 134364856076106178 -or
       !(Test-T7CatalogueInteger $HostWitness.Guards 0) -or !(Test-T7CatalogueInteger $HostWitness.CallerSourceGuards 0) -or
       !(Test-T7CatalogueInteger $Closure.OriginalPTY 100000) -or $Closure.OriginalPTY -ne 99450 -or !(Test-T7CatalogueInteger $Closure.ActualPTYExitCode 0) -or
       $Closure.PlanSHA256 -cne $d.Plan[1] -or $Closure.ReceiptSHA256 -cne $d.Receipt[1] -or $Closure.SameOriginalPreExitSHA256 -cne $d.HostWitness[1]){
        throw 'Exact original CPP D host/actual PTY evidence required.'
    }
    foreach($name in 'NoExitVerified','VerifiedBeforeImportsAndAdmission'){
        if($HostWitness.Host.$name -isnot [bool] -or !$HostWitness.Host.$name){throw 'CPP D original fresh host proof required.'}
    }
    if($HostWitness.Host.Invocation -cne '.' -or $HostWitness.Host.EntryAssembly -cne ([IO.Path]::ChangeExtension($HostWitness.Host.Image,'.dll')) -or
       $HostWitness.Parent.Image -cne $HostWitness.Host.Image -or $HostWitness.Host.Arguments -isnot [array] -or
       $HostWitness.Host.Arguments.Count -ne 6 -or $HostWitness.Host.Arguments[0] -cne $HostWitness.Host.EntryAssembly -or
       ($HostWitness.Host.Arguments[1..4] -join '|') -cne '-NoLogo|-NoProfile|-NoExit|-Command'){
        throw 'CPP D original EXE/entry/NoExit invocation required.'
    }
    if($Closure.OwnedPIDs -isnot [array] -or ($Closure.OwnedPIDs -join '|') -cne '5008|6392|7876|8868|10068|11992|21016|23268|24412|27716|29356' -or
       $Closure.CPPExecuted -isnot [bool] -or !$Closure.CPPExecuted -or
       $Closure.CandidateExecuted -isnot [bool] -or $Closure.CandidateExecuted -or $Closure.Ready -isnot [bool] -or $Closure.Ready){
        throw 'CPP D exact independently closed originals required.'
    }
    foreach($name in 'OwnedLive','Leases','HeavyOrGame'){
        if($Closure.$name -isnot [array] -or $Closure.$name.Count){throw 'CPP D independent closure must be empty.'}
    }
    $exe=@($Receipt.Stages[-1].Artifacts|Where-Object {$_.Path -ceq $Plan.CandidateSource})
    if($exe.Count -ne 1 -or $exe[0].Bytes -ne $d.EXEBytes -or $exe[0].SHA256 -cne $d.EXESHA256 -or
       $Plan.CandidateSource -cne (Join-Path $Build.RunRoot 'link/zonetool-t7.exe') -or $Plan.BuildReceipt -cne (Join-Path $Build.RunRoot 'receipt.json')){
        throw 'CPP D candidate must be its original admitted link artifact.'
    }
}
function ConvertFrom-T7ImageProvenanceRecord([string]$Text,[int]$ExitCode) {
    $records=[regex]::Matches($Text,'(?m)^.*?T7_SELECTED_IMAGE_PROVENANCE (\{[^\r\n]*\})\r?$')
    if(!$records.Count){return [pscustomobject]@{Outcome='ProvenanceNoReport';Record=$null}}
    if($records.Count -ne 1 -or [Text.Encoding]::UTF8.GetByteCount($records[0].Groups[1].Value) -gt 32KB){throw 'One bounded F2 provenance record required.'}
    $record=$records[0].Groups[1].Value|ConvertFrom-Json -Depth 20
    if($record -isnot [pscustomobject] -or $record.schema -isnot [string] -or $record.schema -cne 'iw7.t7-selected-image-provenance/1'){
        throw 'Exact F2 record object/schema required.'
    }
    foreach($name in 'capture_complete','refused') {if($record.$name -isnot [bool]){throw 'Typed F2 capture/refusal required.'}}
    if($record.capture_complete -eq $record.refused){throw 'F2 capture/refusal contradict.'}
    foreach($name in 'same_object_proven','lifetime_proven','allocation_retained','pixels_copied','image_header_read','image_body_admitted','g3_image_header_admission_changed','registration_path_changed','ready'){
        if($record.$name -isnot [bool] -or $record.$name){throw 'F2 metadata record overclaims body/runtime proof.'}
    }
    foreach($name in 'image_body_bytes_read','payload_bytes_read'){
        if(!(Test-T7CatalogueInteger $record.$name 0)){throw 'F2 body/payload bytes forbidden.'}
    }
    if($record.refused){
        if($ExitCode -eq 0){throw 'Refused F2 record cannot have native exit zero.'}
        return [pscustomobject]@{Outcome='ProvenanceRecordRefused';Record=$record}
    }
    [pscustomobject]@{Outcome=$(if($ExitCode -eq 0){'ProvenanceRecordCaptured'}else{'ProvenanceRecordFromFailedProcess'});Record=$record}
}
function Read-T7ImageMetadataStdout($Plan,$State,$Context) {
    if(!$Context.Closed -or !$Context.Lease){throw 'Original F2 job must be closed with admission retained.'}
    $path=Join-Path $Plan.StageRoot 'stdout.log'
    $stream=[IO.FileStream]::new($path,'Open','Read','Read')
    try {
        if($stream.Length -le 0 -or $stream.Length -gt $Plan.LogLimitBytes){throw 'Bounded F2 stdout required.'}
        $hash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($stream)).ToLowerInvariant()
        $pin=[pscustomobject]@{Path=$path;Bytes=$stream.Length;SHA256=$hash};$stream.Position=0
        $reader=[IO.StreamReader]::new($stream,[Text.UTF8Encoding]::new($false,$true),$true,4096,$true)
        try{$text=$reader.ReadToEnd()}finally{$reader.Dispose()}
        $Context.Guards.Add($stream);$stream=$null;$State.Report=$pin
    }finally{if($stream){$stream.Dispose()}}
    return $text
}
function Read-T7ImageProvenanceRecord($Plan,$State,$Context) {
    $text=Read-T7ImageMetadataStdout $Plan $State $Context
    $result=ConvertFrom-T7ImageProvenanceRecord $text $State.ExitCode
    # Source consumer owns detailed epoch/MBI interpretation after closed-JSON handoff.
    $State.SelectedProvenance=[ordered]@{Schema='iw7.t7-selected-image-provenance/1';RecordPresent=($null -ne $result.Record);
        InterpretationPending=$true;ImageBodyRead=$false;Ready=$false}
    $result.Outcome
}
