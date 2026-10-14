param([Parameter(Mandatory)][string]$PlanPath,[Parameter(Mandatory)][ValidatePattern('^[a-f0-9]{64}$')][string]$PlanSHA256,[switch]$Run)
$ErrorActionPreference='Stop'
$PlanPath=[IO.Path]::GetFullPath($PlanPath)
$earlyGuards=[Collections.Generic.List[IDisposable]]::new()
try {
$earlyGuards.Add([IO.File]::Open($PlanPath,'Open','Read','Read'))
if((Get-Item -LiteralPath $PlanPath).Length -gt 64KB -or (Get-FileHash -LiteralPath $PlanPath).Hash -ine $PlanSHA256){throw 'Hash-bound operator plan required.'}
$plan=[IO.File]::ReadAllText($PlanPath)|ConvertFrom-Json
$core=Join-Path $PSScriptRoot 'RigidControlWriter.Core.ps1'
$earlyGuards.Add([IO.File]::Open($core,'Open','Read','Read'))
$earlyGuards.Add([IO.File]::Open($PSCommandPath,'Open','Read','Read'))
if((Get-FileHash -LiteralPath $core).Hash -ine $plan.core_sha256 -or (Get-FileHash -LiteralPath $PSCommandPath).Hash -ine $plan.operator_sha256){throw 'Exact operator sources required.'}
. $core
$pins=Get-RCWProviderPins
foreach($name in $pins.Keys){
    $path=Join-Path $plan.source_package $name
    $earlyGuards.Add([IO.File]::Open($path,'Open','Read','Read'))
    if((Get-FileHash -LiteralPath $path).Hash -ine $pins[$name]){throw ('Provider changed: '+$name)}
}
foreach($name in 'ops/Base-Client.Core.ps1','sdk/modding/BeaconFF.Core.ps1','tools-source/asset-bridge/animation/AnimationFF.Core.ps1','tools-source/asset-bridge/animation/rig/Rig.Core.ps1','tools-source/asset-bridge/animation/rig/Rig.Compiler.ps1'){
    if($name -ne 'ops/Base-Client.Core.ps1'){ # All providers above are reviewed pure definitions.
        $errors=$null;$tokens=$null;$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $plan.source_package $name),[ref]$tokens,[ref]$errors)
        if($errors.Count -or @($ast.EndBlock.Statements|Where-Object {$_ -isnot [Management.Automation.Language.FunctionDefinitionAst]}).Count){throw 'Pure provider import required.'}
    }
    . (Join-Path $plan.source_package $name)
}
Assert-RCWPlan $plan
Assert-BeaconHash (Join-Path $plan.source_package 'source-workspace.json') $plan.source_package_manifest_sha256
Assert-BeaconHash (Join-Path $plan.prepared_source 'source-manifest.json') $plan.prepared_manifest_sha256
$sourceManifest=Read-BeaconJson (Join-Path $plan.prepared_source 'source-manifest.json')
if($sourceManifest.schema -cne 'iw7.original-rig-rigid-control-source-manifest/1' -or !$sourceManifest.source_only -or $sourceManifest.compiled -or $sourceManifest.ff_built){throw 'Exact source-only rigid control required.'}
$sourceFiles=@($sourceManifest.generated.PSObject.Properties)
if($sourceFiles.Count -ne 7){throw 'Exact seven generated source payloads required.'}
foreach($row in $sourceFiles){Assert-BeaconHash (Resolve-IW7BasePath $plan.prepared_source $row.Name) $row.Value.sha256}
$commands=Get-RCWCommands $plan;$policy=Get-RigCompilerPolicy $plan.compiler
function Assert-RCWNativeSource {
    $head=(& git -C $plan.native_source rev-parse HEAD).Trim()
    if($LASTEXITCODE -or $head -cne $plan.native_source_pin){throw 'Pinned native source required.'}
    $dirty=@(& git -C $plan.native_source status --porcelain --untracked-files=all)
    if($LASTEXITCODE -or $dirty.Count){throw 'Changed native source preserved; no compilation.'}
}
Assert-RCWNativeSource
if(!$Run){
    [ordered]@{Schema='iw7.original-rig-rigid-writer-default/1';PlanSHA256=$PlanSHA256;RunRoot=$plan.run_root;Commands=$commands;
        ExpectedWriters=@('retained/first/rigid-writer.exe','retained/second/rigid-writer.exe');CompilerClosure=$policy;
        NativeExecutableHashesRead=$false;NativeTypesLoaded=$false;LeaseAcquired=$false;ToolchainFrozen=$false;Compiled=$false;NativeWriterExecuted=$false;FFBuilt=$false;Ready=$false}|ConvertTo-Json -Depth 12
    foreach($guard in $earlyGuards){$guard.Dispose()};$earlyGuards.Clear()
    return
}
if([Environment]::GetCommandLineArgs() -inotcontains '-NoExit'){throw 'Run requires the original persistent pwsh -NoExit host.'}
if([AppDomain]::CurrentDomain.GetData('IW7.RigidControl.HostContext')){throw 'Existing host context must be recovered in its original host.'}
foreach($type in 'IW7.CommunityBuild.BuildJob','IW7.AnimationRig.JobMembers','IW7HudFileIdentity','IW7ResourceMemoryV1'){
    if($type -as [type]){throw 'Fresh source-bound operator host required.'}
}
}catch{foreach($guard in $earlyGuards){$guard.Dispose()};throw}
$state=[ordered]@{Schema='iw7.original-rig-rigid-writer-run/1';HostPID=$PID;PlanSHA256=$PlanSHA256;RunRoot=$plan.run_root;
    Status='Preparing';Failure=$null;CleanupError=$null;RetainedLeaseToken=$null;LeaseReleased=$false;Phases=@();Writers=@();
    SourceInputsUnchanged=$false;Restored=$false;Compiled=$false;NativeWriterExecuted=$false;FFBuilt=$false;GPUVerified=$false;PixelsVerified=$false;Ready=$false}
