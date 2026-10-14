# Specialized six-stage caller of existing H1 ownership and T7 artifact/link policies.
# Default reads only bounded source/metadata. No tool/game/export entry exists.
[CmdletBinding()]
param([Parameter(Mandatory)][string]$PlanPath,[Parameter(Mandatory)][string]$PlanSHA256,[switch]$Run)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
function Read-PlayerSource([string]$Path,[string]$SHA256,[long]$Bytes=-1) {
    if($SHA256 -cnotmatch '^[0-9a-f]{64}$' -or ![IO.Path]::IsPathFullyQualified($Path)){throw 'Exact source binding required.'}
    for($part=$Path;$part;$part=[IO.Path]::GetDirectoryName($part)){
        if((Get-Item -LiteralPath $part).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Linked source ancestry refused.'}
    }
    $stream=[IO.FileStream]::new($Path,'Open','Read','Read')
    try{
        if($stream.Length -gt 2MB -or ($Bytes -ge 0 -and $stream.Length -ne $Bytes)){throw 'Source size differs.'}
        $buffer=[byte[]]::new(2MB+1);$used=0
        do{$count=$stream.Read($buffer,$used,$buffer.Length-$used);$used+=$count}while($count -gt 0 -and $used -lt $buffer.Length)
        if($used -gt 2MB){throw 'Source grew above cap before hash/decode.'}
        $raw=[byte[]]::new($used);[Array]::Copy($buffer,$raw,$used)
        if([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($raw)).ToLowerInvariant() -cne $SHA256){throw 'Source hash differs.'}
        [Text.Encoding]::UTF8.GetString($raw)
    }finally{$stream.Dispose()}
}
$plan=Read-PlayerSource $PlanPath $PlanSHA256 | ConvertFrom-Json -Depth 30
if(!$plan.PSObject.Properties['RunnerBinding'] -or $plan.RunnerBinding.Path -cne $PSCommandPath){throw 'Exact specialized runner binding required.'}
$null=Read-PlayerSource $plan.RunnerBinding.Path $plan.RunnerBinding.SHA256 $plan.RunnerBinding.Bytes
if($plan.Schema -cne 'iw7.player-template-cohort-source/1' -or $plan.Ready -or $plan.CandidateExecuted -or
   $plan.WeaponReady -or $plan.PhysicsQualified -or $plan.PAPTransactionQualified -or
   $plan.RetainedObjects -ne 412 -or $plan.LinkedObjectCount -ne 413){throw 'Exact unqualified source cohort required.'}
$names=@('name-compile','name-test','argv-compile','argv-test','iw7','link')
if((@($plan.Stages.Name)-join '|') -cne ($names-join '|') -or $plan.Stages[1].ExpectedChecks -ne 8 -or $plan.Stages[3].ExpectedChecks -ne 10){throw 'Fixed six-stage/8+10 sequence required.'}
if($plan.GroupDeadlineSeconds -ne 600 -or $plan.OutputLimitBytes -ne 268435456 -or $plan.MetadataReserveBytes -ne 1048576){throw 'Fixed cohort deadline/output reserve required.'}
$kinds=@('Compile','Probe','Compile','Probe','Compile','Link')
$artifacts=@('name.obj|name.exe|name.pdb|compile.pdb|dependencies.json','','argv.obj|argv.exe|argv.pdb|compile.pdb|dependencies.json','','iw7-player-cli.obj|compile.pdb|dependencies.json','zonetool-iw7-player.exe|zonetool-iw7-player.pdb|zonetool-iw7-player.lib|zonetool-iw7-player.exp')
for($index=0;$index -lt 6;$index++){
    $stage=$plan.Stages[$index];$probe=$kinds[$index] -ceq 'Probe'
    if($stage.Stage -cne $kinds[$index] -or $stage.DeadlineSeconds -ne $(if($probe){15}else{120}) -or
       (@($stage.Artifacts)-join '|') -cne $artifacts[$index]){throw 'Fixed cohort phase/artifacts required.'}
    if($probe){
        $fixture=if($index -eq 1){'name'}else{'argv'}
        $expected=if($index -eq 1){"IW7_PLAYER_TEMPLATE_NAME_CHECKS=8`n"}else{"IW7_PLAYER_TEMPLATE_ARGV_CHECKS=10`n"}
        if($stage.Image -cne (Join-Path (Join-Path $plan.RunRoot "$fixture-compile") "$fixture.exe") -or @($stage.Arguments).Count -ne 0 -or
           $stage.ExpectedStdout -cne $expected){throw 'Fixed cohort probe image/marker required.'}
    }else{
        $rsp=if($index -eq 0){'name'}elseif($index -eq 2){'argv'}else{$stage.Name}
        $image=if($index -eq 5){Join-Path (Split-Path $plan.Compiler -Parent) 'link.exe'}else{$plan.Compiler}
        if($stage.Image -cne $image -or @($stage.Arguments).Count -ne 1 -or $stage.Arguments[0] -cne ('@'+(Join-Path $plan.PreparedRoot "$rsp.rsp"))){throw 'Fixed cohort compiler/link response required.'}
    }
}
if(!$plan.PSObject.Properties['OwnDirectIncludeCoverage'] -or @($plan.OwnDirectIncludeCoverage).Count -lt 1 -or
   @($plan.OwnDirectIncludeCoverage|Where-Object {-not $_.Pinned}).Count -gt 0 -or !$plan.RequireActualDependenciesWithinGuardedSet){throw 'Own IW7 source coverage and future exact dependency guard required.'}
foreach($pin in @($plan.SourceBindings)+@($plan.PreparedBindings)){$null=Read-PlayerSource $pin.Path $pin.SHA256 $pin.Bytes}
$providers=$plan.Providers
$providerPins=@(foreach($name in 'Core','CompilerCore','ObserverSource','CompilerPolicySource','Scheduler','Profile'){
    $pin=@($plan.ParentBindings|Where-Object {$_.Path -ieq $providers.$name -and $_.IsText})
    if($pin.Count -ne 1){throw 'One pinned existing source provider required.'}
    $null=Read-PlayerSource $pin[0].Path $pin[0].SHA256 $pin[0].Bytes;$pin[0]
})
if(Test-Path -LiteralPath $plan.RunRoot){throw 'Fresh owned runtime output required.'}
if(!$Run){
    [ordered]@{Schema='iw7.player-template-build-default/1';PlanSHA256=$PlanSHA256;Stages=6;NameChecksAuthored=8;ArgvChecksAuthored=10;
        NativeTypesLoaded=$false;NativeInputsHashed=$false;RunRootCreated=$false;LeaseAcquired=$false;Ready=$false}|ConvertTo-Json
    return
}
# The physical NoExit/dot host is checked before imports, admission or native IO.
$hostArgs=[Environment]::GetCommandLineArgs()
$commandIndex=[Array]::IndexOf($hostArgs,'-Command')
if('-NoExit' -cnotin $hostArgs -or $commandIndex -lt 0 -or $commandIndex+1 -ge $hostArgs.Length -or
   $hostArgs[$commandIndex+1] -notmatch '^\s*\.\s+' -or $MyInvocation.InvocationName -cne '.'){
    throw 'Fresh physical NoExit host with dot invocation required.'
}
$physical=Get-CimInstance Win32_Process -Filter "ProcessId=$PID"
if(!$physical -or !$physical.ExecutablePath -or !$physical.CreationDate -or $physical.CommandLine -notmatch '(?i)-NoExit\b'){
    throw 'Actual original host identity/NoExit unavailable.'
}
if(('IW7.AnimationProbe.NativeJob' -as [type]) -or ('IW7.H1Diagnostics.JobMembers' -as [type])){throw 'Fresh host required.'}
$guards=[Collections.Generic.List[object]]::new()
$context=[pscustomobject]@{Owner=$null;Closed=$true;Lease=$null;Guards=$guards}
$state=[ordered]@{Schema='iw7.player-template-build/1';PlanSHA256=$PlanSHA256;Status='Pending';Stages=[Collections.Generic.List[object]]::new();
    MaxObservedOutputBytes=0L;NativeInputsReverified=$false;MeasuredReadback=$false;FinalReadback=$false;LeaseReleased=$false;GuardsDisposed=$false;CanExit=$false;Ready=$false;
    Host=[ordered]@{PID=$PID;Image=$physical.ExecutablePath;CreatedUtc=$physical.CreationDate.ToUniversalTime().ToString('o');NoExit=$true;Dot=$true}}
$global:IW7PlayerTemplateBuild=[pscustomobject]@{Context=$context;State=$state;Plan=$plan;Guards=$guards}
$failure=$null;$created=$false
try{
    . $providers.Core
    . $providers.Scheduler
    $context.Lease=Enter-IW7ResourceLease -Scope $plan.RunRoot -Kind Build -PhysicalBytes 4GB -CommitBytes 6GB -Owner 'IW7 one-TU player template CLI and 8+10 fixtures'
    $state.LeaseToken=$context.Lease.Token;$script:T7GroupStarted=Get-H1Clock
    # Keep all providers and source bindings guarded before loading their types.
    foreach($pin in @($plan.SourceBindings)+@($plan.PreparedBindings)+$providerPins+@($plan.RunnerBinding)){$guards.Add((Open-H1Pin $pin))}
    . $providers.CompilerCore
    . $providers.CompilerPolicySource
    . $providers.Profile
    foreach($pin in $plan.RetainedInputPins){Open-T7Pin $pin $context}
    foreach($pin in @($plan.ParentBindings|Where-Object {-not $_.IsText})){Open-T7Pin $pin $context}
    $assembly=@($plan.ParentBindings|Where-Object Path -IEQ $plan.JobAssembly)
    if($assembly.Count -ne 1){throw 'Exact original-job assembly binding required.'}
    Open-T7Pin $assembly[0] $context
    [Reflection.Assembly]::LoadFrom($plan.JobAssembly)|Out-Null
    Add-Type -LiteralPath $providers.ObserverSource
    [IO.Directory]::CreateDirectory($plan.RunRoot)|Out-Null;$created=$true
    # H1 compiler consumers use the existing provider fields; no API is changed.
    $plan|Add-Member NoteProperty ObserverSource $providers.ObserverSource -Force
    $plan|Add-Member NoteProperty CompilerPolicySource $providers.CompilerPolicySource -Force
    $plan|Add-Member NoteProperty Bindings (@($plan.ParentBindings)+@($plan.SourceBindings)+@($plan.PreparedBindings)) -Force
    $plan|Add-Member NoteProperty Inputs @($plan.RetainedInputPins) -Force
    foreach($stage in $plan.Stages){
        if(!$context.Closed){throw 'Previous original job must be closed.'}
        # A failed new factory cannot inherit a prior closed owner's evidence.
        $context.Owner=$null
        $script:T7CurrentStage=$stage;$stageRoot=Join-Path $plan.RunRoot $stage.Name
        [IO.Directory]::CreateDirectory($stageRoot)|Out-Null
        $current=[ordered]@{Name=$stage.Name;Stage=$stage.Stage;DeadlineSeconds=$stage.DeadlineSeconds;TreeClosureConfirmed=$false;
            MaxObservedOutputBytes=$state.MaxObservedOutputBytes;CompilerTelemetry=[ordered]@{Completed=$false;Action=$null}}
        $state.Stages.Add($current)
        $image=if($stage.Stage -ceq 'Probe'){
            $compile=@($state.Stages|Where-Object Name -CEQ ($stage.Name.Replace('-test','-compile')))[0]
            @($compile.Artifacts|Where-Object Path -IEQ $stage.Image)[0]
        }else{@($plan.Bindings|Where-Object Path -IEQ $stage.Image)[0]}
        if(!$image){throw 'One original stage image pin required.'}
        $start=New-T7Start $plan $stage $stageRoot
        Invoke-T7OwnedStage $plan $current $context $start $image.SHA256 $stageRoot (Get-H1Clock)
        $current.Artifacts=@(Get-H1CompilerArtifacts $plan $context)
        if($stage.Stage -ceq 'Compile'){Assert-T7Dependencies $plan $stageRoot}
        if($stage.Stage -ceq 'Probe'){
            $stdout=Join-Path $stageRoot 'stdout.log';$stderr=Join-Path $stageRoot 'stderr.log'
            if((Get-Item -LiteralPath $stdout).Length -gt 128 -or (Get-Item -LiteralPath $stderr).Length -ne 0 -or
               [IO.File]::ReadAllText($stdout).Replace("`r`n","`n") -cne $stage.ExpectedStdout){throw 'Exact 8/10 native fixture evidence required.'}
            $current.Checks=$stage.ExpectedChecks
        }
        $state.MaxObservedOutputBytes=[math]::Max($state.MaxObservedOutputBytes,$current.MaxObservedOutputBytes)
    }
    foreach($pin in $plan.RetainedInputPins){Open-T7Pin $pin $context}
    foreach($pin in @($plan.SourceBindings)+@($plan.PreparedBindings)+$providerPins){$null=Read-PlayerSource $pin.Path $pin.SHA256 $pin.Bytes}
    $state.NativeInputsReverified=$true;$state.Status='MeasuredPassed'
}catch{$failure=$_;$state.Status='Failed';$state.Error=$_.Exception.Message}
finally{
    if(!$context.Closed -and $context.Owner){try{$context.Owner.StopAndConfirm(5000);$context.Closed=$context.Owner.Closed}catch{$state.ClosureError=$_.Exception.Message}}
    if($created -and $context.Closed -and $context.Lease){
        try{
            $measured=Join-Path $plan.RunRoot 'measured-before-release.json'
            $raw=[Text.UTF8Encoding]::new($false).GetBytes(($state|ConvertTo-Json -Depth 20)+"`n")
            if($raw.Length -gt $plan.MetadataReserveBytes -or (Measure-H1Output $plan.RunRoot)+$raw.Length -gt $plan.OutputLimitBytes){throw 'Measured receipt exceeds reserved total output.'}
            $stream=[IO.File]::Open($measured,'CreateNew','Write','Read')
            try{$stream.Write($raw);$stream.Flush($true)}finally{$stream.Dispose()}
            $hash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($raw)).ToLowerInvariant()
            $null=Read-PlayerSource $measured $hash $raw.Length;$state.MeasuredReadback=$true
            # This verified closure tuple exists while the exact guards and lease
            # are still retained. Failed publication/readback cannot release them.
            $before=[ordered]@{Schema='iw7.player-template-build-before-release/1';PlanSHA256=$PlanSHA256;MeasuredSHA256=$hash;
                Host=$state.Host;Status=$state.Status;OriginalRootAndJobClosed=$true;LeaseToken=$context.Lease.Token;
                GuardsHeld=$guards.Count;CandidateExecuted=$false;Ready=$false}
            $beforeFile=Join-Path $plan.RunRoot 'closure-before-release.json'
            $beforeBytes=[Text.UTF8Encoding]::new($false).GetBytes(($before|ConvertTo-Json -Depth 10)+"`n")
            if((Measure-H1Output $plan.RunRoot)+$beforeBytes.Length -gt $plan.OutputLimitBytes){throw 'Closure output budget exceeded before release.'}
            $stream=[IO.File]::Open($beforeFile,'CreateNew','Write','Read')
            try{$stream.Write($beforeBytes);$stream.Flush($true)}finally{$stream.Dispose()}
            $beforeHash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($beforeBytes)).ToLowerInvariant()
            $null=Read-PlayerSource $beforeFile $beforeHash $beforeBytes.Length
            Exit-IW7ResourceLease -Token $context.Lease.Token;$context.Lease=$null;$state.LeaseReleased=$true
            foreach($guard in $guards){$guard.Dispose()};$guards.Clear();$state.GuardsDisposed=$true
            $state.Status=if($failure){'FailedClosed'}else{'Passed'}
            $closure=[ordered]@{Schema='iw7.player-template-build-closure/1';PlanSHA256=$PlanSHA256;MeasuredSHA256=$hash;
                BeforeReleaseSHA256=$beforeHash;Host=$state.Host;Status=$state.Status;OriginalRootAndJobClosed=$true;LeaseReleased=$true;GuardsDisposed=$true;CandidateExecuted=$false;Ready=$false}
            $final=Join-Path $plan.RunRoot 'final-closure.json';$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($closure|ConvertTo-Json -Depth 10)+"`n")
            if($raw.Length+$beforeBytes.Length+$bytes.Length -gt $plan.MetadataReserveBytes -or
               (Measure-H1Output $plan.RunRoot)+$bytes.Length -gt $plan.OutputLimitBytes){throw 'Final closure exceeds reserved output.'}
            $stream=[IO.File]::Open($final,'CreateNew','Write','Read')
            try{$stream.Write($bytes);$stream.Flush($true)}finally{$stream.Dispose()}
            $finalHash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant()
            $null=Read-PlayerSource $final $finalHash $bytes.Length;$state.FinalReadback=$true;$state.CanExit=$true
        }catch{$state.FinalizationError=$_.Exception.Message;if(!$failure){$failure=$_}}
    }
    if(!$state.CanExit){
        $state.Status=if($context.Closed -and $state.LeaseReleased){'ClosedFinalizationIncomplete'}else{'UnknownRetained'}
        $state.CanExit=$false
    }
    $state|ConvertTo-Json -Depth 20
}
if($failure){throw $failure}
