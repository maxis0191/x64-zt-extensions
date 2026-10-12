# Default is read-only Plan verification. -Run needs a separately reviewed GO.
[CmdletBinding()]
param([Parameter(Mandatory)][string]$PlanPath,[Parameter(Mandatory)][string]$PlanSHA256,
    [ValidateSet('Compile','Probe')][string]$Stage='Compile',[switch]$Run)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if(!$IsWindows -or [IntPtr]::Size -ne 8 -or $PSVersionTable.PSVersion.Major -lt 7){throw 'Windows x64 PowerShell 7 required.'}
if($PlanSHA256 -cnotmatch '^[0-9a-f]{64}$'){throw 'Reviewed plan SHA256 required.'}
# Bootstrap is intentionally independent of the mutable core. Check the plan,
# runner and core before importing any function from the plan.
$planGuard=$null;$coreGuard=$null;$runnerGuard=$null
$guards=[Collections.Generic.List[object]]::new()
$context=[pscustomobject]@{Owner=$null;Closed=$true;Lease=$null;Guards=$guards}
$state=$null;$stageRoot=$null;$outputCreated=$false;$launcher=$null;$priority=$null;$failure=$null
try {
    foreach($path in @($PlanPath,$PSCommandPath,(Join-Path $PSScriptRoot 'H1Native.Core.ps1'))) {
        if(![IO.Path]::IsPathFullyQualified($path) -or [IO.Path]::GetFullPath($path) -cne $path){throw 'Canonical bootstrap paths required.'}
        for($part=$path;$part;$part=[IO.Path]::GetDirectoryName($part)) {
            if(([IO.File]::GetAttributes($part) -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Bootstrap reparse path refused.'}
        }
    }
    $planGuard=[IO.FileStream]::new($PlanPath,'Open','Read','Read');$guards.Add($planGuard)
    if($planGuard.Length -gt 128KB){throw 'Plan exceeds 128 KiB.'}
    $bytes=[byte[]]::new([int]$planGuard.Length);$planGuard.ReadExactly($bytes,0,$bytes.Length)
    if([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant() -cne $PlanSHA256){throw 'Reviewed plan hash differs.'}
    $plan=[Text.Encoding]::UTF8.GetString($bytes)|ConvertFrom-Json -Depth 20
    if($plan.Schema -cne 'iw7.h1-native-plan/2' -or $plan.Runner -cne $PSCommandPath -or
       $plan.Core -cne (Join-Path $PSScriptRoot 'H1Native.Core.ps1')){throw 'Plan/runner/core identity differs.'}
    foreach($path in @($plan.Runner,$plan.Core)) {
        $pin=@($plan.Bindings|Where-Object Path -CEQ $path)
        if($pin.Count -ne 1 -or $pin[0].Bytes -gt 128KB -or $pin[0].SHA256 -cnotmatch '^[0-9a-f]{64}$'){throw 'Bootstrap binding invalid.'}
        $stream=[IO.FileStream]::new($path,'Open','Read','Read');$guards.Add($stream)
        if($stream.Length -ne $pin[0].Bytes){throw 'Bootstrap length differs.'}
        $digest=[Security.Cryptography.SHA256]::Create()
        try{$hash=[Convert]::ToHexString($digest.ComputeHash($stream)).ToLowerInvariant()}finally{$digest.Dispose()}
        if($hash -cne $pin[0].SHA256){throw 'Bootstrap source differs from reviewed plan.'}
    }
    . $plan.Core
    if($plan.OutputLimitBytes -ne 32MB -or $plan.MetadataReserveBytes -ne 1MB -or $plan.CleanupSeconds -ne 5 -or
       $plan.Stages.Compile.PhysicalBytes -ne 4GB -or $plan.Stages.Compile.CommitBytes -ne 6GB -or
       $plan.Stages.Compile.DeadlineSeconds -ne 120 -or $plan.Stages.Compile.Kind -cne 'Build' -or
       $plan.Stages.Probe.PhysicalBytes -ne 256MB -or $plan.Stages.Probe.CommitBytes -ne 256MB -or
       $plan.Stages.Probe.DeadlineSeconds -ne 15 -or $plan.Stages.Probe.Kind -cne 'Analysis' -or
       $plan.ParserPoolBytes -ne 1MB -or $plan.CompilerProcesses -ne 1 -or
       $plan.CompilerClosure -cne 'StopOriginalJobAfterVerifiedCompilerAndTelemetry' -or $plan.RequiredTelemetryCaptures -ne 2){throw 'Reviewed fixed budgets differ.'}
    $repo=Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
    $runtime=[IO.Path]::GetFullPath((Join-Path $repo 'runtime'))+[IO.Path]::DirectorySeparatorChar
    foreach($path in @($plan.RunRoot,$plan.FixtureRoot,$plan.PreparedRoot,$plan.SourceRoot,$plan.Compiler,$plan.Executable,$plan.JobAssembly,$plan.Scheduler)) {Assert-H1Path $path}
    if(!$plan.RunRoot.StartsWith($runtime,[StringComparison]::OrdinalIgnoreCase) -or
       $plan.Executable -cne (Join-Path $plan.RunRoot 'compile/native_probe.exe')){throw 'Plan output escapes this worktree.'}
    if(@($plan.Bindings).Count -lt 40 -or @($plan.Bindings).Count -gt 128 -or
       @($plan.Bindings.Path|Sort-Object -Unique).Count -ne @($plan.Bindings).Count){throw 'Bound input set invalid.'}
    foreach($pin in $plan.Bindings){$guards.Add((Open-H1Pin $pin))}
    foreach($required in @($plan.Scheduler,$plan.JobAssembly,$plan.Compiler,$plan.CompilerCore,$plan.ObserverSource,$plan.CompilerPolicySource)) {
        if(@($plan.Bindings|Where-Object Path -CEQ $required).Count -ne 1){throw 'Executable/provider binding absent.'}
    }
    $stageRoot=Join-Path $plan.RunRoot $Stage.ToLowerInvariant()
    $prior=$null;$imageHash=$null
    if($Stage -ceq 'Compile') {
        if(Test-Path -LiteralPath $plan.RunRoot){throw 'Compile requires a fresh run root.'}
        $imageHash=($plan.Bindings|Where-Object Path -CEQ $plan.Compiler).SHA256
    } else {
        if(Test-Path -LiteralPath $stageRoot){throw 'Probe stage must be fresh.'}
        $receiptPath=Join-Path $plan.RunRoot 'compile/receipt.json'
        $priorGuard=[IO.FileStream]::new($receiptPath,'Open','Read','Read');$guards.Add($priorGuard)
        $prior=Read-H1SmallJson $receiptPath
        if($prior.Schema -cne 'iw7.h1-native-stage/1' -or $prior.Stage -cne 'Compile' -or $prior.PlanSHA256 -cne $PlanSHA256 -or
           $prior.Status -cne 'Passed' -or $prior.TreeClosureConfirmed -isnot [bool] -or !$prior.TreeClosureConfirmed -or
           $prior.LeaseReleased -isnot [bool] -or !$prior.LeaseReleased -or $prior.Quarantined -isnot [bool] -or
           $prior.Quarantined -or $prior.ExitCode -ne 0 -or $prior.Executable.Path -cne $plan.Executable){throw 'Successful closed compile receipt for this plan required.'}
        $guards.Add((Open-H1Pin $prior.Executable));$imageHash=$prior.Executable.SHA256
    }
    if(!$Run) {
        [ordered]@{Schema='iw7.h1-native-plan-check/1';Stage=$Stage;PlanSHA256=$PlanSHA256;
            BindingsVerified=@($plan.Bindings).Count;NativeTypesLoaded=$false;LeaseAcquired=$false;
            RunRootCreated=$false;WholeZoneToolValidated=$false;ReadyForCoordinatorReview=$true}|ConvertTo-Json
        return
    }
    if(('IW7.AnimationProbe.NativeJob' -as [type]) -or ('IW7ResourceMemoryV1' -as [type]) -or
       ('IW7.H1Diagnostics.JobMembers' -as [type])){throw 'A fresh PowerShell host is required.'}
    # Existing witnessed DLL only. No new native-job/identity C# implementation.
    $null=[Reflection.Assembly]::LoadFrom($plan.JobAssembly)
    . $plan.Scheduler
    . $plan.CompilerPolicySource
    . $plan.CompilerCore
    $budget=$plan.Stages.$Stage
    $state=[ordered]@{Schema='iw7.h1-native-stage/1';Stage=$Stage;PlanSHA256=$PlanSHA256;Status='Pending';
        DeadlineSeconds=$budget.DeadlineSeconds;PhysicalBytes=$budget.PhysicalBytes;CommitBytes=$budget.CommitBytes;
        EstimatesAreMeasured=$false;WholeZoneToolValidated=$false;TreeClosureConfirmed=$true;
        LeaseReleased=$false;LeaseToken=$null;Quarantined=$false;MaxObservedOutputBytes=0L;
        CompilerTelemetry=[ordered]@{Completed=$false;Action=$null}}
    $context.Lease=Enter-IW7ResourceLease -Scope $stageRoot -Kind $budget.Kind -PhysicalBytes $budget.PhysicalBytes `
        -CommitBytes $budget.CommitBytes -Owner ('H1 original fixture '+$Stage)
    $state.LeaseToken=$context.Lease.Token
    $stageStarted=Get-H1Clock;$state.AdmittedStageStartedUtc=[datetime]::UtcNow.ToString('o')
    if((Test-Path -LiteralPath $stageRoot) -or ($Stage -ceq 'Compile' -and (Test-Path -LiteralPath $plan.RunRoot))){throw 'Stage output appeared during admission.'}
    [IO.Directory]::CreateDirectory($stageRoot)|Out-Null
    $outputCreated=$true
    if($Stage -ceq 'Compile'){Add-Type -LiteralPath $plan.ObserverSource}
    Assert-H1Deadline $stageStarted $budget.DeadlineSeconds
    $launcher=Get-Process -Id $PID;$priority=$launcher.PriorityClass;$launcher.PriorityClass='BelowNormal'
    $start=[Diagnostics.ProcessStartInfo]::new($(if($Stage -ceq 'Compile'){$plan.Compiler}else{$plan.Executable}))
    $start.WorkingDirectory=$stageRoot;$start.UseShellExecute=$false;$start.CreateNoWindow=$true;$start.WindowStyle='Hidden'
    # Limit discovery to the reviewed toolchain and Windows. Telemetry handling
    # uses exact-job observations, without guessing environment opt-out behavior.
    $start.Environment.Remove('CL')|Out-Null;$start.Environment.Remove('_CL_')|Out-Null
    $start.Environment.Remove('LINK')|Out-Null;$start.Environment.Remove('_LINK_')|Out-Null
    $start.Environment['PATH']=$plan.CompilerDirectory+';'+[Environment]::GetFolderPath('System')
    $start.Environment['INCLUDE']=$plan.Include;$start.Environment['LIB']=$plan.Lib
    $start.Environment['TEMP']=$stageRoot;$start.Environment['TMP']=$stageRoot
    $arguments=if($Stage -ceq 'Compile'){@($plan.CompileArguments)}else{@($plan.FixtureRoot)}
    foreach($arg in $arguments){$start.ArgumentList.Add([string]$arg)}
    Invoke-H1OwnedStage $plan $state $context $start $imageHash $stageRoot $stageStarted
    if($Stage -ceq 'Compile') {
        $state.Artifacts=@(Get-H1CompilerArtifacts $plan $context)
        if($state.CompilerTelemetry.Completed) {
            foreach($previous in $state.CompilerTelemetry.Artifacts) {
                $current=@($state.Artifacts|Where-Object Path -CEQ $previous.Path)
                if($current.Count -ne 1 -or $current[0].Bytes -ne $previous.Bytes -or $current[0].SHA256 -cne $previous.SHA256){throw 'Compiler artifact changed across accepted job cleanup.'}
            }
        }
        $state.Executable=@($state.Artifacts|Where-Object Path -CEQ $plan.Executable)[0]
    }else{
        $state.Observation=Read-H1SmallJson (Join-Path $stageRoot 'stdout.log') 4096
        Assert-H1Observation $state.Observation
        $state.Executable=$prior.Executable
    }
    Assert-H1Deadline $stageStarted $budget.DeadlineSeconds
    $state.AcceptanceElapsedMs=(Get-H1Clock)-$stageStarted
    $state.Status='Passed'
}catch{
    $failure=$_
    if($state){$state.Status='Failed';$state.Error=$_.Exception.Message}
}finally{
    if($state){
        Complete-H1Stage $context $state
        if(!$state.LeaseReleased -and !$failure){$failure=[Exception]::new('Stage reservation remains quarantined.')}
    }
    if($launcher -and $null -ne $priority){
        try{$launcher.PriorityClass=$priority}catch{if(!$failure){$failure=$_};if($state){$state.Status='Failed';$state.PriorityRestoreError=$_.Exception.Message}}
    }
    if($state -and $outputCreated) {
        $state.FinishedUtc=[datetime]::UtcNow.ToString('o')
        try{Write-H1Receipt $plan $state $stageRoot}catch{if(!$failure){$failure=$_};Write-Warning ('Receipt publication failed: '+$_.Exception.Message)}
    }
    if($context.Closed -and !$context.Lease){foreach($guard in $guards){$guard.Dispose()};$guards.Clear()}
}
if($failure){throw $failure}
[ordered]@{Stage=$Stage;Status=$state.Status;Receipt=(Join-Path $stageRoot 'receipt.json');TreeClosureConfirmed=$state.TreeClosureConfirmed;LeaseReleased=$state.LeaseReleased}|ConvertTo-Json
