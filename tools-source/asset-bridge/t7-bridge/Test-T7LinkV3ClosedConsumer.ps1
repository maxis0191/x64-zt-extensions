# Authored CPP/index objects and actual early source-only guard; no opaque IO.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
. (Join-Path $repo 'tools-source/asset-bridge/h1-fixture/H1Native.Core.ps1')
. (Join-Path $PSScriptRoot 'T7PrepatchReferenceV2.Profile.ps1')
$script:checks=0
function Check([bool]$Value,[string]$Why){if(!$Value){throw $Why};$script:checks++}
function Refuses([scriptblock]$Body){$caught=$false;try{& $Body}catch{$caught=$true};Check $caught 'Invalid closed cohort accepted'}
function Clone($Value){$text=$Value|ConvertTo-Json -Depth 25;if((Get-Command ConvertFrom-Json).Parameters.ContainsKey('DateKind')){return ($text|ConvertFrom-Json -Depth 25 -DateKind String)};$text|ConvertFrom-Json -Depth 25}
$root=Join-Path ([IO.Path]::GetTempPath()) 't7-link-v3-authored-closed'
$tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Test-T7LinkV3Consumer.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Fixture source parse failed'}
$fixtureFunction=@($ast.FindAll({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq 'New-BuildFixture'},$true))[0]
. ([scriptblock]::Create($fixtureFunction.Extent.Text))
function New-ClosedFixture {
    $f=New-BuildFixture;$cohort=Get-T7ReferenceBuildCohort 't7-prepatch-link-v3'
    foreach($row in @(@('ExpectedBuildPlanSHA256',$cohort.PlanSHA256),@('CandidateSource',(Join-Path $root 'candidate.exe')), @('CandidateBytes',$cohort.CandidateBytes),
        @('CandidateSHA256',$cohort.CandidateSHA256),@('BuildReceipt',(Join-Path $root 'receipt.json')),@('ExpectedBuildReceiptSHA256',$cohort.ReceiptSHA256),@('BuildClosedPins',(Join-Path $root 'index.json')))){
        $f.Plan|Add-Member NoteProperty $row[0] $row[1]
    }
    $proof=[pscustomobject]@{Path=(Join-Path $root 'proof.json');Bytes=8907;SHA256='5a282c19995af210fd9d7c55a8692d87d4456526352fe21034a8f07d83a9fd9d'}
    $f.Build|Add-Member NoteProperty OSResourceContext ([pscustomobject]@{Evidence=$proof})
    $f.Plan.Bindings+=@([pscustomobject]@{Path=$proof.Path;Bytes=$proof.Bytes;SHA256=$proof.SHA256;IsText=$true},[pscustomobject]@{Path=$f.Plan.CandidateSource;Bytes=$cohort.CandidateBytes;SHA256=$cohort.CandidateSHA256;IsText=$false})
    $rows=[ordered]@{}
    foreach($row in @(
        @('Entry','entry.json',1149,'b67d612051d16866afeae8c895f0b19b7a17d4ea7e9a3cd7672718c96d851900'),
        @('Completion','completion.json',649,'5c8f6232d026284337d3b13f253e2fc743c63b0dbd2c3cf61721ef5d235c8c0e'),
        @('ToolExit','actual-pty-exit.local.json',215,'d7b07a7378c933ea87f66f5077cf9b6a272c166b17ab51cd4c51afa7a6b8a711'),
        @('Inventory','cpp-independent-closure.local.json',1207,'6066a2d8ca8f999e23eb1ce7b26167a5a4a8efd43be8915388ba019bf6be439c'),
        @('Build','receipt.json',17200,'0cc0c8b6b46fd75d09c53b3e3c3dc9af40aa4211a786629fcf2f791c52111328'),
        @('Bundle','closed-output-bundle.local.json',1987,'b692b0dc59462003ad046849ce91b764b02ed82be3e4c25cc043bb44cada69bc'))){
        $pin=[pscustomobject]@{Path=(Join-Path $root $row[1]);Bytes=$row[2];SHA256=$row[3]};$rows[$row[0]]=$pin
        $f.Plan.Bindings+=[pscustomobject]@{Path=$pin.Path;Bytes=$pin.Bytes;SHA256=$pin.SHA256;IsText=$true}
    }
    $index=[pscustomobject]@{Schema='iw7.t7-prepatch-link-v3-closed-pins/3';SourceRevision='a8ecff7cb61323cd0e6f75d10e596d55e63a7753';PlanSHA256=$cohort.PlanSHA256;
        Rows=[pscustomobject]$rows;ArtifactPinsAreOriginalLeaseObservations=$true;ActualPTYCompleted=$true;IndependentAbsenceObserved=$true;OpaqueInputsReadAfterRelease=$false;CandidateExecuted=$false;Ready=$false}
    $receipt=[pscustomobject]@{Schema='iw7.t7-minimal-build/1';Status='Passed';PlanSHA256=$cohort.PlanSHA256;BuildProfile=$f.Build.BuildProfile;
        InputsReverified=$true;TreeClosureConfirmed=$true;LeaseReleased=$true;Quarantined=$false;CandidateExecuted=$false;Ready=$false;
        Stages=@(for($i=0;$i -lt 2;$i++){[pscustomobject]@{Name=@('main','link')[$i];ExitCode=0;TreeClosureConfirmed=$true;
            CompilerTelemetry=[pscustomobject]@{Completed=$true;AfterStop=[pscustomobject]@{RootExited=$true;RootExitCode=0;ActiveProcesses=0};AfterStopMembers=[pscustomobject]@{AssignedCount=0;ListedCount=0;Members=@()}};
            Artifacts=$(if($i){@([pscustomobject]@{Path=$f.Plan.CandidateSource;Bytes=$cohort.CandidateBytes;SHA256=$cohort.CandidateSHA256})}else{@()})}})}
    $f|Add-Member NoteProperty Receipt $receipt;$f|Add-Member NoteProperty Index $index;$f
}
$f=New-ClosedFixture;Assert-T7ReferenceCandidate $f.Plan 't7-prepatch-link-v3';Assert-T7RefV2Build $f.Plan $f.Build $f.Receipt 't7-prepatch-link-v3';Assert-T7LinkV3ClosedBuildPins $f.Plan $f.Index;$checks+=3
foreach($field in 'CandidateSHA256','ExpectedBuildPlanSHA256','ExpectedBuildReceiptSHA256'){$f=New-ClosedFixture;$f.Plan.$field='f'*64;Refuses {Assert-T7ReferenceCandidate $f.Plan 't7-prepatch-link-v3'}}
$f=New-ClosedFixture;Refuses {Assert-T7ReferenceCandidate $f.Plan 't7-prepatch-reference-v2'}
foreach($field in 'InputsReverified','TreeClosureConfirmed','LeaseReleased','Quarantined','CandidateExecuted','Ready'){
    $f=New-ClosedFixture;$f.Receipt.$field=!$f.Receipt.$field;Refuses {Assert-T7RefV2Build $f.Plan $f.Build $f.Receipt 't7-prepatch-link-v3'}
    $f=New-ClosedFixture;$f.Receipt.$field=@($f.Receipt.$field);Refuses {Assert-T7RefV2Build $f.Plan $f.Build $f.Receipt 't7-prepatch-link-v3'}
}
foreach($field in 'RootExited','RootExitCode','ActiveProcesses'){$f=New-ClosedFixture;$f.Receipt.Stages[0].CompilerTelemetry.AfterStop.$field=$(if($field -ceq 'RootExited'){$false}else{1});Refuses {Assert-T7RefV2Build $f.Plan $f.Build $f.Receipt 't7-prepatch-link-v3'}}
foreach($field in 'ArtifactPinsAreOriginalLeaseObservations','ActualPTYCompleted','IndependentAbsenceObserved','OpaqueInputsReadAfterRelease','CandidateExecuted','Ready'){$f=New-ClosedFixture;$f.Index.$field=!$f.Index.$field;Refuses {Assert-T7LinkV3ClosedBuildPins $f.Plan $f.Index}}
foreach($role in 'Entry','Completion','ToolExit','Inventory','Build','Bundle'){$f=New-ClosedFixture;$f.Index.Rows.$role.SHA256='f'*64;Refuses {Assert-T7LinkV3ClosedBuildPins $f.Plan $f.Index}}
$f=New-ClosedFixture;$f.Index.Rows.Inventory.Bytes=@(1207);Refuses {Assert-T7LinkV3ClosedBuildPins $f.Plan $f.Index}
$f=New-ClosedFixture;$f.Receipt.Stages[1].Artifacts[0].SHA256='f'*64;Refuses {Assert-T7RefV2Build $f.Plan $f.Build $f.Receipt 't7-prepatch-link-v3'}
$runner=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Run-T7PrepatchReferenceV2.ps1') -Raw
$conflict=[regex]::Match($runner,'(?m)^if\(\$SourceOnly -and \$Run\).*').Value
Check ([bool]$conflict) 'Actual early source-only guard missing'
$SourceOnly=$true;$Run=$true;Refuses {& ([scriptblock]::Create($conflict))}
Check ($runner.IndexOf('if(!$Run)') -lt $runner.IndexOf('Enter-IW7ResourceLease')) 'DEFAULT precedes admission'
[ordered]@{Schema='iw7.t7-link-v3-closed-consumer-source-tests/3';Checks=$checks;Status='Passed';NativeExecuted=$false;LeaseAcquired=$false;OpaqueInputsRead=$false}|ConvertTo-Json
