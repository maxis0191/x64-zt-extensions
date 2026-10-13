# Synthetic source/closure failures. Optional reviewed mode reads bounded text
# only into a qualification context, never an operational export plan or binary.
[CmdletBinding()]
param([string]$ReviewedBuildPlanPath,[string]$IndependentWitnessPath)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
. (Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1')
. (Join-Path $PSScriptRoot 'T7Catalogue.Profile.ps1')
. (Join-Path $PSScriptRoot 'T7ResidentExport.Profile.ps1')
foreach($spec in @(@('t7-bridge/Test-T7CatalogueTrace.ps1',@('Check','Refuses','Copy-Value','New-Pin','New-Binding','New-Fixture','Read-H1SmallJson')),
    @('t7-bridge/Test-T7CataloguePublication.ps1',@('New-PublicationFixture')),
    @('t7-bridge/Test-T7ResidentExportDiagnostic.ps1',@('New-DiagnosticFixture')),
    @('t7-iw7/Test-T7InputBindings.ps1',@('New-BindingFixture')))){
    $tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $repo ('tools-source/asset-bridge/'+$spec[0])),[ref]$tokens,[ref]$errors)
    if($errors.Count){throw 'Synthetic helper parse error.'}
    foreach($name in $spec[1]){
        $nodes=@($ast.FindAll({param($node)$node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq $name},$true))
        if($nodes.Count -ne 1){throw 'Synthetic helper missing.'}
        $text=$nodes[0].Extent.Text.Replace("(Join-Path `$PSScriptRoot 'prepare_build.py')","(Join-Path `$repo 'tools-source/asset-bridge/t7-iw7/prepare_build.py')")
        . ([scriptblock]::Create($text))
    }
}
$root=Join-Path ([IO.Path]::GetTempPath()) ('t7-v2-build-tests-'+[guid]::NewGuid().ToString('N'))
$null=[IO.Directory]::CreateDirectory($root);$script:checks=0
function Add-DClosureBindings($Plan,[string]$WitnessPath){
    $prefix=Join-Path (Split-Path (Split-Path $Plan.BuildPlan -Parent) -Parent) 't7-multisurface-build-d-'
    foreach($row in @(@(($prefix+'completion.local.json'),16438,'962e795e474f8fd5a86a41eff3f4bd31879ba07d77c510053b0442a98c8ae199'),
        @(($prefix+'host-exit.local.json'),1290,'b776e7cce3ad68c0e994fb12a29aa7dcfc769663985260125c2a6308c8c2bbfe'),
        @(($prefix+'original-host-closure.local.json'),368,'690e509cd2363e4937b22a915164a03bceb8b167ec6cb5c5098fda32242ff1f0'),
        @(($prefix+'host-identity.local.json'),835,'8b2726f6bcc3c27a548c9b3e3aa1e6fce97be56aaec44211de9f004c8751d217'),
        @($WitnessPath,8167,'29fc704e3c173b4ae1c72fe4a3e4f6627c4d6768209a5a685905ab63d039dd19'))){
        $Plan.Bindings+=@(New-Binding ([pscustomobject]@{Path=$row[0];Bytes=$row[1];SHA256=$row[2]}))
    }
}
function New-V2BuildFixture {
    $f=New-DiagnosticFixture;$p=$f.Plan;$b=$f.Build;$r=$f.Receipt
    $p.PSObject.Properties.Remove('ResidentSurfaceCountDiagnostic')
    $p|Add-Member NoteProperty ResidentMultiSurfaceV2 ([pscustomobject]@{Schema='iw7.t7-resident-multi-surface/2'})
    $p.ExpectedBuildPlanSHA256='551a4017b334d573e5873dfda3e6134968549db08e0aabacbc269ad4a398488a'
    $p.ExpectedBuildReceiptSHA256='25d2593dbb412ac676f5e11f1b4d8ae34f26623217159ddb36dfc3f42d96ce0b'
    ($p.Bindings|Where-Object Path -CEQ $p.BuildPlan).Bytes=365638
    ($p.Bindings|Where-Object Path -CEQ $p.BuildPlan).SHA256=$p.ExpectedBuildPlanSHA256
    ($p.Bindings|Where-Object Path -CEQ $p.BuildReceipt).Bytes=22380
    ($p.Bindings|Where-Object Path -CEQ $p.BuildReceipt).SHA256=$p.ExpectedBuildReceiptSHA256
    $p.CandidateBytes=21805568;$p.CandidateSHA256='3c9271a0ef0e96cce26f44c30e6b04aa4c2338c86057ac52da489a7bc0e28e7f'
    $r.Stages[2].Artifacts[0].Bytes=$p.CandidateBytes;$r.Stages[2].Artifacts[0].SHA256=$p.CandidateSHA256
    $r.PlanSHA256=$p.ExpectedBuildPlanSHA256;$r|Add-Member NoteProperty LeaseToken 'synthetic-lease'
    $inputFixture=New-BindingFixture;$proof=$inputFixture.ReuseCompile.ResidentMultiSurfaceV2
    $proof.DependencyJSON=$b.ReuseCompile.ResidentSurfaceCountDiagnostic.DependencyJSON
    $b.ReuseCompile.PSObject.Properties.Remove('ResidentSurfaceCountDiagnostic');$b.ReuseCompile|Add-Member NoteProperty ResidentMultiSurfaceV2 $proof
    $b|Add-Member NoteProperty Inputs $inputFixture.Inputs
    foreach($transition in $proof.SourceTransitions){
        $path=Join-Path (Split-Path $b.PreparedRoot -Parent) $transition.Path
        foreach($collection in @($p.Bindings,$b.Bindings)){
            $pin=@($collection|Where-Object Path -CEQ $path)[0];$pin.Bytes=$transition.WiredBytes;$pin.SHA256=$transition.WiredSHA256
        }
        if($transition.Path -notlike '*.hpp'){
            $name=if($transition.Path -like '*main.cpp'){'PreparedMain'}else{'PreparedCLI'}
            $b.BuildProfile.$name.Bytes=$transition.WiredBytes;$b.BuildProfile.$name.SHA256=$transition.WiredSHA256
        }
    }
    $r.BuildProfile=Copy-Value $b.BuildProfile
    $b.Bindings+=@(foreach($pin in $proof.AdditionalHeaderInputs.Inputs){New-Binding $pin})
    while($b.Bindings.Count -lt 135){$b.Bindings+=@(New-Binding (New-Pin (Join-Path $root ('synthetic-'+$b.Bindings.Count+'.txt'))))}
    $b.Bindings+=@($inputFixture.Bindings|Where-Object {!$_.IsText})
    $script:json[$r.Stages[1].Artifacts[-1].Path].Data.Includes=@((Join-Path $b.PreparedRoot 't7_iw7_resident_model.hpp'))+@($proof.AdditionalHeaderInputs.Inputs.Path)
    Add-DClosureBindings $p (Join-Path $root 'independent.json');$pins=Get-T7ResidentMultiSurfaceBuildPins $p
    $hostIdentity=[pscustomobject]@{PID=1;ParentPID=2;Image='synthetic/pwsh.exe';CreatedUtc='2026-10-13T09:00:00Z'}
    $parentIdentity=[pscustomobject]@{PID=2;Image='synthetic/pwsh.exe';CreatedUtc='2026-10-13T08:59:59Z'}
    $identity=[pscustomobject]@{Schema='iw7.t7-build-d-host-identity/1';PlanSHA256=$p.ExpectedBuildPlanSHA256;SessionId=7;Host=$hostIdentity;Parent=$parentIdentity;ExactPlanCommandMatched=$true}
    $closure=[pscustomobject]@{Schema='iw7.t7-build-d-original-host-closure/1';SessionId=7;HostPID=1;Closed=$true;OwnerClosed=$true;NativeOwnerExitCode=0;GuardCount=0;
        LeaseIsNull=$true;RegistryLeaseCount=0;ReceiptStatus='Passed';InputsReverified=$true;CanExit=$true}
    $actual=[pscustomobject]@{Schema='iw7.t7-build-d-host-exit/1';SessionId=7;HostIdentity=$pins.HostIdentity;OriginalHostClosure=$pins.OriginalHostClosure;
        ActualCompletion=[pscustomobject]@{ToolChunkId='d29829';ExitCode=0;SessionCompleted=$true}}
    $completion=[pscustomobject]@{Schema='iw7.t7-multisurface-build-completion/1';SourceCommit='0bc0b16aafb2ceb3863f9c20b5f50fb5c8a5f777';Status='PassedOriginalHostExitedIndependentPending';
        NativeInvocationCount=1;Plan=$pins.BuildPlan;Receipt=$pins.BuildReceipt;SourceTrackedClean=$true;InputsReverified=$true;TreeClosureConfirmed=$true;LeaseReleased=$true;
        OriginalHostClosureConfirmed=$true;Quarantined=$false;CandidateExecuted=$false;ExportExecuted=$false;FastfileBuilt=$false;RuntimeVerified=$false;OwnerAccepted=$false;Ready=$false;
        ExitCode=0;LeaseToken=$r.LeaseToken;ActualPTYCompletion=(Copy-Value $actual.ActualCompletion)}
    $absent=@(foreach($role in 'Host','Parent'){$value=Copy-Value $identity.$role;$value|Add-Member NoteProperty Role $role;$value})
    for($i=0;$i -lt 3;$i++){
        $stage=$r.Stages[$i];$stage.PlanSHA256=$p.ExpectedBuildPlanSHA256
        $original=[pscustomobject]@{PID=(10+$i);Image='synthetic/compiler.exe';CreatedUtc='2026-10-13T09:00:01Z'}
        $telemetry=[pscustomobject]@{PID=(20+$i);Image='synthetic/vctip.exe';CreatedUtc='2026-10-13T09:00:02Z'}
        $stage|Add-Member NoteProperty Identity $original
        $stage|Add-Member NoteProperty LastOriginalSnapshot ([pscustomobject]@{ActiveProcesses=0})
        $stage|Add-Member NoteProperty CompilerTelemetry ([pscustomobject]@{Completed=$true;CompilerResult=[pscustomobject]@{BoundInputsVerified=141;ExitCode=0};
            BeforeStopFirst=[pscustomobject]@{Members=@($telemetry)};AfterStopMembers=[pscustomobject]@{ListedCount=0}})
        foreach($pair in @(@('Root',$original),@('Telemetry',$telemetry))){$value=Copy-Value $pair[1];$value|Add-Member NoteProperty Role ($stage.Name+$pair[0]);$absent+=@($value)}
    }
    $witness=[pscustomobject]@{Schema='iw7.t7-build-independent-absence/1';WitnessStatus='Passed';BuildStatus='Passed';SourceCommit=$completion.SourceCommit;
        PlanSHA256=$p.ExpectedBuildPlanSHA256;SourceCleanAndStable=$true;SchedulerAndIndependentCimAgree=$true;ObservedDescendantCount=0;RootProcessCount=0;
        OtherCommandLineRootProcessCount=0;LeaseCount=0;HeavyIncludingVctipCount=0;AbsentExactIdentities=$absent;EvidencePins=@();
        ActualExit=[pscustomobject]@{PTYSessionId=7;Code=0;ToolChunkId='d29829';OwnerThreadCommandStatus='completed';OwnerThreadCommandExitCode=0;ExitInferredFromAbsence=$false}}
    foreach($role in 'BuildReceipt','HostIdentity','OriginalHostClosure','ActualHostExit'){$pin=Copy-Value $pins[$role];$pin|Add-Member NoteProperty Role $role;$witness.EvidencePins+=@($pin)}
    foreach($pair in @(@('Completion',$completion),@('ActualHostExit',$actual),@('OriginalHostClosure',$closure),@('HostIdentity',$identity),@('Witness',$witness))){$script:json[$pins[$pair[0]].Path]=$pair[1]}
    $f|Add-Member NoteProperty Pins $pins;$f
}
function New-ObservationClosureFixture {
    $script:json=@{}
    $p=[pscustomobject]@{Operation='ResidentExportV1';ResidentMultiSurfaceV2=[pscustomobject]@{Schema='iw7.t7-resident-multi-surface/2'};
        SelectedMeshMaterialObservation=[pscustomobject]@{Schema='iw7.t7-selected-mesh-material-probe/1'};
        BuildPlan=(Join-Path $root 'runtime/mesh-material-plan-e2/build-plan.local.json');BuildReceipt=(Join-Path $root 'runtime/mesh-material-build-e2/receipt.json');
        ExpectedBuildPlanSHA256='13318cc0cdd91621c47edaf838a81357f774649a2940fc9df2e85f1351b7223f';
        ExpectedBuildReceiptSHA256='1d54bdceca45ae97ef0875ad745eac79a9214d02927b6f444eb526bdc589a511';
        CandidateBytes=21849600;CandidateSHA256='7c7ad775b201dea60ec050a28e5943cbf1eeeaa8e6386eba675c7ffc001f5e7f';Bindings=@()}
    # Populate invented pins, then use the real bounded-pin validator below.
    $pins=& {function Assert-T7CatalogueTextPin($Pin,$Bindings) {};Get-T7SelectedObservationBuildPins $p}
    foreach($pin in $pins.Values){$p.Bindings+=@(New-Binding $pin)}
    $r=[pscustomobject]@{LeaseToken='synthetic-e2';Stages=@()}
    foreach($name in 'main','zonetool11','link'){
        $r.Stages+=@([pscustomobject]@{Name=$name;Identity=[pscustomobject]@{PID=(30+$r.Stages.Count);Image='synthetic/compiler.exe';CreatedUtc='2026-10-13T19:38:05Z'};
            CompilerTelemetry=[pscustomobject]@{Completed=$true;CompilerResult=[pscustomobject]@{BoundInputsVerified=144}};
            LastOriginalSnapshot=[pscustomobject]@{ActiveProcesses=0}})
    }
    $c=[pscustomobject]@{Schema='iw7.t7-build-e2-completion/1';CompiledAssetCommit='afdd8062732499698a6a810918b8aae082ba3668';
        NativeDependencyCommit='2f9462db806bbd3ab51f9ecb2f3b25ae54ae10f1';UpstreamSourceCommit='fab935826c898806855376662a8a03317b3ad8f1';
        Status='Passed';LeaseToken=$r.LeaseToken;BuildPlan=$pins.BuildPlan;BuildReceipt=$pins.BuildReceipt;InputsReverified=$true;TreeClosureConfirmed=$true;LeaseReleased=$true;
        Quarantined=$false;CandidateExecuted=$false;ArtifactBytesReadOrHashedAfterRelease=$false;FixturePassed=$false;StockSondeExecuted=$false;
        OriginalSessionId=75422;OriginalPTYExitCode=0;Stages=@(foreach($stage in $r.Stages){[pscustomobject]@{Name=$stage.Name;Identity=(Copy-Value $stage.Identity);ExitCode=0;TreeClosureConfirmed=$true}})}
    $h=[pscustomobject]@{Schema='iw7.t7-build-e2-host-closure/1';OriginalSessionId=75422;ActualPTYExit=[pscustomobject]@{ExitCode=0;ChunkId='96d4f3'};
        HostState=[pscustomobject]@{Closed=$true;Lease=$null;Guards=0;Status='Passed'};
        FreshClosureInventory=[pscustomobject]@{LeaseCount=0;OriginalHostsAndStagesAbsent=$true;HeavyAndGameProcessesAbsent=$true}}
    $t=[pscustomobject]@{Schema='iw7.t7-build-e2-original-tool-evidence/1';Records=@(foreach($chunk in '041444','1656ef','96d4f3','8e6728','d1f504'){
        [pscustomobject]@{ToolResult=[pscustomobject]@{chunk_id=$chunk;exit_code=0}}
    })}
    $s=[pscustomobject]@{product='x64-zt-extensions';revisions=[pscustomobject]@{'x64-zt-extensions'=$c.CompiledAssetCommit;'iw7-mod-components'=$c.NativeDependencyCommit}}
    $bundle=[pscustomobject]@{Schema='iw7.t7-build-e2-closure-bundle/1';Files=@($pins.Completion,$pins.HostClosure,$pins.ToolEvidence)}
    foreach($pair in @(@('Completion',$c),@('HostClosure',$h),@('ToolEvidence',$t),@('SourceReceipt',$s),@('Bundle',$bundle))){$script:json[$pins[$pair[0]].Path]=$pair[1]}
    [pscustomobject]@{Plan=$p;Receipt=$r;Pins=$pins;Completion=$c;Host=$h;Tools=$t;Source=$s;Bundle=$bundle}
}
try {
    $e=New-ObservationClosureFixture
    $qualifiedPins=Get-T7ResidentMultiSurfaceBuildPins $e.Plan
    Check ($qualifiedPins.BuildPlan.SHA256 -ceq $e.Plan.ExpectedBuildPlanSHA256 -and !$qualifiedPins.Contains('Witness')) 'E2 pins became D pins.'
    Assert-T7SelectedObservationClosure $e.Plan $e.Receipt $e.Pins;$checks++
    foreach($mutation in 'schema','v1','mixed','extra-marker','candidate','asset-source','native-source','upstream-source','lease','guard','exit','chunk','missing-tool','duplicate-tool','executed','fixture-overclaim','stock-overclaim','bundle','stage','stage-pid','stage-date','telemetry','bound-inputs','live-child'){
        $e=New-ObservationClosureFixture
        switch($mutation){
            schema {$e.Plan.SelectedMeshMaterialObservation.Schema='other'}
            v1 {$e.Plan.PSObject.Properties.Remove('ResidentMultiSurfaceV2')}
            mixed {$e.Plan|Add-Member NoteProperty ResidentSurfaceCountDiagnostic $null}
            extra-marker {$e.Plan.SelectedMeshMaterialObservation|Add-Member NoteProperty Ready $true}
            candidate {$e.Plan.CandidateSHA256='0'*64}
            asset-source {$e.Completion.CompiledAssetCommit='0'*40}
            native-source {$e.Source.revisions.'iw7-mod-components'='0'*40}
            upstream-source {$e.Completion.UpstreamSourceCommit='0'*40}
            lease {$e.Host.HostState.Lease='retained'}
            guard {$e.Host.HostState.Guards=1}
            exit {$e.Host.ActualPTYExit.ExitCode=1}
            chunk {$e.Host.ActualPTYExit.ChunkId='different'}
            missing-tool {$e.Tools.Records=$e.Tools.Records[0..3]}
            duplicate-tool {$e.Tools.Records+=@($e.Tools.Records[0])}
            executed {$e.Completion.CandidateExecuted=$true}
            fixture-overclaim {$e.Completion.FixturePassed=$true}
            stock-overclaim {$e.Completion.StockSondeExecuted=$true}
            bundle {$e.Bundle.Files=$e.Bundle.Files[0..1]}
            stage {$e.Completion.Stages[0].ExitCode=1}
            stage-pid {$e.Completion.Stages[0].Identity.PID++}
            stage-date {$e.Completion.Stages[0].Identity.CreatedUtc='2026-10-13T19:38:06Z'}
            telemetry {$e.Receipt.Stages[0].CompilerTelemetry.Completed=$false}
            bound-inputs {$e.Receipt.Stages[0].CompilerTelemetry.CompilerResult.BoundInputsVerified=141}
            live-child {$e.Receipt.Stages[0].LastOriginalSnapshot.ActiveProcesses=1}
        }
        Refuses {$null=Get-T7ResidentMultiSurfaceBuildPins $e.Plan;Assert-T7SelectedObservationClosure $e.Plan $e.Receipt $e.Pins} 'required|differ|source|closure|contract|mixed|fields|scope|host exit|tool completion|bundle|creation'
    }
    $f=New-V2BuildFixture;Assert-T7CatalogueBuild $f.Plan $f.Receipt;$checks++
    foreach($name in $f.Pins.Keys){
        foreach($change in 'missing','hash','bytes','binary','duplicate'){
            $f=New-V2BuildFixture;$path=$f.Pins[$name].Path;$binding=@($f.Plan.Bindings|Where-Object Path -CEQ $path)[0]
            switch($change){missing{$f.Plan.Bindings=@($f.Plan.Bindings|Where-Object Path -CNE $path)} hash{$binding.SHA256='0'*64} bytes{$binding.Bytes++} binary{$binding.IsText=$false} duplicate{$f.Plan.Bindings+=@($binding)}}
            Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'guarded|pin differs|witness binding'
        }
    }
    foreach($mode in 'plan-marker','build-marker','mixed','status','inputs','tree','lease','quarantine','executed','candidate','duplicate-exe','binding-count','input-count','header-input','header-mutant-all','source-transition','old-header','retained-dep','missing-include','duplicate-include','excluded-pch'){
        $f=New-V2BuildFixture;$p=$f.Plan;$b=$f.Build;$r=$f.Receipt;$proof=$b.ReuseCompile.ResidentMultiSurfaceV2
        switch($mode){
            plan-marker{$p.PSObject.Properties.Remove('ResidentMultiSurfaceV2')}
            build-marker{$b.ReuseCompile.PSObject.Properties.Remove('ResidentMultiSurfaceV2')}
            mixed{$p|Add-Member NoteProperty ResidentSurfaceCountDiagnostic $null}
            status{$r.Status='Failed'} inputs{$r.InputsReverified=$false} tree{$r.TreeClosureConfirmed=$false} lease{$r.LeaseReleased=$false}
            quarantine{$r.Quarantined=$true} executed{$r.CandidateExecuted=$true} candidate{$p.CandidateSHA256='1'*64}
            duplicate-exe{$r.Stages[2].Artifacts+=@($r.Stages[2].Artifacts[0])}
            binding-count{$b.Bindings=$b.Bindings[0..139]} input-count{$b.Inputs=$b.Inputs[0..1144]}
            header-input{$b.Inputs[0].SHA256='1'*64}
            header-mutant-all{$pin=$proof.AdditionalHeaderInputs.Inputs[0];$pin.SHA256='1'*64;($b.Bindings|Where-Object Path -CEQ $pin.Path).SHA256=$pin.SHA256;($b.Inputs|Where-Object Path -CEQ $pin.Path).SHA256=$pin.SHA256}
            source-transition{$proof.SourceTransitions[0].PreviousBytes++}
            old-header{$proof.SHA256='97a417b82ab7edf002f73039d1280b5e2a34370594e151ff07698db3a81f65ed'}
            retained-dep{$proof.DependencyJSON[0].Bytes++}
            missing-include{$script:json[$r.Stages[1].Artifacts[-1].Path].Data.Includes=$proof.AdditionalHeaderInputs.Inputs.Path}
            duplicate-include{$script:json[$r.Stages[1].Artifacts[-1].Path].Data.Includes+=@($proof.AdditionalHeaderInputs.Inputs[0].Path)}
            excluded-pch{$script:json[$r.Stages[1].Artifacts[-1].Path].Data.Includes+=@($proof.AdditionalHeaderInputs.PCHExcludedForPreparedYMinus)}
        }
        Refuses {Assert-T7CatalogueBuild $p $r} 'required|differ|guarded|mixed|Duplicate|must include'
    }
    foreach($index in 0..2){
        foreach($mode in 'exit','crossed-plan','live','unclosed','inputs'){
            $f=New-V2BuildFixture;$s=$f.Receipt.Stages[$index]
            switch($mode){exit{$s.ExitCode=1} crossed-plan{$s.PlanSHA256='1'*64} live{$s.LastOriginalSnapshot.ActiveProcesses=1} unclosed{$s.TreeClosureConfirmed=$false} inputs{$s.CompilerTelemetry.CompilerResult.BoundInputsVerified=140}}
            Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'successful and closed|compiler and telemetry'
        }
    }
    foreach($mode in 'private-upstream','completion-pin','witness-pin','witness-other-plan','witness-pending','witness-missing-host','witness-wrong-time','witness-reused-pid','host-live','owner-failed','guards','lease-token','can-exit','pty-live','pty-failed','actual-missing','inferred-exit','descendants','false-as-string'){
        $f=New-V2BuildFixture;$pins=$f.Pins;$c=$script:json[$pins.Completion.Path];$w=$script:json[$pins.Witness.Path];$h=$script:json[$pins.OriginalHostClosure.Path];$a=$script:json[$pins.ActualHostExit.Path]
        switch($mode){
            private-upstream{$c.SourceCommit='fab935826c898806855376662a8a03317b3ad8f1'} completion-pin{$c.Plan=Copy-Value $c.Plan;$c.Plan.SHA256='1'*64}
            witness-pin{$w.EvidencePins[0].SHA256='1'*64} witness-other-plan{$w.PlanSHA256='1'*64} witness-pending{$w.WitnessStatus='Pending'}
            witness-missing-host{$w.AbsentExactIdentities=$w.AbsentExactIdentities[1..7]} witness-wrong-time{$w.AbsentExactIdentities[0].CreatedUtc='2026-10-13T10:00:00Z'}
            witness-reused-pid{$w.AbsentExactIdentities[2].Image='other.exe'} host-live{$h.Closed=$false} owner-failed{$h.NativeOwnerExitCode=1}
            guards{$h.GuardCount=1} lease-token{$c.LeaseToken='other'} can-exit{$h.CanExit=$false} pty-live{$a.ActualCompletion.SessionCompleted=$false}
            pty-failed{$a.ActualCompletion.ExitCode=1} actual-missing{$w.ActualExit.OwnerThreadCommandStatus='running'} inferred-exit{$w.ActualExit.ExitInferredFromAbsence=$true}
            descendants{$w.ObservedDescendantCount=1} false-as-string{$c.CandidateExecuted='false'}
        }
        Refuses {Assert-T7CatalogueBuild $f.Plan $f.Receipt} 'closure|witness|host exit|PTY|identities'
    }
    # Candidate-only transition: v2 keeps all 26 noncandidate metadata rows.
    $base=[pscustomobject]@{CandidateSource='old';CandidateBytes=1;InputMetadata=@([pscustomobject]@{Path='old';Bytes=1})}
    $base.InputMetadata+=@(1..26|ForEach-Object {[pscustomobject]@{Path=('stock-'+$_);Bytes=$_;LastWriteUtc='2026-10-01T00:00:00Z'}})
    $p=[pscustomobject]@{CandidateSource='new';CandidateBytes=2;InputMetadata=(Copy-Value $base.InputMetadata)}
    $p.InputMetadata[0]=[pscustomobject]@{Path='new';Bytes=2};Assert-T7ResidentExportDiagnosticMetadata $p $base;$checks++
    foreach($i in 1..26){$bad=Copy-Value $p;$bad.InputMetadata[$i].Bytes++;Refuses {Assert-T7ResidentExportDiagnosticMetadata $bad $base} 'noncandidate'}
    [ordered]@{Status='Passed';Checks=$checks;Evidence='Synthetic metadata and text';BinaryRead=$false;OperationalPlanCreated=$false;NativeRun=$false}|ConvertTo-Json
}finally{
    $full=[IO.Path]::GetFullPath($root);$temp=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if(!$full.StartsWith($temp,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($full) -cnotmatch '^t7-v2-build-tests-[0-9a-f]{32}$'){throw 'Refuse cleanup outside synthetic v2 build root.'}
    Remove-Item -LiteralPath $full -Recurse -Force
}
if($ReviewedBuildPlanPath -or $IndependentWitnessPath){
    if(!$ReviewedBuildPlanPath -or !$IndependentWitnessPath){throw 'Both reviewed text paths are required.'}
    # Restore the ordinary bounded reader after the synthetic fixture stub.
    . (Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1')
    $context=[pscustomobject]@{Guards=[Collections.Generic.List[object]]::new()};$textBytes=0L
    function Hold-ReviewedText($Pin){
        if([IO.Path]::GetExtension($Pin.Path) -cnotin @('.json','.cpp','.hpp','.py','.inc','.rsp')){throw 'Reviewed mode accepts only explicit small source/JSON/response text.'}
        $script:textBytes+=$Pin.Bytes;if($script:textBytes -gt 8MB){throw 'Reviewed text budget exceeded.'}
        $item=Get-Item -LiteralPath $Pin.Path
        if($item.Length -ne $Pin.Bytes -or $item.Length -gt 1MB){throw 'Reviewed text bound differs.'}
        $stream=[IO.File]::Open($Pin.Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
        $context.Guards.Add($stream)
        if([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($stream)).ToLowerInvariant() -cne $Pin.SHA256){throw 'Reviewed text digest differs.'}
    }
    try{
        $buildPin=[pscustomobject]@{Path=$ReviewedBuildPlanPath;Bytes=365638;SHA256='551a4017b334d573e5873dfda3e6134968549db08e0aabacbc269ad4a398488a'}
        Hold-ReviewedText $buildPin;$build=Read-H1SmallJson $buildPin.Path 1MB
        $receiptPin=[pscustomobject]@{Path=(Join-Path $build.RunRoot 'receipt.json');Bytes=22380;SHA256='25d2593dbb412ac676f5e11f1b4d8ae34f26623217159ddb36dfc3f42d96ce0b'}
        Hold-ReviewedText $receiptPin;$receipt=Read-H1SmallJson $receiptPin.Path 128KB
        $candidate=@($receipt.Stages[2].Artifacts|Where-Object Path -CEQ (Join-Path $build.RunRoot 'link/zonetool-t7.exe'))[0]
        # This partial read-only context has no runtime/export paths, budgets or arguments.
        $review=[pscustomobject]@{Operation='ResidentExportV1';ResidentMultiSurfaceV2=[pscustomobject]@{Schema='iw7.t7-resident-multi-surface/2'};
            CandidateProfile='t7-catalog-message-publication';BuildPlan=$buildPin.Path;ExpectedBuildPlanSHA256=$buildPin.SHA256;
            BuildReceipt=$receiptPin.Path;ExpectedBuildReceiptSHA256=$receiptPin.SHA256;CandidateSource=$candidate.Path;CandidateBytes=$candidate.Bytes;CandidateSHA256=$candidate.SHA256;
            Bindings=@((New-Binding $buildPin),(New-Binding $receiptPin))}
        foreach($name in 'Wiring','PreparedMain','BaseBuildPlan','BaseBuildReceipt','PublicationWiring','PublicationSource','PreparedCLI','MainResponse','CLIResponse','LinkResponse'){
            $review.Bindings+=@(New-Binding $build.BuildProfile.$name)
        }
        foreach($stage in $receipt.Stages[0..1]){$review.Bindings+=@(New-Binding @($stage.Artifacts|Where-Object { $_.Path.EndsWith('\dependencies.json',[StringComparison]::Ordinal) })[0])}
        $review.Bindings+=@(New-Binding ([pscustomobject]@{Path=(Join-Path $build.PreparedRoot 't7_iw7_resident_model.hpp');Bytes=21290;SHA256='857d57b5f3c1c970f45e513e357215f3506e9c48b2daea4b4f62cb33e0d9bce4'}))
        Add-DClosureBindings $review $IndependentWitnessPath
        foreach($binding in $review.Bindings|Select-Object -Skip 2){Hold-ReviewedText $binding}
        Assert-T7CatalogueBuild $review $receipt
        [ordered]@{Status='Passed';Evidence='Exact reviewed D texts and original admitted artifact tuples';GuardedTextBytes=$textBytes;
            BuildPlanSHA256=$buildPin.SHA256;BuildReceiptSHA256=$receiptPin.SHA256;BinaryRead=$false;OperationalPlanCreated=$false;NativeRun=$false}|ConvertTo-Json
    }finally{foreach($guard in $context.Guards){$guard.Dispose()}}
}
