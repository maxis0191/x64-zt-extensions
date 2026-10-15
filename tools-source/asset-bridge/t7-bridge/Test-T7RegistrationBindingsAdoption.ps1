# Pure Source, bounded capture and actual Catalogue-finally tests with owned fakes.
# No operational DEFAULT, process, opaque input, admission or NativeJob is invoked.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path (Split-Path $PSScriptRoot -Parent) 'h1-fixture/H1Native.Core.ps1')
. (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
. (Join-Path $PSScriptRoot 'T7CatalogueHost.Core.ps1')
$checks=0
function Check([bool]$Value,[string]$Why){if(!$Value){throw $Why};$script:checks++}
function Refuses([scriptblock]$Action){$caught=$false;try{& $Action}catch{$caught=$true};Check $caught 'Altered CPP80/capture accepted.'}
$source=Join-Path (Split-Path $PSScriptRoot -Parent) 't7-iw7'
$contractPath=Join-Path $source 'registration-bindings-build-source-contract.json'
$contract=Get-Content -LiteralPath $contractPath -Raw|ConvertFrom-Json
$producer=Get-Content -LiteralPath (Join-Path $source 'registration-material-bindings-source-contract.json') -Raw|ConvertFrom-Json
$contractSHA=(Get-FileHash -LiteralPath $contractPath).Hash.ToLowerInvariant()
$cohort=Get-T7RegistrationBindingsCpp80Cohort;$hash=$cohort.Plan[1];$stdout=$contract.fixture_stdout
$tokens=$null;$errors=$null
$fixtureAST=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Test-T7RegistrationBindingsCppSource.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Fixture Source parse error.'}
$definition=$fixtureAST.Find({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq 'New-DeclaredFixture'},$false)
. ([scriptblock]::Create($definition.Extent.Text))
function Pin([string]$Name){[pscustomobject]@{Path=('C:\authored\'+$Name+'.json');Bytes=$cohort[$Name][0];SHA256=$cohort[$Name][1]}}
function New-CompiledPlan {
    $m=[pscustomobject]@{Schema='iw7.t7-registration-bindings-cpp80/1';SourceRevision='92118595079b86d66c340c22b299de90c49a2b6a';ReaderRevision='6d16303437f706df4037c636b3ee9f8a5da00aaf';
        Contract=[pscustomobject]@{Path='C:\authored\registration-material-bindings-source-contract.json';Bytes=5391;SHA256='d60f0e33d9dddb69656744f6481ba32ced1a7a040d75ff913908192297e3c9a6'};
        Reader=[pscustomobject]@{Path='C:\authored\registration_bindings_consumer.py';Bytes=9687;SHA256='8e1d464c6467492b65e102b784aa9f265723560b9b486499e3a49cb4073f5c81'};
        NativeSchema='iw7.t7-registration-material-bindings/1';BindingCount=7;ReportLimitBytes=32768;SourceOnlyPending=$false;BuildRecipeWired=$true;
        CompiledExtensionSource=$cohort.Source;CPPQualification=(Pin 'Handoff');CPPQualified=$true;NativeObserved=$false;DeepMetadataOutcome=$null;QualifiedObjectMipCount=$null;Ready=$false}
    [pscustomobject]@{Schema='iw7.t7-registration-bindings-plan/1';Operation='RegistrationMaterialBindingsV1';CandidateProfile='t7-registration-material-bindings-v1';
        Arguments=@('-t7-iw7-registration-material-bindings-v1','mp_freerun_04','p7_fre_platform_cap_02','0');CandidateSource='C:\authored\run\link\zonetool-t7.exe';
        CandidateBytes=$cohort.EXEBytes;CandidateSHA256=$cohort.EXESHA256;BuildPlan='C:\authored\Plan.json';BuildReceipt='C:\authored\run\receipt.json';
        ExpectedBuildPlanSHA256=$cohort.Plan[1];ExpectedBuildReceiptSHA256=$cohort.Receipt[1];OutputKey='t7_iw7_registration_material_bindings_v1';TraceStderrLimitBytes=16384;
        SelectedRegistrationMaterialBindingsV1=$m;Bindings=@(foreach($p in @($m.CPPQualification,$m.Contract,$m.Reader)){[pscustomobject]@{Path=$p.Path;Bytes=$p.Bytes;SHA256=$p.SHA256;IsText=$true}})}
}
function New-Proof {
    $f=New-DeclaredFixture;$plan=New-CompiledPlan
    $exe=@($f.Receipt.Stages[-1].Artifacts|Where-Object {[IO.Path]::GetExtension($_.Path) -ceq '.exe'})[0]
    $exe.Bytes=$cohort.EXEBytes;$exe.SHA256=$cohort.EXESHA256
    $h=[ordered]@{Schema='iw7.t7-registration-bindings-cpp-actual-handoff/1';SourceCommit=$cohort.Source;NativeSourceCommit=$cohort.NativeSource;Status='Passed';
        OriginalRootKey='IW7.RegistrationBindingsCPP.Original.D';TotalChecks=80;ActualPTYAggregateExitCode=0;OriginalIdentitiesAbsent=@(1,2,3,4,5,6,7);
        FreshHeavyProcesses=@();FreshLeases=@();FixtureStderr=[pscustomobject]@{Bytes=0;SHA256='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'};
        Candidate=[pscustomobject]@{Path=$plan.CandidateSource;Bytes=$cohort.EXEBytes;SHA256=$cohort.EXESHA256}}
    foreach($n in 'OriginalContextGuardsStatePSVariableValuesSame','OriginalReferencesVerified','OriginalOwnerClosed','OriginalLeaseNull','PreReleasePublished','CompletionPublished','ContextCanExit','CallerCanExit','ReceiptTextPinsUnchanged','ArtifactPinsCapturedReverifiedUnderCPPLease','CPPExecuted','CPP80ObservedClosed','OperationalGate170Closed'){$h[$n]=$true}
    foreach($n in 'OriginalInputGuards','OriginalPublicationGuards','CallerSourceGuards'){$h[$n]=0}
    foreach($n in 'CandidateExecuted','StockRead','NativeObserved','Ready','CandidateOrSymbolsReadAfterRelease'){$h[$n]=$false}
    $pre=[ordered]@{Schema='iw7.t7-registration-bindings-cpp-pre-exit/1';CallerSourceGuards=0;InputGuards=0;PublicationGuards=0}
    foreach($n in 'OriginalAppDomainRootSame','OriginalContextGuardsStatePSVariableValuesSame','OriginalReferencesVerified','CallerCanExit','ContextClosed','OwnerClosed','LeaseNull','PreReleasePublished','CompletionPublished','ContextCanExit'){$pre[$n]=$true}
    $post=[ordered]@{Schema='iw7.t7-registration-bindings-cpp-post-exit/1';SourceCommit=$cohort.Source;NativeSourceCommit=$cohort.NativeSource;Status='Passed';ActualPTYAggregateExitCode=0;
        OriginalHostParentStagesAbsent=$true;ReceiptTextPinsUnchanged=$true;CPPExecuted=$true;OperationalGate170Closed=$true;AbsentPIDs=@(1,2,3,4,5,6,7);FreshHeavyProcesses=@();FreshLive=[pscustomobject]@{Leases=@()}}
    [pscustomobject]@{Plan=$plan;Build=$f.Build;Receipt=$f.Receipt;Handoff=[pscustomobject]$h;Manifest=[pscustomobject]@{revisions=[pscustomobject]@{'x64-zt-extensions'=$cohort.Source}};Pre=[pscustomobject]$pre;Post=[pscustomobject]$post}
}
$f=New-Proof
Assert-T7RegistrationBindingsPlan $f.Plan
Assert-T7RegistrationBindingsCpp80 $f.Plan $f.Build $f.Receipt $f.Handoff $f.Manifest $f.Pre $f.Post $stdout
Check ((Get-T7CatalogueHostSchema $f.Plan 'host') -ceq 'iw7.t7-registration-bindings-host/1') 'Compiled host schema refused.'
Check ((Get-T7CatalogueHostOutcomeName $f.Plan) -ceq 'RegistrationBindingsOutcome') 'Compiled outcome differs.'
foreach($name in 'CandidateBytes','CandidateSHA256','ExpectedBuildPlanSHA256','ExpectedBuildReceiptSHA256','TraceStderrLimitBytes'){
    $f=New-Proof;$f.Plan.$name=@($f.Plan.$name);Refuses {Assert-T7RegistrationBindingsPlan $f.Plan}
}
foreach($name in 'SourceOnlyPending','BuildRecipeWired','CPPQualified','NativeObserved','Ready'){
    $f=New-Proof;$f.Plan.SelectedRegistrationMaterialBindingsV1.$name='false';Refuses {Assert-T7RegistrationBindingsPlan $f.Plan}
}
foreach($name in 'Plan','Build','Receipt','Handoff','Manifest','Pre','Post'){
    $f=New-Proof;$f.$name=@($f.$name);Refuses {Assert-T7RegistrationBindingsCpp80 $f.Plan $f.Build $f.Receipt $f.Handoff $f.Manifest $f.Pre $f.Post $stdout}
}
foreach($case in 'old-exe','wrong-source','refs','pre-guard','lease','pty','absence','native','post-lease','fake-receipt-flag'){
    $f=New-Proof
    switch($case){
        old-exe {$f.Handoff.Candidate.SHA256='4fcb0205e30979457784d1b883a153ecf5c20751543b68dfb184671d59e3ee4d'}
        wrong-source {$f.Manifest.revisions.'x64-zt-extensions'='e6c0b262973b7832b87c91a6122a7cbb2daef987'}
        refs {$f.Handoff.OriginalReferencesVerified=$false}
        pre-guard {$f.Pre.PublicationGuards=1}
        lease {$f.Handoff.FreshLeases=@('retained')}
        pty {$f.Handoff.ActualPTYAggregateExitCode=1}
        absence {$f.Post.AbsentPIDs=@(1,2,3,4,5,6,8)}
        native {$f.Handoff.NativeObserved=$true}
        post-lease {$f.Post.FreshLive.Leases=@('retained')}
        fake-receipt-flag {$f.Receipt|Add-Member RegistrationBindingsCPPQualified $true}
    }
    Refuses {Assert-T7RegistrationBindingsCpp80 $f.Plan $f.Build $f.Receipt $f.Handoff $f.Manifest $f.Pre $f.Post $stdout}
}
foreach($pair in @(@('Handoff','Schema'),@('Handoff','Status'),@('Handoff','OriginalRootKey'),@('Post','Schema'),@('Post','SourceCommit'),@('Post','Status'))){
    $f=New-Proof;$f.($pair[0]).($pair[1])=@($f.($pair[0]).($pair[1]))
    Refuses {Assert-T7RegistrationBindingsCpp80 $f.Plan $f.Build $f.Receipt $f.Handoff $f.Manifest $f.Pre $f.Post $stdout}
}
$f=New-Proof;$f.Post.FreshLive=@($f.Post.FreshLive);Refuses {Assert-T7RegistrationBindingsCpp80 $f.Plan $f.Build $f.Receipt $f.Handoff $f.Manifest $f.Pre $f.Post $stdout}
$f=New-Proof;$f.Handoff.OriginalIdentitiesAbsent[0]='1';Refuses {Assert-T7RegistrationBindingsCpp80 $f.Plan $f.Build $f.Receipt $f.Handoff $f.Manifest $f.Pre $f.Post $stdout}
$minimal='{"schema":"iw7.t7-registration-material-bindings/1","source_profile":"t7-registration-material-bindings-v1","native_source_commit":"fab935826c898806855376662a8a03317b3ad8f1"}'
$text='[INFO] T7_REGISTRATION_MATERIAL_BINDINGS '+$minimal+"`r`n"
Check ((ConvertFrom-T7RegistrationBindingsRecord $text 0).Record -ceq $minimal) 'Raw JSON was not preserved.'
Check ((ConvertFrom-T7RegistrationBindingsRecord $text 1).Outcome -ceq 'RegistrationBindingsRecordFromFailedProcess') 'Failed-process record was lost/promoted.'
Check ((ConvertFrom-T7RegistrationBindingsRecord 'ordinary output' 0).Outcome -ceq 'RegistrationBindingsNoReport') 'Missing report promoted.'
foreach($bad in @($text+$text,($text.Replace($minimal,'[]')),($text.Replace($minimal,'{"schema":[]}')),('x'*1048577),($text.Replace($minimal,('{"padding":"'+('a'*32768)+'"}'))))){Refuses {ConvertFrom-T7RegistrationBindingsRecord $bad 0}}
foreach($exit in @($true,'0',4294967296L,-2147483649L)){Refuses {ConvertFrom-T7RegistrationBindingsRecord $text $exit}}
# Reach the complete common plan validator with the existing synthetic bootstrap
# builders. Every opaque metadata query is satisfied by the fake provider only.
function Assert-H1Path([string]$Path){if(![IO.Path]::IsPathFullyQualified($Path) -or [IO.Path]::GetFullPath($Path) -cne $Path){throw 'Authored absolute path required.'}}
foreach($file in 'Test-T7CatalogueBootstrap.ps1','Test-T7CatalogueBootstraps.ps1'){
    $tree=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $file),[ref]$tokens,[ref]$errors)
    if($errors.Count){throw 'Common fixture Source parse error.'}
    foreach($name in $(if($file -ceq 'Test-T7CatalogueBootstrap.ps1'){@('Copy-Value','New-Fixture')}else{@('New-Qualified')})){
        $fn=$tree.Find({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$false)
        . ([scriptblock]::Create($fn.Extent.Text))
    }
}
function Get-Item($LiteralPath){if(!$script:provider.ContainsKey($LiteralPath)){throw 'Unexpected filesystem metadata query.'};$script:provider[$LiteralPath]}
$root=Join-Path ([IO.Path]::GetTempPath()) ('t7-bindings-adoption-'+[guid]::NewGuid().ToString('N'))
$null=[IO.Directory]::CreateDirectory($root)
try{
    $q=New-Qualified 23 'QualifiedCollectionV3';$compiled=New-CompiledPlan
    $removed=@($q.Plan.Bootstraps[0..11].QualificationScript.Path)
    $shared=[pscustomobject]@{Script=[pscustomobject]@{Path=(Join-Path $root 'Qualify-T7BootstrapGroup.ps1');Bytes=100;SHA256=('d'*64)};
        Plan=[pscustomobject]@{Path=(Join-Path $root 'shared-plan.json');Bytes=100;SHA256=('d'*64)};
        Receipt=[pscustomobject]@{Path=(Join-Path $root 'shared-receipt.json');Bytes=100;SHA256=('d'*64)}}
    for($i=0;$i -lt 12;$i++){$q.Plan.Bootstraps[$i].QualificationScript=Copy-Value $shared.Script}
    $q.Plan|Add-Member SharedQualification $shared
    $q.Plan.Bindings=@($q.Plan.Bindings|Where-Object {$_.Path -cnotin $removed})
    foreach($p in @($shared.Script,$shared.Plan,$shared.Receipt)){$b=Copy-Value $p;$b|Add-Member IsText $true;$q.Plan.Bindings+=@($b)}
    $q.Plan.RunRoot=Join-Path $q.Repo 'runtime/t7-registration-bindings-authored'
    foreach($n in 'work','evidence','temp'){$null=[IO.Directory]::CreateDirectory((Join-Path $q.Plan.RunRoot $n))}
    $q.Plan.WorkingDirectory=Join-Path $q.Plan.RunRoot 'work';$q.Plan.StageRoot=Join-Path $q.Plan.RunRoot 'evidence';$q.Plan.Image=Join-Path $q.Plan.WorkingDirectory 't7-zonetool-candidate.exe'
    foreach($n in 'Schema','Operation','CandidateProfile','Arguments','CandidateSource','CandidateBytes','CandidateSHA256','BuildPlan','BuildReceipt','ExpectedBuildPlanSHA256','ExpectedBuildReceiptSHA256','OutputKey','TraceStderrLimitBytes','SelectedRegistrationMaterialBindingsV1'){
        $q.Plan|Add-Member -Force NoteProperty $n $compiled.$n
    }
    $q.Plan.ReportLimitBytes=32768;$q.Plan.OutputLimitBytes=106059160L+$cohort.EXEBytes+23000
    $q.Plan.Bindings[0].Path=$compiled.CandidateSource;$q.Plan.Bindings[0].Bytes=$cohort.EXEBytes;$q.Plan.Bindings[0].SHA256=$cohort.EXESHA256
    $q.Plan.InputMetadata[0].Path=$compiled.CandidateSource;$q.Plan.InputMetadata[0].Bytes=$cohort.EXEBytes
    $q.Plan.Bindings+=@($compiled.Bindings)
    for($i=0;$i -lt 27;$i++){$q.Plan.Bindings+=@([pscustomobject]@{Path=(Join-Path $root ('extra-'+$i+'.json'));Bytes=100;SHA256=('c'*64);IsText=$true})}
    foreach($p in $q.Plan.Bindings){$script:provider[$p.Path]=[pscustomobject]@{PSIsContainer=$false;Length=$p.Bytes;Attributes='Archive';CreationTimeUtc=([datetimeoffset]'2026-10-12T00:00:00Z').UtcDateTime;LastWriteTimeUtc=([datetimeoffset]'2026-10-12T00:00:00Z').UtcDateTime}}
    Assert-T7CataloguePlan $q.Plan $q.Repo 'synthetic-runner';Check $true 'Full compiled common plan refused.'
    Check (@($q.Plan.Bindings).Count -eq 112) 'Finite common binding count differs.'
    foreach($n in 'ReportLimitBytes','OutputLimitBytes'){$bad=Copy-Value $q.Plan;$bad.$n++;Refuses {Assert-T7CataloguePlan $bad $q.Repo 'synthetic-runner'}}
    $bad=Copy-Value $q.Plan;$bad.Bindings=$bad.Bindings[0..110];Refuses {Assert-T7CataloguePlan $bad $q.Repo 'synthetic-runner'}
    function New-T7PrepatchStart {[Diagnostics.ProcessStartInfo]::new()}
    $start=New-T7CatalogueStart $q.Plan
    Check (($start.ArgumentList -join '|') -ceq ($compiled.Arguments -join '|')) 'Existing command setup changed bindings arguments.'
}finally{
    $resolved=[IO.Path]::GetFullPath($root);$prefix=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if(!$resolved.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -cnotmatch '^t7-bindings-adoption-[0-9a-f]{32}$'){throw 'Test cleanup path differs.'}
    [IO.Directory]::Delete($resolved,$true)
}
# Execute the real runner finally body with only fakes for I/O, scheduling and
# receipt streams. This catches branching/release/disposal order in production.
$runnerAST=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Run-T7Catalogue.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Runner Source parse error.'}
$tryAST=@($runnerAST.EndBlock.Statements|Where-Object {$_ -is [Management.Automation.Language.TryStatementAst]})[0]
$finally=[scriptblock]::Create($tryAST.Finally.Extent.Text.Trim().Substring(1).TrimEnd().TrimEnd('}'))
function New-Guard {
    $g=[pscustomobject]@{Disposed=$false}
    $g|Add-Member ScriptMethod Dispose {if($script:fault -ceq 'source-dispose' -and $this -eq $script:sourceGuard){throw 'injected input disposal unknown'};$this.Disposed=$true}
    $g
}
function Open-H1Pin($Pin){if($script:fault -ceq 'final-guard' -and $Pin.Path -ceq 'C:\authored\receipt.json'){throw 'injected final guard failure'};New-Guard}
function Write-H1Receipt($Plan,$State,$StageRoot,$Name='receipt.json',[switch]$PassThru){
    $script:events.Add('publish:'+ $Name)
    if(($script:fault -ceq 'pre-publish' -and $Name -ceq 'receipt-before-release.json') -or ($script:fault -ceq 'final-publish' -and $Name -ceq 'receipt.json')){throw 'injected publication failure'}
    if($PassThru){[pscustomobject]@{Path=('C:\authored\'+$Name);Bytes=1;SHA256=('a'*64)}}
}
function Exit-IW7ResourceLease($Token){$script:events.Add('release')}
function Assert-T7CatalogueMain($Plan){[pscustomobject]@{Baseline='Stopped'}}
function Assert-H1Deadline {}
function Test-H1Budget {}
function Assert-T7CatalogueEngineOutputs {}
function Assert-T7CatalogueMetadata {}
function Read-T7ImageMetadataStdout {$text}
foreach($case in 'success','known-native-failure','pre-publish','final-publish','final-guard','unclosed','source-dispose'){
    $script:fault=$case;$script:events=[Collections.Generic.List[string]]::new()
    $guards=[Collections.Generic.List[object]]::new();$script:sourceGuard=New-Guard;$guards.Add($script:sourceGuard)
    $owner=[pscustomobject]@{Closed=($case -cne 'unclosed');ExitCode=$(if($case -ceq 'known-native-failure'){1}else{0})}
    $owner|Add-Member ScriptMethod StopAndConfirm {param($Timeout)}
    $context=[pscustomobject]@{Owner=$owner;Closed=$owner.Closed;Lease=[pscustomobject]@{Token=('c'*32)};Guards=$guards;
        PublicationGuards=[Collections.Generic.List[object]]::new();Publications=[Collections.Generic.List[object]]::new();PreReleasePublished=$false;CompletionPublished=$false;CanExit=$false}
    $state=[ordered]@{Schema='iw7.t7-registration-bindings-run/1';Status='Running';TreeClosureConfirmed=$owner.Closed;ExitCode=$owner.ExitCode;TerminationRequested=$false;Quarantined=$false;
        LeaseToken=('c'*32);LeaseReleased=$false;InputsReverified=$false;EngineOutputsValidated=$false;Aliases=@();InputFileIds=@();
        RegistrationBindingsOutcome='RegistrationBindingsNoReport';SelectedRegistrationBindings=$null}
    $plan=[pscustomobject]@{RunRoot='C:\authored';StageRoot='C:\authored';Bindings=@();InputMetadata=@()};$zonePin=[pscustomobject]@{Path='C:\authored\zone.ff'}
    $failure=if($case -ceq 'known-native-failure'){[Exception]::new('native exit 1')}else{$null}
    $export=$parts=$provenance=$registration=$incoming=$false;$registrationBindings=$true;$attempted=$true;$script:T7CatalogueGroupStarted=[Diagnostics.Stopwatch]::StartNew()
    try{. $finally}catch{if($case -cne 'source-dispose'){throw}}
    if($case -cin @('success','known-native-failure')){
        Check ($context.CanExit -and $context.CompletionPublished -and $context.PreReleasePublished -and !$context.Lease -and !$guards.Count -and !$context.PublicationGuards.Count) 'Known closed path did not publish/dispose.'
        Check (($events -join '|') -ceq 'publish:receipt-before-release.json|release|publish:receipt.json') 'Publication/release order differs.'
        Check (!$state.SelectedRegistrationBindings.NativeObserved -and !$state.SelectedRegistrationBindings.Ready -and $null -eq $state.SelectedRegistrationBindings.DeepMetadataOutcome) 'Shell promoted deep semantics.'
        if($case -ceq 'success'){Check ($state.Status -ceq 'RegistrationBindingsCapturedPendingReview') 'Capture status differs.'}
        else{Check ($state.RegistrationBindingsOutcome -ceq 'RegistrationBindingsRecordFromFailedProcess') 'Original failure/capture lost.'}
    }else{
        Check (!$context.CanExit -and $guards.Count -eq 1 -and !$script:sourceGuard.Disposed) 'Unknown path disposed original input guards or allowed exit.'
        if($case -cin @('pre-publish','unclosed')){Check ($null -ne $context.Lease) 'Unknown before release lost original lease.'}
        else{Check ($context.PreReleasePublished -and !$context.Lease) 'Post-release failure rewrote historical release state.'}
    }
    [AppDomain]::CurrentDomain.SetData(('IW7.H1.Quarantine.'+('c'*32)),$null)
}
Write-Output ('T7_REGISTRATION_BINDINGS_ADOPTION_CHECKS='+$checks)
