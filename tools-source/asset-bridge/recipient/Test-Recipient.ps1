# Pure source/contract fixtures only. No native imports, leases, files or jobs.
$ErrorActionPreference='Stop'
$checks=0
function Check([bool]$Value,[string]$Name){if(!$Value){throw $Name};$script:checks++}
function Refuses([scriptblock]$Action,[string]$Name){$failed=$false;try{& $Action|Out-Null}catch{$failed=$true};Check $failed $Name}
function RefusesWithMessage([scriptblock]$Action,[string]$Message,[string]$Name){$failure=$null;try{& $Action|Out-Null}catch{$failure=$_.Exception.Message};Check ($failure -ceq $Message) $Name}
foreach($name in @('Recipient.Core.ps1','Run-RecipientClosure.ps1')){
    $errors=$null;$tokens=$null
    $ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $name),[ref]$tokens,[ref]$errors)
    Check ($errors.Count -eq 0) "Parse $name"
    if($name -eq 'Recipient.Core.ps1'){
        Check (@($ast.EndBlock.Statements|Where-Object {$_ -isnot [Management.Automation.Language.FunctionDefinitionAst]}).Count -eq 0) 'Pure helper import'
    }else{
        $guard=@($ast.EndBlock.Statements|Where-Object {$_ -is [Management.Automation.Language.IfStatementAst] -and $_.Extent.Text.StartsWith('if(!$Run)')})
        Check ($guard.Count -eq 1 -and $guard[0].Extent.Text.Contains(';return')) 'Default plan returns'
        $native=@($ast.FindAll({param($node) $node -is [Management.Automation.Language.CommandAst] -and $node.GetCommandName() -in @('Add-Type','Enter-IW7ResourceLease','New-Item')},$true))
        Check (@($native|Where-Object {$_.Extent.StartOffset -lt $guard[0].Extent.EndOffset}).Count -eq 0) 'No native/lease/directory command before default return'
        $code=$ast.Extent.Text
        Check ($code.IndexOf('$script:closed=$false') -lt $code.IndexOf('::Prepare(')) 'Quarantine before factory'
        Check ($code.IndexOf('Get-BeaconJobIdentity') -lt $code.IndexOf('$owner.Resume()')) 'Original identity before Resume'
        Check ($code.IndexOf('$owner.Resume()') -lt $code.IndexOf('Register-AnimationPhase')) 'CIM registration after Resume'
        Check ($code.Contains('$owner.Active -eq 0 -and $owner.Exited')) 'Original tree closure required'
        Check ($code.Contains('Wait-RecipientPhase $owner $identity $plan.OuterPhaseSeconds $plan.RootExitDrainSeconds')) 'Original owner passed to bounded drain'
        Check (!$code.Contains('Stop-Process')) 'No PID cleanup'
        Check ($code.Contains('foreach($phase in $plan.Phases)') -and !$code.Contains('Invoke-RecipientPhase script')) 'Execution follows reviewed phase list only'
        Check ($code.Contains('ReferencesObservedScriptNotRun')) 'References-only status does not claim script observation'
    }
}
. "$PSScriptRoot/Recipient.Core.ps1"
Check ((@(Get-RecipientPhases) -join ',') -ceq 'references,script') 'Default retains both phases'
Check ((@(Get-RecipientPhases -ReferencesOnly) -join ',') -ceq 'references') 'Diagnostic explicitly suppresses utility phase'
$ordinary=Get-RecipientLimits
Check ($ordinary.PhaseSeconds -eq 240 -and $ordinary.OuterPhaseSeconds -eq 245 -and $ordinary.OverallSeconds -eq 600) 'Ordinary timing retained'
$diagnostic=Get-RecipientLimits -FatalTextDiagnostic
Check ($diagnostic.PhaseSeconds -eq 45 -and $diagnostic.OuterPhaseSeconds -eq 50 -and $diagnostic.OverallSeconds -eq 60) 'Fatal diagnostic timing bounded'
$names=@('techsets_global_core_mp','techsets_common_core_mp','code_post_gfx','global','common','techsets_cp_zmb','cp_zmb','patch_cp_zmb')
$inputs=@(foreach($name in $names){@{Relative=('main/'+$name+'.ff')};@{Relative=('zone/'+$name+'.ff')}})
$order=@(Get-RecipientZoneOrder $inputs)
Check (($order -join ',') -ceq ($names -join ',')) 'Exact available source load order'
Refuses {Get-RecipientZoneOrder @()} 'Missing cp_zmb refuses'
$log=($names|ForEach-Object {'[ INFO ] Loading zone "'+$_+'"...'}) -join "`n"
Check ((@(Assert-RecipientZoneLog $log $order) -join ',') -ceq ($order -join ',')) 'Observed order accepted'
$loaded=$log.Replace('Loading zone "cp_zmb"...','zone "cp_zmb" is already loaded...')
Check (@(Assert-RecipientZoneLog $loaded $order).Count -eq $order.Count) 'Already loaded witness accepted'
Refuses {Assert-RecipientZoneLog ($log+"`n"+$log) $order} 'Repeated load order refuses'
Refuses {Assert-RecipientZoneLog ($log+"`n[ ERROR ] missing") $order} 'Native load error refuses'
Refuses {Assert-RecipientZoneLog $log @('cp_zmb')} 'Unexpected earlier zones refuse'
$result=[pscustomobject]@{schema='iw7.recipient-phase-result/1';phase='script';executable_sha256='e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04';failure=$null;exit_code=0;log_limit_each=2MB;observation=@{closure_complete=$false;package_ready=$false}}
$identity=@{ExitCode=0;JobActiveAtClose=0}
Assert-RecipientResult $result script $identity;$checks++
$identity.JobActiveAtClose=1;Refuses {Assert-RecipientResult $result script $identity} 'Living descendant refuses'
$identity.JobActiveAtClose=0;$result.observation.package_ready=$true
Refuses {Assert-RecipientResult $result script $identity} 'Invented package closure refuses'
$script:tick=0;$script:saves=0;$script:budgets=0
$fake=[pscustomobject]@{ExitCode=0}
$fake|Add-Member ScriptProperty Exited { $script:tick -ge 1 }
$fake|Add-Member ScriptProperty Active { if($script:tick -lt 3){1}else{0} }
$identity=@{PostRootExitObservations=@()}
Wait-RecipientPhase $fake $identity 245 5 {$script:tick} {$script:budgets++} {$script:saves++} {$script:tick++}
Check ($script:tick -eq 3 -and $script:budgets -eq 3 -and $script:saves -eq 3) 'Delayed job drain succeeds only when empty'
Check (($identity.PostRootExitObservations.Active -join ',') -ceq '1,1,0') 'Actual nonzero then zero counts retained'
Check (($identity.PostRootExitObservations.DrainSeconds -join ',') -ceq '0,1,2') 'Drain elapsed observations retained'
$script:tick=0;$fake=[pscustomobject]@{Exited=$true;Active=1;ExitCode=0};$identity=@{PostRootExitObservations=@()}
Refuses {Wait-RecipientPhase $fake $identity 245 5 {$script:tick} {} {} {$script:tick++}} 'Persistent member exceeds drain deadline'
Check ($script:tick -eq 5 -and $identity.PostRootExitObservations.Count -eq 6) 'Persistent drain bounded at five seconds'
$script:tick=0;$fake=[pscustomobject]@{Exited=$false;Active=0;ExitCode=0};$identity=@{PostRootExitObservations=@()}
Refuses {Wait-RecipientPhase $fake $identity 2 5 {$script:tick} {} {} {$script:tick++}} 'Empty job without root exit cannot succeed'
Check ($script:tick -eq 3 -and $identity.PostRootExitObservations.Count -eq 0) 'Outer deadline applies before root exit'
$script:tick=246;$fake=[pscustomobject]@{Exited=$true;Active=0;ExitCode=0};$identity=@{PostRootExitObservations=@()}
Refuses {Wait-RecipientPhase $fake $identity 245 5 {$script:tick} {} {} {throw 'Unexpected wait'}} 'Late closure still exceeds outer deadline'
# Getters and persistence advance a fake monotonic clock; no real sleep/process.
# An empty job must not be accepted using a timestamp from before these calls.
foreach($case in @(
    @{Name='ExitCode crosses phase deadline';Start=244.0;Slow='ExitCode';Advance=1.001},
    @{Name='Save crosses phase deadline';Start=244.0;Slow='Save';Advance=1.001},
    @{Name='ExitCode crosses drain deadline';Start=10.0;Slow='ExitCode';Advance=5.001},
    @{Name='Save crosses drain deadline';Start=10.0;Slow='Save';Advance=5.001},
    @{Name='Active getter crosses drain deadline';Start=10.0;Slow='Active';Advance=5.001},
    @{Name='Exited getter crosses phase deadline';Start=244.0;Slow='Exited';Advance=1.001}
)){
    $script:tick=$case.Start;$script:slow=$case.Slow;$script:advance=$case.Advance
    $script:saves=0;$script:exitReads=0;$script:activeReads=0
    $fake=[pscustomobject]@{}
    $fake|Add-Member ScriptProperty Exited {if($script:slow -ceq 'Exited'){$script:tick+=$script:advance};$true}
    $fake|Add-Member ScriptProperty Active {$script:activeReads++;if($script:slow -ceq 'Active'){$script:tick+=$script:advance};0}
    $fake|Add-Member ScriptProperty ExitCode {$script:exitReads++;if($script:slow -ceq 'ExitCode'){$script:tick+=$script:advance};0}
    $identity=@{PostRootExitObservations=@()}
    $message=if($case.Name.Contains('phase deadline')){'Recipient phase deadline exceeded.'}else{'Original job closure exceeded the post-root-exit drain deadline.'}
    RefusesWithMessage {Wait-RecipientPhase $fake $identity 245 5 {$script:tick} {throw 'Unexpected budget call'} {
        $script:saves++;if($script:slow -ceq 'Save'){$script:tick+=$script:advance}
    } {throw 'Unexpected delay'}} $message $case.Name
    Check ($script:tick -eq ($case.Start+$case.Advance)) ($case.Name+' really advanced elapsed time')
    if($case.Slow -ceq 'Exited'){Check ($script:activeReads -eq 0) 'Late root getter refuses before Active query'}
    if($case.Slow -ceq 'Active'){Check ($script:exitReads -eq 0) 'Late Active getter refuses before ExitCode query'}
    if($case.Slow -ceq 'ExitCode'){Check ($script:saves -eq 0) 'Late ExitCode getter refuses before Save'}
    if($case.Slow -ceq 'Save'){Check ($script:saves -eq 1) 'Late Save ran once but cannot authorize closure'}
}
$script:tick=240.0;$script:saves=0
$fake=[pscustomobject]@{Exited=$true}
$fake|Add-Member ScriptProperty Active {$script:tick+=0.5;0}
$fake|Add-Member ScriptProperty ExitCode {$script:tick+=0.5;0}
$identity=@{PostRootExitObservations=@()}
Wait-RecipientPhase $fake $identity 245 5 {$script:tick} {throw 'Unexpected budget call'} {$script:saves++;$script:tick+=1} {throw 'Unexpected delay'}
Check ($script:tick -eq 242 -and $script:saves -eq 1) 'Slow calls within both limits still permit closure'
Check ($identity.PostRootExitObservations[0].PhaseSeconds -eq 241 -and $identity.PostRootExitObservations[0].DrainSeconds -eq 1) 'Observation timestamp follows the completed ExitCode read'
$script:tick=240.0;$fake=[pscustomobject]@{Exited=$true;Active=0;ExitCode=0};$identity=@{PostRootExitObservations=@()}
Wait-RecipientPhase $fake $identity 245 5 {$script:tick} {} {$script:tick+=5} {throw 'Unexpected delay'}
Check ($script:tick -eq 245) 'Confirmed empty job at both exact inclusive limits succeeds'
$script:tick=244.0;$script:delays=0;$fake=[pscustomobject]@{Exited=$false;Active=1};$identity=@{PostRootExitObservations=@()}
RefusesWithMessage {Wait-RecipientPhase $fake $identity 245 5 {$script:tick} {$script:tick+=1.001} {} {$script:delays++}} 'Recipient phase deadline exceeded.' 'Slow budget check crosses phase deadline'
Check ($script:delays -eq 0) 'Fresh budget deadline check refuses before another delay'
# Exercise the real budget function with only in-memory dependency doubles.
$runner=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Run-RecipientClosure.ps1'),[ref]$tokens,[ref]$errors)
$budgetFunction=$runner.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq 'Assert-RecipientBudget'},$false)
Invoke-Expression $budgetFunction.Extent.Text
$plan=@{OverallSeconds=600;FatalTextDiagnostic=$false};$overall=@{Elapsed=@{TotalSeconds=1}}
$runRoot='C:\recipient-pure-budget-fixture';$created=$false;$script:measureCalls=0;$script:committed=80;$script:marker=$null
function Test-Path {param($LiteralPath) $LiteralPath -ceq (Join-Path $runRoot ([string]$script:marker))}
function Measure-RecipientOutput {$script:measureCalls++}
function Get-IW7ResourceSnapshot {@{Committed=$script:committed;CommitLimit=100}}
Assert-RecipientBudget
Check ($script:measureCalls -eq 0) 'Pre-staging budget never enumerates the absent run directory'
$created=$true;Assert-RecipientBudget
Check ($script:measureCalls -eq 1) 'Created-run budget still measures output'
$created=$false;$script:committed=86
Refuses {Assert-RecipientBudget} 'Pre-staging budget refuses fresh commit pressure'
$script:committed=80;$overall.Elapsed.TotalSeconds=601
Refuses {Assert-RecipientBudget} 'Pre-staging budget refuses elapsed deadline'
$overall.Elapsed.TotalSeconds=1;$script:marker='fatal-stop.request'
Refuses {Assert-RecipientBudget} 'Normal-mode fatal marker requests original-owner stop'
$script:marker='diagnostic-stop.request';Assert-RecipientBudget;$checks++
$plan.FatalTextDiagnostic=$true
Refuses {Assert-RecipientBudget} 'Diagnostic marker still requires diagnostic mode'
"$checks source/contract checks passed; native execution untested."