$context=[ordered]@{Plan=$plan;Policy=$policy;State=$state;Owner=$null;Closed=$true;Lease=$null;Saved=$false;Transaction=$null;SourceIntact=$false;
    Guards=$earlyGuards;Baselines=[Collections.Generic.List[object]]::new();Created=$false;Save={Save-RCWState}}
[AppDomain]::CurrentDomain.SetData('IW7.RigidControl.HostContext',$context)
$clock=[Diagnostics.Stopwatch]::StartNew();$statePath=Join-Path $plan.run_root 'state.local.json'
function Save-RCWState {if($context.Created){Write-RigJson $state $statePath}}
function Assert-RCWBudget {
    if($clock.Elapsed.TotalSeconds -gt 600 -or (Test-Path -LiteralPath (Join-Path $plan.run_root 'stop.request'))){throw 'Owned compile group stopped or expired.'}
    $bytes=[long]((Get-ChildItem -LiteralPath $plan.run_root -Recurse -File -Force|Measure-Object Length -Sum).Sum)
    if($bytes -gt 128MB){throw 'Bounded compiler output exceeded 128MiB.'}
}
function Assert-RCWSources {
    Assert-RCWNativeSource
    Assert-RigBaselines $context.Baselines -Hashes
    if($toolchain){Assert-RigToolchainInventory $toolchain $commands.FreezeRoots}
}
$toolchain=$null
try {
    # The registry and every original handle live in this persistent host.
    . (Join-Path $plan.source_package 'ops/Resource-Scheduler.Core.ps1')
    $context.Lease=Enter-IW7ResourceLease -Scope $plan.run_root -Kind Build -PhysicalBytes 2GB -CommitBytes 3GB -Owner 'Original ribbon rigid two-writer compilation'
    $state.RetainedLeaseToken=$context.Lease.Token
    [IO.Directory]::CreateDirectory((Split-Path $plan.run_root))|Out-Null
    New-Item -ItemType Directory -Path $plan.run_root -ErrorAction Stop|Out-Null
    $context.Created=$true;Save-RCWState
    Assert-BeaconHash $plan.compiler $policy.CompilerSHA256
    Assert-BeaconHash $policy.Telemetry $policy.TelemetrySHA256
    Assert-BeaconHash $plan.python $plan.python_sha256
    Add-Type -LiteralPath (Join-Path $plan.source_package 'tools-source/asset-bridge/model/BuildJob.cs')
    Add-Type -LiteralPath (Join-Path $plan.source_package 'ops/hud-lab/HudFileIdentity.cs')
    Add-Type -LiteralPath (Join-Path $plan.source_package 'tools-source/asset-bridge/animation/rig/Rig.JobMembers.cs')
    $inputPins=[ordered]@{}
    $inputPins[$PlanPath]=$PlanSHA256;$inputPins[$core]=$plan.core_sha256;$inputPins[$PSCommandPath]=$plan.operator_sha256
    $inputPins[$plan.python]=$plan.python_sha256;$inputPins[$plan.compiler]=$plan.compiler_sha256;$inputPins[$policy.Telemetry]=$policy.TelemetrySHA256
    foreach($name in $pins.Keys){$inputPins[(Join-Path $plan.source_package $name)]=$pins[$name]}
    $inputPins[(Join-Path $plan.source_package 'source-workspace.json')]=$plan.source_package_manifest_sha256
    $inputPins[(Join-Path $plan.prepared_source 'source-manifest.json')]=$plan.prepared_manifest_sha256
    foreach($row in $sourceFiles){$inputPins[(Resolve-IW7BasePath $plan.prepared_source $row.Name)]=$row.Value.sha256}
    foreach($p in $inputPins.Keys){Add-RigGuard $p $inputPins[$p] $context.Guards $context.Baselines}
    $toolchain=@(Get-RigToolchainInventory $commands.FreezeRoots)
    foreach($item in $toolchain){Add-RigGuard $item.Path $null $context.Guards $context.Baselines;Assert-RCWBudget}
    Assert-RigToolchainInventory $toolchain $commands.FreezeRoots
    Write-RigNewJson @($context.Baselines) (Join-Path $plan.run_root 'input-freeze.local.json')
    $source=Join-Path $plan.run_root 'source';[IO.Directory]::CreateDirectory($source)|Out-Null
    foreach($row in $sourceFiles){
        $dest=Resolve-IW7BasePath $source $row.Name;[IO.Directory]::CreateDirectory((Split-Path $dest))|Out-Null
        Copy-Item -LiteralPath (Resolve-IW7BasePath $plan.prepared_source $row.Name) -Destination $dest
        Add-RigGuard $dest $row.Value.sha256 $context.Guards $context.Baselines
    }
    $build=Join-Path $plan.run_root 'build';[IO.Directory]::CreateDirectory($build)|Out-Null
    $transactionPlan=[pscustomobject]@{GameRoot=$build;MutableFiles=@('first/rigid-writer.exe','first/writer.obj','first/writer.pdb','second/rigid-writer.exe','second/writer.obj','second/writer.pdb');ProfileDirectory='unused';ProfileDirectories=@('first','second','tmp')}
    $context.Transaction=Save-IW7BaseTransaction $transactionPlan (Join-Path $plan.run_root 'backup');$context.Saved=$true
    foreach($dir in 'first','second','tmp'){[IO.Directory]::CreateDirectory((Resolve-IW7BasePath $build $dir))|Out-Null}
    [IO.Directory]::CreateDirectory((Join-Path $plan.run_root 'logs'))|Out-Null
    foreach($phase in $commands.Phases){
        Assert-RCWSources;Assert-RCWBudget
        $specPath=Join-Path $plan.run_root ('compile-'+$phase.Profile+'.spec.json');Write-RigNewJson $phase.Spec $specPath
        $specSHA=(Get-FileHash -LiteralPath $specPath).Hash;Add-RigGuard $specPath $specSHA $context.Guards $context.Baselines
        $state.Status='Compiling-'+$phase.Profile;Save-RCWState
        Invoke-RCWPhase $context $phase $specPath $specSHA {Assert-RCWBudget}
        Assert-RCWSources
        $outputs=@(foreach($file in 'rigid-writer.exe','writer.obj','writer.pdb'){
            $src=Resolve-IW7BasePath $build ($phase.Profile+'/'+$file)
            if($file -eq 'writer.pdb' -and !(Test-Path -LiteralPath $src)){continue}
            Assert-RigArtifact $src 32MB
            $dst=Resolve-IW7BasePath (Join-Path $plan.run_root 'retained') ($phase.Profile+'/'+$file)
            [IO.Directory]::CreateDirectory((Split-Path $dst))|Out-Null
            $hash=(Get-FileHash -LiteralPath $src).Hash;Copy-Item -LiteralPath $src -Destination $dst
            Add-RigGuard $dst $hash $context.Guards $context.Baselines
            [ordered]@{Path=$dst;Bytes=(Get-Item -LiteralPath $dst).Length;SHA256=$hash}
        })
        $state.Writers+=,[ordered]@{Profile=$phase.Profile;Files=$outputs};Save-RCWState
    }
    Assert-RCWSources;Assert-RCWBudget
    $state.Compiled=$true;$state.Status='Compiled';Save-RCWState
} catch {$state.Failure=$_.Exception.Message;$state.Status='Failed';throw}
finally {
    if($context.Owner){
        $state['StopEvidence']=[ordered]@{};$context.Closed=Stop-RigOwnedPhase $context.Owner $state.StopEvidence
        if($context.Closed){$context.Owner.Dispose();$context.Owner=$null}
    }
    try{Assert-RCWSources;$context.SourceIntact=$true;$state.SourceInputsUnchanged=$true}catch{$state.CleanupError=$_.Exception.Message}
    try{
        if(Complete-RCWContext $context){
            $state.Status=if($state.Compiled -and !$state.Failure){'CompilePassedRestored'}else{'FailedRestored'}
            [AppDomain]::CurrentDomain.SetData('IW7.RigidControl.HostContext',$null)
        }else{$state.CleanupError='Closure/source proof incomplete; original host context, guards and lease retained.'}
    }catch{$state.CleanupError=$_.Exception.Message}
    Save-RCWState
}
if($context.Lease -or !$state.Restored -or !$state.Compiled){throw 'Compilation or cleanup incomplete; inspect original host context.'}
$state|ConvertTo-Json -Depth 15
