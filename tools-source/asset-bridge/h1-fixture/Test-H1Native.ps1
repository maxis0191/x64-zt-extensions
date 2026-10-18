# Light mocked lifecycle checks: no native types, leases, compiler or probe.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$sourceTokens=$null;$sourceErrors=$null
$sourceTree=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'H1Native.Core.ps1'),[ref]$sourceTokens,[ref]$sourceErrors)
if($sourceErrors.Count){throw 'Core Source AST parse failed'}
foreach($sourceName in 'Assert-H1Path','Open-H1Pin','Read-H1SmallJson','Assert-H1OutputName','New-H1AuthoredOutputBudget',
    'Assert-H1AuthoredOutputBudget','Measure-H1AuthoredOutput','Measure-H1Output','Get-H1Clock','Assert-H1Deadline',
    'Test-H1Budget','Invoke-H1OwnedStage','Complete-H1Stage','Assert-H1ReceiptBytes','Write-H1Receipt'){
    $sourceDefinition=$sourceTree.Find({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $sourceName},$true)
    . ([scriptblock]::Create($sourceDefinition.Extent.Text))
}
$reviewedBudget=${function:Test-H1Budget}
$passed=0
function Check([bool]$Value,[string]$Message){if(!$Value){throw $Message};$script:passed++}
function Refuses([scriptblock]$Action,[string]$Message){$failed=$false;try{& $Action|Out-Null}catch{$failed=$true};Check $failed $Message}
function New-FakeOwner([bool]$Empty=$true,[bool]$StopFails=$false,[int]$ExitCode=0) {
    $item=[pscustomobject]@{Empty=$Empty;StopFails=$StopFails;Closed=$false;ExitCode=$ExitCode;
        PID=123;Image='C:\fixture.exe';CreationFileTime=[datetime]::UtcNow.ToFileTimeUtc();Starts=0;Stops=0;StartFails=$false}
    $item|Add-Member ScriptMethod Start {param($a,$b,$c,$d) $this.Starts++;if($this.StartFails){throw 'Partial start failure'}}
    $item|Add-Member ScriptMethod TreeExited {return $this.Empty}
    $item|Add-Member ScriptMethod CloseConfirmed {if(!$this.Empty){throw 'not empty'};$this.Closed=$true}
    $item|Add-Member ScriptMethod StopAndConfirm {param($timeout) $this.Stops++;if($this.StopFails){throw 'unknown closure'};$this.Empty=$true;$this.Closed=$true}
    $item
}
function New-Case {
    $script:events=[Collections.Generic.List[string]]::new()
    $script:clock=0;$script:registrationFails=$false;$script:telemetryDelay=0;$script:releaseFails=$false;$script:factoryFails=$false
    [pscustomobject]@{Owner=$null;Closed=$true;Lease=[pscustomobject]@{Token=[guid]::NewGuid().ToString('N')};Guards=@()}
}
function New-State($Context) {
    [ordered]@{Status='Pending';Stage='Probe';DeadlineSeconds=15;LeaseToken=$Context.Lease.Token;LeaseReleased=$false;
        Quarantined=$false;TreeClosureConfirmed=$true;MaxObservedOutputBytes=0L}
}
function New-H1Owner {if($script:factoryFails){throw 'Factory failed'};$script:fake}
function Get-H1Clock {$script:clock}
function Register-H1Original($Lease,$Identity){$script:events.Add('register');if($script:registrationFails){throw 'CIM absent'}}
function Test-H1Budget($Plan,$State){$script:clock+=$script:telemetryDelay}
function Exit-IW7ResourceLease($Token){$script:events.Add('release');if($script:releaseFails){throw 'release refused'}}
$start=[pscustomobject]@{FileName='C:\fixture.exe'}
$context=New-Case;$state=New-State $context;$script:fake=New-FakeOwner
Invoke-H1OwnedStage $null $state $context $start ('a'*64) 'C:\unused'
Complete-H1Stage $context $state
Check ($state.TreeClosureConfirmed -and $state.LeaseReleased -and $script:fake.Stops -eq 0) 'Normal original-tree closure/release failed.'
Check (($script:events -join ',') -ceq 'register,release') 'Stage registration/release ordering differs.'

