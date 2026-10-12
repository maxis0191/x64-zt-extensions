# Pure source/contract fixtures only. No native imports, leases, files or jobs.
$ErrorActionPreference='Stop'
$checks=0
function Check([bool]$Value,[string]$Name){if(!$Value){throw $Name};$script:checks++}
function Refuses([scriptblock]$Action,[string]$Name){$failed=$false;try{& $Action|Out-Null}catch{$failed=$true};Check $failed $Name}
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
"$checks source/contract checks passed; native execution untested."
