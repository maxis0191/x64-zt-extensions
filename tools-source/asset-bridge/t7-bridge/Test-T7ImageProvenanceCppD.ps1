$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path (Split-Path $PSScriptRoot -Parent) 'h1-fixture/H1Native.Core.ps1')
. (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
. (Join-Path $PSScriptRoot 'T7ImageProvenance.Profile.ps1')
$checks=0
function Check($Value,[string]$Message){if(!$Value){throw $Message};$script:checks++}
function Refuses([scriptblock]$Action){$caught=$false;try{& $Action}catch{$caught=$true};Check $caught 'Expected compiled-D refusal.'}
function New-ClosedD {
    $d=Get-T7ImageProvenanceCppD
    $root='C:\authored\cpp-d'
    $plan=[pscustomobject]@{CandidateBytes=$d.EXEBytes;CandidateSHA256=$d.EXESHA256;ExpectedBuildPlanSHA256=$d.Plan[1];ExpectedBuildReceiptSHA256=$d.Receipt[1];CandidateSource=(Join-Path $root 'link/zonetool-t7.exe');BuildReceipt=(Join-Path $root 'receipt.json')}
    $build=[pscustomobject]@{SourceCommit=$d.NativeSource;RunRoot=$root;BuildProfile=[pscustomobject]@{Name='t7-image-provenance-v1';Option='-t7-iw7-image-provenance-v1';ArgumentCount=5;ObservationSchema='iw7.t7-selected-image-provenance/1';SourceOnlyPending=$false;MetadataMapperChecks=54;MetadataGuardChecks=13}}
    $stages=@()
    foreach($name in 'metadata-fixture-compile','metadata-fixture-test','main','zonetool11','link'){
        $stages+=,[pscustomobject]@{Name=$name;Stage=$(if($name -ceq 'metadata-fixture-test'){'Probe'}elseif($name -ceq 'link'){'Link'}else{'Compile'});ExitCode=0;TreeClosureConfirmed=$true;
            CompilerTelemetry=[pscustomobject]@{Completed=$true;AfterStop=[pscustomobject]@{RootExited=$true;RootExitCode=0;ActiveProcesses=0};AfterStopMembers=[pscustomobject]@{Members=@()}};Artifacts=@()}
    }
    $stages[-1].Artifacts=@([pscustomobject]@{Path=$plan.CandidateSource;Bytes=$d.EXEBytes;SHA256=$d.EXESHA256})
    $receipt=[pscustomobject]@{Schema='iw7.t7-minimal-build/1';Status='Passed';PlanSHA256=$d.Plan[1];InputsReverified=$true;TreeClosureConfirmed=$true;LeaseReleased=$true;Quarantined=$false;CandidateExecuted=$false;Stages=$stages}
    $manifest=[pscustomobject]@{revisions=[pscustomobject]@{'x64-zt-extensions'=$d.Source}}
    $shell='C:\authored\pwsh.exe';$entry='C:\authored\pwsh.dll'
    $hostWitness=[pscustomobject]@{Schema='iw7.t7-image-metadata-cpp-preexit/1';Status='Passed';Host=[pscustomobject]@{PID=7876;CreationFileTime=[long]134364856078036793;Image=$shell;EntryAssembly=$entry;Invocation='.';NoExitVerified=$true;VerifiedBeforeImportsAndAdmission=$true;Arguments=@($entry,'-NoLogo','-NoProfile','-NoExit','-Command','. authored.ps1')};Parent=[pscustomobject]@{PID=27716;CreationFileTime=[long]134364856076106178;Image=$shell};Guards=0;CallerSourceGuards=0;Quarantined=$false;CandidateExecuted=$false;Ready=$false}
    foreach($name in 'SameOriginalAppDomain','ContextVariableSame','GuardsVariableSame','StateVariableSame','ContextSame','CanExit','Closed','OwnerClosed','LeaseIsNull','TreeClosureConfirmed','LeaseReleased','InputsReverified','CPPExecuted'){$hostWitness|Add-Member $name $true}
    $closure=[pscustomobject]@{Schema='iw7.t7-image-metadata-cpp-closure/1';Status='Passed';CPPExecuted=$true;CandidateExecuted=$false;Ready=$false;OwnedPIDs=@(5008,6392,7876,8868,10068,11992,21016,23268,24412,27716,29356);OriginalPTY=99450;ActualPTYExitCode=0;PlanSHA256=$d.Plan[1];ReceiptSHA256=$d.Receipt[1];SameOriginalPreExitSHA256=$d.HostWitness[1];OwnedLive=@();Leases=@();HeavyOrGame=@()}
    [pscustomobject]@{Plan=$plan;Build=$build;Receipt=$receipt;Manifest=$manifest;Host=$hostWitness;Closure=$closure}
}
function Qualify($f){Assert-T7ImageProvenanceCppD $f.Plan $f.Build $f.Receipt $f.Manifest $f.Host $f.Closure}
function New-CompiledPlan {
    $d=Get-T7ImageProvenanceCppD;$root='C:\authored';$bindings=@();$marker=[ordered]@{Schema='iw7.t7-image-provenance-cpp-d/1'}
    foreach($name in 'SourceManifest','HostWitness','ClosureWitness','FixtureStdout'){
        $pin=[pscustomobject]@{Path=(Join-Path $root ($name+'.json'));Bytes=$d[$name][0];SHA256=$d[$name][1]}
        $marker[$name]=$pin;$bindings+=,[pscustomobject]@{Path=$pin.Path;Bytes=$pin.Bytes;SHA256=$pin.SHA256;IsText=$true}
    }
    foreach($name in 'Plan','Receipt'){$bindings+=,[pscustomobject]@{Path=(Join-Path $root ($name+'.json'));Bytes=$d[$name][0];SHA256=$d[$name][1];IsText=$true}}
    [pscustomobject]@{Schema='iw7.t7-image-provenance-plan/1';Operation='ImageProvenanceV1';CandidateProfile='t7-image-provenance-v1';BootstrapPolicy='QualifiedCollectionV3';Bootstraps=@(1..23);SharedQualification=[pscustomobject]@{};
        CandidateBytes=$d.EXEBytes;CandidateSHA256=$d.EXESHA256;ExpectedBuildPlanSHA256=$d.Plan[1];ExpectedBuildReceiptSHA256=$d.Receipt[1];
        OutputKey='t7_iw7_image_provenance_v1';TraceStderrLimitBytes=16384;SelectedImageProvenanceV1=[pscustomobject]$marker;
        BuildPlan=(Join-Path $root 'Plan.json');BuildReceipt=(Join-Path $root 'Receipt.json');Bindings=$bindings;
        Arguments=@('-t7-iw7-image-provenance-v1','mp_freerun_04','p7_fre_platform_cap_02','0')}
}
$plan=New-CompiledPlan;Assert-T7ImageProvenanceCompiledPlan $plan;Check (Test-T7ImageProvenanceCompiledPlan $plan) 'Compiled selector failed.'
foreach($case in 'schema','old-marker','old-cli','body-option','part','collection','text-pin','provider'){
    $plan=New-CompiledPlan
    switch($case){
        schema {$plan.Schema='iw7.t7-image-provenance-source-plan/1'}
        old-marker {$plan.SelectedImageProvenanceV1.Schema='iw7.t7-image-provenance-proposal/1'}
        old-cli {$plan.CandidateSHA256='cce8'}
        body-option {$plan.Arguments[0]='-t7-iw7-image-metadata-v1'}
        part {$plan.Arguments[3]='1'}
        collection {$plan.Bootstraps=@(1..22)}
        text-pin {$plan.Bindings[0].SHA256='old'}
        provider {$plan|Add-Member SelectedXpakProvider ([pscustomobject]@{})}
    }
    Refuses {Assert-T7ImageProvenanceCompiledPlan $plan}
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
        pty {$f.Closure.ActualPTYExitCode=1}
        present {$f.Closure.OwnedLive=@(7876)}
        reverified {$f.Receipt.InputsReverified='true'}
        executed {$f.Receipt.CandidateExecuted=$true}
        stage-kind {$f.Receipt.Stages[0].Stage='Probe'}
        generation {$f.Host.Host.CreationFileTime++}
        argv {$f.Host.Host.Arguments[3]='-Exit'}
        closed-execution {$f.Closure.CandidateExecuted=$true}
    }
    Refuses {Qualify $f}
}
$record=[ordered]@{schema='iw7.t7-selected-image-provenance/1';capture_complete=$true;refused=$false;image_body_bytes_read=0;payload_bytes_read=0}
foreach($name in 'same_object_proven','lifetime_proven','allocation_retained','pixels_copied','image_header_read','image_body_admitted','g3_image_header_admission_changed','registration_path_changed','ready'){$record[$name]=$false}
$text='T7_SELECTED_IMAGE_PROVENANCE '+($record|ConvertTo-Json -Compress)
Check ((ConvertFrom-T7ImageProvenanceRecord $text 0).Outcome -ceq 'ProvenanceRecordCaptured') 'Record capture failed.'
Check ((ConvertFrom-T7ImageProvenanceRecord $text 1).Outcome -ceq 'ProvenanceRecordFromFailedProcess') 'Nonzero promoted.'
Check ((ConvertFrom-T7ImageProvenanceRecord '' 0).Outcome -ceq 'ProvenanceNoReport') 'Missing record fabricated.'
Refuses {ConvertFrom-T7ImageProvenanceRecord ($text+"`n"+$text) 0}
$record.capture_complete=$false;$record.refused=$true;$text='T7_SELECTED_IMAGE_PROVENANCE '+($record|ConvertTo-Json -Compress)
Check ((ConvertFrom-T7ImageProvenanceRecord $text 1).Outcome -ceq 'ProvenanceRecordRefused') 'Refusal lost.'
Refuses {ConvertFrom-T7ImageProvenanceRecord $text 0}
$record.image_body_bytes_read=264;$text='T7_SELECTED_IMAGE_PROVENANCE '+($record|ConvertTo-Json -Compress)
Refuses {ConvertFrom-T7ImageProvenanceRecord $text 1}
[ordered]@{Status='Passed';Checks=$checks;AuthoredClosedObjects=$true;CPPExecuted=$false;NativeRun=$false;LeaseAcquired=$false;OpaqueRead=$false}|ConvertTo-Json