$context=New-Case;$state=New-State $context;$script:fake=New-FakeOwner
Refuses {Invoke-H1OwnedStage $null $state $context $start ('a'*64) 'C:\unused' -15000} 'Expired admitted setup budget must prevent process creation.'
Check ($script:fake.Starts -eq 0 -and $context.Closed) 'Setup consumed the deadline but still launched a native child.'

$context=New-Case;$state=New-State $context;$script:fake=New-FakeOwner;$script:registrationFails=$true
Invoke-H1OwnedStage $null $state $context $start ('a'*64) 'C:\unused'
Complete-H1Stage $context $state
Check ($state.Registration -like 'Original job already empty*' -and $state.LeaseReleased) 'Fast exit must use original empty-job evidence.'

$context=New-Case;$state=New-State $context;$script:fake=New-FakeOwner $false;$script:registrationFails=$true
Refuses {Invoke-H1OwnedStage $null $state $context $start ('a'*64) 'C:\unused'} 'Live child with unavailable identity must fail.'
Complete-H1Stage $context $state
Check ($script:fake.Stops -eq 1 -and $state.TreeClosureConfirmed -and $state.LeaseReleased) 'Failure cleanup must stop/confirm original job before release.'

$context=New-Case;$state=New-State $context;$script:fake=New-FakeOwner;$script:telemetryDelay=15001
Refuses {Invoke-H1OwnedStage $null $state $context $start ('a'*64) 'C:\unused'} 'Slow telemetry must not allow late success.'
Complete-H1Stage $context $state
Check $state.LeaseReleased 'Deadline failure cleanup did not release a closed job.'

$context=New-Case;$state=New-State $context;$script:fake=New-FakeOwner $false $true;$script:registrationFails=$true
Refuses {Invoke-H1OwnedStage $null $state $context $start ('a'*64) 'C:\unused'} 'Unknown closure setup failed.'
Complete-H1Stage $context $state
Check ($state.Quarantined -and !$state.LeaseReleased -and $context.Lease -and !($script:events.Contains('release'))) 'Unconfirmed closure released a lease.'
[AppDomain]::CurrentDomain.SetData(('IW7.H1.Quarantine.'+$state.LeaseToken),$null)

$context=New-Case;$state=New-State $context;$script:factoryFails=$true
Refuses {Invoke-H1OwnedStage $null $state $context $start ('a'*64) 'C:\unused'} 'Throwing factory must fail the stage.'
Complete-H1Stage $context $state
Check ($state.Quarantined -and !$state.LeaseReleased) 'A failed owner factory must not prove closure.'
[AppDomain]::CurrentDomain.SetData(('IW7.H1.Quarantine.'+$state.LeaseToken),$null)

$context=New-Case;$state=New-State $context;$script:fake=New-FakeOwner $false;$script:fake.StartFails=$true
Refuses {Invoke-H1OwnedStage $null $state $context $start ('a'*64) 'C:\unused'} 'Partial native start must fail.'
Complete-H1Stage $context $state
Check ($script:fake.Stops -eq 1 -and $state.LeaseReleased) 'Owner was lost across a partial start exception.'

$context=New-Case;$state=New-State $context;$script:fake=New-FakeOwner $true $false 7
Refuses {Invoke-H1OwnedStage $null $state $context $start ('a'*64) 'C:\unused'} 'Nonzero native exit must fail.'
Complete-H1Stage $context $state
Check ($state.ExitCode -eq 7 -and $state.LeaseReleased) 'Nonzero exit must retain exit evidence after cleanup.'

