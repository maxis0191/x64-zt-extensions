# Default checks source/metadata only. Native execution needs a reviewed exact
# plan and separate coordinator GO; no ZoneTool/game launch exists in this runner.
[CmdletBinding()]
param([Parameter(Mandatory)][string]$PlanPath,[Parameter(Mandatory)][string]$PlanSHA256,[switch]$Run)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
if(!$IsWindows -or [IntPtr]::Size -ne 8 -or $PSVersionTable.PSVersion.Major -lt 7){throw 'Windows x64 PowerShell 7 required.'}
if($PlanSHA256 -cnotmatch '^[0-9a-f]{64}$'){throw 'Exact reviewed plan SHA256 required.'}
$guards=[Collections.Generic.List[object]]::new()
$context=[pscustomobject]@{Owner=$null;Closed=$true;Lease=$null;Guards=$guards}
$state=$null;$failure=$null;$created=$false;$launcher=$null;$priority=$null
function Open-T7Bootstrap($Path,[long]$Bytes,[string]$SHA256) {
    if(![IO.Path]::IsPathFullyQualified($Path) -or [IO.Path]::GetFullPath($Path) -cne $Path){throw 'Canonical bootstrap path required.'}
    for($part=$Path;$part;$part=[IO.Path]::GetDirectoryName($part)) {
        if(([IO.File]::GetAttributes($part) -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Bootstrap reparse path refused.'}
    }
    if($Bytes -le 0 -or $Bytes -gt 32MB -or $SHA256 -cnotmatch '^[0-9a-f]{64}$'){throw 'Invalid source binding.'}
    $stream=[IO.FileStream]::new($Path,'Open','Read','Read');$guards.Add($stream)
    if($stream.Length -ne $Bytes){throw 'Bootstrap length differs.'}
    $hash=[Security.Cryptography.SHA256]::Create()
    try{$actual=[Convert]::ToHexString($hash.ComputeHash($stream)).ToLowerInvariant()}finally{$hash.Dispose()}
    if($actual -cne $SHA256){throw 'Bootstrap source differs.'}
    $stream.Position=0;return $stream
}
try {
    $planSize=(Get-Item -LiteralPath $PlanPath).Length
    if($planSize -gt 2MB){throw 'Plan exceeds 2 MiB.'}
    $planStream=Open-T7Bootstrap $PlanPath $planSize $PlanSHA256
    $reader=[IO.StreamReader]::new($planStream,[Text.Encoding]::UTF8,$true,4096,$true)
    try{$plan=$reader.ReadToEnd()|ConvertFrom-Json -Depth 25}finally{$reader.Dispose()}
    if($plan.Schema -cne 'iw7.t7-minimal-build-plan/1' -or $plan.Runner -cne $PSCommandPath -or
       $plan.Profile -cne (Join-Path $PSScriptRoot 'T7Build.Profile.ps1')){throw 'Exact T7 runner/profile required.'}
    if($plan.PhysicalBytes -ne 4GB -or $plan.CommitBytes -ne 6GB -or $plan.GroupDeadlineSeconds -ne 600 -or
       $plan.OutputLimitBytes -ne 256MB -or $plan.MetadataReserveBytes -ne 1MB -or $plan.CleanupSeconds -ne 5 -or
       $plan.ReusedObjects -ne 410 -or $plan.ReusedProjectLibraries -ne 18 -or $plan.ReusedResources -ne 1){throw 'Fixed minimal build limits differ.'}
    $reuse=$plan.PSObject.Properties.Name -contains 'ReuseCompile' -and $null -ne $plan.ReuseCompile
    $names=@(if($reuse){'link'}else{'helper','probe','main','zonetool11','xpak','link'})
    if(@($plan.Stages).Count -ne $names.Count -or (@($plan.Stages.Name)-join ',') -cne ($names-join ',')){throw 'Exact full-build or retained-compile link stages required.'}
    if(@($plan.Bindings).Count -gt 128 -or @($plan.Inputs).Count -gt 2048 -or
       @($plan.Bindings.Path|Sort-Object -Unique).Count -ne @($plan.Bindings).Count){throw 'Input set bound/uniqueness differs.'}
    foreach($pin in $plan.Bindings) {
        if($pin.IsText -isnot [bool]){throw 'Binding text/binary classification required.'}
        if($pin.IsText){$null=Open-T7Bootstrap $pin.Path $pin.Bytes $pin.SHA256}
        elseif((Get-Item -LiteralPath $pin.Path).Length -ne $pin.Bytes){throw 'Binary metadata changed.'}
    }
    foreach($required in @($plan.Runner,$plan.Profile,$plan.Core,$plan.CompilerCore,$plan.ObserverSource,$plan.CompilerPolicySource,$plan.Scheduler)) {
        if(@($plan.Bindings|Where-Object {$_.Path -ceq $required -and $_.IsText}).Count -ne 1){throw 'Exact source provider pin missing.'}
    }
    . $plan.Core
    $runtime=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../runtime'))
    Assert-H1Path $plan.RunRoot
    if([IO.Path]::GetDirectoryName($plan.RunRoot) -cne $runtime -or (Test-Path -LiteralPath $plan.RunRoot)){throw 'Fresh output directly under owned runtime required.'}
    foreach($stage in $plan.Stages) {
        $expectedType=if($stage.Name -ceq 'probe'){'Probe'}elseif($stage.Name -ceq 'link'){'Link'}else{'Compile'}
        $expectedSeconds=if($expectedType -ceq 'Probe'){15}else{120}
        if($stage.Stage -cne $expectedType -or $stage.DeadlineSeconds -ne $expectedSeconds){throw 'Fixed stage profile differs.'}
        Assert-H1Path $stage.Image
    }
    foreach($pin in $plan.Inputs) {
        Assert-H1Path $pin.Path
        if((Get-Item -LiteralPath $pin.Path).Length -ne $pin.Bytes){throw 'Recorded input metadata differs.'}
    }
    if($reuse) {
        $prior=Read-H1SmallJson $plan.ReuseCompile.Receipt
        if($prior.Schema -cne 'iw7.t7-minimal-build/1' -or $prior.Status -cne 'Failed' -or
           $prior.TreeClosureConfirmed -isnot [bool] -or !$prior.TreeClosureConfirmed -or
           $prior.LeaseReleased -isnot [bool] -or !$prior.LeaseReleased -or
           $prior.Quarantined -isnot [bool] -or $prior.Quarantined -or
           $prior.PlanSHA256 -cne $plan.ReuseCompile.SourcePlanSHA256 -or $plan.ReuseCompile.Checks -ne 51){throw 'Retained compile proof differs.'}
        foreach($name in 'helper','probe','main','zonetool11','xpak') {
            $row=@($prior.Stages|Where-Object Name -CEQ $name)
            if($row.Count -ne 1 -or $row[0].ExitCode -ne 0 -or !$row[0].TreeClosureConfirmed){throw 'Retained sub-stage was not successful and closed.'}
        }
        if(@($prior.Stages|Where-Object Name -CEQ 'probe')[0].Checks -ne 51){throw 'Retained name probe differs.'}
        foreach($required in @($plan.ReuseCompile.Receipt,$plan.ReuseCompile.SourcePlan)) {
            if(@($plan.Bindings|Where-Object {$_.Path -ceq $required -and $_.IsText}).Count -ne 1){throw 'Retained receipt/plan binding absent.'}
        }
    }
    if(!$Run) {
        [ordered]@{Schema='iw7.t7-minimal-build-check/1';PlanSHA256=$PlanSHA256;Stages=@($plan.Stages).Count;ReusedCompilation=$reuse;
            ExpectedInputs=@($plan.Inputs).Count;MissingExpectedPins=@($plan.MissingExpectedPins).Count;
            NativeTypesLoaded=$false;BinaryInputsHashed=$false;LeaseAcquired=$false;RunRootCreated=$false;Ready=$false}|ConvertTo-Json
        return
    }
    if($plan.InputPinsComplete -isnot [bool] -or !$plan.InputPinsComplete -or @($plan.MissingExpectedPins).Count){throw 'Complete reviewed expected input pins required before native GO.'}
    if(('IW7.AnimationProbe.NativeJob' -as [type]) -or ('IW7.H1Diagnostics.JobMembers' -as [type]) -or ('IW7ResourceMemoryV1' -as [type])){throw 'Fresh PowerShell host required.'}
    . $plan.Scheduler
    $state=[ordered]@{Schema='iw7.t7-minimal-build/1';PlanSHA256=$PlanSHA256;Status='Pending';Ready=$false;
        EstimatesAreMeasured=$false;TreeClosureConfirmed=$true;LeaseReleased=$false;Quarantined=$false;
        MaxObservedOutputBytes=0L;CompilerTelemetry=[ordered]@{Completed=$false};Stages=[Collections.Generic.List[object]]::new()}
    $context.Lease=Enter-IW7ResourceLease -Scope $plan.RunRoot -Kind Build -PhysicalBytes $plan.PhysicalBytes -CommitBytes $plan.CommitBytes -Owner 'T7 three TU build and name helper'
    $state.LeaseToken=$context.Lease.Token;$script:T7GroupStarted=Get-H1Clock
    if(Test-Path -LiteralPath $plan.RunRoot){throw 'Output appeared during admission.'}
    [IO.Directory]::CreateDirectory($plan.RunRoot)|Out-Null;$created=$true
    . $plan.CompilerPolicySource
    . $plan.CompilerCore
    . $plan.Profile
    $launcher=Get-Process -Id $PID;$priority=$launcher.PriorityClass;$launcher.PriorityClass='BelowNormal'
    # No binary contents are read until the one account-wide reservation exists.
    foreach($pin in @($plan.Inputs)+@($plan.Bindings|Where-Object {!$_.IsText})){Open-T7Pin $pin $context}
    if($reuse){foreach($root in $plan.ReuseCompile.StageRoots){Assert-T7Dependencies $plan $root}}
    $null=[Reflection.Assembly]::LoadFrom($plan.JobAssembly)
    Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
    Add-Type -LiteralPath $plan.ObserverSource
    Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
    foreach($stage in $plan.Stages) {
        Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
        if(!$context.Closed){throw 'Previous original job not closed.'}
        $script:T7CurrentStage=$stage
        $stageRoot=Join-Path $plan.RunRoot $stage.Name
        [IO.Directory]::CreateDirectory($stageRoot)|Out-Null
        $stageState=[ordered]@{Stage=$stage.Stage;Name=$stage.Name;PlanSHA256=$PlanSHA256;DeadlineSeconds=$stage.DeadlineSeconds;
            MaxObservedOutputBytes=$state.MaxObservedOutputBytes;TreeClosureConfirmed=$false;
            CompilerTelemetry=[ordered]@{Completed=$false;Action=$null}}
        $state.Stages.Add($stageState)
        $stageStarted=Get-H1Clock
        $image=if($stage.Stage -ceq 'Probe'){@($state.Stages[0].Artifacts|Where-Object Path -CEQ $stage.Image)[0]}
               else{@($plan.Bindings|Where-Object Path -CEQ $stage.Image)[0]}
        $start=New-T7Start $plan $stage $stageRoot
        Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
        Invoke-T7OwnedStage $plan $stageState $context $start $image.SHA256 $stageRoot $stageStarted
        $stageState.Artifacts=@(Get-H1CompilerArtifacts $plan $context)
        if($stageState.CompilerTelemetry.Completed) {
            foreach($prior in $stageState.CompilerTelemetry.Artifacts) {
                $now=@($stageState.Artifacts|Where-Object Path -CEQ $prior.Path)
                if($now.Count -ne 1 -or $now[0].SHA256 -cne $prior.SHA256 -or $now[0].Bytes -ne $prior.Bytes){throw 'Artifact changed across compiler cleanup.'}
            }
        }
        if($stage.Stage -ceq 'Compile'){Assert-T7Dependencies $plan $stageRoot}
        if($stage.Stage -ceq 'Probe') {
            $stdout=Join-Path $stageRoot 'stdout.log';$stderr=Join-Path $stageRoot 'stderr.log'
            if((Get-Item -LiteralPath $stdout).Length -gt 128 -or (Get-Item -LiteralPath $stderr).Length -ne 0){throw 'Name helper output differs.'}
            $observed=[IO.File]::ReadAllText($stdout)
            if($observed -cne "T7_ASSET_NAME_CHECKS=51`n" -and $observed -cne "T7_ASSET_NAME_CHECKS=51`r`n"){throw 'Exactly 51 native name checks required.'}
            $stageState.Checks=51
        }
        Test-H1Budget $plan $stageState
        Assert-H1Deadline $stageStarted $stage.DeadlineSeconds
        $state.MaxObservedOutputBytes=[math]::Max($state.MaxObservedOutputBytes,$stageState.MaxObservedOutputBytes)
    }
    foreach($pin in $plan.Inputs){Open-T7Pin $pin $context}
    foreach($pin in $plan.Bindings){$guard=Open-H1Pin $pin;try{}finally{$guard.Dispose()};Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds}
    Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
    $state.ElapsedMs=(Get-H1Clock)-$script:T7GroupStarted
    $state.InputsReverified=$true;$state.CandidateExecuted=$false
}catch{
    $failure=$_
    if($state){$state.Status='Failed';$state.Error=$_.Exception.Message}
}finally{
    if($state){Complete-H1Stage $context $state}
    if($launcher -and $null -ne $priority){try{$launcher.PriorityClass=$priority}catch{if(!$failure){$failure=$_};$state.Status='Failed'}}
    if($context.Closed -and !$context.Lease){foreach($guard in $guards){$guard.Dispose()};$guards.Clear()}
    if($state -and $created) {
        try {
            Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds
            if(!$failure -and $context.Closed -and !$context.Lease){$state.Status='Passed'}
        }catch{
            if(!$failure){$failure=$_}
            if($state.Status -cne 'Quarantined'){$state.Status='Failed'}
            $state.GroupDeadlineError=$_.Exception.Message
        }
        $state.ElapsedMs=(Get-H1Clock)-$script:T7GroupStarted
        $state.FinishedUtc=[datetime]::UtcNow.ToString('o')
        try{Write-H1Receipt $plan $state $plan.RunRoot}catch{if(!$failure){$failure=$_};Write-Warning $_.Exception.Message}
        if(!$failure) {
            try{Assert-H1Deadline $script:T7GroupStarted $plan.GroupDeadlineSeconds}
            catch {
                $failure=$_;$state.Status='Failed';$state.GroupDeadlineError=$_.Exception.Message
                $state.ElapsedMs=(Get-H1Clock)-$script:T7GroupStarted
                # A slow publication must not leave a canonical Passed receipt.
                # Preserve the late attempt, then publish failure diagnostics.
                try {
                    $receipt=Join-Path $plan.RunRoot 'receipt.json'
                    $late=Join-Path $plan.RunRoot 'receipt.deadline-exceeded.json'
                    Assert-H1Path $receipt;Assert-H1Path $late
                    [IO.File]::Move($receipt,$late)
                    Write-H1Receipt $plan $state $plan.RunRoot
                }catch{Write-Warning ('Late receipt failure: '+$_.Exception.Message)}
            }
        }
    }
}
if($failure){throw $failure}
if(!$state.LeaseReleased -or $state.Status -cne 'Passed'){throw 'Build did not close and release successfully.'}
[ordered]@{Status=$state.Status;Receipt=(Join-Path $plan.RunRoot 'receipt.json');CandidateExecuted=$false;Ready=$false}|ConvertTo-Json
