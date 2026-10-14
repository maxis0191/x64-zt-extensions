$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path (Split-Path $PSScriptRoot -Parent) 'h1-fixture/H1Native.Core.ps1')
. (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
. (Join-Path $PSScriptRoot 'T7RegistrationImage.Profile.ps1')
$checks=0
function Check($Value,[string]$Message){if(!$Value){throw $Message};$script:checks++}
function Refuses([scriptblock]$Action){$caught=$false;try{& $Action}catch{$caught=$true};Check $caught 'Expected compiled-D refusal.'}
function New-ClosedD {
    $d=Get-T7RegistrationImageCohort
    $root='C:\authored\cpp-d'
    $plan=[pscustomobject]@{CandidateBytes=$d.EXEBytes;CandidateSHA256=$d.EXESHA256;ExpectedBuildPlanSHA256=$d.Plan[1];ExpectedBuildReceiptSHA256=$d.Receipt[1];CandidateSource=(Join-Path $root 'link/zonetool-t7.exe');BuildReceipt=(Join-Path $root 'receipt.json')}
    $build=[pscustomobject]@{SourceCommit=$d.NativeSource;RunRoot=$root;BuildProfile=[pscustomobject]@{Name='t7-registration-image-header-metadata-v1';Option='-t7-iw7-image-registration-metadata-v1';ArgumentCount=5;ObservationSchema='iw7.t7-registration-image-header-metadata/1';SourceOnlyPending=$false;RegistrationFixtureChecks=39;RegistrationSchema='iw7.t7-registration-image-header-metadata/1';RegistrationCPPQualified=$false}}
    $stages=@()
    foreach($name in 'registration-fixture-compile','registration-fixture-test','main','zonetool11','link'){
        $stages+=,[pscustomobject]@{Name=$name;Stage=$(if($name -ceq 'registration-fixture-test'){'Probe'}elseif($name -ceq 'link'){'Link'}else{'Compile'});ExitCode=0;TreeClosureConfirmed=$true;
            CompilerTelemetry=[pscustomobject]@{Completed=$true;AfterStop=[pscustomobject]@{RootExited=$true;RootExitCode=0;ActiveProcesses=0};AfterStopMembers=[pscustomobject]@{Members=@()}};Artifacts=@()}
    }
    $stages[1]|Add-Member Checks 39;$stages[1]|Add-Member EngineInvoked $false
    $stages[-1].Artifacts=@([pscustomobject]@{Path=$plan.CandidateSource;Bytes=$d.EXEBytes;SHA256=$d.EXESHA256})
    $receipt=[pscustomobject]@{Schema='iw7.t7-minimal-build/1';Status='Passed';RegistrationCPPQualified=$true;RegistrationFixturePassed=$true;PlanSHA256=$d.Plan[1];InputsReverified=$true;TreeClosureConfirmed=$true;LeaseReleased=$true;Quarantined=$false;CandidateExecuted=$false;Stages=$stages}
    $manifest=[pscustomobject]@{revisions=[pscustomobject]@{'x64-zt-extensions'=$d.Source}}
    $shell='C:\authored\pwsh.exe';$entry='C:\authored\pwsh.dll'
    $hostWitness=[pscustomobject]@{Schema='iw7.t7-image-registration-cpp-preexit/1';Status='Passed';Host=[pscustomobject]@{PID=788;CreationFileTime=[long]134364942263246878;Image=$shell;EntryAssembly=$entry;Invocation='.';NoExitVerified=$true;VerifiedBeforeImportsAndAdmission=$true;Arguments=@($entry,'-NoLogo','-NoProfile','-NoExit','-Command','. authored.ps1')};Parent=[pscustomobject]@{PID=8584;CreationFileTime=[long]134364942260845785;Image=$shell};Guards=0;CallerSourceGuards=0;PlanSHA256=$d.Plan[1];OriginalOwner=[pscustomobject]@{PID=28908;ExitCode=0;MatchesLastStage=$true;JobHandleClosed=$true;ProcessHandleClosed=$true};Quarantined=$false;CandidateExecuted=$false;Ready=$false}
    foreach($name in 'SameOriginalAppDomain','ContextVariableSame','GuardsVariableSame','StateVariableSame','ContextSame','CanExit','Closed','OwnerClosed','LeaseIsNull','TreeClosureConfirmed','LeaseReleased','InputsReverified','RegistrationFixturePassed','RegistrationCPPQualified','CPPExecuted'){$hostWitness|Add-Member $name $true}
    $closure=[pscustomobject]@{Schema='iw7.t7-image-registration-cpp-closure/1';Passed=$true;CPPExecuted=$true;CandidateExecuted=$false;RegistrationCPPQualified=$true;Ready=$false;ExpectedIDs=@(788,3176,7536,8584,10528,19112,24732,24976,27288,28244,28908);ActualPTYSession=82491;ActualPTYExit=0;PlanSHA256=$d.Plan[1];Receipt=[pscustomobject]@{SHA256=$d.Receipt[1]};Preexit=[pscustomobject]@{SHA256=$d.HostWitness[1]};RemainingOwn=@();Leases=@();HeavyOrGames=@()}
    [pscustomobject]@{Plan=$plan;Build=$build;Receipt=$receipt;Manifest=$manifest;Host=$hostWitness;Closure=$closure}
}
function Qualify($f){Assert-T7RegistrationImageCpp39 $f.Plan $f.Build $f.Receipt $f.Manifest $f.Host $f.Closure}
function New-CompiledPlan {
    $d=Get-T7RegistrationImageCohort;$root='C:\authored';$bindings=@();$marker=[ordered]@{Schema='iw7.t7-registration-image-cpp39/1'}
    foreach($name in 'SourceManifest','HostWitness','ClosureWitness','FixtureStdout'){
        $pin=[pscustomobject]@{Path=(Join-Path $root ($name+'.json'));Bytes=$d[$name][0];SHA256=$d[$name][1]}
        $marker[$name]=$pin;$bindings+=,[pscustomobject]@{Path=$pin.Path;Bytes=$pin.Bytes;SHA256=$pin.SHA256;IsText=$true}
    }
    foreach($name in 'Plan','Receipt'){$bindings+=,[pscustomobject]@{Path=(Join-Path $root ($name+'.json'));Bytes=$d[$name][0];SHA256=$d[$name][1];IsText=$true}}
    [pscustomobject]@{Schema='iw7.t7-registration-image-plan/1';Operation='RegistrationImageMetadataV1';CandidateProfile='t7-registration-image-header-metadata-v1';BootstrapPolicy='QualifiedCollectionV3';Bootstraps=@(1..23);SharedQualification=[pscustomobject]@{};
        CandidateBytes=$d.EXEBytes;CandidateSHA256=$d.EXESHA256;ExpectedBuildPlanSHA256=$d.Plan[1];ExpectedBuildReceiptSHA256=$d.Receipt[1];
        OutputKey='t7_iw7_registration_image_metadata_v1';TraceStderrLimitBytes=16384;SelectedRegistrationImageHeaderV1=[pscustomobject]$marker;
        BuildPlan=(Join-Path $root 'Plan.json');BuildReceipt=(Join-Path $root 'Receipt.json');Bindings=$bindings;
        Arguments=@('-t7-iw7-image-registration-metadata-v1','mp_freerun_04','p7_fre_platform_cap_02','0')}
}
$plan=New-CompiledPlan;Assert-T7RegistrationImagePlan $plan;Check (Test-T7RegistrationImagePlan $plan) 'Compiled selector failed.'
foreach($case in 'schema','old-marker','old-cli','body-option','part','collection','text-pin','provider'){
    $plan=New-CompiledPlan
    switch($case){
        schema {$plan.Schema='iw7.t7-image-provenance-source-plan/1'}
        old-marker {$plan.SelectedRegistrationImageHeaderV1.Schema='iw7.t7-image-provenance-proposal/1'}
        old-cli {$plan.CandidateSHA256='cce8'}
        body-option {$plan.Arguments[0]='-t7-iw7-image-metadata-v1'}
        part {$plan.Arguments[3]='1'}
        collection {$plan.Bootstraps=@(1..22)}
        text-pin {$plan.Bindings[0].SHA256='old'}
        provider {$plan|Add-Member SelectedXpakProvider ([pscustomobject]@{})}
    }
    Refuses {Assert-T7RegistrationImagePlan $plan}
}
$f=New-ClosedD;Qualify $f;Check $true 'Valid authored closed D refused.'
foreach($case in 'exe','recipe','source','native-source','pending','stages','exit','members','host-context','pty','present','reverified','executed','stage-kind','generation','argv','closed-execution'){
    $f=New-ClosedD
    switch($case){
        exe {$f.Plan.CandidateSHA256='cce8'}
        recipe {$f.Plan.ExpectedBuildPlanSHA256='old'}
        source {$f.Manifest.revisions.'x64-zt-extensions'='a8ecff7'}
        native-source {$f.Build.SourceCommit=$f.Manifest.revisions.'x64-zt-extensions'}
        pending {$f.Build.BuildProfile.SourceOnlyPending=$true}
        stages {$f.Receipt.Stages=$f.Receipt.Stages[2..4]}
        exit {$f.Receipt.Stages[0].ExitCode=2}
        members {$f.Receipt.Stages[-1].CompilerTelemetry.AfterStopMembers.Members=@(123)}
        host-context {$f.Host.ContextSame=$false}
        pty {$f.Closure.ActualPTYExit=1}
        present {$f.Closure.RemainingOwn=@(788)}
        reverified {$f.Receipt.InputsReverified='true'}
        executed {$f.Receipt.CandidateExecuted=$true}
        stage-kind {$f.Receipt.Stages[0].Stage='Probe'}
        generation {$f.Host.Host.CreationFileTime++}
        argv {$f.Host.Host.Arguments[3]='-Exit'}
        closed-execution {$f.Closure.CandidateExecuted=$true}
    }
    Refuses {Qualify $f}
}
$r=[ordered]@{}
foreach($name in 'allocation_retained','atomic_snapshot_proven','lifetime_proven','model_default','pixels_copied','ready','refused','runtime_abi_proven','same_object_proven'){$r[$name]=$false}
foreach($name in 'registration_header_observed','association_rechecked_at_registration','header_rechecked_at_registration','name_rechecked_at_registration'){$r[$name]=$true}
$r.schema='iw7.t7-registration-image-header-metadata/1';$r.source_profile='t7-registration-image-header-metadata-v1'
$r.capture_phase='after_original_model_add';$r.recheck_phase=$r.capture_phase;$r.capture_ordinal=1
$r.native_source_commit='fab935826c898806855376662a8a03317b3ad8f1';$r.zone='mp_freerun_04';$r.model='p7_fre_platform_cap_02'
$r.lod=0;$r.slot=0;$r.binding_index=4;$r.binding_hash_u32=2695565377;$r.image_header_bytes=264;$r.header_copies=2;$r.registration_header_bytes_copied=528;$r.payload_bytes_read=0
$r.failure_stage=$null;$r.reason=$null;$r.image=[pscustomobject]@{};$r.provenance=[pscustomobject]@{registration=[pscustomobject]@{ordinal=1}}
function Encode-Record {'T7_REGISTRATION_IMAGE_METADATA '+($r|ConvertTo-Json -Compress -Depth 8)}
Check ((ConvertFrom-T7RegistrationImageRecord (Encode-Record) 0) -ceq 'RegistrationRecordCaptured') 'Registration record lost.'
Check ((ConvertFrom-T7RegistrationImageRecord (Encode-Record) 1) -ceq 'RegistrationRecordFromFailedProcess') 'Nonzero promoted.'
Check ((ConvertFrom-T7RegistrationImageRecord '' 0) -ceq 'RegistrationNoReport') 'Missing record fabricated.'
Refuses {ConvertFrom-T7RegistrationImageRecord ((Encode-Record)+"`n"+(Encode-Record)) 0}
foreach($name in 'capture_phase','header_copies','payload_bytes_read','lifetime_proven','capture_ordinal'){
    $old=$r[$name];$r[$name]=switch($name){capture_phase{'after_zone_model_lookup'};header_copies{'2'};payload_bytes_read{1};lifetime_proven{$true};capture_ordinal{2}}
    Refuses {ConvertFrom-T7RegistrationImageRecord (Encode-Record) 0};$r[$name]=$old
}
$r.refused=$true
Check ((ConvertFrom-T7RegistrationImageRecord (Encode-Record) 1) -ceq 'RegistrationRecordRefused') 'Registration refusal lost.'
Refuses {ConvertFrom-T7RegistrationImageRecord (Encode-Record) 0}
[ordered]@{Status='Passed';Checks=$checks;AuthoredCPP39Objects=$true;NativeRun=$false;LeaseAcquired=$false;OpaqueRead=$false}|ConvertTo-Json