$context=New-Case;$state=New-State $context;$script:fake=New-FakeOwner;$script:releaseFails=$true
Invoke-H1OwnedStage $null $state $context $start ('a'*64) 'C:\unused'
Complete-H1Stage $context $state
Check ($state.Quarantined -and $state.TreeClosureConfirmed -and !$state.LeaseReleased) 'Scheduler release refusal must quarantine admission.'
[AppDomain]::CurrentDomain.SetData(('IW7.H1.Quarantine.'+$state.LeaseToken),$null)

$temp=Join-Path ([IO.Path]::GetTempPath()) ('iw7-h1-source-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($temp)|Out-Null
$path=Join-Path $temp 'bound.txt'
try {
    [IO.File]::WriteAllText($path,'original')
    $pin=[pscustomobject]@{Path=$path;Bytes=8;SHA256=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()}
    $guard=Open-H1Pin $pin
    try{Refuses {[IO.File]::WriteAllText($path,'mutated!')} 'An open input guard must deny writing.'}finally{$guard.Dispose()}
    [IO.File]::WriteAllText($path,'mutated!')
    Refuses {Open-H1Pin $pin} 'Same-length changed source must fail binding.'
    [IO.File]::WriteAllText($path,('x'*130))
    Refuses {Read-H1SmallJson $path 128} 'JSON size bound failed.'
    $budgetPlan=[pscustomobject]@{RunRoot=$temp;OutputLimitBytes=16KB;MetadataReserveBytes=1KB}
    $script:memoryReads=0;$script:memoryFails=$false
    function Get-IW7ResourceSnapshot {
        $script:memoryReads++
        if($script:memoryFails){throw 'Synthetic native memory provider failed.'}
        $script:memorySnapshot
    }
    foreach($percent in @(84.99,85,85.01,99,100)){
        $script:memorySnapshot=[pscustomobject]@{CommitLimit=1000000L;Committed=[long]($percent*10000);
            CapturedUtc=[datetime]::UtcNow.ToString('o');Source='synthetic-no-allocation'}
        foreach($budgetState in @([ordered]@{MaxObservedOutputBytes=0L},[pscustomobject]@{MaxObservedOutputBytes=0L})){
            & $reviewedBudget $budgetPlan $budgetState
            Check ($budgetState.LastMemoryObservation.Policy -ceq 'TelemetryOnly' -and
                $budgetState.LastMemoryObservation.CommitUsedPercent -eq $percent) 'Near/high commit percentage refused or lost telemetry.'
            Check ($budgetState.MaxObservedOutputBytes -eq 130) 'Memory policy change must preserve actual output accounting.'
        }
    }
    Check ($script:memoryReads -eq 10) 'Every budget observation must read fresh native telemetry.'
    $budgetState=[ordered]@{MaxObservedOutputBytes=0L}
    $script:memorySnapshot=[pscustomobject]@{CommitLimit=1000000L;Committed=850100L}
    & $reviewedBudget $budgetPlan $budgetState
    $script:memorySnapshot=[pscustomobject]@{CommitLimit=1000000L;Committed=990000L}
    & $reviewedBudget $budgetPlan $budgetState
    Check ($budgetState.LastMemoryObservation.CommitUsedPercent -eq 99 -and
        @($budgetState.Keys | Where-Object {$_ -eq 'LastMemoryObservation'}).Count -eq 1) 'Fresh observations must replace one bounded record.'
    foreach($invalid in @($null,[pscustomobject]@{CommitLimit=0;Committed=0},
        [pscustomobject]@{CommitLimit=100;Committed=-1},[pscustomobject]@{CommitLimit=100;Committed=101})){
        $script:memorySnapshot=$invalid
        Refuses {& $reviewedBudget $budgetPlan $budgetState} 'Missing/impossible telemetry must still fail.'
    }
    $script:memoryFails=$true
    Refuses {& $reviewedBudget $budgetPlan $budgetState} 'A native memory provider exception must still fail.'
    $script:memoryFails=$false
    $script:memorySnapshot=[pscustomobject]@{CommitLimit=1000000L;Committed=990000L}
    # Exercise the actual budget observer together with synthetic original-job
    # OOM failure/cleanup. No native process or pressure allocation is induced.
    $lifecycleBudget=${function:Test-H1Budget}
    try {
        ${function:Test-H1Budget}=$reviewedBudget
        $context=New-Case;$state=New-State $context;$script:fake=New-FakeOwner $true $false -1073741801
        Refuses {Invoke-H1OwnedStage $budgetPlan $state $context $start ('a'*64) 'C:\unused'} 'An out-of-memory exit must not be converted to success.'
        Complete-H1Stage $context $state
        Check ($state.ExitCode -eq -1073741801 -and $state.LeaseReleased -and
            $state.LastMemoryObservation.CommitUsedPercent -eq 99) 'OOM failure/confirmed teardown must survive telemetry-only memory.'
    }finally{${function:Test-H1Budget}=$lifecycleBudget}
    $overOutputPlan=[pscustomobject]@{RunRoot=$temp;OutputLimitBytes=130;MetadataReserveBytes=1}
    Refuses {& $reviewedBudget $overOutputPlan $budgetState} 'Output cap must still fail even with telemetry-only memory.'
    $outputPlan=[pscustomobject]@{RunRoot=$temp;OutputLimitBytes=132;MetadataReserveBytes=128}
    Refuses {Write-H1Receipt $outputPlan ([ordered]@{Status='Passed'}) $temp} 'Final receipt must count its own bytes.'
    Check (!(Test-Path -LiteralPath (Join-Path $temp 'receipt.json'))) 'Oversized success receipt was published.'
    $publishPlan=[pscustomobject]@{RunRoot=$temp;OutputLimitBytes=1MB;MetadataReserveBytes=64KB}
    $publication=Write-H1Receipt $publishPlan ([ordered]@{Status='MockReleasePending';LeaseReleased=$false}) $temp -Name 'verified.json' -PassThru
    $expected=[IO.File]::ReadAllBytes($publication.Path)
    Check ($publication.Bytes -eq $expected.Length -and $publication.SHA256 -ceq ([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($expected))).ToLowerInvariant()) 'Flushed/read-back receipt hash differs.'
    [IO.File]::WriteAllText($publication.Path,'changed')
    Refuses {Assert-H1ReceiptBytes $publication.Path $expected} 'Changed receipt must fail readback validation.'
}finally{
    # Only these exact test-created files; never recursive deletion.
    foreach($name in 'bound.txt','receipt.pending.json','receipt.json','verified.pending.json','verified.json') {
        $item=Join-Path $temp $name;if([IO.File]::Exists($item)){[IO.File]::Delete($item)}
    }
    [IO.Directory]::Delete($temp,$false)
}
$context=New-Case;$state=New-State $context
$saved=$context.Lease
Complete-H1Stage $context $state {throw 'Final bound-input/guard check failed'}
Check ($context.Closed -and [object]::ReferenceEquals($context.Lease,$saved) -and !$state.LeaseReleased -and $state.Quarantined) 'Failed before-release check must retain the same original lease.'
$context=New-Case;$state=New-State $context;$script:beforeRelease=$false
Complete-H1Stage $context $state {$script:beforeRelease=$true;Check ($context.Lease -ne $null) 'Before-release check must still hold admission.'}
Check ($script:beforeRelease -and $state.LeaseReleased -and $null -eq $context.Lease) 'Successful before-release check must precede ordinary release.'
$context=New-Case;$state=New-State $context;$context.Owner=New-FakeOwner $false $true;$context.Closed=$false
$saved=$context.Lease;$script:beforeRelease=$false
Complete-H1Stage $context $state {$script:beforeRelease=$true}
Check (!$script:beforeRelease -and [object]::ReferenceEquals($saved,$context.Lease) -and !$state.LeaseReleased) 'Unknown original closure must retain admission without running guard-release callback.'
# Real owned Source files exercise the group envelope, not a copy of its logic.
$authoredParent=[IO.Path]::GetFullPath((Join-Path ([IO.Path]::GetTempPath()) ('iw7-authored-output-'+[guid]::NewGuid().ToString('N'))))
$authoredPrefix=$authoredParent+'\'
$authoredFiles=[Collections.Generic.List[string]]::new()
$authoredDirectories=[Collections.Generic.List[string]]::new()
function New-AuthoredOwnedEntry([string]$Path,[bool]$Directory=$false){
    $absolute=[IO.Path]::GetFullPath($Path)
    if($absolute -cne $authoredParent -and !$absolute.StartsWith($authoredPrefix,[StringComparison]::OrdinalIgnoreCase)){throw 'Test-owned absolute cleanup scope differs.'}
    if($Directory){[IO.Directory]::CreateDirectory($absolute)|Out-Null;$authoredDirectories.Add($absolute)}
    else{[IO.File]::WriteAllText($absolute,'x');$authoredFiles.Add($absolute)}
}
$authoredNames=@('weapon-core','attachment-core','fixture-compile','fixture-link','fixture-test','weapondef','weaponattachment','filesystem')
$authoredStages=@(for($i=0;$i -lt 8;$i++){
    [pscustomobject]@{Name=$authoredNames[$i];Stage=$(if($i -eq 4){'Probe'}elseif($i -eq 3){'Link'}else{'Compile'});
        Artifacts=$(if($i -eq 4){@()}elseif($i -eq 3){@('fixture.exe','fixture.pdb')}
            else{@($(if($i -eq 2){'fixture.obj'}else{$authoredNames[$i]+'.obj'}),'compile.pdb','dependencies.json')})}
})
try{
    New-AuthoredOwnedEntry $authoredParent $true
    $authoredRun=Join-Path $authoredParent 'run';New-AuthoredOwnedEntry $authoredRun $true
    $derived=New-H1AuthoredOutputBudget $authoredRun $authoredStages
    Check ($derived.Entries.Count -eq 48 -and $derived.ResidualEntries -eq 64) 'Derived eight-directory/forty-file plus single64 envelope differs.'
    foreach($entry in $derived.Entries.GetEnumerator()){
        if([IO.Path]::GetDirectoryName($entry.Key) -ceq $authoredRun -and $entry.Value -ceq 'File'){continue}
        New-AuthoredOwnedEntry $entry.Key ($entry.Value -ceq 'Directory')
    }
    for($i=0;$i -lt 21;$i++){New-AuthoredOwnedEntry (Join-Path (Join-Path $authoredRun $authoredNames[$i%2]) ('temporary-'+$i+'.tmp'))}
    Refuses {Measure-H1Output $authoredRun} 'Unchanged legacy64 accepted the owned65-entry shape.'
    Check ((Measure-H1Output $authoredRun $derived) -eq 57) 'Real derived65-entry Source tree measured incorrectly.'
    for($i=21;$i -lt 64;$i++){New-AuthoredOwnedEntry (Join-Path (Join-Path $authoredRun $authoredNames[$i%2]) ('temporary-'+$i+'.tmp'))}
    # 44 declared +65 residual =109 TOTAL: below112, so only the SINGLE
    # residual counter can reject this two-stage-root causal.
    $extra=Join-Path (Join-Path $authoredRun $authoredNames[1]) 'temporary-64.tmp';New-AuthoredOwnedEntry $extra
    $residualError=$null;try{$null=Measure-H1Output $authoredRun $derived}catch{$residualError=$_.Exception.Message}
    Check ($residualError -ceq 'Authored group residual output entry count exceeded 64.') 'Two roots bypassed the SINGLE residual64 counter below the112 total.'
    [IO.File]::Delete($extra)
    foreach($entry in $derived.Entries.GetEnumerator()){
        if([IO.Path]::GetDirectoryName($entry.Key) -ceq $authoredRun -and $entry.Value -ceq 'File'){New-AuthoredOwnedEntry $entry.Key}
    }
    Check ((Measure-H1Output $authoredRun $derived) -eq 104) 'All112 slots or the combined64 residual envelope differ.'
    $rogue=Join-Path $authoredRun 'undeclared-root.txt';New-AuthoredOwnedEntry $rogue
    Refuses {Measure-H1Output $authoredRun $derived} 'Undeclared root file accepted.'
    [IO.File]::Delete($rogue)
    $wrongType=Join-Path $authoredRun 'fixture-link\fixture.exe'
    [IO.File]::Delete($wrongType);New-AuthoredOwnedEntry $wrongType $true
    Refuses {Measure-H1Output $authoredRun $derived} 'Declared file replaced by directory accepted.'
    [IO.Directory]::Delete($wrongType,$false);New-AuthoredOwnedEntry $wrongType
    foreach($badName in @('..','name.','name ','AUX.txt','COM¹.tmp','CONOUT$','name:stream','a\b')){
        Refuses {Assert-H1OutputName $badName} 'Win32 component alias/traversal accepted.'
    }
    $badStages=$authoredStages|ConvertTo-Json -Depth 8|ConvertFrom-Json
    $badStages[1].Name=$badStages[0].Name.ToUpperInvariant()
    Refuses {New-H1AuthoredOutputBudget $authoredRun $badStages} 'Case-overlapping declared stage roots accepted.'
    $boundPlan=[pscustomobject]@{Schema='iw7.authored-pair-core-cpp-source/1';Stages=$authoredStages;
        RunRoot=$authoredRun;AuthoredOutputBudget=$derived;OutputLimitBytes=104;MetadataReserveBytes=1}
    Refuses {& $reviewedBudget $boundPlan ([ordered]@{MaxObservedOutputBytes=0L})} 'Derived entry policy bypassed the original aggregate byte reserve.'
    $boundPlan.Schema='iw7.player-template-cohort-source/1'
    $profileError=$null;try{& $reviewedBudget $boundPlan ([ordered]@{MaxObservedOutputBytes=0L})}catch{$profileError=$_.Exception.Message}
    Check ($profileError -ceq 'Only the authored eight-stage cohort may select its output budget.') 'A property alone selected the authored policy outside its profile.'
    # Forged maps preserve all cardinalities. They must fail by pure set/type
    # validation BEFORE any IO of this deliberately absent owned output root.
    $absent=Join-Path $authoredParent 'absent'
    $absentBudget=New-H1AuthoredOutputBudget $absent $authoredStages
    foreach($mutation in @('root-entry','type','stage-root','case-alias','lying-count')){
        $map=[Collections.Generic.Dictionary[string,string]]::new([StringComparer]::Ordinal)
        foreach($pair in $absentBudget.Entries.GetEnumerator()){$map.Add($pair.Key,$pair.Value)}
        $forged=[pscustomobject]@{Schema=$absentBudget.Schema;Root=$absent;Entries=$map;
            StageRoots=@($absentBudget.StageRoots);Stages=$authoredStages;ResidualEntries=64;MaximumDepth=64}
        if($mutation -ceq 'root-entry'){$null=$map.Remove((Join-Path $absent 'stop.request'));$map.Add((Join-Path $absent 'rogue.txt'),'File')}
        if($mutation -ceq 'type'){$map[(Join-Path $absent 'weapon-core')]='File'}
        if($mutation -ceq 'stage-root'){$forged.StageRoots[0]=Join-Path $absent 'rogue-stage'}
        if($mutation -ceq 'case-alias'){$null=$map.Remove((Join-Path $absent 'stop.request'));$map.Add((Join-Path $absent 'weapon-core').ToUpperInvariant(),'Directory')}
        if($mutation -ceq 'lying-count'){
            $forged.Entries=[pscustomobject]@{Count=48}
            $forged.Entries|Add-Member ScriptMethod GetEnumerator {return @()}
        }
        $forgedError=$null;try{$null=Measure-H1Output $absent $forged}catch{$forgedError=$_.Exception.Message}
        Check ($null -ne $forgedError -and $forgedError -like 'Authored * differ from the exact Source profile.') 'A forged48/8 budget reached filesystem IO or accepted an arbitrary path/type/alias.'
        Check (![IO.Directory]::Exists($absent)) 'Pure forged-budget rejection created its absent root.'
    }
    # J8 is eight real phases, with a separate immutable44/8 output derivation.
    $ownedNames=@('helper-compile','helper-link','helper-test','weapon-core','attachment-core','fixture-compile','fixture-link','fixture-test')
    $ownedStages=@(for($i=0;$i -lt 8;$i++){
        $kind=if($i -in @(2,7)){'Probe'}elseif($i -in @(1,6)){'Link'}else{'Compile'}
        $artifacts=if($kind -ceq 'Probe'){@()}elseif($i -eq 1){@('helper.exe','helper.pdb')}
            elseif($i -eq 6){@('fixture.exe','fixture.pdb')}
            else{@($(if($i -eq 0){'helper.obj'}elseif($i -eq 5){'fixture.obj'}else{$ownedNames[$i]+'.obj'}),'compile.pdb','dependencies.json')}
        [pscustomobject]@{Name=$ownedNames[$i];Stage=$kind;Artifacts=$artifacts}
    })
    $ownedRun=Join-Path $authoredParent 'owned-input';New-AuthoredOwnedEntry $ownedRun $true
    $ownedBudget=New-H1AuthoredOutputBudget $ownedRun $ownedStages
    Check ($ownedBudget.Schema -ceq 'iw7.h1-owned-input-output-budget/1' -and $ownedBudget.Entries.Count -eq 44 -and
        @($ownedBudget.Entries.Values|Where-Object {$_ -ceq 'File'}).Count -eq 36) 'J8 closed44/36 shape differs.'
    foreach($entry in $ownedBudget.Entries.GetEnumerator()){
        if([IO.Path]::GetDirectoryName($entry.Key) -ceq $ownedRun -and $entry.Value -ceq 'File'){continue}
        New-AuthoredOwnedEntry $entry.Key ($entry.Value -ceq 'Directory')
    }
    for($i=0;$i -lt 65;$i++){
        New-AuthoredOwnedEntry (Join-Path (Join-Path $ownedRun $ownedNames[$i%2]) ('residual-'+$i+'.tmp'))
    }
    $ownedResidualError=$null;try{$null=Measure-H1Output $ownedRun $ownedBudget}catch{$ownedResidualError=$_.Exception.Message}
    Check ($ownedResidualError -ceq 'Authored group residual output entry count exceeded 64.') 'J8 residual65 at105 entries bypassed the shared64 before108 total.'
    [IO.File]::Delete((Join-Path (Join-Path $ownedRun $ownedNames[0]) 'residual-64.tmp'))
    Check ((Measure-H1Output $ownedRun $ownedBudget) -eq 96) 'J8 exact shared64 stage envelope differs.'
    foreach($entry in $ownedBudget.Entries.GetEnumerator()){
        if([IO.Path]::GetDirectoryName($entry.Key) -ceq $ownedRun -and $entry.Value -ceq 'File'){New-AuthoredOwnedEntry $entry.Key}
    }
    Check ((Measure-H1Output $ownedRun $ownedBudget) -eq 100) 'J8 all108 slots differ.'
    $ownedAbsent=Join-Path $authoredParent 'owned-absent';$ownedAbsentBudget=New-H1AuthoredOutputBudget $ownedAbsent $ownedStages
    foreach($mutation in 'root','type','case'){
        $map=[Collections.Generic.Dictionary[string,string]]::new([StringComparer]::Ordinal)
        foreach($pair in $ownedAbsentBudget.Entries.GetEnumerator()){$map.Add($pair.Key,$pair.Value)}
        if($mutation -ceq 'root'){$null=$map.Remove((Join-Path $ownedAbsent 'stop.request'));$map.Add((Join-Path $ownedAbsent 'rogue.txt'),'File')}
        if($mutation -ceq 'type'){$map[(Join-Path $ownedAbsent 'helper-compile')]='File'}
        if($mutation -ceq 'case'){$null=$map.Remove((Join-Path $ownedAbsent 'stop.request'));$map.Add((Join-Path $ownedAbsent 'helper-compile').ToUpperInvariant(),'Directory')}
        $forged=[pscustomobject]@{Schema=$ownedAbsentBudget.Schema;Root=$ownedAbsent;Entries=$map;StageRoots=$ownedAbsentBudget.StageRoots;
            Stages=$ownedStages;ResidualEntries=64;MaximumDepth=64}
        Refuses {Measure-H1Output $ownedAbsent $forged} 'J8 forged44 map reached IO or accepted changed roots/types/aliases.'
        Check (![IO.Directory]::Exists($ownedAbsent)) 'J8 forged map created its deliberately absent root.'
    }
    $wrongProfile=[pscustomobject]@{Schema='iw7.authored-pair-core-cpp-source/1';Stages=$ownedStages;
        RunRoot=$ownedAbsent;AuthoredOutputBudget=$ownedAbsentBudget}
    Refuses {& $reviewedBudget $wrongProfile ([ordered]@{MaxObservedOutputBytes=0L})} 'J7 schema selected J8 geometry.'
    $wrongProfile.Schema='iw7.authored-owned-input-core-cpp-source/1';$wrongProfile.Stages=$authoredStages
    Refuses {& $reviewedBudget $wrongProfile ([ordered]@{MaxObservedOutputBytes=0L})} 'J8 schema selected J7 geometry.'
    $depthRun=Join-Path $authoredParent 'depth';New-AuthoredOwnedEntry $depthRun $true
    $depthBudget=New-H1AuthoredOutputBudget $depthRun $authoredStages
    $deep=Join-Path $depthRun 'weapon-core';New-AuthoredOwnedEntry $deep $true
    for($i=0;$i -lt 64;$i++){$deep=Join-Path $deep 'd';New-AuthoredOwnedEntry $deep $true}
    Refuses {Measure-H1Output $depthRun $depthBudget} 'Bounded-depth refusal failed before descent.'
    $outside=Join-Path $authoredParent 'outside';New-AuthoredOwnedEntry $outside $true
    $reparseRun=Join-Path $authoredParent 'reparse';New-AuthoredOwnedEntry $reparseRun $true
    $reparseBudget=New-H1AuthoredOutputBudget $reparseRun $authoredStages
    $link=Join-Path $reparseRun 'weapon-core'
    New-Item -ItemType Junction -Path $link -Target $outside|Out-Null
    $authoredDirectories.Add($link)
    $reparseError=$null;try{$null=Measure-H1Output $reparseRun $reparseBudget}catch{$reparseError=$_.Exception.Message}
    Check ($reparseError -ceq 'Output reparse entry refused before descent.') 'A junction was not refused before descent.'
}finally{
    foreach($owned in $authoredFiles){
        if(![IO.Path]::GetFullPath($owned).StartsWith($authoredPrefix,[StringComparison]::OrdinalIgnoreCase)){throw 'Owned Source file cleanup escaped its absolute scope.'}
        if([IO.File]::Exists($owned)){[IO.File]::Delete($owned)}
    }
    foreach($owned in @($authoredDirectories|Select-Object -Unique|Sort-Object Length -Descending)){
        if($owned -cne $authoredParent -and ![IO.Path]::GetFullPath($owned).StartsWith($authoredPrefix,[StringComparison]::OrdinalIgnoreCase)){throw 'Owned Source directory cleanup escaped its absolute scope.'}
        if([IO.Directory]::Exists($owned)){[IO.Directory]::Delete($owned,$false)}
    }
}
Check (!(('IW7.AnimationProbe.NativeJob' -as [type]) -or ('IW7ResourceMemoryV1' -as [type]))) 'Light tests loaded native providers.'
[ordered]@{Schema='iw7.h1-native-runner-source-tests/1';Assertions=$passed;NativeTypesLoaded=$false;
    RealJobsTested=$false;LeaseAcquired=$false;CompilerLaunched=$false}|ConvertTo-Json
